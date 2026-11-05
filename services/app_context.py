"""
Application context – creates the database and every service once and
wires them together. Both the GUI and the tests use this class.
"""

from database.database import Database
from services.auth_service import AuthService
from services.booking_service import BookingService
from services.bus_service import BusService
from services.passenger_service import PassengerService
from services.report_service import ReportService
from services.route_service import RouteService


class SmartBusApp:
    def __init__(self, db_path=None, seed=True):
        self.db = Database(db_path)
        self.db.initialize(seed=seed)
        self.auth = AuthService(self.db)
        self.routes = RouteService(self.db)
        self.buses = BusService(self.db, self.routes)
        self.passengers = PassengerService(self.db, self.auth)
        self.bookings = BookingService(self.db, self.buses)
        self.reports = ReportService(self.db)

    def delete_passenger(self, passenger_id):
        """Delete safely, then refresh in-memory booking structures."""
        passenger = self.passengers.delete(passenger_id)
        self.bookings.reload()
        return passenger

    def close(self):
        self.db.close()
