"""Small general-purpose helper functions."""

import secrets
import string
from datetime import datetime, date

from utils.constants import CURRENCY, DATE_FMT, DATETIME_FMT, TIME_FMT

_BOOKING_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion


def now_str():
    return datetime.now().strftime(DATETIME_FMT)


def today_str():
    return date.today().strftime(DATE_FMT)


def format_currency(amount):
    try:
        return f"{CURRENCY} {float(amount):,.0f}"
    except (TypeError, ValueError):
        return f"{CURRENCY} 0"


def format_distance(km):
    try:
        return f"{float(km):,.0f} km"
    except (TypeError, ValueError):
        return "-"


def time_to_minutes(value):
    """'14:30' -> 870. Used as a numeric sort key for departure times."""
    try:
        t = datetime.strptime(value, TIME_FMT)
        return t.hour * 60 + t.minute
    except (TypeError, ValueError):
        return 0


def generate_booking_id(exists):
    """
    Generate a unique booking ID such as 'SB-7KQ2MX'.

    `exists` is a function that tells us whether an ID is already used.
    SMARTBUS passes the custom hash table's `contains` method here, so the
    uniqueness check is an O(1) average-case hash lookup.
    """
    while True:
        code = "".join(secrets.choice(_BOOKING_ID_ALPHABET) for _ in range(6))
        booking_id = f"SB-{code}"
        if not exists(booking_id):
            return booking_id


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def initials(name):
    parts = [p for p in str(name).split() if p and p[0] in string.ascii_letters]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
