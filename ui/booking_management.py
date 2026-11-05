"""
Booking management (admin: all bookings; passenger: "My bookings").

* Lookup by booking ID uses the custom HashTable – the screen shows which
  bucket was probed and how many chain entries were compared.
* The undo panel shows the user's Stack from top to bottom.
"""

import json
import time
import tkinter as tk
from tkinter import ttk

from algorithms.sorting import SortStats
from services.booking_service import BOOKING_SORT_KEYS
from ui.components import (Button, Card, DataTable, Dialog, ListToolbar, PageHeader,
                           auto_wrap, card_title, combo, confirm, labeled, show_error,
                           sort_info_text, toast)
from ui.seat_selection import SeatSelectionDialog, open_seat_selection, show_booking_details
from ui.theme import C, font, mono
from utils.constants import BOOKING_STATUSES
from utils.helpers import format_currency


class BookingManagementPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        self.session = ctx.session
        admin = self.session.is_admin
        header = PageHeader(self, "Bookings" if admin else "My Bookings",
                            "Create, find, change and cancel reservations" if admin else
                            "Your tickets, waiting-list requests and history")
        header.pack(fill="x", pady=(0, 10))
        if admin:
            header.add_action("New booking", self.new_booking, icon="ticket")
        else:
            header.add_action("Find buses", lambda: ctx.navigate("search"), icon="search")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        main = tk.Frame(nb, bg=C["background"])
        log = tk.Frame(nb, bg=C["background"])
        nb.add(main, text="Bookings")
        nb.add(log, text="Activity history")
        nb.bind("<<NotebookTabChanged>>",
                lambda e: self._refresh_log() if nb.index("current") == 1 else None)
        self._build_main(main)
        self._build_log(log)

    # ------------------------------------------------------------------ main
    def _build_main(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=0, minsize=250)
        tab.grid_rowconfigure(0, weight=1)

        card = Card(tab, padding=14)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(10, 0))
        lookup = tk.Frame(card.body, bg=C["primary_light"])
        lookup.pack(fill="x", pady=(0, 10))
        tk.Label(lookup, text="Booking ID lookup (hash table)", bg=C["primary_light"],
                 fg=C["primary_dark"], font=font(9, "bold")).pack(side="left", padx=(12, 8),
                                                                  pady=8)
        self.id_entry = ttk.Entry(lookup, width=14, font=mono(10))
        self.id_entry.pack(side="left")
        self.id_entry.bind("<Return>", lambda e: self.lookup())
        Button(lookup, "Look up", self.lookup, small=True).pack(side="left", padx=8)
        self.lookup_info = tk.Label(lookup, text="", bg=C["primary_light"], fg=C["text"],
                                    font=font(9), anchor="w")
        self.lookup_info.pack(side="left", fill="x", expand=True)
        auto_wrap(self.lookup_info)

        self.toolbar = ListToolbar(card.body, self.refresh, list(BOOKING_SORT_KEYS.keys()),
                                   "Status", ["All", *BOOKING_STATUSES],
                                   placeholder="ID, passenger or bus…", wrap=True)
        self.toolbar.search.entry.configure(width=20)
        self.toolbar.pack(fill="x", pady=(0, 6))
        self.info = auto_wrap(tk.Label(card.body, text="", bg=C["card"], fg=C["text_light"], font=font(8),
                             anchor="w"))
        self.info.pack(fill="x")

        cols = [("id", "Booking ID", 100, "w"), ("passenger", "Passenger", 140, "w"),
                ("bus", "Bus", 190, "w"), ("trip", "From → To", 170, "w"),
                ("travel", "Travel", 90, "center"), ("seat", "Seat", 50, "center"),
                ("amount", "Amount", 85, "e"), ("booked", "Booked on", 140, "w"),
                ("status", "Status", 90, "center")]
        if not self.session.is_admin:
            cols.pop(1)
        self.table = DataTable(card.body, cols, height=8, status_column="status",
                               on_double=lambda iid: self.view(),
                               empty_text="No bookings found.")
        self.table.pack(fill="both", expand=True, pady=(6, 0))

        actions = tk.Frame(card.body, bg=C["card"])
        actions.pack(fill="x", pady=(10, 0))
        Button(actions, "View confirmation", self.view, "secondary").pack(side="left")
        Button(actions, "Change seat", self.change_seat, "secondary").pack(side="left", padx=8)
        Button(actions, "Cancel booking", self.cancel, "danger").pack(side="right")

        side = Card(tab, padding=14)
        side.grid(row=0, column=1, sticky="nsew", pady=(10, 0))
        card_title(side.body, "Undo stack (LIFO)",
                   "Top = most recent action. Undo pops the top item.").pack(fill="x")
        self.stack_frame = tk.Frame(side.body, bg=C["card"])
        self.stack_frame.pack(fill="both", expand=True, pady=10)
        Button(side.body, "Undo last action", self.ctx.undo, icon="undo").pack(fill="x")
        self.hash_info = tk.Label(side.body, text="", bg=C["card"], fg=C["text_light"],
                                  font=font(8), justify="left", anchor="w", wraplength=210)
        self.hash_info.pack(fill="x", pady=(12, 0))

    def refresh(self):
        stats = SortStats()
        start = time.perf_counter()
        bookings = self.app.bookings.list_bookings(self.session, self.toolbar.query,
                                                   self.toolbar.filter, self.toolbar.sort_by,
                                                   self.toolbar.algorithm, stats=stats)
        elapsed = (time.perf_counter() - start) * 1000
        rows = []
        for b in bookings:
            values = [b.booking_id, b.passenger_name, b.bus_label, f"{b.from_city} → {b.to_city}",
                      b.travel_date, b.seat_label, format_currency(b.amount), b.booking_date,
                      b.status]
            if not self.session.is_admin:
                values.pop(1)
            rows.append((b.booking_id, tuple(values)))
        self.table.set_rows(rows)
        self.info.configure(text=sort_info_text(len(bookings), self.toolbar.algorithm, stats,
                                                elapsed, "bookings"))
        self._draw_stack()
        st = self.app.bookings.index.stats()
        self.hash_info.configure(
            text=f"Hash table: {st['size']} bookings in {st['capacity']} buckets · load factor "
                 f"{st['load_factor']} · longest chain {st['longest_chain']} · "
                 f"{st['collisions']} collisions handled by separate chaining")

    def _draw_stack(self):
        for w in self.stack_frame.winfo_children():
            w.destroy()
        items = self.app.bookings.undo_preview(self.session)
        if not items:
            tk.Label(self.stack_frame, text="Stack is empty.\nYour booking actions will "
                                            "appear here.", bg=C["card"], fg=C["text_light"],
                     font=font(9), justify="center").pack(pady=20)
            return
        for i, text in enumerate(items[:7]):
            top = i == 0
            box = tk.Frame(self.stack_frame, bg=C["primary"] if top else "#F1F5F9")
            box.pack(fill="x", pady=2)
            tk.Label(box, text=("TOP  " if top else "") + text, bg=box["bg"],
                     fg="white" if top else C["text"], font=font(8, "bold" if top else "normal"),
                     wraplength=200, justify="left", anchor="w").pack(fill="x", padx=8, pady=6)
        if len(items) > 7:
            tk.Label(self.stack_frame, text=f"… {len(items) - 7} more below", bg=C["card"],
                     fg=C["text_light"], font=font(8)).pack()

    # --------------------------------------------------------------- actions
    def lookup(self):
        key = self.id_entry.get().strip().upper()
        if not key:
            toast(self, "Enter a booking ID such as SB-7KQ2MX.", "warning")
            return
        start = time.perf_counter()
        bucket, compared, booking = self.app.bookings.index.search_trace(key)
        elapsed = (time.perf_counter() - start) * 1_000_000
        if booking is None or (not self.session.is_admin and
                               booking.passenger_id != self.session.passenger_id):
            self.lookup_info.configure(text=f"Not found · bucket {bucket} probed, "
                                            f"{len(compared)} key(s) compared")
            toast(self, f"No booking found with ID {key}.", "error")
            return
        self.lookup_info.configure(text=f"Found in bucket {bucket} after {len(compared)} "
                                        f"comparison(s) · {elapsed:.1f} µs")
        self.toolbar.search.entry.set("")
        self.toolbar.filter_box.set("All")
        self.refresh()
        self.table.select(key)
        show_booking_details(self, self.app, booking)

    def _selected_booking(self):
        iid = self.table.selected()
        if iid is None:
            toast(self, "Please select a booking first.", "warning")
            return None
        return self.app.bookings.get_booking(iid)

    def view(self):
        booking = self._selected_booking()
        if booking:
            show_booking_details(self, self.app, booking)

    def cancel(self):
        booking = self._selected_booking()
        if booking is None:
            return
        if booking.status == "Cancelled":
            toast(self, "This booking is already cancelled.", "info")
            return
        what = "waiting-list request" if booking.status == "Waiting" else \
            f"seat {booking.seat_number}"
        if not confirm(self, "Cancel booking",
                       f"Cancel booking {booking.booking_id} ({what} on {booking.bus_label})?"
                       "\n\nIf passengers are waiting, the seat goes to the first one in the "
                       "queue. You can undo this while the seat is still free."):
            return
        try:
            result = self.app.bookings.cancel_booking(self.session, booking.booking_id)
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)
            return
        toast(self, result.message(), "success")
        self.ctx.refresh_all()

    def change_seat(self):
        booking = self._selected_booking()
        if booking is None:
            return
        if booking.status != "Confirmed":
            toast(self, "Only confirmed bookings can change seats.", "warning")
            return
        try:
            SeatSelectionDialog(self, self.ctx, booking.bus_id, mode="change", booking=booking,
                                on_done=self.ctx.refresh_all)
        except Exception as exc:      # noqa: BLE001
            show_error(self, exc)

    def new_booking(self):
        NewBookingDialog(self, self.ctx)

    # ------------------------------------------------------------------- log
    def _build_log(self, tab):
        card = Card(tab, padding=14)
        card.pack(fill="both", expand=True, pady=(10, 0))
        card_title(card.body, "Activity history",
                   "Every booking operation is stored in booking_history. The undo stack is "
                   "rebuilt from this table after a restart.").pack(fill="x", pady=(0, 8))
        self.log = DataTable(card.body, [
            ("id", "#", 50, "center"), ("time", "Time", 150, "w"), ("user", "User", 170, "w"),
            ("action", "Action", 90, "center"), ("booking", "Booking", 100, "w"),
            ("details", "Details", 330, "w"), ("undo", "Undo state", 110, "center")],
            height=8, empty_text="No activity recorded yet.")
        self.log.pack(fill="both", expand=True)

    def _refresh_log(self):
        rows = []
        for r in self.app.bookings.history_log(self.session):
            try:
                details = json.loads(r["details"])
            except ValueError:
                details = {}
            text = ", ".join(f"{k}={v}" for k, v in details.items() if k != "bus_id")
            state = "undone" if r["undone"] else ("can undo" if r["undoable"] else "—")
            rows.append((r["history_id"], (r["history_id"], r["created_at"],
                                           r["username"] or "system", r["action"],
                                           r["booking_id"] or "", text, state)))
        self.log.set_rows(rows)


class NewBookingDialog(Dialog):
    """Admin: pick passenger + bus, then continue to the seat map."""

    def __init__(self, parent, ctx):
        super().__init__(parent, "New booking", width=520)
        self.ctx = ctx
        app = ctx.app
        people = app.passengers.list_passengers(sort_by="Name (A → Z)")
        self.people = {f"{p.full_name} — {p.email}": p.passenger_id for p in people}
        buses = app.buses.list_buses(status="Active", sort_by="Departure (earliest)")
        self.buses = {f"{b.travel_date} {b.departure_time} · {b.label} · {b.route_name} · "
                      f"{b.available_seats} free": b.bus_id for b in buses}
        self.p_box = labeled(self.body, "Passenger", lambda p: combo(p, list(self.people)))
        self.p_box.pack(fill="x", pady=6)
        self.b_box = labeled(self.body, "Bus", lambda p: combo(p, list(self.buses), width=60))
        self.b_box.pack(fill="x", pady=6)
        self.add_button("Choose seats →", self._next)
        self.add_button("Cancel", self.destroy, "secondary")
        self.show()

    def _next(self):
        pid = self.people.get(self.p_box.widget.get())
        bus_id = self.buses.get(self.b_box.widget.get())
        if pid is None or bus_id is None:
            toast(self, "Choose a passenger and a bus.", "warning")
            return
        parent = self.master
        self.destroy()
        try:
            open_seat_selection(parent, self.ctx, bus_id, passenger_id=pid,
                                on_done=self.ctx.refresh_all)
        except Exception as exc:     # noqa: BLE001
            show_error(parent, exc)
