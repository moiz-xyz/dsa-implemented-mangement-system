"""Passenger model."""

from dataclasses import dataclass


@dataclass
class Passenger:
    passenger_id: int
    user_id: int
    full_name: str
    email: str
    phone: str
    registration_date: str
    total_bookings: int = 0

    @classmethod
    def from_row(cls, row):
        return cls(
            passenger_id=row["passenger_id"], user_id=row["user_id"],
            full_name=row["full_name"], email=row["email"], phone=row["phone"],
            registration_date=row["registration_date"],
            total_bookings=row.get("total_bookings", 0) or 0,
        )

    @property
    def name_key(self):
        """Case-insensitive key used for alphabetical sorting / binary search."""
        return self.full_name.lower()
