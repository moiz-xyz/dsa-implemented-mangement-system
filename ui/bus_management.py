"""Bus management: add, edit, delete, view, search and sort buses."""

import time
import tkinter as tk
from tkinter import ttk

from algorithms.sorting import SortStats
from services.bus_service import BUS_SORT_KEYS
from ui.components import (Button, Card, DataTable, Dialog, ListToolbar, PageHeader,
                           auto_wrap, combo, confirm, labeled, show_error, sort_info_text, toast)
from ui.seat_selection import open_seat_selection
from ui.theme import C, font
from utils.constants import BUS_STATUSES, BUS_TYPES
from utils.helpers import format_currency, today_str

COLUMNS = [("id", "ID", 45, "center"), ("name", "Bus name", 150, "w"),
           ("number", "Number", 90, "w"), ("type", "Type", 95, "w"),
           ("route", "Route", 200, "w"), ("date", "Date", 95, "center"),
           ("dep", "Dep.", 60, "center"), ("arr", "Arr.", 60, "center"),
           ("price", "Price", 85, "e"), ("seats", "Booked", 75, "center"),
           ("avail", "Free", 55, "center"), ("wait", "Waiting", 65, "center"),
           ("status", "Status", 95, "center")]


class BusManagementPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        header = PageHeader(self, "Bus Management",
                            "Fleet, schedules and seat capacity")
        header.pack(fill="x", pady=(0, 14))
        header.add_action("Add bus", self.add_bus, icon="bus")

        card = Card(self, padding=14)
        card.pack(fill="both", expand=True)
        self.toolbar = ListToolbar(card.body, self.refresh, list(BUS_SORT_KEYS.keys()),
                                   "Status", ["All", *BUS_STATUSES],
                                   placeholder="Search name, number, route…")
        self.toolbar.pack(fill="x", pady=(0, 10))

        lookup = tk.Frame(card.body, bg=C["card"])
        lookup.pack(fill="x", pady=(0, 10))
        tk.Label(lookup, text="Exact lookup by bus number (binary search):", bg=C["card"],
                 fg=C["text_muted"], font=font(9)).pack(side="left")
        self.lookup_entry = ttk.Entry(lookup, width=14)
        self.lookup_entry.pack(side="left", padx=6)
        self.lookup_entry.bind("<Return>", lambda e: self.lookup())
        Button(lookup, "Find", self.lookup, "secondary", small=True).pack(side="left")
        self.info = auto_wrap(tk.Label(card.body, text="", bg=C["card"], fg=C["text_light"],
                                       font=font(8), anchor="w"))
        self.info.pack(fill="x", pady=(0, 6))

        self.table = DataTable(card.body, COLUMNS, height=8, status_column="status",
                               on_double=lambda iid: self.edit_bus(),
                               empty_text="No buses match your search.")
        self.table.pack(fill="both", expand=True)

        actions = tk.Frame(card.body, bg=C["card"])
        actions.pack(fill="x", pady=(12, 0))
        Button(actions, "Edit", self.edit_bus, "secondary").pack(side="left")
        Button(actions, "Seat map / book", self.view_seats, "secondary").pack(side="left",
                                                                            padx=8)
        Button(actions, "Cancel bus", self.cancel_bus, "secondary").pack(side="left")
        Button(actions, "Delete", self.delete_bus, "danger").pack(side="right")

    def refresh(self):
        stats = SortStats()
        start = time.perf_counter()
        buses = self.app.buses.list_buses(self.toolbar.query, self.toolbar.filter,
                                          self.toolbar.sort_by, self.toolbar.algorithm,
                                          stats=stats)
        elapsed = (time.perf_counter() - start) * 1000
        rows = []
        for b in buses:
            rows.append((b.bus_id, (b.bus_id, b.bus_name, b.bus_number, b.bus_type,
                                    b.route_name, b.travel_date, b.departure_time,
                                    b.arrival_time, format_currency(b.ticket_price),
                                    f"{b.booked_seats}/{b.total_seats}", b.available_seats,
                                    b.waiting_count, b.status)))
        self.table.set_rows(rows)
        self.info.configure(text=sort_info_text(len(buses), self.toolbar.algorithm, stats,
                                                elapsed, "buses"))

    def _selected(self):
        iid = self.table.selected()
        if iid is None:
            toast(self, "Please select a bus first.", "warning")
            return None
        return int(iid)

    def lookup(self):
        number = self.lookup_entry.get().strip()
        if not number:
            toast(self, "Enter a bus number, e.g. KHI-1001.", "warning")
            return
        bus, comparisons = self.app.buses.find_by_number(number)
        if bus is None:
            toast(self, f"No bus with number {number.upper()} "
                        f"({comparisons} binary-search comparisons).", "error")
            return
        self.toolbar.search.entry.set("")
        self.refresh()
        self.table.select(bus.bus_id)
        toast(self, f"Found {bus.label} in {comparisons} comparisons (binary search).", "info")

    def add_bus(self):
        BusFormDialog(self, self.app, None, self._saved)

    def edit_bus(self):
        bus_id = self._selected()
        if bus_id is not None:
            BusFormDialog(self, self.app, self.app.buses.get(bus_id), self._saved)

    def _saved(self, bus, created):
        toast(self, f"{bus.label} {'added' if created else 'updated'} successfully.")
        self.ctx.refresh_all()
        self.table.select(bus.bus_id)

    def view_seats(self):
        bus_id = self._selected()
        if bus_id is not None:
            try:
                open_seat_selection(self, self.ctx, bus_id, on_done=self.ctx.refresh_all)
            except Exception as exc:     # noqa: BLE001
                show_error(self, exc)

    def cancel_bus(self):
        bus_id = self._selected()
        if bus_id is None:
            return
        bus = self.app.buses.get(bus_id)
        if not confirm(self, "Cancel bus",
                       f"Cancel {bus.label}?\n\nAll {bus.booked_seats} confirmed booking(s) and "
                       f"{bus.waiting_count} waiting request(s) will be cancelled and the bus "
                       "will be marked as Cancelled. This cannot be undone."):
            return
        try:
            count = self.app.bookings.cancel_bus(self.ctx.session, bus_id)
        except Exception as exc:          # noqa: BLE001
            show_error(self, exc)
            return
        toast(self, f"{bus.label} cancelled · {count} booking(s) cancelled.")
        self.ctx.refresh_all()

    def delete_bus(self):
        bus_id = self._selected()
        if bus_id is None:
            return
        bus = self.app.buses.get(bus_id)
        if not confirm(self, "Delete bus", f"Permanently delete {bus.label}?"):
            return
        try:
            self.app.buses.delete_bus(bus_id)
        except Exception as exc:          # noqa: BLE001
            show_error(self, exc)
            return
        toast(self, f"{bus.label} deleted.")
        self.ctx.refresh_all()


class BusFormDialog(Dialog):
    def __init__(self, parent, app, bus, on_saved):
        super().__init__(parent, "Edit bus" if bus else "Add bus", width=620)
        self.app = app
        self.bus = bus
        self.on_saved = on_saved
        routes = app.routes.list_routes(sort_by="name")
        self.route_ids = {r.route_name: r.route_id for r in routes}

        grid = self.body
        for col in (0, 1):
            grid.grid_columnconfigure(col, weight=1, uniform="form")
        self.widgets = {}

        def place(key, label, factory, row, col, hint=None, colspan=1):
            f = labeled(grid, label, factory, hint=hint)
            f.grid(row=row, column=col, columnspan=colspan, sticky="ew",
                   padx=(0 if col == 0 else 10, 0), pady=6)
            self.widgets[key] = f.widget

        place("bus_name", "Bus name", lambda p: ttk.Entry(p), 0, 0)
        place("bus_number", "Bus number", lambda p: ttk.Entry(p), 0, 1, "e.g. KHI-1001")
        place("bus_type", "Bus type", lambda p: combo(p, BUS_TYPES), 1, 0,
              "Sleeper = 3 seats per row, others = 4")
        place("total_seats", "Total seats", lambda p: ttk.Spinbox(p, from_=4, to=80), 1, 1)
        place("ticket_price", "Ticket price (Rs.)", lambda p: ttk.Entry(p), 2, 0)
        place("status", "Status", lambda p: combo(p, BUS_STATUSES), 2, 1)
        place("route", "Assigned route", lambda p: combo(p, list(self.route_ids.keys())), 3, 0,
              colspan=2)
        place("travel_date", "Travel date", lambda p: ttk.Entry(p), 4, 0, "YYYY-MM-DD")
        place("departure_time", "Departure time", lambda p: ttk.Entry(p), 5, 0, "HH:MM (24h)")
        place("arrival_time", "Arrival time", lambda p: ttk.Entry(p), 5, 1, "HH:MM (24h)")

        if bus:
            for key in ("bus_name", "bus_number", "total_seats", "ticket_price", "travel_date",
                        "departure_time", "arrival_time"):
                w = self.widgets[key]
                w.delete(0, "end")
                value = getattr(bus, key)
                w.insert(0, f"{value:.0f}" if key == "ticket_price" else str(value))
            self.widgets["bus_type"].set(bus.bus_type)
            self.widgets["status"].set(bus.status)
            self.widgets["route"].set(bus.route_name)
        else:
            self.widgets["total_seats"].set(40)
            self.widgets["travel_date"].insert(0, today_str())
            self.widgets["departure_time"].insert(0, "08:00")
            self.widgets["arrival_time"].insert(0, "14:00")

        self.add_button("Save bus", self._save)
        self.add_button("Cancel", self.destroy, "secondary")
        self.show()

    def _save(self):
        data = {k: w.get() for k, w in self.widgets.items() if k != "route"}
        data["route_id"] = self.route_ids.get(self.widgets["route"].get())
        try:
            if self.bus:
                bus = self.app.buses.update_bus(self.bus.bus_id, data)
            else:
                bus = self.app.buses.add_bus(data)
        except Exception as exc:          # noqa: BLE001
            show_error(self, exc)
            return
        self.destroy()
        self.on_saved(bus, self.bus is None)
