"""
Passenger service – registration, profile edits, safe deletion, search and
sorting (alphabetical sorting uses our own sorting algorithms; exact email
lookup uses binary search on the sorted list).
"""

import sqlite3

from algorithms.searching import binary_search, linear_search, linear_search_all
from algorithms.sorting import sort_items, DEFAULT_ALGORITHM
from models.passenger import Passenger
from utils import validators
from utils.constants import ROLE_PASSENGER
from utils.exceptions import BookingError, NotFoundError, ValidationError
from utils.helpers import now_str

PASSENGER_SORT_KEYS = {
    "Name (A → Z)": (lambda p: p.name_key, False),
    "Name (Z → A)": (lambda p: p.name_key, True),
    "Newest registration": (lambda p: p.registration_date, True),
    "Oldest registration": (lambda p: p.registration_date, False),
    "Most bookings": (lambda p: p.total_bookings, True),
}

_SELECT = ("SELECT p.*, (SELECT COUNT(*) FROM bookings b WHERE b.passenger_id = p.passenger_id) "
           "AS total_bookings FROM passengers p")


class PassengerService:
    def __init__(self, db, auth_service):
        self.db = db
        self.auth = auth_service

    def all_passengers(self):
        return [Passenger.from_row(r) for r in self.db.query(_SELECT + " ORDER BY passenger_id")]

    def get(self, passenger_id):
        row = self.db.query_one(_SELECT + " WHERE p.passenger_id = ?", (passenger_id,))
        if row is None:
            raise NotFoundError("Passenger not found.")
        return Passenger.from_row(row)

    def list_passengers(self, query="", sort_by="Name (A → Z)", algorithm=DEFAULT_ALGORITHM,
                        stats=None):
        passengers = self.all_passengers()
        if query:
            q = query.strip().lower()
            passengers = linear_search_all(
                passengers, lambda p: q in p.full_name.lower() or q in p.email.lower()
                or q in p.phone)
        if sort_by in PASSENGER_SORT_KEYS:
            key, desc = PASSENGER_SORT_KEYS[sort_by]
            passengers = sort_items(passengers, key=key, reverse=desc, algorithm=algorithm,
                                    stats=stats)
        return passengers

    def find_by_email(self, email):
        """Binary search by email on the list sorted with merge sort."""
        ordered = sort_items(self.all_passengers(), key=lambda p: p.email.lower(),
                             algorithm="Merge Sort")
        result = binary_search(ordered, email.strip().lower(), key=lambda p: p.email.lower())
        return (ordered[result.index] if result.found else None), result.comparisons

    def find_by_id_linear(self, passenger_id):
        passengers = self.all_passengers()
        result = linear_search(passengers, passenger_id, key=lambda p: p.passenger_id)
        return (passengers[result.index] if result.found else None), result.comparisons

    # ------------------------------------------------------------ mutations
    def register(self, full_name, email, phone, password, confirm=None):
        full_name = validators.validate_name(full_name)
        email = validators.validate_email(email)
        phone = validators.validate_phone(phone)
        validators.validate_password(password)
        if confirm is not None and confirm != password:
            raise ValidationError("Passwords do not match.")
        try:
            with self.db.transaction():
                user_id = self.auth.create_user(email, password, ROLE_PASSENGER)
                cur = self.db.execute(
                    "INSERT INTO passengers (user_id, full_name, email, phone, registration_date) "
                    "VALUES (?, ?, ?, ?, ?)", (user_id, full_name, email, phone, now_str()))
        except sqlite3.IntegrityError:
            raise ValidationError(f"An account with email {email} already exists.") from None
        return self.get(cur.lastrowid)

    def update(self, passenger_id, full_name, email, phone):
        passenger = self.get(passenger_id)
        full_name = validators.validate_name(full_name)
        email = validators.validate_email(email)
        phone = validators.validate_phone(phone)
        try:
            with self.db.transaction():
                self.db.execute("UPDATE passengers SET full_name=?, email=?, phone=? "
                                "WHERE passenger_id=?", (full_name, email, phone, passenger_id))
                self.db.execute("UPDATE users SET username=? WHERE user_id=?",
                                (email, passenger.user_id))
                self.db.execute("UPDATE bookings SET passenger_name=? WHERE passenger_id=?",
                                (full_name, passenger_id))
        except sqlite3.IntegrityError:
            raise ValidationError(f"Email {email} is already used by another account.") from None
        return self.get(passenger_id)

    def active_booking_count(self, passenger_id):
        return self.db.query_value(
            "SELECT COUNT(*) FROM bookings WHERE passenger_id = ? "
            "AND status IN ('Confirmed','Waiting')", (passenger_id,), 0)

    def delete(self, passenger_id):
        """
        Safe delete: refused while the passenger has confirmed or waiting
        bookings. Past bookings are kept for reports (passenger_id becomes NULL
        but the passenger_name snapshot remains).
        """
        passenger = self.get(passenger_id)
        active = self.active_booking_count(passenger_id)
        if active:
            raise BookingError(f"{passenger.full_name} has {active} active booking(s). "
                               "Cancel them before deleting the passenger.")
        with self.db.transaction():
            self.db.execute("DELETE FROM users WHERE user_id = ?", (passenger.user_id,))
        return passenger
