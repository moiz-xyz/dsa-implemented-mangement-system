"""
Integration tests for the booking workflow: SQLite + in-memory structures.
Each test gets a fresh temporary database seeded with demo data.
"""
import os
import shutil
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

from services.app_context import SmartBusApp
from utils.exceptions import (AuthenticationError, BookingError, PermissionDeniedError,
                              SeatUnavailableError, UndoError, ValidationError)

TOMORROW = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


class BookingTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "test.db")
        self.app = SmartBusApp(self.path)
        self.admin = self.app.auth.login("admin", "admin123", "admin")
        self.ali = self.app.auth.login("ali.khan@example.com", "pass123", "passenger")
        self.sara = self.app.auth.login("sara.malik@example.com", "pass123", "passenger")
        self.moiz = self.app.auth.login("moiz.ahmed@example.com", "pass123", "passenger")
        route = self.app.routes.find_by_name("Islamabad – Peshawar Motorway")
        self.bus = self.app.buses.add_bus({
            "bus_name": "Test Mini", "bus_number": "TST-001", "bus_type": "Standard",
            "total_seats": 4, "ticket_price": 1000, "route_id": route.route_id,
            "departure_time": "09:00", "arrival_time": "12:00", "travel_date": TOMORROW,
            "status": "Active"})

    def tearDown(self):
        self.app.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def restart(self):
        """Simulate closing and reopening the application."""
        self.app.close()
        self.app = SmartBusApp(self.path)

    def fill_bus(self):
        self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1, 2, 3, 4])


class TestAuthAndValidation(BookingTestCase):
    def test_invalid_credentials(self):
        with self.assertRaises(AuthenticationError):
            self.app.auth.login("admin", "wrong", "admin")
        with self.assertRaises(AuthenticationError):
            self.app.auth.login("ali.khan@example.com", "pass123", "admin")
        with self.assertRaises(ValidationError):
            self.app.auth.login("", "x", "admin")

    def test_register_and_login(self):
        p = self.app.passengers.register("Test User", "test.user@example.com", "03001112233",
                                         "secret1", "secret1")
        session = self.app.auth.login("test.user@example.com", "secret1", "passenger")
        self.assertEqual(session.passenger_id, p.passenger_id)
        with self.assertRaises(ValidationError):            # duplicate email
            self.app.passengers.register("Other", "test.user@example.com", "03001112233",
                                         "secret1")
        for bad in [("", "a@b.com", "03001112233", "secret1"),
                    ("Name", "not-an-email", "03001112233", "secret1"),
                    ("Name", "x@y.com", "12", "secret1"),
                    ("Name", "x@y.com", "03001112233", "123")]:
            with self.assertRaises(ValidationError):
                self.app.passengers.register(*bad)

    def test_password_is_hashed(self):
        row = self.app.db.query_one("SELECT * FROM users WHERE username='admin'")
        self.assertNotEqual(row["password_hash"], "admin123")
        self.assertEqual(len(row["password_hash"]), 64)


class TestSeatBooking(BookingTestCase):
    def test_book_and_lookup_with_hash_table(self):
        bookings = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [2])
        b = bookings[0]
        self.assertEqual(self.app.bookings.get_booking(b.booking_id).seat_number, 2)
        self.assertEqual(self.app.bookings.get_booking(b.booking_id.lower()).booking_id,
                         b.booking_id)
        self.assertFalse(self.app.bookings.seat_map(self.bus.bus_id).is_available(2))
        row = self.app.db.query_one("SELECT * FROM bookings WHERE booking_id=?", (b.booking_id,))
        self.assertEqual(row["status"], "Confirmed")

    def test_prevent_duplicate_seat_booking(self):
        self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1])
        with self.assertRaises(SeatUnavailableError):
            self.app.bookings.book_seats(self.sara, self.bus.bus_id, [1])
        with self.assertRaises(ValidationError):
            self.app.bookings.book_seats(self.sara, self.bus.bus_id, [2, 2])
        with self.assertRaises(SeatUnavailableError):
            self.app.bookings.book_seats(self.sara, self.bus.bus_id, [99])
        # Database unique index is the last line of defence.
        with self.assertRaises(sqlite3.IntegrityError):
            self.app.db.execute(
                "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, from_city, "
                "to_city, amount, status, booking_date, travel_date, passenger_name, bus_label) "
                "VALUES ('SB-DUPE01', 1, ?, 1, 'A', 'B', 1, 'Confirmed', 'x', 'x', 'x', 'x')",
                (self.bus.bus_id,))

    def test_failed_transaction_leaves_memory_untouched(self):
        # Seat 3 taken directly in the DB behind the service's back.
        self.app.db.execute(
            "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, from_city, "
            "to_city, amount, status, booking_date, travel_date, passenger_name, bus_label) "
            "VALUES ('SB-GHOST1', 1, ?, 3, 'Islamabad', 'Peshawar', 1, 'Confirmed', 'x', ?, "
            "'x', 'x')", (self.bus.bus_id, TOMORROW))
        with self.assertRaises(SeatUnavailableError):
            self.app.bookings.book_seats(self.sara, self.bus.bus_id, [2, 3])
        self.assertTrue(self.app.bookings.seat_map(self.bus.bus_id).is_available(2))
        self.assertEqual(self.app.db.query_value(
            "SELECT COUNT(*) FROM bookings WHERE bus_id=? AND seat_number=2", (self.bus.bus_id,)),
            0)

    def test_cancel_booking_releases_seat(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [4])[0]
        result = self.app.bookings.cancel_booking(self.ali, b.booking_id)
        self.assertEqual(result.booking.status, "Cancelled")
        self.assertTrue(self.app.bookings.seat_map(self.bus.bus_id).is_available(4))
        with self.assertRaises(BookingError):
            self.app.bookings.cancel_booking(self.ali, b.booking_id)

    def test_passenger_cannot_cancel_others_booking(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1])[0]
        with self.assertRaises(PermissionDeniedError):
            self.app.bookings.cancel_booking(self.sara, b.booking_id)

    def test_seat_limit_per_passenger(self):
        route = self.app.routes.find_by_name("Islamabad – Peshawar Motorway")
        big = self.app.buses.add_bus({
            "bus_name": "Big", "bus_number": "TST-BIG", "bus_type": "Standard",
            "total_seats": 20, "ticket_price": 500, "route_id": route.route_id,
            "departure_time": "09:00", "arrival_time": "12:00", "travel_date": TOMORROW})
        self.app.bookings.book_seats(self.ali, big.bus_id, [1, 2, 3, 4, 5, 6])
        with self.assertRaises(BookingError):
            self.app.bookings.book_seats(self.ali, big.bus_id, [7])

    def test_change_seat(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1])[0]
        self.app.bookings.change_seat(self.ali, b.booking_id, 3)
        matrix = self.app.bookings.seat_map(self.bus.bus_id)
        self.assertTrue(matrix.is_available(1))
        self.assertFalse(matrix.is_available(3))
        self.assertEqual(self.app.db.query_value(
            "SELECT seat_number FROM bookings WHERE booking_id=?", (b.booking_id,)), 3)


class TestWaitingList(BookingTestCase):
    def test_join_only_when_full(self):
        with self.assertRaises(BookingError):
            self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)

    def test_fifo_auto_allocation_after_cancellation(self):
        self.fill_bus()
        _, pos1 = self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)
        _, pos2 = self.app.bookings.join_waiting_list(self.moiz, self.bus.bus_id)
        self.assertEqual((pos1, pos2), (1, 2))
        with self.assertRaises(BookingError):                 # duplicate request
            self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)

        ali_booking = self.app.bookings.list_bookings(self.ali, bus_id=self.bus.bus_id,
                                                      status="Confirmed")[0]
        seat = ali_booking.seat_number
        result = self.app.bookings.cancel_booking(self.ali, ali_booking.booking_id)

        # Sara was first in the queue, so she receives the seat.
        self.assertEqual(len(result.allocations), 1)
        allocated, allocated_seat = result.allocations[0]
        self.assertEqual(allocated.passenger_id, self.sara.passenger_id)
        self.assertEqual(allocated_seat, seat)
        self.assertEqual(allocated.status, "Confirmed")
        queue = self.app.bookings.queue_for(self.bus.bus_id)
        self.assertEqual(queue.size(), 1)
        self.assertEqual(queue.peek().passenger_id, self.moiz.passenger_id)
        self.assertTrue(self.app.bookings.seat_map(self.bus.bus_id).is_full())
        db_status = self.app.db.query_value("SELECT status FROM waiting_list WHERE booking_id=?",
                                            (allocated.booking_id,))
        self.assertEqual(db_status, "Allocated")

    def test_leave_waiting_list(self):
        self.fill_bus()
        b, _ = self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)
        self.app.bookings.cancel_booking(self.sara, b.booking_id)
        self.assertTrue(self.app.bookings.queue_for(self.bus.bus_id).is_empty())

    def test_adding_seats_serves_queue(self):
        self.fill_bus()
        self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)
        data = {k: getattr(self.bus, k) for k in (
            "bus_name", "bus_number", "bus_type", "ticket_price", "route_id", "departure_time",
            "arrival_time", "travel_date", "status")}
        data["total_seats"] = 6
        self.app.buses.update_bus(self.bus.bus_id, data)
        self.assertTrue(self.app.bookings.queue_for(self.bus.bus_id).is_empty())
        self.assertEqual(self.app.bookings.seat_map(self.bus.bus_id).occupied_count(), 5)
        self.assertTrue(self.app.bookings.drain_notifications())

    def test_seeded_waiting_list_order(self):
        full = self.app.buses.find_by_number("ISB-4001")[0]
        names = [r["passenger_name"] for r in self.app.bookings.waiting_entries(full.bus_id)]
        self.assertEqual(names, ["Sara Malik", "Ahmed Raza", "Moiz Ahmed"])


class TestUndo(BookingTestCase):
    def test_undo_empty(self):
        with self.assertRaises(UndoError):
            self.app.bookings.undo_last(self.moiz)

    def test_undo_booking(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1, 2])
        self.app.bookings.undo_last(self.ali)
        self.assertTrue(self.app.bookings.seat_map(self.bus.bus_id).is_available(1))
        self.assertEqual(self.app.bookings.get_booking(b[0].booking_id).status, "Cancelled")

    def test_undo_cancel_restores_seat(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [2])[0]
        self.app.bookings.cancel_booking(self.ali, b.booking_id)
        self.app.bookings.undo_last(self.ali)
        self.assertEqual(self.app.bookings.get_booking(b.booking_id).status, "Confirmed")
        self.assertFalse(self.app.bookings.seat_map(self.bus.bus_id).is_available(2))

    def test_undo_cancel_refused_when_seat_reallocated(self):
        self.fill_bus()
        self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)
        b = self.app.bookings.list_bookings(self.ali, bus_id=self.bus.bus_id,
                                            status="Confirmed")[0]
        self.app.bookings.cancel_booking(self.ali, b.booking_id)
        with self.assertRaises(UndoError):
            self.app.bookings.undo_last(self.ali)
        # The failed action is discarded; the previous one (BOOK) is now on top.
        self.assertIn("Booked", self.app.bookings.undo_preview(self.ali)[0])

    def test_undo_change(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1])[0]
        self.app.bookings.change_seat(self.ali, b.booking_id, 4)
        self.app.bookings.undo_last(self.ali)
        self.assertEqual(self.app.bookings.get_booking(b.booking_id).seat_number, 1)

    def test_undo_stack_survives_restart(self):
        b = self.app.bookings.book_seats(self.ali, self.bus.bus_id, [3])[0]
        self.restart()
        self.assertEqual(len(self.app.bookings.undo_preview(self.ali)), 1)
        self.app.bookings.undo_last(self.ali)
        self.assertEqual(self.app.bookings.get_booking(b.booking_id).status, "Cancelled")
        self.restart()
        self.assertEqual(self.app.bookings.undo_preview(self.ali), [])


class TestPersistence(BookingTestCase):
    def test_restore_records_after_restart(self):
        self.fill_bus()
        self.app.bookings.join_waiting_list(self.sara, self.bus.bus_id)
        self.app.bookings.join_waiting_list(self.moiz, self.bus.bus_id)
        before = len(self.app.bookings.index)
        self.restart()
        self.assertEqual(len(self.app.bookings.index), before)
        self.assertTrue(self.app.bookings.seat_map(self.bus.bus_id).is_full())
        queue = self.app.bookings.queue_for(self.bus.bus_id)
        self.assertEqual([e.passenger_id for e in queue],
                         [self.sara.passenger_id, self.moiz.passenger_id])
        # FIFO still works after the restart.
        b = self.app.bookings.list_bookings(self.ali, bus_id=self.bus.bus_id,
                                            status="Confirmed")[0]
        result = self.app.bookings.cancel_booking(self.ali, b.booking_id)
        self.assertEqual(result.allocations[0][0].passenger_id, self.sara.passenger_id)


class TestAdminRules(BookingTestCase):
    def test_bus_with_active_bookings_cannot_be_deleted(self):
        self.app.bookings.book_seats(self.ali, self.bus.bus_id, [1])
        with self.assertRaises(BookingError):
            self.app.buses.delete_bus(self.bus.bus_id)
        count = self.app.bookings.cancel_bus(self.admin, self.bus.bus_id)
        self.assertEqual(count, 1)
        self.app.buses.delete_bus(self.bus.bus_id)
        self.assertEqual(self.app.db.query_value("SELECT COUNT(*) FROM buses WHERE bus_id=?",
                                                 (self.bus.bus_id,)), 0)

    def test_passenger_safe_delete(self):
        p = self.app.passengers.register("Temp Person", "temp@example.com", "03001112299",
                                         "secret1")
        session = self.app.auth.login("temp@example.com", "secret1", "passenger")
        b = self.app.bookings.book_seats(session, self.bus.bus_id, [1])[0]
        with self.assertRaises(BookingError):
            self.app.delete_passenger(p.passenger_id)
        self.app.bookings.cancel_booking(session, b.booking_id)
        self.app.delete_passenger(p.passenger_id)
        # History is kept with the name snapshot.
        self.assertEqual(self.app.db.query_value(
            "SELECT passenger_name FROM bookings WHERE booking_id=?", (b.booking_id,)),
            "Temp Person")

    def test_route_edit_updates_linked_list_and_graph(self):
        route = self.app.routes.find_by_name("Islamabad – Peshawar Motorway")
        self.app.routes.add_stop(route.route_id, "Attock", 80, position=1, distance_to_next=105)
        self.assertEqual(route.stops.stop_names(), ["Islamabad", "Attock", "Peshawar"])
        self.assertTrue(self.app.routes.graph.has_connection("Attock", "Peshawar"))
        self.restart()
        route = self.app.routes.find_by_name("Islamabad – Peshawar Motorway")
        self.assertEqual(route.stops.stop_names(), ["Islamabad", "Attock", "Peshawar"])
        self.app.routes.remove_stop(route.route_id, "Attock")
        self.assertEqual(route.total_distance, 185)

    def test_bus_search(self):
        results = self.app.buses.search_buses("Karachi", "Multan", sort_by="Cheapest first")
        self.assertTrue(results)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i].ticket_price, results[i + 1].ticket_price)
        with self.assertRaises(ValidationError):
            self.app.buses.search_buses("Lahore", "Lahore")
        self.assertEqual(self.app.buses.search_buses("Multan", "Karachi"), [])   # wrong way

    def test_reports_and_csv(self):
        for name in self.app.reports.REPORTS:
            report = self.app.reports.build_report(name)
            path = self.app.reports.export_csv(report, os.path.join(self.tmp, "r.csv"))
            with open(path, encoding="utf-8") as fh:
                self.assertGreaterEqual(len(fh.readlines()), 1)
        stats = self.app.reports.dashboard_stats()
        self.assertEqual(stats["total_passengers"], 18)
        self.assertGreater(stats["total_revenue"], 0)


if __name__ == "__main__":
    unittest.main()
