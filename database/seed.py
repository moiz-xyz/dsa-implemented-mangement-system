"""
Demo data for SMARTBUS.

Runs automatically the first time the application starts (when the users
table is empty). Dates are generated relative to *today*, so the demo
always contains upcoming trips and recent booking activity.

Run manually to rebuild a fresh demo database:
    python -m database.seed --reset
"""

import os
import random
import sys
from datetime import date, datetime, timedelta

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.constants import (DATE_FMT, DATETIME_FMT, DEFAULT_ADMIN_PASSWORD,
                             DEFAULT_ADMIN_USERNAME, DEFAULT_PASSENGER_PASSWORD,
                             MAX_SEATS_PER_PASSENGER_PER_BUS)
from utils.helpers import generate_booking_id

# (route name, description, [(stop, distance from previous stop), ...])
ROUTES = [
    ("Karachi – Lahore Express", "Main north–south corridor via Sukkur and Multan",
     [("Karachi", 0), ("Hyderabad", 165), ("Nawabshah", 130), ("Sukkur", 185),
      ("Multan", 450), ("Lahore", 340)]),
    ("Karachi – Multan Southern", "Southern Punjab route via Rahim Yar Khan",
     [("Karachi", 0), ("Hyderabad", 165), ("Sukkur", 330), ("Rahim Yar Khan", 175),
      ("Bahawalpur", 190), ("Multan", 100)]),
    ("Lahore – Islamabad GT Road", "Grand Trunk Road with intermediate stops",
     [("Lahore", 0), ("Gujranwala", 70), ("Jhelum", 105), ("Rawalpindi", 115),
      ("Islamabad", 15)]),
    ("Islamabad – Lahore Motorway", "Non-stop motorway service",
     [("Islamabad", 0), ("Lahore", 375)]),
    ("Lahore – Multan via Faisalabad", "Central Punjab service",
     [("Lahore", 0), ("Faisalabad", 180), ("Multan", 240)]),
    ("Islamabad – Peshawar Motorway", "Capital to Khyber Pakhtunkhwa",
     [("Islamabad", 0), ("Peshawar", 185)]),
    ("Karachi – Quetta Highway", "Coastal highway to Balochistan",
     [("Karachi", 0), ("Khuzdar", 390), ("Quetta", 300)]),
    ("Quetta – Sukkur Link", "Bolan Pass connection",
     [("Quetta", 0), ("Sukkur", 390)]),
]

# (name, number, type, seats, price, route index, departure, arrival, day offset, status)
BUSES = [
    ("Indus Express", "KHI-1001", "Business", 40, 6500, 0, "07:00", "23:30", 1, "Active"),
    ("Mehran Night Coach", "KHI-1002", "Sleeper", 30, 7800, 0, "20:00", "12:30", 2, "Active"),
    ("Sindh Star", "KHI-2001", "AC Standard", 44, 4200, 1, "08:30", "22:00", 1, "Active"),
    ("Thar Traveller", "KHI-2002", "Standard", 48, 3200, 1, "21:00", "11:00", 3, "Active"),
    ("Margalla Line", "LHR-3001", "AC Standard", 40, 1800, 2, "09:00", "14:00", 1, "Active"),
    ("Five Rivers", "LHR-3002", "Standard", 44, 1400, 2, "15:30", "20:45", 2, "Active"),
    ("Capital Shuttle", "ISB-4001", "Business", 12, 3000, 3, "10:00", "14:30", 1, "Active"),
    ("Ravi Comfort", "LHR-5001", "AC Standard", 40, 2400, 4, "06:45", "13:00", 2, "Active"),
    ("Chenab Swift", "LHR-5002", "Standard", 36, 1900, 4, "18:15", "00:30", 4, "Active"),
    ("Khyber Coach", "ISB-6001", "AC Standard", 32, 1500, 5, "11:30", "14:00", 1, "Active"),
    ("Bolan Express", "QTA-7001", "Business", 36, 5200, 6, "16:00", "06:00", 3, "Active"),
    ("Desert Eagle", "QTA-8001", "Standard", 40, 2800, 7, "07:30", "15:00", 5, "Active"),
    ("Green Line", "KHI-1003", "AC Standard", 44, 6000, 0, "06:00", "21:30", 7, "Maintenance"),
    # Past trips – give the dashboard and monthly reports real history.
    ("Blue Horizon", "LHR-3003", "AC Standard", 40, 1800, 2, "08:00", "13:00", -70, "Completed"),
    ("Sindh Star II", "KHI-2003", "AC Standard", 44, 4200, 1, "08:30", "22:00", -40, "Completed"),
    ("Ravi Comfort II", "LHR-5003", "AC Standard", 40, 2400, 4, "06:45", "13:00", -18, "Completed"),
    ("Capital Shuttle II", "ISB-4002", "Business", 12, 3000, 3, "10:00", "14:30", -6, "Completed"),
]

PASSENGERS = [
    ("Ali Khan", "ali.khan@example.com", "03001234567"),
    ("Ahmed Raza", "ahmed.raza@example.com", "03011234568"),
    ("Moiz Ahmed", "moiz.ahmed@example.com", "03021234569"),
    ("Sara Malik", "sara.malik@example.com", "03031234570"),
    ("Fatima Noor", "fatima.noor@example.com", "03041234571"),
    ("Hassan Iqbal", "hassan.iqbal@example.com", "03051234572"),
    ("Ayesha Siddiqui", "ayesha.siddiqui@example.com", "03061234573"),
    ("Bilal Hussain", "bilal.hussain@example.com", "03071234574"),
    ("Zainab Shah", "zainab.shah@example.com", "03081234575"),
    ("Usman Tariq", "usman.tariq@example.com", "03091234576"),
    ("Hira Javed", "hira.javed@example.com", "03101234577"),
    ("Omar Farooq", "omar.farooq@example.com", "03111234578"),
    ("Mariam Aslam", "mariam.aslam@example.com", "03121234579"),
    ("Danish Ali", "danish.ali@example.com", "03131234580"),
    ("Iqra Butt", "iqra.butt@example.com", "03141234581"),
    ("Kamran Akmal", "kamran.akmal@example.com", "03151234582"),
    ("Nadia Hameed", "nadia.hameed@example.com", "03161234583"),
    ("Saad Qureshi", "saad.qureshi@example.com", "03171234584"),
]

# Fraction of seats booked per bus (index into BUSES). The 12-seat Capital
# Shuttle is completely full so the waiting-list feature can be demonstrated.
OCCUPANCY = [0.55, 0.7, 0.45, 0.35, 0.8, 0.4, 1.0, 0.5, 0.3, 0.6, 0.45, 0.25, 0.0,
             0.85, 0.75, 0.7, 0.9]
FULL_BUS_INDEX = 6
WAITING_PASSENGERS = [3, 1, 2]   # indexes into PASSENGERS (Sara, Ahmed, Moiz)


def seed_database(db, rng_seed=2024):
    from services.auth_service import hash_password   # local import avoids a cycle

    rng = random.Random(rng_seed)
    today = date.today()
    now = datetime.now()
    created = (now - timedelta(days=120)).strftime(DATETIME_FMT)
    used_ids = set()

    with db.transaction():
        # ---------------------------------------------------------- admin
        pw_hash, salt = hash_password(DEFAULT_ADMIN_PASSWORD)
        db.execute("INSERT INTO users (username, password_hash, salt, role, created_at) "
                   "VALUES (?, ?, ?, 'admin', ?)", (DEFAULT_ADMIN_USERNAME, pw_hash, salt, created))

        # ----------------------------------------------------- passengers
        passenger_ids = []
        for i, (name, email, phone) in enumerate(PASSENGERS):
            pw_hash, salt = hash_password(DEFAULT_PASSENGER_PASSWORD)
            reg = (now - timedelta(days=110 - i * 5)).strftime(DATETIME_FMT)
            cur = db.execute("INSERT INTO users (username, password_hash, salt, role, created_at) "
                             "VALUES (?, ?, ?, 'passenger', ?)", (email, pw_hash, salt, reg))
            cur = db.execute("INSERT INTO passengers (user_id, full_name, email, phone, "
                             "registration_date) VALUES (?, ?, ?, ?, ?)",
                             (cur.lastrowid, name, email, phone, reg))
            passenger_ids.append(cur.lastrowid)

        # --------------------------------------------------------- routes
        route_ids = []
        for name, desc, stops in ROUTES:
            cur = db.execute("INSERT INTO routes (route_name, description, created_at) "
                             "VALUES (?, ?, ?)", (name, desc, created))
            route_ids.append(cur.lastrowid)
            for order, (stop, dist) in enumerate(stops):
                db.execute("INSERT INTO route_stops (route_id, stop_order, stop_name, "
                           "distance_from_prev) VALUES (?, ?, ?, ?)",
                           (cur.lastrowid, order, stop, dist))

        # ---------------------------------------------------------- buses
        for b_index, bus in enumerate(BUSES):
            (name, number, btype, seats, price, r_index, dep, arr, offset, status) = bus
            travel = today + timedelta(days=offset)
            cur = db.execute(
                "INSERT INTO buses (bus_name, bus_number, bus_type, total_seats, ticket_price, "
                "route_id, departure_time, arrival_time, travel_date, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, number, btype, seats, price, route_ids[r_index], dep, arr,
                 travel.strftime(DATE_FMT), status, created))
            bus_id = cur.lastrowid
            route_name, _, stops = ROUTES[r_index]
            label = f"{name} ({number})"

            # Choose which seats are booked.
            booked_count = int(round(seats * OCCUPANCY[b_index]))
            seat_pool = list(range(1, seats + 1))
            rng.shuffle(seat_pool)
            booked_seats = seat_pool[:booked_count]
            per_passenger = {}

            for seat in booked_seats:
                # pick a passenger who still has quota on this bus
                while True:
                    p_index = rng.randrange(len(passenger_ids))
                    if b_index == FULL_BUS_INDEX and p_index in WAITING_PASSENGERS:
                        continue
                    if per_passenger.get(p_index, 0) < MAX_SEATS_PER_PASSENGER_PER_BUS:
                        break
                per_passenger[p_index] = per_passenger.get(p_index, 0) + 1

                # booking made 1-20 days before travel (but not in the future)
                days_before = rng.randint(1, 20)
                booked_on = datetime.combine(travel, datetime.min.time()) - timedelta(
                    days=days_before, hours=rng.randint(0, 12), minutes=rng.randint(0, 59))
                if booked_on > now:
                    booked_on = now - timedelta(hours=rng.randint(1, 72))
                booking_id = generate_booking_id(lambda x: x in used_ids)
                used_ids.add(booking_id)
                db.execute(
                    "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, "
                    "from_city, to_city, amount, status, booking_date, travel_date, "
                    "passenger_name, bus_label, route_name) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?, ?, ?, ?, ?)",
                    (booking_id, passenger_ids[p_index], bus_id, seat, stops[0][0],
                     stops[-1][0], price, booked_on.strftime(DATETIME_FMT),
                     travel.strftime(DATE_FMT), PASSENGERS[p_index][0], label, route_name))

            # A few historical cancellations on each non-empty bus.
            if booked_count and b_index != FULL_BUS_INDEX:
                for _ in range(rng.randint(1, 3)):
                    p_index = rng.randrange(len(passenger_ids))
                    booked_on = now - timedelta(days=rng.randint(2, 25))
                    if offset < 0:
                        booked_on = datetime.combine(travel, datetime.min.time()) - \
                            timedelta(days=rng.randint(2, 15))
                    cancelled_on = booked_on + timedelta(hours=rng.randint(2, 30))
                    booking_id = generate_booking_id(lambda x: x in used_ids)
                    used_ids.add(booking_id)
                    db.execute(
                        "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, "
                        "from_city, to_city, amount, status, booking_date, travel_date, "
                        "passenger_name, bus_label, route_name, cancelled_at, cancel_reason) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, 'Cancelled', ?, ?, ?, ?, ?, ?, ?)",
                        (booking_id, passenger_ids[p_index], bus_id, rng.randint(1, seats),
                         stops[0][0], stops[-1][0], price, booked_on.strftime(DATETIME_FMT),
                         travel.strftime(DATE_FMT), PASSENGERS[p_index][0], label, route_name,
                         cancelled_on.strftime(DATETIME_FMT), "Cancelled by passenger"))

            # Waiting list for the full bus (FIFO order = insertion order).
            if b_index == FULL_BUS_INDEX:
                for k, p_index in enumerate(WAITING_PASSENGERS):
                    requested = (now - timedelta(hours=30 - k * 6)).strftime(DATETIME_FMT)
                    booking_id = generate_booking_id(lambda x: x in used_ids)
                    used_ids.add(booking_id)
                    db.execute(
                        "INSERT INTO bookings (booking_id, passenger_id, bus_id, seat_number, "
                        "from_city, to_city, amount, status, booking_date, travel_date, "
                        "passenger_name, bus_label, route_name) "
                        "VALUES (?, ?, ?, NULL, ?, ?, ?, 'Waiting', ?, ?, ?, ?, ?)",
                        (booking_id, passenger_ids[p_index], bus_id, stops[0][0], stops[-1][0],
                         price, requested, travel.strftime(DATE_FMT), PASSENGERS[p_index][0],
                         label, route_name))
                    db.execute("INSERT INTO waiting_list (booking_id, passenger_id, bus_id, "
                               "request_date, status) VALUES (?, ?, ?, ?, 'Waiting')",
                               (booking_id, passenger_ids[p_index], bus_id, requested))


if __name__ == "__main__":
    from database.database import Database
    from utils.constants import DEFAULT_DB_PATH

    path = os.environ.get("SMARTBUS_DB") or DEFAULT_DB_PATH
    if "--reset" in sys.argv and os.path.exists(path):
        os.remove(path)
        print(f"Removed {path}")
    database = Database(path)
    database.initialize()
    print(f"Database ready at {path}")
