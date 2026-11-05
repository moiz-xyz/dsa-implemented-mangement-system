"""Booking, waiting-list and history models."""

import json
from dataclasses import dataclass, field


@dataclass
class Booking:
    booking_id: str
    passenger_id: int
    bus_id: int
    seat_number: int
    from_city: str
    to_city: str
    amount: float
    status: str
    booking_date: str
    travel_date: str
    passenger_name: str
    bus_label: str
    route_name: str = ""
    cancelled_at: str = None
    cancel_reason: str = None

    @classmethod
    def from_row(cls, row):
        return cls(**{k: row.get(k) for k in cls.__dataclass_fields__})

    @property
    def seat_label(self):
        return str(self.seat_number) if self.seat_number else "—"


@dataclass
class WaitingEntry:
    """One person waiting in a bus's FIFO queue."""
    waiting_id: int
    booking_id: str
    passenger_id: int
    bus_id: int
    request_date: str
    passenger_name: str = ""
    status: str = "Waiting"

    @classmethod
    def from_row(cls, row):
        return cls(waiting_id=row["waiting_id"], booking_id=row["booking_id"],
                   passenger_id=row["passenger_id"], bus_id=row["bus_id"],
                   request_date=row["request_date"],
                   passenger_name=row.get("passenger_name") or "",
                   status=row.get("status") or "Waiting")


@dataclass
class HistoryEntry:
    """
    A reversible operation stored on the undo Stack.

    `details` contains everything needed to reverse the action, e.g. for a
    cancellation: the booking ID, the seat that was released and which
    waiting passenger (if any) received that seat.
    """
    history_id: int
    user_id: int
    action: str
    booking_id: str
    details: dict = field(default_factory=dict)
    created_at: str = ""

    @classmethod
    def from_row(cls, row):
        try:
            details = json.loads(row.get("details") or "{}")
        except (TypeError, ValueError):
            details = {}
        return cls(history_id=row["history_id"], user_id=row["user_id"],
                   action=row["action"], booking_id=row["booking_id"],
                   details=details, created_at=row["created_at"])

    def describe(self):
        d = self.details
        if self.action == "BOOK":
            ids = d.get("booking_ids", [self.booking_id])
            seats = ", ".join(str(s) for s in d.get("seats", []))
            return f"Booked seat(s) {seats} on {d.get('bus_label', 'bus')} ({', '.join(ids)})"
        if self.action == "CANCEL":
            return f"Cancelled booking {self.booking_id}"
        if self.action == "CHANGE":
            return (f"Changed {self.booking_id} from seat {d.get('old_seat')} "
                    f"to seat {d.get('new_seat')}")
        if self.action == "WAITLIST":
            return f"Joined waiting list for {d.get('bus_label', 'bus')} ({self.booking_id})"
        return f"{self.action} {self.booking_id or ''}"
