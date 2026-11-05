"""Domain models (plain data classes)."""

from models.bus import Bus
from models.passenger import Passenger
from models.booking import Booking, WaitingEntry, HistoryEntry
from models.route import Route

__all__ = ["Bus", "Passenger", "Booking", "WaitingEntry", "HistoryEntry", "Route"]
