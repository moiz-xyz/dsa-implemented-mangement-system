"""Bus model."""

from dataclasses import dataclass

from utils.constants import SEAT_COLUMNS, DEFAULT_SEAT_COLUMNS
from utils.helpers import time_to_minutes


@dataclass
class Bus:
    bus_id: int
    bus_name: str
    bus_number: str
    bus_type: str
    total_seats: int
    ticket_price: float
    route_id: int
    departure_time: str
    arrival_time: str
    travel_date: str
    status: str
    route_name: str = ""
    # filled in by services (not stored in the buses table)
    booked_seats: int = 0
    waiting_count: int = 0
    segment_distance: float = 0.0     # km between searched cities (bus search)

    @classmethod
    def from_row(cls, row):
        return cls(
            bus_id=row["bus_id"], bus_name=row["bus_name"], bus_number=row["bus_number"],
            bus_type=row["bus_type"], total_seats=row["total_seats"],
            ticket_price=row["ticket_price"], route_id=row["route_id"],
            departure_time=row["departure_time"], arrival_time=row["arrival_time"],
            travel_date=row["travel_date"], status=row["status"],
            route_name=row.get("route_name", "") or "",
        )

    @property
    def seat_columns(self):
        return SEAT_COLUMNS.get(self.bus_type, DEFAULT_SEAT_COLUMNS)

    @property
    def available_seats(self):
        return max(self.total_seats - self.booked_seats, 0)

    @property
    def label(self):
        return f"{self.bus_name} ({self.bus_number})"

    @property
    def departure_minutes(self):
        """Departure time as minutes after midnight – numeric sort key."""
        return time_to_minutes(self.departure_time)

    @property
    def departure_key(self):
        """Sort key combining date and time, e.g. '2026-11-05 07:00'."""
        return f"{self.travel_date} {self.departure_time}"

    @property
    def occupancy_percent(self):
        return 0 if self.total_seats == 0 else round(100 * self.booked_seats / self.total_seats)
