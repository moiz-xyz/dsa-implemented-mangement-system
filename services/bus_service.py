"""
Bus service – CRUD, searching and sorting of buses.

Sorting uses our own algorithms (algorithms.sorting) and searching uses
our own linear / binary search (algorithms.searching). SQL is only used to
load and save rows.
"""

import sqlite3
from datetime import date

from algorithms.searching import binary_search, linear_search_all
from algorithms.sorting import sort_items, DEFAULT_ALGORITHM
from models.bus import Bus
from utils import validators
from utils.constants import BUS_STATUSES, BUS_TYPES, DATE_FMT
from utils.exceptions import BookingError, NotFoundError, ValidationError
from utils.helpers import now_str, time_to_minutes

# Sort options offered in the UI: label -> (key function, descending?)
BUS_SORT_KEYS = {
    "Ticket price (low → high)": (lambda b: b.ticket_price, False),
    "Ticket price (high → low)": (lambda b: b.ticket_price, True),
    "Departure (earliest)": (lambda b: b.departure_key, False),
    "Departure time of day": (lambda b: b.departure_minutes, False),
    "Available seats (most)": (lambda b: b.available_seats, True),
    "Bus name (A → Z)": (lambda b: b.bus_name.lower(), False),
    "Bus number": (lambda b: b.bus_number, False),
}

SEARCH_SORT_KEYS = {
    "Cheapest first": (lambda b: b.ticket_price, False),
    "Earliest departure": (lambda b: b.departure_key, False),
    "Shortest distance": (lambda b: b.segment_distance, False),
    "Most available seats": (lambda b: b.available_seats, True),
}

_SELECT = ("SELECT b.*, r.route_name FROM buses b "
           "JOIN routes r ON r.route_id = b.route_id")


class BusService:
    def __init__(self, db, route_service):
        self.db = db
        self.routes = route_service
        # Set by the application context: bus_id -> (booked, waiting). It reads
        # the in-memory seat arrays and queues kept by BookingService.
        self.occupancy = None
        # Called with bus_id whenever a bus changes so cached seat maps refresh.
        self.on_change = None

    # ------------------------------------------------------------- helpers
    def _attach_occupancy(self, buses):
        if self.occupancy is not None:
            for bus in buses:
                bus.booked_seats, bus.waiting_count = self.occupancy(bus)
        return buses

    def _notify(self, bus_id):
        if self.on_change is not None:
            self.on_change(bus_id)

    # ------------------------------------------------------------- queries
    def all_buses(self):
        rows = self.db.query(_SELECT + " ORDER BY b.bus_id")
        return self._attach_occupancy([Bus.from_row(r) for r in rows])

    def get(self, bus_id):
        row = self.db.query_one(_SELECT + " WHERE b.bus_id = ?", (bus_id,))
        if row is None:
            raise NotFoundError("Bus not found.")
        return self._attach_occupancy([Bus.from_row(row)])[0]

    def list_buses(self, query="", status=None, sort_by=None, algorithm=DEFAULT_ALGORITHM,
                   stats=None):
        """Admin listing: filter with linear search, sort with the chosen algorithm."""
        buses = self.all_buses()
        if status and status != "All":
            buses = linear_search_all(buses, lambda b: b.status == status)
        if query:
            q = query.strip().lower()
            buses = linear_search_all(
                buses, lambda b: q in b.bus_name.lower() or q in b.bus_number.lower()
                or q in b.route_name.lower() or q in b.bus_type.lower())
        if sort_by in BUS_SORT_KEYS:
            key, desc = BUS_SORT_KEYS[sort_by]
            buses = sort_items(buses, key=key, reverse=desc, algorithm=algorithm, stats=stats)
        return buses

    def find_by_number(self, bus_number):
        """
        Exact lookup by bus number with BINARY SEARCH:
        1) sort buses by number (merge sort), 2) binary search the sorted list.
        """
        buses = sort_items(self.all_buses(), key=lambda b: b.bus_number, algorithm="Merge Sort")
        result = binary_search(buses, bus_number.strip().upper(), key=lambda b: b.bus_number)
        return (buses[result.index] if result.found else None), result.comparisons

    def search_buses(self, from_city, to_city, travel_date=None, departure_after=None,
                     max_price=None, min_seats=None, sort_by="Earliest departure",
                     algorithm=DEFAULT_ALGORITHM, include_full=True, stats=None):
        """
        Passenger search. A bus matches if its route's linked list contains
        from_city BEFORE to_city (checked with RouteLinkedList.distance_between).
        """
        from_city = validators.validate_city(from_city, "Departure city")
        to_city = validators.validate_city(to_city, "Destination city")
        if from_city == to_city:
            raise ValidationError("Departure and destination cities must be different.")
        if travel_date:
            travel_date = validators.validate_date(travel_date, "Travel date")
        if departure_after:
            departure_after = validators.validate_time(departure_after, "Departure time")
        if max_price not in (None, ""):
            max_price = validators.validate_positive_float(max_price, "Maximum price")
        else:
            max_price = None
        if min_seats not in (None, ""):
            min_seats = validators.validate_positive_int(min_seats, "Minimum seats", 1)
        else:
            min_seats = None

        segment = {route.route_id: dist for route, dist in
                   self.routes.routes_through(from_city, to_city)}
        today = date.today().strftime(DATE_FMT)
        results = []
        for bus in self.all_buses():
            if bus.status != "Active" or bus.route_id not in segment:
                continue
            if bus.travel_date < today:
                continue
            if travel_date and bus.travel_date != travel_date:
                continue
            if departure_after and time_to_minutes(bus.departure_time) < \
                    time_to_minutes(departure_after):
                continue
            if max_price is not None and bus.ticket_price > max_price:
                continue
            if min_seats is not None and bus.available_seats < min_seats:
                continue
            if not include_full and bus.available_seats == 0:
                continue
            bus.segment_distance = segment[bus.route_id]
            results.append(bus)

        key, desc = SEARCH_SORT_KEYS.get(sort_by, SEARCH_SORT_KEYS["Earliest departure"])
        return sort_items(results, key=key, reverse=desc, algorithm=algorithm, stats=stats)

    # ------------------------------------------------------------ mutations
    def _validate(self, data):
        clean = {
            "bus_name": validators.require(data.get("bus_name"), "Bus name"),
            "bus_number": validators.validate_bus_number(data.get("bus_number")),
            "bus_type": validators.validate_choice(data.get("bus_type"), BUS_TYPES, "Bus type"),
            "total_seats": validators.validate_seat_count(data.get("total_seats")),
            "ticket_price": validators.validate_positive_float(data.get("ticket_price"),
                                                               "Ticket price"),
            "departure_time": validators.validate_time(data.get("departure_time"),
                                                       "Departure time"),
            "arrival_time": validators.validate_time(data.get("arrival_time"), "Arrival time"),
            "travel_date": validators.validate_date(data.get("travel_date"), "Travel date"),
            "status": validators.validate_choice(data.get("status") or "Active", BUS_STATUSES,
                                                 "Status"),
        }
        try:
            route_id = int(data.get("route_id"))
        except (TypeError, ValueError):
            raise ValidationError("Please select a route for this bus.") from None
        self.routes.get(route_id)            # raises NotFoundError if invalid
        clean["route_id"] = route_id
        return clean

    def add_bus(self, data):
        clean = self._validate(data)
        if clean["travel_date"] < date.today().strftime(DATE_FMT) and clean["status"] == "Active":
            raise ValidationError("An active bus cannot have a travel date in the past.")
        try:
            with self.db.transaction():
                cur = self.db.execute(
                    "INSERT INTO buses (bus_name, bus_number, bus_type, total_seats, "
                    "ticket_price, route_id, departure_time, arrival_time, travel_date, status, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (clean["bus_name"], clean["bus_number"], clean["bus_type"],
                     clean["total_seats"], clean["ticket_price"], clean["route_id"],
                     clean["departure_time"], clean["arrival_time"], clean["travel_date"],
                     clean["status"], now_str()))
        except sqlite3.IntegrityError:
            raise ValidationError(f"Bus number {clean['bus_number']} already exists.") from None
        self._notify(cur.lastrowid)
        return self.get(cur.lastrowid)

    def update_bus(self, bus_id, data):
        current = self.get(bus_id)
        clean = self._validate(data)

        # Seat-array safety: shrinking the bus must not delete booked seats.
        highest = self.db.query_value(
            "SELECT MAX(seat_number) FROM bookings WHERE bus_id = ? AND status = 'Confirmed'",
            (bus_id,), 0)
        if clean["total_seats"] < highest:
            raise BookingError(f"Seat {highest} is booked, so the bus needs at least "
                               f"{highest} seats.")
        # (If seats are ADDED while passengers are waiting, BookingService
        #  automatically allocates the new seats to the queue – see on_change.)
        if clean["route_id"] != current.route_id and self._active_bookings(bus_id):
            raise BookingError("The route cannot be changed while the bus has active bookings.")
        if clean["status"] in ("Cancelled", "Maintenance") and clean["status"] != current.status \
                and self._active_bookings(bus_id):
            raise BookingError("This bus has active bookings. Use 'Cancel bus' to cancel all "
                               "bookings safely instead of changing the status directly.")
        try:
            with self.db.transaction():
                self.db.execute(
                    "UPDATE buses SET bus_name=?, bus_number=?, bus_type=?, total_seats=?, "
                    "ticket_price=?, route_id=?, departure_time=?, arrival_time=?, "
                    "travel_date=?, status=? WHERE bus_id=?",
                    (clean["bus_name"], clean["bus_number"], clean["bus_type"],
                     clean["total_seats"], clean["ticket_price"], clean["route_id"],
                     clean["departure_time"], clean["arrival_time"], clean["travel_date"],
                     clean["status"], bus_id))
                label = f"{clean['bus_name']} ({clean['bus_number']})"
                self.db.execute("UPDATE bookings SET travel_date = ?, bus_label = ? "
                                "WHERE bus_id = ? AND status IN ('Confirmed','Waiting')",
                                (clean["travel_date"], label, bus_id))
        except sqlite3.IntegrityError:
            raise ValidationError(f"Bus number {clean['bus_number']} already exists.") from None
        self._notify(bus_id)
        return self.get(bus_id)

    def _active_bookings(self, bus_id):
        return self.db.query_value(
            "SELECT COUNT(*) FROM bookings WHERE bus_id = ? AND status IN ('Confirmed','Waiting')",
            (bus_id,), 0)

    def delete_bus(self, bus_id):
        """Deletion is refused while confirmed or waiting bookings exist."""
        bus = self.get(bus_id)
        active = self._active_bookings(bus_id)
        if active:
            raise BookingError(f"{bus.label} has {active} active booking(s). Use 'Cancel bus' "
                               "to cancel them safely before deleting.")
        with self.db.transaction():
            self.db.execute("DELETE FROM buses WHERE bus_id = ?", (bus_id,))
        self._notify(bus_id)
