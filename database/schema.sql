-- ==========================================================================
-- SMARTBUS database schema (SQLite)
-- The file is idempotent: every statement uses IF NOT EXISTS so it can be
-- executed on every application start.
-- ==========================================================================

PRAGMA foreign_keys = ON;

-- Login accounts (admins and passengers)
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash  TEXT    NOT NULL,
    salt           TEXT    NOT NULL,
    role           TEXT    NOT NULL CHECK (role IN ('admin', 'passenger')),
    created_at     TEXT    NOT NULL
);

-- Passenger profiles (one per passenger user account)
CREATE TABLE IF NOT EXISTS passengers (
    passenger_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    full_name          TEXT    NOT NULL,
    email              TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    phone              TEXT    NOT NULL,
    registration_date  TEXT    NOT NULL
);

-- Bus routes; the ordered stops live in route_stops
CREATE TABLE IF NOT EXISTS routes (
    route_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    route_name   TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    description  TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL
);

-- Each row is one node of a route's linked list, persisted in order.
CREATE TABLE IF NOT EXISTS route_stops (
    stop_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id            INTEGER NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
    stop_order          INTEGER NOT NULL CHECK (stop_order >= 0),
    stop_name           TEXT    NOT NULL,
    distance_from_prev  REAL    NOT NULL DEFAULT 0 CHECK (distance_from_prev >= 0),
    UNIQUE (route_id, stop_order),
    UNIQUE (route_id, stop_name)
);

CREATE TABLE IF NOT EXISTS buses (
    bus_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_name        TEXT    NOT NULL,
    bus_number      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    bus_type        TEXT    NOT NULL,
    total_seats     INTEGER NOT NULL CHECK (total_seats > 0),
    ticket_price    REAL    NOT NULL CHECK (ticket_price > 0),
    route_id        INTEGER NOT NULL REFERENCES routes(route_id) ON DELETE RESTRICT,
    departure_time  TEXT    NOT NULL,
    arrival_time    TEXT    NOT NULL,
    travel_date     TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'Active'
                    CHECK (status IN ('Active', 'Maintenance', 'Cancelled', 'Completed')),
    created_at      TEXT    NOT NULL
);

-- One row per seat reservation. Waiting bookings have seat_number NULL.
-- passenger_name / bus_label are snapshots so reports stay correct even if
-- the passenger or bus is later deleted.
CREATE TABLE IF NOT EXISTS bookings (
    booking_id      TEXT    PRIMARY KEY,
    passenger_id    INTEGER REFERENCES passengers(passenger_id) ON DELETE SET NULL,
    bus_id          INTEGER REFERENCES buses(bus_id) ON DELETE SET NULL,
    seat_number     INTEGER CHECK (seat_number IS NULL OR seat_number > 0),
    from_city       TEXT    NOT NULL,
    to_city         TEXT    NOT NULL,
    amount          REAL    NOT NULL CHECK (amount >= 0),
    status          TEXT    NOT NULL CHECK (status IN ('Confirmed', 'Cancelled', 'Waiting')),
    booking_date    TEXT    NOT NULL,
    travel_date     TEXT    NOT NULL,
    passenger_name  TEXT    NOT NULL,
    bus_label       TEXT    NOT NULL,
    route_name      TEXT    NOT NULL DEFAULT '',
    cancelled_at    TEXT,
    cancel_reason   TEXT,
    CHECK ((status = 'Confirmed' AND seat_number IS NOT NULL) OR status <> 'Confirmed')
);

-- Database-level guarantee against double booking:
-- at most ONE confirmed booking per (bus, seat).
CREATE UNIQUE INDEX IF NOT EXISTS ux_bookings_active_seat
    ON bookings (bus_id, seat_number) WHERE status = 'Confirmed';
CREATE INDEX IF NOT EXISTS ix_bookings_passenger ON bookings (passenger_id);
CREATE INDEX IF NOT EXISTS ix_bookings_bus ON bookings (bus_id);
CREATE INDEX IF NOT EXISTS ix_bookings_date ON bookings (booking_date);
CREATE INDEX IF NOT EXISTS ix_bookings_status ON bookings (status);

-- FIFO waiting list. waiting_id (AUTOINCREMENT) records arrival order, so
-- the in-memory queue can be rebuilt in exactly the same order.
CREATE TABLE IF NOT EXISTS waiting_list (
    waiting_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id    TEXT    NOT NULL UNIQUE REFERENCES bookings(booking_id) ON DELETE CASCADE,
    passenger_id  INTEGER REFERENCES passengers(passenger_id) ON DELETE CASCADE,
    bus_id        INTEGER REFERENCES buses(bus_id) ON DELETE CASCADE,
    request_date  TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'Waiting'
                  CHECK (status IN ('Waiting', 'Allocated', 'Cancelled')),
    resolved_at   TEXT
);
CREATE INDEX IF NOT EXISTS ix_waiting_bus_status ON waiting_list (bus_id, status);

-- Persistent log of booking operations; also used to rebuild the undo stack.
CREATE TABLE IF NOT EXISTS booking_history (
    history_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    action       TEXT    NOT NULL,
    booking_id   TEXT,
    details      TEXT    NOT NULL DEFAULT '{}',
    undoable     INTEGER NOT NULL DEFAULT 1 CHECK (undoable IN (0, 1)),
    undone       INTEGER NOT NULL DEFAULT 0 CHECK (undone IN (0, 1)),
    created_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_history_user ON booking_history (user_id, undone);
