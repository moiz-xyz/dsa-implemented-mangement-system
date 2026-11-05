"""
BOOKING SERVICE – where all the data structures work together
=============================================================

In-memory structures (rebuilt from SQLite at start-up):

    index        HashTable   booking_id -> Booking       (O(1) lookup)
    seat_maps    HashTable   bus_id     -> SeatMatrix    (2-D seat array)
    queues       HashTable   bus_id     -> Queue         (FIFO waiting list)
    undo_stacks  HashTable   user_id    -> Stack         (LIFO undo history)

Keeping SQLite and memory synchronised
--------------------------------------
Every operation follows the same two-phase pattern (see `_run`):

  1. Inside ONE SQLite transaction, execute all SQL statements. While doing
     so, collect "effects" – small functions that will update the in-memory
     structures.
  2. Only if COMMIT succeeds, run the effects. If anything fails, SQLite
     rolls back and the effects are thrown away, so memory never shows a
     state that is not in the database.

Double booking is prevented twice: the SeatMatrix check gives a friendly
message, and the database's partial UNIQUE index on (bus_id, seat_number)
for confirmed bookings makes it impossible at storage level.

Waiting-list invariant
----------------------
A passenger can only join a bus's queue when the bus is FULL, and every
freed seat is immediately given to the passenger at the FRONT of the
queue. Therefore: "queue not empty  =>  bus has no free seats".
Undo operations are validated so they can never break this rule.
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date

from algorithms.searching import linear_search_all
from algorithms.sorting import sort_items, DEFAULT_ALGORITHM
from data_structures.custom_array import SeatMatrix
from data_structures.hash_table import HashTable
from data_structures.queue import Queue
from data_structures.stack import Stack
from models.booking import Booking, HistoryEntry, WaitingEntry
from utils.constants import (DATE_FMT, DEFAULT_SEAT_COLUMNS, MAX_SEATS_PER_PASSENGER_PER_BUS,
                             SEAT_COLUMNS, STATUS_CANCELLED, STATUS_CONFIRMED, STATUS_WAITING,
                             UNDO_HISTORY_LIMIT)
from utils.exceptions import (BookingError, NotFoundError, PermissionDeniedError,
                              SeatUnavailableError, SmartBusError, UndoError, ValidationError)
from utils.helpers import format_currency, generate_booking_id, now_str

BOOKING_SORT_KEYS = {
    "Booking date (newest)": (lambda b: b.booking_date, True),
    "Booking date (oldest)": (lambda b: b.booking_date, False),
    "Travel date": (lambda b: b.travel_date, False),
    "Amount (high → low)": (lambda b: b.amount, True),
    "Passenger name": (lambda b: (b.passenger_name or "").lower(), False),
    "Booking ID": (lambda b: b.booking_id, False),
}


@dataclass
class CancelResult:
    booking: Booking
    allocations: list = field(default_factory=list)   # [(Booking, seat)]

    def message(self):
        text = f"Booking {self.booking.booking_id} has been cancelled."
        for booking, seat in self.allocations:
            text += (f"\nSeat {seat} was automatically allocated to {booking.passenger_name} "
                     f"from the waiting list ({booking.booking_id}).")
        return text


class BookingService:
    def __init__(self, db, bus_service):
        self.db = db
        self.buses = bus_service
        self.index = HashTable(64)
        self.seat_maps = HashTable(32)
        self.queues = HashTable(32)
        self.undo_stacks = HashTable(16)
        self.notifications = []          # messages for the UI (auto allocations)
        bus_service.occupancy = self.occupancy_for
        bus_service.on_change = self._on_bus_changed
        self.reload()

    # ================================================================ loading
    def reload(self):
        """Rebuild every in-memory structure from the database."""
        self.index = HashTable(64)
        self.seat_maps = HashTable(32)
        self.queues = HashTable(32)
        self.undo_stacks = HashTable(16)

        for row in self.db.query("SELECT * FROM bookings"):
            self.index.insert(row["booking_id"], Booking.from_row(row))

        for row in self.db.query("SELECT bus_id, total_seats, bus_type FROM buses"):
            self._build_seat_map(row)

        # Restore each FIFO queue in the original arrival order (waiting_id).
        rows = self.db.query(
            "SELECT w.*, p.full_name AS passenger_name FROM waiting_list w "
            "LEFT JOIN passengers p ON p.passenger_id = w.passenger_id "
            "WHERE w.status = 'Waiting' ORDER BY w.waiting_id")
        for row in rows:
            self.queue_for(row["bus_id"]).enqueue(WaitingEntry.from_row(row))

    def _build_seat_map(self, bus_row):
        columns = SEAT_COLUMNS.get(bus_row["bus_type"], DEFAULT_SEAT_COLUMNS)
        matrix = SeatMatrix(bus_row["total_seats"], columns)
        bus_id = bus_row["bus_id"]
        for booking in self.index.values():
            if booking.bus_id == bus_id and booking.status == STATUS_CONFIRMED \
                    and booking.seat_number and booking.seat_number <= bus_row["total_seats"]:
                matrix.reserve(booking.seat_number)
        self.seat_maps.insert(bus_id, matrix)
        return matrix

    def seat_map(self, bus_id):
        matrix = self.seat_maps.search(bus_id)
        if matrix is None:
            row = self.db.query_one("SELECT bus_id, total_seats, bus_type FROM buses "
                                    "WHERE bus_id = ?", (bus_id,))
            if row is None:
                raise NotFoundError("Bus not found.")
            matrix = self._build_seat_map(row)
        return matrix

    def queue_for(self, bus_id):
        queue = self.queues.search(bus_id)
        if queue is None:
            queue = Queue()
            self.queues.insert(bus_id, queue)
        return queue

    def occupancy_for(self, bus):
        """(booked seats, waiting passengers) – read from the in-memory structures."""
        try:
            matrix = self.seat_map(bus.bus_id)
        except NotFoundError:
            return 0, 0
        return matrix.occupied_count(), self.queue_for(bus.bus_id).size()

    def _on_bus_changed(self, bus_id):
        """Called by BusService after a bus is added, edited or deleted."""
        row = self.db.query_one("SELECT bus_id, total_seats, bus_type FROM buses "
                                "WHERE bus_id = ?", (bus_id,))
        if row is None:                               # bus deleted
            if self.seat_maps.contains(bus_id):
                self.seat_maps.delete(bus_id)
            if self.queues.contains(bus_id):
                self.queues.delete(bus_id)
            for booking in self.index.values():
                if booking.bus_id == bus_id:
                    booking.bus_id = None            # mirrors ON DELETE SET NULL
            return
        matrix = self._build_seat_map(row)
        queue = self.queue_for(bus_id)
        # Seats were added while people are waiting -> serve the queue.
        if not queue.is_empty() and matrix.available_count() > 0:
            free = matrix.available_seats()
            allocations = self._run(lambda eff: self._sql_allocate(bus_id, free, eff))
            for booking, seat in allocations:
                self.notifications.append(
                    f"Seat {seat} allocated to {booking.passenger_name} from the waiting list.")

    def drain_notifications(self):
        messages, self.notifications = self.notifications, []
        return messages

    # ================================================================ helpers
    def _run(self, operation):
        """
        Two-phase execution: run SQL inside a transaction while collecting
        memory effects, then apply the effects only after a successful commit.
        """
        effects = []
        try:
            with self.db.transaction():
                result = operation(effects)
        except sqlite3.IntegrityError as exc:
            if "seat_number" in str(exc):
                raise SeatUnavailableError("That seat has just been booked by someone else. "
                                           "Please choose another seat.") from None
            raise BookingError(f"The booking could not be saved: {exc}") from None
        for effect in effects:
            effect()
        return result

    def _undo_stack(self, user_id):
        """Load (once) the user's undo stack from booking_history."""
        stack = self.undo_stacks.search(user_id)
        if stack is None:
            stack = Stack(max_size=UNDO_HISTORY_LIMIT)
            rows = self.db.query(
                "SELECT * FROM booking_history WHERE user_id = ? AND undoable = 1 "
                "AND undone = 0 ORDER BY history_id DESC LIMIT ?", (user_id, UNDO_HISTORY_LIMIT))
            for i in range(len(rows) - 1, -1, -1):      # oldest first -> newest on top
                stack.push(HistoryEntry.from_row(rows[i]))
            self.undo_stacks.insert(user_id, stack)
        return stack

    def _sql_history(self, session, action, booking_id, details, effects, undoable=True):
        user_id = session.user_id if session else None
        created = now_str()
        cur = self.db.execute(
            "INSERT INTO booking_history (user_id, action, booking_id, details, undoable, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, booking_id, json.dumps(details), 1 if undoable else 0, created))
        entry = HistoryEntry(cur.lastrowid, user_id, action, booking_id, details, created)
        if undoable and user_id is not None:
            effects.append(lambda: self._undo_stack(user_id).push(entry))
        return entry

    def get_booking(self, booking_id):
        """O(1) average lookup in the custom hash table."""
        if not booking_id or not str(booking_id).strip():
            raise ValidationError("Please enter a booking ID.")
        key = str(booking_id).strip().upper()
        booking = self.index.search(key)
        if booking is None:
            raise NotFoundError(f"No booking found with ID {key}.")
        return booking

    def _owned_booking(self, session, booking_id):
        booking = self.get_booking(booking_id)
        if not session.is_admin and booking.passenger_id != session.passenger_id:
            raise PermissionDeniedError("You can only manage your own bookings.")
        return booking

    def _resolve_passenger(self, session, passenger_id):
        if not session.is_admin:
            return session.passenger_id
        if passenger_id is None:
            raise ValidationError("Please select a passenger.")
        return int(passenger_id)

    def _passenger_name(self, passenger_id):
        name = self.db.query_value("SELECT full_name FROM passengers WHERE passenger_id = ?",
                                   (passenger_id,))
        if name is None:
            raise NotFoundError("Passenger not found.")
        return name

    def _check_bus_open(self, bus):
        if bus.status != "Active":
            raise BookingError(f"{bus.label} is not accepting bookings (status: {bus.status}).")
        if bus.travel_date < date.today().strftime(DATE_FMT):
            raise BookingError(f"{bus.label} has already departed ({bus.travel_date}).")

    def _segment(self, bus, from_city, to_city):
        route = self.buses.routes.get(bus.route_id)
        from_city = from_city or route.source
        to_city = to_city or route.destination
        if route.stops.distance_between(from_city, to_city) is None:
            raise ValidationError(f"{bus.label} does not travel from {from_city} to {to_city}.")
        return from_city, to_city, route.route_name

    def _seats_held(self, passenger_id, bus_id):
        count = 0
        for b in self.index.values():
            if b.passenger_id == passenger_id and b.bus_id == bus_id \
                    and b.status in (STATUS_CONFIRMED, STATUS_WAITING):
                count += 1
        return count

    # =============================================================== booking
    def book_seats(self, session, bus_id, seats, passenger_id=None, from_city=None,
                   to_city=None):
        """Book one or more specific seats. Returns the list of new Booking objects."""
        passenger_id = self._resolve_passenger(session, passenger_id)
        passenger_name = self._passenger_name(passenger_id)
        bus = self.buses.get(bus_id)
        self._check_bus_open(bus)
        from_city, to_city, route_name = self._segment(bus, from_city, to_city)

        if not seats:
            raise ValidationError("Please select at least one seat.")
        unique = []
        for seat in seats:
            if seat in unique:
                raise ValidationError(f"Seat {seat} was selected twice.")
            unique.append(seat)
        held = self._seats_held(passenger_id, bus_id)
        if held + len(unique) > MAX_SEATS_PER_PASSENGER_PER_BUS:
            raise BookingError(f"A passenger can hold at most {MAX_SEATS_PER_PASSENGER_PER_BUS} "
                               f"seats on one bus ({held} already held).")

        matrix = self.seat_map(bus_id)
        for seat in unique:
            try:
                if not matrix.is_available(seat):
                    raise SeatUnavailableError(f"Seat {seat} is already booked. "
                                               "Please choose another seat.")
            except IndexError:
                raise SeatUnavailableError(f"Seat {seat} does not exist on {bus.label}.") from None

        created = now_str()
        bookings = []
        for seat in unique:
            booking_id = generate_booking_id(
                lambda x: self.index.contains(x) or any(b.booking_id == x for b in bookings))
            bookings.append(Booking(booking_id, passenger_id, bus_id, seat, from_city, to_city,
                                    bus.ticket_price, STATUS_CONFIRMED, created, bus.travel_date,
                                    passenger_name, bus.label, route_name))

        def operation(effects):
            for b in bookings:
                self.db.execute(
                    "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, "
                    "from_city, to_city, amount, status, booking_date, travel_date, "
                    "passenger_name, bus_label, route_name) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (b.booking_id, b.passenger_id, b.bus_id, b.seat_number, b.from_city,
                     b.to_city, b.amount, b.status, b.booking_date, b.travel_date,
                     b.passenger_name, b.bus_label, b.route_name))
            self._sql_history(session, "BOOK", bookings[0].booking_id, {
                "booking_ids": [b.booking_id for b in bookings],
                "seats": unique, "bus_id": bus_id, "bus_label": bus.label}, effects)

            def apply():
                for b in bookings:
                    matrix.reserve(b.seat_number)        # update the 2-D array
                    self.index.insert(b.booking_id, b)   # update the hash table
            effects.insert(0, apply)
            return bookings

        return self._run(operation)

    # ========================================================== waiting list
    def join_waiting_list(self, session, bus_id, passenger_id=None, from_city=None,
                          to_city=None):
        """Enqueue the passenger on a FULL bus. Returns (Booking, queue position)."""
        passenger_id = self._resolve_passenger(session, passenger_id)
        passenger_name = self._passenger_name(passenger_id)
        bus = self.buses.get(bus_id)
        self._check_bus_open(bus)
        from_city, to_city, route_name = self._segment(bus, from_city, to_city)

        if not self.seat_map(bus_id).is_full():
            raise BookingError("Seats are still available on this bus – please book a seat "
                               "directly instead of joining the waiting list.")
        queue = self.queue_for(bus_id)
        if queue.position_of(lambda e: e.passenger_id == passenger_id) != -1:
            raise BookingError(f"{passenger_name} is already on the waiting list for this bus.")
        if self._seats_held(passenger_id, bus_id) >= MAX_SEATS_PER_PASSENGER_PER_BUS:
            raise BookingError("Seat limit for this bus reached.")

        booking_id = generate_booking_id(self.index.contains)
        created = now_str()
        booking = Booking(booking_id, passenger_id, bus_id, None, from_city, to_city,
                          bus.ticket_price, STATUS_WAITING, created, bus.travel_date,
                          passenger_name, bus.label, route_name)

        def operation(effects):
            self.db.execute(
                "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, from_city, "
                "to_city, amount, status, booking_date, travel_date, passenger_name, bus_label, "
                "route_name) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (booking_id, passenger_id, bus_id, from_city, to_city, bus.ticket_price,
                 STATUS_WAITING, created, bus.travel_date, passenger_name, bus.label,
                 route_name))
            entry = self._sql_enqueue(booking, created)

            def apply():
                self.index.insert(booking_id, booking)
                queue.enqueue(entry)                       # FIFO: join at the rear
            effects.append(apply)
            self._sql_history(session, "WAITLIST", booking_id,
                              {"bus_id": bus_id, "bus_label": bus.label}, effects)
            return booking, queue.size() + 1

        return self._run(operation)

    def _sql_enqueue(self, booking, request_date):
        cur = self.db.execute("INSERT INTO waiting_list (booking_id, passenger_id, bus_id, "
                              "request_date, status) VALUES (?, ?, ?, ?, 'Waiting')",
                              (booking.booking_id, booking.passenger_id, booking.bus_id,
                               request_date))
        return WaitingEntry(cur.lastrowid, booking.booking_id, booking.passenger_id,
                            booking.bus_id, request_date, booking.passenger_name)

    def _sql_allocate(self, bus_id, free_seats, effects):
        """
        Give free seats to waiting passengers in FIFO order.
        Walks the queue from the FRONT; entries that are no longer eligible
        (e.g. their booking vanished) are purged. Returns [(Booking, seat)].
        """
        queue = self.queue_for(bus_id)
        seats = list(free_seats)
        plan, purge = [], []
        for entry in queue:                       # front -> rear
            if not seats:
                break
            waiting_booking = self.index.search(entry.booking_id)
            if waiting_booking is None or waiting_booking.status != STATUS_WAITING \
                    or waiting_booking.passenger_id is None:
                purge.append(entry)
                continue
            plan.append((entry, waiting_booking, seats.pop(0)))

        stamp = now_str()
        for entry in purge:
            self.db.execute("UPDATE waiting_list SET status='Cancelled', resolved_at=? "
                            "WHERE waiting_id=?", (stamp, entry.waiting_id))
        for entry, waiting_booking, seat in plan:
            self.db.execute("UPDATE bookings SET status='Confirmed', seat_number=? "
                            "WHERE booking_id=? AND status='Waiting'",
                            (seat, waiting_booking.booking_id))
            self.db.execute("UPDATE waiting_list SET status='Allocated', resolved_at=? "
                            "WHERE waiting_id=?", (stamp, entry.waiting_id))
        if plan:
            self._sql_history(None, "ALLOCATE", plan[0][1].booking_id,
                              {"allocations": [[w.booking_id, s] for _, w, s in plan]},
                              effects, undoable=False)

        def apply():
            for entry in purge:
                queue.remove_where(lambda e, wid=entry.waiting_id: e.waiting_id == wid)
            matrix = self.seat_map(bus_id)
            for entry, waiting_booking, seat in plan:
                front = queue.dequeue()            # the allocated passenger is at the front
                assert front.waiting_id == entry.waiting_id, "FIFO order violated"
                waiting_booking.status = STATUS_CONFIRMED
                waiting_booking.seat_number = seat
                matrix.reserve(seat)
        effects.append(apply)
        return [(w, s) for _, w, s in plan]

    # ========================================================== cancellation
    def _sql_cancel(self, booking, reason, effects, allocate=True):
        """Cancel one booking (SQL + effects). Returns the auto-allocations."""
        stamp = now_str()
        allocations = []
        if booking.status == STATUS_CONFIRMED:
            cur = self.db.execute(
                "UPDATE bookings SET status='Cancelled', cancelled_at=?, cancel_reason=? "
                "WHERE booking_id=? AND status='Confirmed'", (stamp, reason, booking.booking_id))
            if cur.rowcount != 1:
                raise BookingError("This booking was changed by another operation. Refresh.")
            seat = booking.seat_number
            matrix = self.seat_map(booking.bus_id) if booking.bus_id else None

            def apply():
                booking.status = STATUS_CANCELLED
                booking.cancelled_at = stamp
                booking.cancel_reason = reason
                if matrix is not None:
                    matrix.release(seat)               # free the cell in the 2-D array
            effects.append(apply)
            if allocate and booking.bus_id:
                allocations = self._sql_allocate(booking.bus_id, [seat], effects)
        elif booking.status == STATUS_WAITING:
            self.db.execute("UPDATE bookings SET status='Cancelled', cancelled_at=?, "
                            "cancel_reason=? WHERE booking_id=?", (stamp, reason,
                                                                 booking.booking_id))
            self.db.execute("UPDATE waiting_list SET status='Cancelled', resolved_at=? "
                            "WHERE booking_id=? AND status='Waiting'", (stamp, booking.booking_id))

            def apply():
                booking.status = STATUS_CANCELLED
                booking.cancelled_at = stamp
                booking.cancel_reason = reason
                if booking.bus_id:
                    self.queue_for(booking.bus_id).remove_where(
                        lambda e: e.booking_id == booking.booking_id)
            effects.append(apply)
        else:
            raise BookingError(f"Booking {booking.booking_id} is already cancelled.")
        return allocations

    def cancel_booking(self, session, booking_id, reason=None):
        booking = self._owned_booking(session, booking_id)
        if booking.status == STATUS_CANCELLED:
            raise BookingError(f"Booking {booking.booking_id} is already cancelled.")
        if booking.bus_id is None:
            raise BookingError("The bus for this booking no longer exists.")
        bus = self.buses.get(booking.bus_id)
        if bus.travel_date < date.today().strftime(DATE_FMT):
            raise BookingError("Trips that have already departed cannot be cancelled.")
        reason = reason or ("Cancelled by admin" if session.is_admin else "Cancelled by passenger")
        previous = {"booking_id": booking.booking_id, "previous_status": booking.status,
                    "seat_number": booking.seat_number, "bus_id": booking.bus_id}

        def operation(effects):
            allocations = self._sql_cancel(booking, reason, effects)
            previous["allocated_to"] = [b.booking_id for b, _ in allocations]
            self._sql_history(session, "CANCEL", booking.booking_id, previous, effects)
            return CancelResult(booking, allocations)

        return self._run(operation)

    def cancel_bus(self, session, bus_id, reason="Bus cancelled by operator"):
        """Admin: cancel every active booking of a bus and mark it Cancelled."""
        if not session.is_admin:
            raise PermissionDeniedError("Only administrators can cancel a bus.")
        bus = self.buses.get(bus_id)
        active = linear_search_all(list(self.index.values()),
                                   lambda b: b.bus_id == bus_id and
                                   b.status in (STATUS_CONFIRMED, STATUS_WAITING))

        def operation(effects):
            for booking in active:
                self._sql_cancel(booking, reason, effects, allocate=False)
            self.db.execute("UPDATE buses SET status='Cancelled' WHERE bus_id=?", (bus_id,))
            self._sql_history(session, "CANCEL_BUS", None,
                              {"bus_id": bus_id, "bus_label": bus.label, "count": len(active)},
                              effects, undoable=False)
            return len(active)

        return self._run(operation)

    # ========================================================== change seat
    def change_seat(self, session, booking_id, new_seat):
        booking = self._owned_booking(session, booking_id)
        if booking.status != STATUS_CONFIRMED:
            raise BookingError("Only confirmed bookings can change seats.")
        bus = self.buses.get(booking.bus_id)
        self._check_bus_open(bus)
        matrix = self.seat_map(booking.bus_id)
        try:
            new_seat = int(new_seat)
            available = matrix.is_available(new_seat)
        except (TypeError, ValueError, IndexError):
            raise SeatUnavailableError(f"Seat {new_seat} does not exist on {bus.label}.") from None
        if new_seat == booking.seat_number:
            raise ValidationError("That is already your seat.")
        if not available:
            raise SeatUnavailableError(f"Seat {new_seat} is already booked.")
        old_seat = booking.seat_number

        def operation(effects):
            self._sql_move_seat(booking, old_seat, new_seat, effects)
            self._sql_history(session, "CHANGE", booking.booking_id,
                              {"old_seat": old_seat, "new_seat": new_seat,
                               "bus_id": booking.bus_id}, effects)
            return booking

        return self._run(operation)

    def _sql_move_seat(self, booking, old_seat, new_seat, effects):
        cur = self.db.execute("UPDATE bookings SET seat_number=? WHERE booking_id=? "
                              "AND status='Confirmed' AND seat_number=?",
                              (new_seat, booking.booking_id, old_seat))
        if cur.rowcount != 1:
            raise BookingError("This booking was changed by another operation.")
        matrix = self.seat_map(booking.bus_id)

        def apply():
            matrix.release(old_seat)
            matrix.reserve(new_seat)
            booking.seat_number = new_seat
        effects.append(apply)

    # ================================================================== undo
    def undo_preview(self, session):
        """Top-to-bottom descriptions of the user's undo stack."""
        return [entry.describe() for entry in self._undo_stack(session.user_id)]

    def can_undo(self, session):
        return not self._undo_stack(session.user_id).is_empty()

    def undo_last(self, session):
        """
        Pop the most recent operation from the user's Stack and reverse it.
        Every reversal is validated against the CURRENT state, so undo can
        never double-book a seat or jump the waiting-list queue.
        """
        stack = self._undo_stack(session.user_id)
        if stack.is_empty():
            raise UndoError("Nothing to undo – your recent-action stack is empty.")
        entry = stack.pop()
        handlers = {"BOOK": self._undo_book, "CANCEL": self._undo_cancel,
                    "CHANGE": self._undo_change, "WAITLIST": self._undo_waitlist}
        handler = handlers.get(entry.action)

        def operation(effects):
            if handler is None:
                raise UndoError(f"'{entry.action}' operations cannot be undone.")
            message = handler(session, entry, effects)
            self.db.execute("UPDATE booking_history SET undone = 1 WHERE history_id = ?",
                            (entry.history_id,))
            self._sql_history(session, "UNDO", entry.booking_id,
                              {"undone_history_id": entry.history_id,
                               "undone_action": entry.action}, effects, undoable=False)
            return message

        try:
            return self._run(operation)
        except SmartBusError as exc:
            # The action can never become undoable again, so drop it permanently.
            self.db.execute("UPDATE booking_history SET undoable = 0 WHERE history_id = ?",
                            (entry.history_id,))
            raise UndoError(f"Cannot undo “{entry.describe()}”: {exc}\n\n"
                            "This action has been removed from your undo history.") from None

    def _undo_book(self, session, entry, effects):
        ids = entry.details.get("booking_ids", [entry.booking_id])
        bookings = []
        for booking_id in ids:
            booking = self.index.search(booking_id)
            if booking is None or booking.status != STATUS_CONFIRMED:
                raise UndoError(f"booking {booking_id} is no longer confirmed")
            bookings.append(booking)
        bus = self.buses.get(bookings[0].bus_id)
        self._check_bus_open(bus)
        # Cancel all seats first, then hand the freed seats to the queue in ONE
        # FIFO pass (planning several passes against the same queue would give
        # the same front passenger several seats).
        for booking in bookings:
            self._sql_cancel(booking, "Undone by user", effects, allocate=False)
        allocations = self._sql_allocate(bus.bus_id, [b.seat_number for b in bookings], effects)
        msg = f"Undo complete: booking(s) {', '.join(ids)} removed and seat(s) released."
        for booking, seat in allocations:
            msg += f"\nSeat {seat} went to {booking.passenger_name} from the waiting list."
        return msg

    def _undo_cancel(self, session, entry, effects):
        d = entry.details
        booking = self.index.search(entry.booking_id)
        if booking is None or booking.status != STATUS_CANCELLED:
            raise UndoError("the booking is not cancelled any more")
        if booking.passenger_id is None or booking.bus_id is None:
            raise UndoError("the passenger or bus no longer exists")
        bus = self.buses.get(booking.bus_id)
        self._check_bus_open(bus)

        if d.get("previous_status") == STATUS_CONFIRMED:
            seat = d.get("seat_number")
            matrix = self.seat_map(booking.bus_id)
            if seat is None or seat > matrix.total_seats or not matrix.is_available(seat):
                raise UndoError(f"seat {seat} has already been given to another passenger")
            if not self.queue_for(booking.bus_id).is_empty():
                raise UndoError("passengers are waiting for this bus; restoring would skip "
                                "the waiting-list queue")
            self.db.execute("UPDATE bookings SET status='Confirmed', seat_number=?, "
                            "cancelled_at=NULL, cancel_reason=NULL WHERE booking_id=?",
                            (seat, booking.booking_id))

            def apply():
                booking.status = STATUS_CONFIRMED
                booking.seat_number = seat
                booking.cancelled_at = booking.cancel_reason = None
                matrix.reserve(seat)
            effects.append(apply)
            return f"Undo complete: booking {booking.booking_id} restored on seat {seat}."

        # The cancelled booking was a waiting-list entry: re-join at the rear.
        if not self.seat_map(booking.bus_id).is_full():
            raise UndoError("seats are now available; please book a seat directly")
        queue = self.queue_for(booking.bus_id)
        if queue.position_of(lambda e: e.passenger_id == booking.passenger_id) != -1:
            raise UndoError("the passenger is already on this waiting list")
        stamp = now_str()
        self.db.execute("UPDATE bookings SET status='Waiting', cancelled_at=NULL, "
                        "cancel_reason=NULL WHERE booking_id=?", (booking.booking_id,))
        self.db.execute("DELETE FROM waiting_list WHERE booking_id=?", (booking.booking_id,))
        new_entry = self._sql_enqueue(booking, stamp)

        def apply():
            booking.status = STATUS_WAITING
            booking.cancelled_at = booking.cancel_reason = None
            queue.enqueue(new_entry)
        effects.append(apply)
        return (f"Undo complete: {booking.passenger_name} re-joined the waiting list at "
                f"position {queue.size() + 1} (FIFO – the original place was taken by others).")

    def _undo_change(self, session, entry, effects):
        d = entry.details
        booking = self.index.search(entry.booking_id)
        if booking is None or booking.status != STATUS_CONFIRMED \
                or booking.seat_number != d.get("new_seat"):
            raise UndoError("the booking has changed since then")
        self._check_bus_open(self.buses.get(booking.bus_id))
        old_seat = d.get("old_seat")
        matrix = self.seat_map(booking.bus_id)
        if old_seat is None or old_seat > matrix.total_seats or not matrix.is_available(old_seat):
            raise UndoError(f"seat {old_seat} is now booked by someone else")
        self._sql_move_seat(booking, d.get("new_seat"), old_seat, effects)
        return f"Undo complete: booking {booking.booking_id} moved back to seat {old_seat}."

    def _undo_waitlist(self, session, entry, effects):
        booking = self.index.search(entry.booking_id)
        if booking is None or booking.status != STATUS_WAITING:
            raise UndoError("the waiting request was already allocated or cancelled")
        self._sql_cancel(booking, "Undone by user", effects)
        return f"Undo complete: {booking.booking_id} removed from the waiting list."

    # =============================================================== queries
    def list_bookings(self, session=None, query="", status="All", sort_by="Booking date (newest)",
                      algorithm=DEFAULT_ALGORITHM, passenger_id=None, bus_id=None, stats=None):
        bookings = list(self.index.values())        # traverse the hash table
        if session is not None and not session.is_admin:
            passenger_id = session.passenger_id
        if passenger_id is not None:
            bookings = linear_search_all(bookings, lambda b: b.passenger_id == passenger_id)
        if bus_id is not None:
            bookings = linear_search_all(bookings, lambda b: b.bus_id == bus_id)
        if status and status != "All":
            bookings = linear_search_all(bookings, lambda b: b.status == status)
        if query:
            q = query.strip().lower()
            bookings = linear_search_all(
                bookings, lambda b: q in b.booking_id.lower() or
                q in (b.passenger_name or "").lower() or q in (b.bus_label or "").lower())
        key, desc = BOOKING_SORT_KEYS.get(sort_by, BOOKING_SORT_KEYS["Booking date (newest)"])
        return sort_items(bookings, key=key, reverse=desc, algorithm=algorithm, stats=stats)

    def waiting_entries(self, bus_id=None, passenger_id=None):
        """Rows for the waiting-list screen, in FIFO order per bus."""
        rows = []
        for b_id, queue in self.queues.items():
            if bus_id is not None and b_id != bus_id:
                continue
            position = 1
            for entry in queue:
                booking = self.index.search(entry.booking_id)
                if passenger_id is None or entry.passenger_id == passenger_id:
                    rows.append({
                        "position": position, "entry": entry, "booking": booking,
                        "bus_id": b_id,
                        "bus_label": booking.bus_label if booking else "",
                        "passenger_name": booking.passenger_name if booking else
                        entry.passenger_name,
                        "request_date": entry.request_date, "status": "Waiting",
                    })
                position += 1
        return sort_items(rows, key=lambda r: (r["bus_label"], r["position"]),
                          algorithm="Merge Sort")

    def history_log(self, session, limit=200):
        if session.is_admin:
            rows = self.db.query(
                "SELECT h.*, u.username FROM booking_history h LEFT JOIN users u "
                "ON u.user_id = h.user_id ORDER BY h.history_id DESC LIMIT ?", (limit,))
        else:
            rows = self.db.query(
                "SELECT h.*, u.username FROM booking_history h LEFT JOIN users u "
                "ON u.user_id = h.user_id WHERE h.user_id = ? ORDER BY h.history_id DESC "
                "LIMIT ?", (session.user_id, limit))
        return rows

    def confirmation_text(self, booking):
        bus = None
        if booking.bus_id:
            try:
                bus = self.buses.get(booking.bus_id)
            except NotFoundError:
                bus = None
        lines = [
            "SMARTBUS – BOOKING CONFIRMATION",
            "=" * 40,
            f"Booking ID     : {booking.booking_id}",
            f"Status         : {booking.status}",
            f"Passenger      : {booking.passenger_name}",
            f"Bus            : {booking.bus_label}",
            f"Route          : {booking.route_name}",
            f"From → To      : {booking.from_city} → {booking.to_city}",
            f"Travel date    : {booking.travel_date}",
        ]
        if bus is not None:
            lines.append(f"Departure      : {bus.departure_time}   Arrival: {bus.arrival_time}")
        if booking.status == STATUS_WAITING and booking.bus_id:
            pos = self.queue_for(booking.bus_id).position_of(
                lambda e: e.booking_id == booking.booking_id)
            lines.append(f"Seat           : waiting list position #{pos}")
        else:
            lines.append(f"Seat           : {booking.seat_label}")
        lines += [f"Fare           : {format_currency(booking.amount)}",
                  f"Booked on      : {booking.booking_date}"]
        if booking.status == STATUS_CANCELLED:
            lines.append(f"Cancelled on   : {booking.cancelled_at} ({booking.cancel_reason})")
        lines.append("=" * 40)
        lines.append("Please arrive 30 minutes before departure.")
        return "\n".join(lines)
