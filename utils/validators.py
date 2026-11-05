"""
Input validation helpers.

Each validator either returns a cleaned value or raises ValidationError with
a message that can be shown directly to the user.
"""

import re
from datetime import datetime, date

from utils.constants import DATE_FMT, TIME_FMT, MIN_SEATS, MAX_SEATS
from utils.exceptions import ValidationError

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Accepts e.g. 03001234567, +923001234567, 0300-1234567, +1 555 123 4567
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s-]{8,17}[0-9]$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,59}$")
BUS_NUMBER_RE = re.compile(r"^[A-Za-z0-9-]{3,15}$")


def require(value, field):
    """Return the stripped string, or raise if it is empty."""
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValidationError(f"{field} is required.")
    return text


def validate_name(value, field="Full name"):
    text = require(value, field)
    if not NAME_RE.match(text):
        raise ValidationError(
            f"{field} must start with a letter and contain only letters, "
            "spaces, dots, apostrophes or hyphens (2-60 characters).")
    return " ".join(text.split())


def validate_email(value):
    text = require(value, "Email").lower()
    if not EMAIL_RE.match(text):
        raise ValidationError("Please enter a valid email address (e.g. ali@example.com).")
    return text


def validate_phone(value):
    text = require(value, "Phone number")
    digits = re.sub(r"\D", "", text)
    if not PHONE_RE.match(text) or not 10 <= len(digits) <= 15:
        raise ValidationError("Please enter a valid phone number (10-15 digits, e.g. 03001234567).")
    return text


def validate_password(value, field="Password"):
    if value is None or value == "":
        raise ValidationError(f"{field} is required.")
    if len(value) < 6:
        raise ValidationError(f"{field} must be at least 6 characters long.")
    return value


def validate_date(value, field="Date", allow_past=True):
    text = require(value, field)
    try:
        parsed = datetime.strptime(text, DATE_FMT).date()
    except ValueError:
        raise ValidationError(f"{field} must be a valid date in YYYY-MM-DD format.") from None
    if not allow_past and parsed < date.today():
        raise ValidationError(f"{field} cannot be in the past.")
    return parsed.strftime(DATE_FMT)


def validate_time(value, field="Time"):
    text = require(value, field)
    try:
        parsed = datetime.strptime(text, TIME_FMT)
    except ValueError:
        raise ValidationError(f"{field} must be a valid 24-hour time in HH:MM format.") from None
    return parsed.strftime(TIME_FMT)


def validate_positive_int(value, field, minimum=1, maximum=None):
    text = require(value, field)
    try:
        number = int(text)
    except ValueError:
        raise ValidationError(f"{field} must be a whole number.") from None
    if number < minimum:
        raise ValidationError(f"{field} must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field} must be at most {maximum}.")
    return number


def validate_positive_float(value, field, allow_zero=False):
    text = require(value, field)
    try:
        number = float(text)
    except ValueError:
        raise ValidationError(f"{field} must be a number.") from None
    if number < 0 or (number == 0 and not allow_zero):
        raise ValidationError(f"{field} must be greater than zero.")
    return round(number, 2)


def validate_seat_count(value):
    return validate_positive_int(value, "Total seats", MIN_SEATS, MAX_SEATS)


def validate_bus_number(value):
    text = require(value, "Bus number").upper()
    if not BUS_NUMBER_RE.match(text):
        raise ValidationError("Bus number must be 3-15 letters, digits or hyphens (e.g. KHI-1234).")
    return text


def validate_choice(value, choices, field):
    text = require(value, field)
    if text not in choices:
        raise ValidationError(f"{field} must be one of: {', '.join(choices)}.")
    return text


def validate_city(value, field="City"):
    text = require(value, field)
    if not re.match(r"^[A-Za-z][A-Za-z .'-]{1,49}$", text):
        raise ValidationError(f"{field} must contain only letters, spaces or hyphens.")
    # Normalise to "Title Case" so "karachi" and "Karachi" are the same city.
    return " ".join(part.capitalize() for part in text.split())
