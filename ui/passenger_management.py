"""Passenger management: register, edit, delete safely, search, sort, booking history."""

import time
import tkinter as tk
from tkinter import ttk

from algorithms.sorting import SortStats
from services.passenger_service import PASSENGER_SORT_KEYS
from ui.components import (auto_wrap, Button, Card, DataTable, Dialog, ListToolbar, PageHeader,
                           card_title, confirm, labeled, show_error, sort_info_text, toast)
from ui.login_window import RegisterDialog
from ui.theme import C, font
from utils.helpers import format_currency


class PassengerManagementPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        header = PageHeader(self, "Passengers", "Registered passengers and their booking history")
        header.pack(fill="x", pady=(0, 14))
        header.add_action("Register passenger", self.register, icon="user")

        body = tk.Frame(self, bg=C["background"])
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        card = Card(body, padding=14)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.toolbar = ListToolbar(card.body, self.refresh, list(PASSENGER_SORT_KEYS.keys()),
                                   placeholder="Name, email or phone…", wrap=True)
        self.toolbar.pack(fill="x", pady=(0, 8))

        lookup = tk.Frame(card.body, bg=C["card"])
        lookup.pack(fill="x", pady=(0, 8))
        tk.Label(lookup, text="Exact email lookup (binary search):", bg=C["card"],
                 fg=C["text_muted"], font=font(9)).pack(side="left")
        self.email_entry = ttk.Entry(lookup, width=26)
        self.email_entry.pack(side="left", padx=6)
        self.email_entry.bind("<Return>", lambda e: self.lookup())
        Button(lookup, "Find", self.lookup, "secondary", small=True).pack(side="left")
        self.info = auto_wrap(tk.Label(card.body, text="", bg=C["card"], fg=C["text_light"], font=font(8),
                             anchor="w"))
        self.info.pack(fill="x")

        self.table = DataTable(card.body, [
            ("id", "ID", 45, "center"), ("name", "Full name", 160, "w"),
            ("email", "Email", 210, "w"), ("phone", "Phone", 115, "w"),
            ("reg", "Registered", 100, "center"), ("count", "Bookings", 70, "center")],
            height=8, on_select=self._show_history, on_double=lambda i: self.edit(),
            empty_text="No passengers match your search.")
        self.table.pack(fill="both", expand=True, pady=(6, 0))
        actions = tk.Frame(card.body, bg=C["card"])
        actions.pack(fill="x", pady=(10, 0))
        Button(actions, "Edit", self.edit, "secondary").pack(side="left")
        Button(actions, "Delete", self.delete, "danger").pack(side="right")

        side = Card(body, padding=14)
        side.grid(row=0, column=1, sticky="nsew")
        self.history_title = card_title(side.body, "Booking history",
                                        "Select a passenger to view their bookings.")
        self.history_title.pack(fill="x", pady=(0, 8))
        self.history = DataTable(side.body, [
            ("id", "Booking", 95, "w"), ("bus", "Bus", 150, "w"), ("seat", "Seat", 45, "center"),
            ("date", "Travel", 90, "center"), ("status", "Status", 85, "center")],
            height=8, status_column="status", empty_text="No bookings yet.")
        self.history.pack(fill="both", expand=True)
        self.spent = tk.Label(side.body, text="", bg=C["card"], fg=C["text_muted"],
                              font=font(9), anchor="w")
        self.spent.pack(fill="x", pady=(8, 0))

    def refresh(self):
        stats = SortStats()
        start = time.perf_counter()
        people = self.app.passengers.list_passengers(self.toolbar.query, self.toolbar.sort_by,
                                                     self.toolbar.algorithm, stats=stats)
        elapsed = (time.perf_counter() - start) * 1000
        self.table.set_rows([(p.passenger_id, (p.passenger_id, p.full_name, p.email, p.phone,
                                               p.registration_date[:10], p.total_bookings))
                             for p in people])
        self.info.configure(text=sort_info_text(len(people), self.toolbar.algorithm, stats,
                                                elapsed, "passengers"))

    def _selected(self):
        iid = self.table.selected()
        if iid is None:
            toast(self, "Please select a passenger first.", "warning")
            return None
        return int(iid)

    def _show_history(self, iid):
        if iid is None:
            return
        passenger = self.app.passengers.get(int(iid))
        bookings = self.app.bookings.list_bookings(passenger_id=passenger.passenger_id,
                                                   sort_by="Booking date (newest)")
        title, subtitle = self.history_title.winfo_children()
        title.configure(text=passenger.full_name)
        subtitle.configure(text=f"{passenger.email} · {passenger.phone}")
        self.history.set_rows([(b.booking_id, (b.booking_id, b.bus_label, b.seat_label,
                                               b.travel_date, b.status)) for b in bookings])
        spent = sum(b.amount for b in bookings if b.status == "Confirmed")
        self.spent.configure(text=f"{len(bookings)} bookings · {format_currency(spent)} "
                                  "in confirmed tickets")

    def lookup(self):
        email = self.email_entry.get().strip()
        if not email:
            toast(self, "Enter an email address.", "warning")
            return
        passenger, comparisons = self.app.passengers.find_by_email(email)
        if passenger is None:
            toast(self, f"No passenger with that email ({comparisons} comparisons).", "error")
            return
        self.toolbar.search.entry.set("")
        self.refresh()
        self.table.select(passenger.passenger_id)
        toast(self, f"Found {passenger.full_name} in {comparisons} comparisons.", "info")

    def register(self):
        RegisterDialog(self, self.app, self._registered, title="Register passenger")

    def _registered(self, passenger):
        toast(self, f"{passenger.full_name} registered.")
        self.refresh()
        self.table.select(passenger.passenger_id)

    def edit(self):
        pid = self._selected()
        if pid is not None:
            EditPassengerDialog(self, self.app, self.app.passengers.get(pid), self._edited)

    def _edited(self, passenger):
        toast(self, f"{passenger.full_name} updated.")
        self.app.bookings.reload()          # refresh name snapshots in the hash table
        self.refresh()
        self.table.select(passenger.passenger_id)

    def delete(self):
        pid = self._selected()
        if pid is None:
            return
        passenger = self.app.passengers.get(pid)
        if not confirm(self, "Delete passenger",
                       f"Delete {passenger.full_name}'s account?\n\nPast bookings stay in the "
                       "reports, but the passenger will no longer be able to sign in."):
            return
        try:
            self.app.delete_passenger(pid)
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)
            return
        toast(self, f"{passenger.full_name} deleted.")
        self.ctx.refresh_all()


class EditPassengerDialog(Dialog):
    def __init__(self, parent, app, passenger, on_saved):
        super().__init__(parent, "Edit passenger", width=440)
        self.app = app
        self.passenger = passenger
        self.on_saved = on_saved
        self.fields = {}
        for key, label in (("full_name", "Full name"), ("email", "Email"),
                           ("phone", "Phone number")):
            f = labeled(self.body, label, lambda p: ttk.Entry(p))
            f.pack(fill="x", pady=5)
            f.widget.insert(0, getattr(passenger, key))
            self.fields[key] = f.widget
        self.add_button("Save changes", self._save)
        self.add_button("Cancel", self.destroy, "secondary")
        self.show()

    def _save(self):
        try:
            passenger = self.app.passengers.update(self.passenger.passenger_id,
                                                   self.fields["full_name"].get(),
                                                   self.fields["email"].get(),
                                                   self.fields["phone"].get())
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)
            return
        self.destroy()
        self.on_saved(passenger)
