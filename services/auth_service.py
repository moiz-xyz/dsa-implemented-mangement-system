"""
Authentication service.

Passwords are never stored in plain text. We use PBKDF2-HMAC-SHA256 from
Python's standard `hashlib` with a random 16-byte salt per user and many
iterations, which makes brute-force guessing slow. Comparison uses
`hmac.compare_digest` to avoid timing attacks.
"""

import hashlib
import hmac
import os
from dataclasses import dataclass

from utils.constants import PBKDF2_ITERATIONS, ROLE_ADMIN, ROLE_PASSENGER
from utils.exceptions import AuthenticationError, ValidationError
from utils.helpers import now_str
from utils import validators


def hash_password(password, salt_hex=None):
    """Return (hash_hex, salt_hex)."""
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password, hash_hex, salt_hex):
    candidate, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, hash_hex)


@dataclass
class Session:
    """The currently logged-in user."""
    user_id: int
    username: str
    role: str
    display_name: str
    passenger_id: int = None

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN


class AuthService:
    def __init__(self, db):
        self.db = db

    def login(self, username, password, role):
        username = (username or "").strip()
        if not username:
            raise ValidationError("Please enter your username or email.")
        if not password:
            raise ValidationError("Please enter your password.")
        if role not in (ROLE_ADMIN, ROLE_PASSENGER):
            raise ValidationError("Please choose Admin or Passenger login.")

        user = self.db.query_one("SELECT * FROM users WHERE username = ? AND role = ?",
                                 (username, role))
        # Same message for unknown user and wrong password (do not leak which one).
        if user is None or not verify_password(password, user["password_hash"], user["salt"]):
            raise AuthenticationError("Invalid credentials. Please check your username and password.")

        if role == ROLE_ADMIN:
            return Session(user["user_id"], user["username"], ROLE_ADMIN, "Administrator")

        passenger = self.db.query_one("SELECT * FROM passengers WHERE user_id = ?",
                                      (user["user_id"],))
        if passenger is None:
            raise AuthenticationError("This passenger account has no profile.")
        return Session(user["user_id"], user["username"], ROLE_PASSENGER,
                       passenger["full_name"], passenger["passenger_id"])

    def change_password(self, user_id, old_password, new_password):
        user = self.db.query_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if user is None or not verify_password(old_password or "", user["password_hash"],
                                               user["salt"]):
            raise AuthenticationError("Current password is incorrect.")
        validators.validate_password(new_password, "New password")
        pw_hash, salt = hash_password(new_password)
        self.db.execute("UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?",
                        (pw_hash, salt, user_id))

    def create_user(self, username, password, role):
        """Insert a users row (caller handles the transaction). Returns user_id."""
        pw_hash, salt = hash_password(password)
        cur = self.db.execute(
            "INSERT INTO users (username, password_hash, salt, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)", (username, pw_hash, salt, role, now_str()))
        return cur.lastrowid
