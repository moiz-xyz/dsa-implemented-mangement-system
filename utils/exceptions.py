"""
Custom exception hierarchy.

Every error that the user can cause (bad input, a seat that is already
booked, a wrong password ...) is raised as a subclass of SmartBusError.
The UI catches SmartBusError and shows the message in a friendly dialog,
so ordinary mistakes never crash the application.
"""


class SmartBusError(Exception):
    """Base class for all expected (user-facing) errors."""


class ValidationError(SmartBusError):
    """Raised when user input is missing or malformed."""


class NotFoundError(SmartBusError):
    """Raised when a requested record does not exist."""


class AuthenticationError(SmartBusError):
    """Raised for invalid credentials."""


class PermissionDeniedError(SmartBusError):
    """Raised when a user tries an operation they are not allowed to do."""


class SeatUnavailableError(SmartBusError):
    """Raised when a seat is already booked or does not exist."""


class BookingError(SmartBusError):
    """Raised when a booking rule is violated."""


class UndoError(SmartBusError):
    """Raised when an operation cannot be undone."""


class DatabaseError(SmartBusError):
    """Raised when the database reports an unexpected error."""
