"""
Passenger portal: bus search, my bookings, waiting list, route planner,
profile and the DSA Lab.
"""

import time
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from algorithms.sorting import ALGORITHM_NAMES, DEFAULT_ALGORITHM, SortStats
from services.bus_service import SEARCH_SORT_KEYS
from ui.components import (Button, Card, DataTable, FlowFrame, PageHeader, card_title, combo,
                           labeled, labeled_inline, show_error, sort_info_text, toast)
from ui.seat_selection import open_seat_selection
from ui.theme import C, font
from utils.constants import DATE_FMT
from utils.helpers import format_currency, format_distance


class SearchBusesPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        greeting = ctx.session.display_name.split()[0]
        PageHeader(self, f"Where to, {greeting}?" if not ctx.session.is_admin else "Find buses",
                   "Search upcoming buses, compare and reserve your seat").pack(
            fill="x", pady=(0, 14))

        form = Card(self, padding=16)
        form.pack(fill="x")
        # Both rows are FlowFrames: fields wrap onto a new line on small screens.
        fields = FlowFrame(form.body, hgap=12, vgap=10)
        fields.pack(fill="x")
        self.src = fields.add(labeled(fields, "From", lambda p: combo(p, [], width=16)),
                              gap=4)
        swap = tk.Frame(fields, bg=C["card"])
        tk.Label(swap, text=" ", bg=C["card"], font=font(9, "bold")).pack()
        Button(swap, "⇄", self._swap, "ghost", small=True).pack()
        fields.add(swap, gap=4)
        self.dst = fields.add(labeled(fields, "To", lambda p: combo(p, [], width=16)))
        self.date = fields.add(labeled(fields, "Travel date", lambda p: ttk.Entry(p, width=14),
                                       hint="YYYY-MM-DD · empty = any"))
        self.after_time = fields.add(labeled(fields, "Depart after",
                                             lambda p: ttk.Entry(p, width=8), hint="HH:MM"))
        self.max_price = fields.add(labeled(fields, "Max price (Rs.)",
                                            lambda p: ttk.Entry(p, width=10)))

        row2 = FlowFrame(form.body, hgap=6, vgap=8)
        row2.pack(fill="x", pady=(12, 0))
        self.min_seats = labeled_inline(row2, "Min. free seats",
                                        lambda p: ttk.Spinbox(p, from_=0, to=10, width=4))
        self.min_seats.set(0)
        for text, days in (("Today", 0), ("Tomorrow", 1), ("Any date", None)):
            row2.add(Button(row2, text, lambda d=days: self._quick_date(d), "ghost",
                            small=True), gap=2)
        row2.add(tk.Frame(row2, bg=C["card"], width=12, height=1), gap=0)
        self.sort_box = labeled_inline(row2, "Sort results",
                                       lambda p: combo(p, list(SEARCH_SORT_KEYS.keys()),
                                                       width=20))
        self.sort_box.bind("<<ComboboxSelected>>", lambda e: self.search(quiet=True))
        self.algo_box = labeled_inline(row2, "using",
                                       lambda p: combo(p, ALGORITHM_NAMES, width=14))
        self.algo_box.set(DEFAULT_ALGORITHM)
        self.algo_box.bind("<<ComboboxSelected>>", lambda e: self.search(quiet=True))
        row2.add(Button(row2, "Search buses", self.search, icon="search"))

        results = Card(self, padding=14)
        results.pack(fill="both", expand=True, pady=(12, 0))
        self.result_title = card_title(results.body, "Available buses",
                                       "Choose cities and press Search.")
        self.result_title.pack(fill="x", pady=(0, 8))
        self.table = DataTable(results.body, [
            ("bus", "Bus", 190, "w"), ("type", "Type", 95, "w"),
            ("date", "Date", 95, "center"), ("dep", "Departs", 70, "center"),
            ("arr", "Arrives", 70, "center"), ("dist", "Distance", 80, "e"),
            ("price", "Fare", 85, "e"), ("free", "Free seats", 80, "center"),
            ("route", "Route", 220, "w")], height=8,
            on_double=lambda iid: self.select_seats(),
            empty_text="No buses yet – try another date or remove filters.")
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(results.body, bg=C["card"])
        actions.pack(fill="x", pady=(10, 0))
        self.info = tk.Label(actions, text="", bg=C["card"], fg=C["text_light"], font=font(8))
        self.info.pack(side="left")
        Button(actions, "Select seats →", self.select_seats).pack(side="right")
        self._loaded = False

    def refresh(self):
        cities = self.app.routes.all_cities()
        for box in (self.src.widget, self.dst.widget):
            box.configure(values=cities)
        if not self._loaded and cities:
            self.src.widget.set("Karachi" if "Karachi" in cities else cities[0])
            self.dst.widget.set("Lahore" if "Lahore" in cities else cities[-1])
            self._loaded = True
            self.search(quiet=True)
        elif self._loaded:
            self.search(quiet=True)

    def _swap(self):
        a, b = self.src.widget.get(), self.dst.widget.get()
        self.src.widget.set(b)
        self.dst.widget.set(a)

    def _quick_date(self, days):
        entry = self.date.widget
        entry.delete(0, "end")
        if days is not None:
            entry.insert(0, (date.today() + timedelta(days=days)).strftime(DATE_FMT))
        self.search()

    def search(self, quiet=False):
        stats = SortStats()
        start = time.perf_counter()
        try:
            buses = self.app.buses.search_buses(
                self.src.widget.get(), self.dst.widget.get(), self.date.widget.get().strip(),
                self.after_time.widget.get().strip(), self.max_price.widget.get().strip(),
                self.min_seats.get().strip() if self.min_seats.get().strip() not in ("", "0")
                else None, self.sort_box.get(), self.algo_box.get(), stats=stats)
        except Exception as exc:      # noqa: BLE001
            if not quiet:
                show_error(self, exc)
            return
        elapsed = (time.perf_counter() - start) * 1000
        self._buses = {b.bus_id: b for b in buses}
        rows = []
        for b in buses:
            free = "FULL – waitlist" if b.available_seats == 0 else b.available_seats
            rows.append((b.bus_id, (b.label, b.bus_type, b.travel_date, b.departure_time,
                                    b.arrival_time, format_distance(b.segment_distance),
                                    format_currency(b.ticket_price), free, b.route_name)))
        self.table.set_rows(rows)
        title, subtitle = self.result_title.winfo_children()
        title.configure(text=f"{len(buses)} bus(es) from {self.src.widget.get()} to "
                             f"{self.dst.widget.get()}")
        subtitle.configure(text="Matched with the route linked lists (stop order matters) · "
                                "double-click a bus to choose seats")
        self.info.configure(text=sort_info_text(len(buses), self.algo_box.get(), stats, elapsed,
                                                "results"))

    def select_seats(self):
        iid = self.table.selected()
        if iid is None:
            toast(self, "Select a bus from the results first.", "warning")
            return
        try:
            open_seat_selection(self, self.ctx, int(iid), from_city=self.src.widget.get(),
                                to_city=self.dst.widget.get(), on_done=self._booked)
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)

    def _booked(self):
        self.ctx.refresh_all()


class ProfilePage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        PageHeader(self, "My Profile", "Update your contact details and password").pack(
            fill="x", pady=(0, 14))
        wrap = tk.Frame(self, bg=C["background"])
        wrap.pack(fill="x")
        details = Card(wrap, padding=18)
        details.pack(side="left", fill="both", expand=True, padx=(0, 12))
        card_title(details.body, "Personal details").pack(fill="x", pady=(0, 8))
        self.fields = {}
        for key, label in (("full_name", "Full name"), ("email", "Email (used to sign in)"),
                           ("phone", "Phone number")):
            f = labeled(details.body, label, lambda p: ttk.Entry(p))
            f.pack(fill="x", pady=5)
            self.fields[key] = f.widget
        self.member = tk.Label(details.body, text="", bg=C["card"], fg=C["text_light"],
                               font=font(9), anchor="w")
        self.member.pack(fill="x", pady=(6, 10))
        Button(details.body, "Save details", self.save).pack(anchor="w")

        pw = Card(wrap, padding=18)
        pw.pack(side="left", fill="both", expand=True)
        card_title(pw.body, "Change password", "Passwords are stored as salted PBKDF2-SHA256 "
                                               "hashes").pack(fill="x", pady=(0, 8))
        self.pw = {}
        for key, label in (("old", "Current password"), ("new", "New password"),
                           ("confirm", "Confirm new password")):
            f = labeled(pw.body, label, lambda p: ttk.Entry(p, show="•"))
            f.pack(fill="x", pady=5)
            self.pw[key] = f.widget
        Button(pw.body, "Update password", self.change_password, "secondary").pack(
            anchor="w", pady=(10, 0))

    def refresh(self):
        p = self.app.passengers.get(self.ctx.session.passenger_id)
        for key, widget in self.fields.items():
            widget.delete(0, "end")
            widget.insert(0, getattr(p, key))
        self.member.configure(text=f"Passenger #{p.passenger_id} · member since "
                                   f"{p.registration_date[:10]} · {p.total_bookings} bookings")

    def save(self):
        try:
            p = self.app.passengers.update(self.ctx.session.passenger_id,
                                           self.fields["full_name"].get(),
                                           self.fields["email"].get(),
                                           self.fields["phone"].get())
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)
            return
        self.ctx.session.display_name = p.full_name
        self.ctx.session.username = p.email
        self.app.bookings.reload()
        toast(self, "Profile updated.")

    def change_password(self):
        if self.pw["new"].get() != self.pw["confirm"].get():
            toast(self, "New passwords do not match.", "error")
            return
        try:
            self.app.auth.change_password(self.ctx.session.user_id, self.pw["old"].get(),
                                          self.pw["new"].get())
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)
            return
        for w in self.pw.values():
            w.delete(0, "end")
        toast(self, "Password changed.")


class RoutePlannerPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        from ui.route_management import NetworkPanel
        PageHeader(self, "Route Planner", "Find the shortest road route between any two cities"
                   ).pack(fill="x", pady=(0, 4))
        self.panel = NetworkPanel(self, ctx)
        self.panel.pack(fill="both", expand=True)

    def refresh(self):
        self.panel.refresh()


def _search(parent, ctx):
    return SearchBusesPage(parent, ctx)


def _bookings(parent, ctx):
    from ui.booking_management import BookingManagementPage
    return BookingManagementPage(parent, ctx)


def _waiting(parent, ctx):
    from ui.waiting_list import WaitingListPage
    return WaitingListPage(parent, ctx)


def _planner(parent, ctx):
    return RoutePlannerPage(parent, ctx)


def _profile(parent, ctx):
    return ProfilePage(parent, ctx)


def _lab(parent, ctx):
    from ui.dsa_lab import DSALabPage
    return DSALabPage(parent, ctx)


PASSENGER_PAGES = [
    ("search", "Search Buses", "search", _search),
    ("bookings", "My Bookings", "ticket", _bookings),
    ("waiting", "My Waiting List", "queue", _waiting),
    ("planner", "Route Planner", "map", _planner),
    ("profile", "My Profile", "user", _profile),
    ("lab", "DSA Lab", "lab", _lab),
]
