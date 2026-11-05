"""
Application-wide constants for SMARTBUS.

Keeping every "magic value" in one place makes the rest of the code easier
to read and lets us change the look or the rules of the system from a
single file.
"""

import os

APP_NAME = "SMARTBUS"
APP_TAGLINE = "Intelligent Bus Reservation & Route Management System"
APP_TITLE = f"{APP_NAME} – {APP_TAGLINE}"
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "smartbus.db")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "database", "schema.sql")
ICON_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
EXPORT_DIR = os.path.join(PROJECT_ROOT, "exports")

# --------------------------------------------------------------------------
# Visual theme (taken from the project specification)
# --------------------------------------------------------------------------
COLORS = {
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "primary_light": "#DBEAFE",
    "secondary": "#22D3EE",
    "success": "#10B981",
    "success_light": "#D1FAE5",
    "danger": "#EF4444",
    "danger_dark": "#DC2626",
    "danger_light": "#FEE2E2",
    "warning": "#F59E0B",
    "warning_light": "#FEF3C7",
    "background": "#F8FAFC",
    "sidebar": "#0F172A",
    "sidebar_hover": "#1E293B",
    "sidebar_active": "#2563EB",
    "sidebar_text": "#CBD5E1",
    "sidebar_muted": "#64748B",
    "card": "#FFFFFF",
    "text": "#1E293B",
    "text_muted": "#64748B",
    "text_light": "#94A3B8",
    "border": "#E2E8F0",
    "row_alt": "#F8FAFC",
    "input_bg": "#FFFFFF",
    "white": "#FFFFFF",
    # Seat-map colours required by the specification
    "seat_available": "#10B981",
    "seat_booked": "#EF4444",
    "seat_selected": "#2563EB",
}

# --------------------------------------------------------------------------
# Business rules
# --------------------------------------------------------------------------
BUS_TYPES = ("Standard", "AC Standard", "Business", "Sleeper")
BUS_STATUSES = ("Active", "Maintenance", "Cancelled", "Completed")

# Seats per row (columns of the 2-D seat array) for each bus type.
# Standard coaches use a 2 + 2 layout; sleepers use a 1 + 2 layout.
SEAT_COLUMNS = {"Standard": 4, "AC Standard": 4, "Business": 4, "Sleeper": 3}
DEFAULT_SEAT_COLUMNS = 4
MIN_SEATS = 4
MAX_SEATS = 80

STATUS_CONFIRMED = "Confirmed"
STATUS_CANCELLED = "Cancelled"
STATUS_WAITING = "Waiting"
BOOKING_STATUSES = (STATUS_CONFIRMED, STATUS_CANCELLED, STATUS_WAITING)

WAIT_WAITING = "Waiting"
WAIT_ALLOCATED = "Allocated"
WAIT_CANCELLED = "Cancelled"

# Maximum number of seats a single passenger may hold on one bus.
MAX_SEATS_PER_PASSENGER_PER_BUS = 6

# Undo history: how many recent operations are restored after a restart.
UNDO_HISTORY_LIMIT = 25

ROLE_ADMIN = "admin"
ROLE_PASSENGER = "passenger"

# Demo admin account (documented in README.md)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_PASSENGER_PASSWORD = "pass123"

# Password hashing (PBKDF2-HMAC-SHA256 from hashlib)
PBKDF2_ITERATIONS = int(os.environ.get("SMARTBUS_PBKDF2_ITERATIONS", "100000"))

# --------------------------------------------------------------------------
# Date / time formats
# --------------------------------------------------------------------------
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"

CURRENCY = "Rs."
