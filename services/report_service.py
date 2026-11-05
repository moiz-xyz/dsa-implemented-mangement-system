"""
Reports and analytics.

All numbers are computed from real database records with aggregate SQL
(COUNT / SUM / GROUP BY). Result rows are ordered with our own merge sort.
Reports can be exported to CSV with Python's csv module.
"""

import csv
import os
from datetime import date, timedelta

from algorithms.sorting import merge_sort
from utils.constants import DATE_FMT, EXPORT_DIR


class ReportService:
    REPORTS = ("Daily booking report", "Monthly revenue report", "Passenger report",
               "Bus occupancy report", "Route popularity report", "Cancellation report")

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------ dashboard
    def dashboard_stats(self):
        today = date.today().strftime(DATE_FMT)
        q = self.db.query_value
        upcoming_capacity = q("SELECT SUM(total_seats) FROM buses WHERE status='Active' "
                              "AND travel_date >= ?", (today,), 0)
        occupied = q("SELECT COUNT(*) FROM bookings k JOIN buses b ON b.bus_id = k.bus_id "
                     "WHERE k.status='Confirmed' AND b.status='Active' AND b.travel_date >= ?",
                     (today,), 0)
        return {
            "total_buses": q("SELECT COUNT(*) FROM buses", (), 0),
            "active_buses": q("SELECT COUNT(*) FROM buses WHERE status='Active' "
                              "AND travel_date >= ?", (today,), 0),
            "total_passengers": q("SELECT COUNT(*) FROM passengers", (), 0),
            "total_bookings": q("SELECT COUNT(*) FROM bookings", (), 0),
            "confirmed_bookings": q("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'", (), 0),
            "available_seats": upcoming_capacity - occupied,
            "occupied_seats": occupied,
            "cancelled_bookings": q("SELECT COUNT(*) FROM bookings WHERE status='Cancelled'", (), 0),
            "waiting_passengers": q("SELECT COUNT(*) FROM waiting_list WHERE status='Waiting'",
                                    (), 0),
            "total_revenue": q("SELECT SUM(amount) FROM bookings WHERE status='Confirmed'", (), 0),
            "routes": q("SELECT COUNT(*) FROM routes", (), 0),
        }

    def daily_bookings(self, days=14):
        start = date.today() - timedelta(days=days - 1)
        rows = self.db.query(
            "SELECT substr(booking_date, 1, 10) AS day, COUNT(*) AS bookings, "
            "SUM(CASE WHEN status='Confirmed' THEN amount ELSE 0 END) AS revenue "
            "FROM bookings WHERE substr(booking_date, 1, 10) >= ? GROUP BY day",
            (start.strftime(DATE_FMT),))
        by_day = {r["day"]: r for r in rows}
        result = []
        for i in range(days):                     # include days with zero bookings
            d = (start + timedelta(days=i)).strftime(DATE_FMT)
            r = by_day.get(d)
            result.append({"day": d, "bookings": r["bookings"] if r else 0,
                           "revenue": r["revenue"] if r else 0})
        return result

    def monthly_revenue(self, months=6):
        rows = self.db.query(
            "SELECT substr(booking_date, 1, 7) AS month, "
            "SUM(CASE WHEN status='Confirmed' THEN amount ELSE 0 END) AS revenue, "
            "SUM(CASE WHEN status='Confirmed' THEN 1 ELSE 0 END) AS confirmed, "
            "SUM(CASE WHEN status='Cancelled' THEN 1 ELSE 0 END) AS cancelled "
            "FROM bookings GROUP BY month")
        by_month = {r["month"]: r for r in rows}
        result = []
        y, m = date.today().year, date.today().month
        keys = []
        for _ in range(months):
            keys.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        for key in reversed(keys):
            r = by_month.get(key)
            result.append({"month": key, "revenue": r["revenue"] if r else 0,
                           "confirmed": r["confirmed"] if r else 0,
                           "cancelled": r["cancelled"] if r else 0})
        return result

    def popular_routes(self, limit=6):
        rows = self.db.query(
            "SELECT route_name, COUNT(*) AS bookings, SUM(amount) AS revenue FROM bookings "
            "WHERE status='Confirmed' AND route_name <> '' GROUP BY route_name")
        return merge_sort(rows, key=lambda r: r["bookings"], reverse=True)[:limit]

    def bus_occupancy(self, upcoming_only=True):
        today = date.today().strftime(DATE_FMT)
        where = "WHERE b.status='Active' AND b.travel_date >= ?" if upcoming_only else ""
        params = (today,) if upcoming_only else ()
        rows = self.db.query(
            "SELECT b.bus_id, b.bus_name, b.bus_number, b.total_seats, b.travel_date, b.status, "
            "b.departure_time, r.route_name, "
            "(SELECT COUNT(*) FROM bookings k WHERE k.bus_id=b.bus_id AND k.status='Confirmed') "
            "AS booked, "
            "(SELECT COALESCE(SUM(amount),0) FROM bookings k WHERE k.bus_id=b.bus_id "
            " AND k.status='Confirmed') AS revenue, "
            "(SELECT COUNT(*) FROM waiting_list w WHERE w.bus_id=b.bus_id AND w.status='Waiting') "
            "AS waiting "
            f"FROM buses b JOIN routes r ON r.route_id=b.route_id {where}", params)
        for r in rows:
            r["available"] = r["total_seats"] - r["booked"]
            r["occupancy"] = round(100 * r["booked"] / r["total_seats"]) if r["total_seats"] else 0
        return merge_sort(rows, key=lambda r: (r["travel_date"], r["departure_time"]))

    # -------------------------------------------------------------- reports
    def build_report(self, name):
        builders = {
            "Daily booking report": self._daily_report,
            "Monthly revenue report": self._monthly_report,
            "Passenger report": self._passenger_report,
            "Bus occupancy report": self._occupancy_report,
            "Route popularity report": self._route_report,
            "Cancellation report": self._cancellation_report,
        }
        if name not in builders:
            raise ValueError(f"Unknown report: {name}")
        columns, rows, summary = builders[name]()
        return {"title": name, "columns": columns, "rows": rows, "summary": summary}

    def _daily_report(self):
        rows = self.db.query(
            "SELECT substr(booking_date,1,10) AS day, COUNT(*) AS total, "
            "SUM(status='Confirmed') AS confirmed, SUM(status='Cancelled') AS cancelled, "
            "SUM(status='Waiting') AS waiting, "
            "SUM(CASE WHEN status='Confirmed' THEN amount ELSE 0 END) AS revenue "
            "FROM bookings GROUP BY day")
        rows = merge_sort(rows, key=lambda r: r["day"], reverse=True)
        cols = [("day", "Date"), ("total", "Bookings"), ("confirmed", "Confirmed"),
                ("cancelled", "Cancelled"), ("waiting", "Waiting"), ("revenue", "Revenue (Rs.)")]
        total = sum(r["total"] for r in rows)
        return cols, rows, f"{len(rows)} days with activity · {total} bookings"

    def _monthly_report(self):
        rows = self.db.query(
            "SELECT substr(booking_date,1,7) AS month, "
            "SUM(status='Confirmed') AS confirmed, SUM(status='Cancelled') AS cancelled, "
            "SUM(CASE WHEN status='Confirmed' THEN amount ELSE 0 END) AS revenue "
            "FROM bookings GROUP BY month")
        for r in rows:
            r["average_fare"] = round(r["revenue"] / r["confirmed"]) if r["confirmed"] else 0
        rows = merge_sort(rows, key=lambda r: r["month"], reverse=True)
        cols = [("month", "Month"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"),
                ("revenue", "Revenue (Rs.)"), ("average_fare", "Avg fare (Rs.)")]
        total = sum(r["revenue"] for r in rows)
        return cols, rows, f"Total revenue Rs. {total:,.0f}"

    def _passenger_report(self):
        rows = self.db.query(
            "SELECT p.passenger_id, p.full_name, p.email, p.phone, p.registration_date, "
            "COUNT(k.booking_id) AS total, SUM(k.status='Confirmed') AS confirmed, "
            "SUM(k.status='Cancelled') AS cancelled, "
            "COALESCE(SUM(CASE WHEN k.status='Confirmed' THEN k.amount END),0) AS spent "
            "FROM passengers p LEFT JOIN bookings k ON k.passenger_id = p.passenger_id "
            "GROUP BY p.passenger_id")
        for r in rows:
            r["confirmed"] = r["confirmed"] or 0
            r["cancelled"] = r["cancelled"] or 0
        rows = merge_sort(rows, key=lambda r: r["full_name"].lower())
        cols = [("full_name", "Passenger"), ("email", "Email"), ("phone", "Phone"),
                ("total", "Bookings"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"),
                ("spent", "Total spent (Rs.)")]
        return cols, rows, f"{len(rows)} registered passengers"

    def _occupancy_report(self):
        rows = self.bus_occupancy(upcoming_only=False)
        for r in rows:
            r["bus"] = f"{r['bus_name']} ({r['bus_number']})"
            r["occupancy_text"] = f"{r['occupancy']}%"
        cols = [("bus", "Bus"), ("route_name", "Route"), ("travel_date", "Date"),
                ("status", "Status"), ("total_seats", "Seats"), ("booked", "Booked"),
                ("available", "Available"), ("waiting", "Waiting"),
                ("occupancy_text", "Occupancy"), ("revenue", "Revenue (Rs.)")]
        avg = round(sum(r["occupancy"] for r in rows) / len(rows)) if rows else 0
        return cols, rows, f"{len(rows)} buses · average occupancy {avg}%"

    def _route_report(self):
        rows = self.db.query(
            "SELECT r.route_name, COUNT(DISTINCT b.bus_id) AS buses, "
            "COUNT(k.booking_id) AS bookings, "
            "COUNT(DISTINCT k.passenger_id) AS passengers, "
            "COALESCE(SUM(k.amount),0) AS revenue "
            "FROM routes r LEFT JOIN buses b ON b.route_id = r.route_id "
            "LEFT JOIN bookings k ON k.bus_id = b.bus_id AND k.status = 'Confirmed' "
            "GROUP BY r.route_id")
        rows = merge_sort(rows, key=lambda r: r["bookings"], reverse=True)
        for rank, r in enumerate(rows, 1):
            r["rank"] = rank
        cols = [("rank", "#"), ("route_name", "Route"), ("buses", "Buses"),
                ("bookings", "Confirmed bookings"), ("passengers", "Unique passengers"),
                ("revenue", "Revenue (Rs.)")]
        return cols, rows, f"{len(rows)} routes"

    def _cancellation_report(self):
        rows = self.db.query(
            "SELECT booking_id, passenger_name, bus_label, route_name, booking_date, "
            "cancelled_at, amount, cancel_reason FROM bookings WHERE status='Cancelled'")
        rows = merge_sort(rows, key=lambda r: r["cancelled_at"] or "", reverse=True)
        cols = [("booking_id", "Booking ID"), ("passenger_name", "Passenger"),
                ("bus_label", "Bus"), ("route_name", "Route"), ("booking_date", "Booked on"),
                ("cancelled_at", "Cancelled on"), ("amount", "Amount (Rs.)"),
                ("cancel_reason", "Reason")]
        lost = sum(r["amount"] for r in rows)
        return cols, rows, f"{len(rows)} cancellations · Rs. {lost:,.0f} refunded/lost"

    # --------------------------------------------------------------- export
    @staticmethod
    def export_csv(report, path=None):
        if path is None:
            os.makedirs(EXPORT_DIR, exist_ok=True)
            safe = report["title"].lower().replace(" ", "_")
            path = os.path.join(EXPORT_DIR, f"{safe}_{date.today().strftime('%Y%m%d')}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([header for _, header in report["columns"]])
            for row in report["rows"]:
                writer.writerow([row.get(key, "") for key, _ in report["columns"]])
        return path
