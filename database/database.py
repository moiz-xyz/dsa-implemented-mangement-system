"""
SQLite access layer.

* Opens the database file (creating the folder if needed).
* Enables foreign keys on every connection.
* Executes schema.sql and seeds demo data on first launch.
* Offers a `transaction()` context manager. Nested calls use SAVEPOINTs,
  so a service can call another service inside one atomic unit of work.

All SQL elsewhere in the project uses parameter placeholders (?) –
values are never concatenated into SQL strings, which prevents SQL
injection.
"""

import os
import sqlite3
from contextlib import contextmanager

from utils.constants import DEFAULT_DB_PATH, SCHEMA_PATH
from utils.exceptions import DatabaseError


class Database:
    def __init__(self, path=None):
        self.path = path or os.environ.get("SMARTBUS_DB") or DEFAULT_DB_PATH
        if self.path != ":memory:":
            folder = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(folder, exist_ok=True)
        # isolation_level=None -> we control BEGIN/COMMIT ourselves.
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._depth = 0

    # ------------------------------------------------------------ lifecycle
    def initialize(self, seed=True):
        """Create tables if they do not exist and add demo data when empty."""
        with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
            self.conn.executescript(fh.read())
        self.conn.execute("PRAGMA foreign_keys = ON")
        if seed and self.query_value("SELECT COUNT(*) FROM users") == 0:
            from database.seed import seed_database
            seed_database(self)

    def close(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # --------------------------------------------------------- transactions
    @contextmanager
    def transaction(self):
        """
        Atomic unit of work. Everything inside either commits together or is
        rolled back together (e.g. seat allocation + booking creation).
        """
        if self._depth == 0:
            self.conn.execute("BEGIN IMMEDIATE")
        else:
            self.conn.execute(f"SAVEPOINT sp_{self._depth}")
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("ROLLBACK")
            else:
                self.conn.execute(f"ROLLBACK TO sp_{self._depth}")
                self.conn.execute(f"RELEASE sp_{self._depth}")
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("COMMIT")
            else:
                self.conn.execute(f"RELEASE sp_{self._depth}")

    # --------------------------------------------------------------- helpers
    def execute(self, sql, params=()):
        try:
            return self.conn.execute(sql, params)
        except sqlite3.IntegrityError:
            raise                      # services translate these into friendly messages
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database error: {exc}") from exc

    def executemany(self, sql, seq):
        try:
            return self.conn.executemany(sql, seq)
        except sqlite3.IntegrityError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database error: {exc}") from exc

    def query(self, sql, params=()):
        return [dict(row) for row in self.execute(sql, params).fetchall()]

    def query_one(self, sql, params=()):
        row = self.execute(sql, params).fetchone()
        return dict(row) if row else None

    def query_value(self, sql, params=(), default=None):
        row = self.execute(sql, params).fetchone()
        if row is None or row[0] is None:
            return default
        return row[0]
