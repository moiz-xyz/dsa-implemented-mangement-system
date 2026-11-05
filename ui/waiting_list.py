"""
Waiting list management – every bus has its own FIFO Queue.

The table lists passengers in queue order; the canvas draws the selected
bus's queue from FRONT (next to receive a seat) to REAR (most recent).
"""

import tkinter as tk

from ui.components import (Button, Card, DataTable, PageHeader, combo, confirm, show_error,
                           toast)
from ui.theme import C, font


class WaitingListPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        self.session = ctx.session
        admin = self.session.is_admin
        PageHeader(self, "Waiting List",
                   "FIFO queues – a freed seat is allocated automatically to the front passenger"
                   if admin else "Your position in each bus's FIFO queue").pack(
            fill="x", pady=(0, 14))

        card = Card(self, padding=14)
        card.pack(fill="both", expand=True)
        bar = tk.Frame(card.body, bg=C["card"])
        bar.pack(fill="x", pady=(0, 10))
        tk.Label(bar, text="Bus", bg=C["card"], fg=C["text_muted"], font=font(9)).pack(
            side="left", padx=(0, 6))
        self.bus_box = combo(bar, ["All buses"], width=48)
        self.bus_box.pack(side="left")
        self.bus_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.summary = tk.Label(bar, text="", bg=C["card"], fg=C["text_muted"], font=font(9))
        self.summary.pack(side="right")

        self.queue_canvas = tk.Canvas(card.body, height=110, bg="#F8FAFC", highlightthickness=1,
                                      highlightbackground=C["border"])
        self.queue_canvas.pack(fill="x", pady=(0, 10))
        self.queue_canvas.bind("<Configure>", lambda e: self._draw_queue())

        self.table = DataTable(card.body, [
            ("pos", "Queue position", 110, "center"), ("name", "Passenger", 180, "w"),
            ("bus", "Bus", 230, "w"), ("booking", "Booking ID", 110, "w"),
            ("date", "Request date", 160, "w"), ("status", "Status", 100, "center")],
            height=8, status_column="status",
            empty_text="Nobody is waiting. Queues appear when a bus is fully booked.")
        self.table.pack(fill="both", expand=True)
        actions = tk.Frame(card.body, bg=C["card"])
        actions.pack(fill="x", pady=(10, 0))
        Button(actions, "Remove from queue", self.remove, "danger").pack(side="right")
        tk.Label(actions, text="enqueue: O(1) at rear · dequeue: O(1) from front · position "
                               "lookup: O(n)", bg=C["card"], fg=C["text_light"],
                 font=font(8)).pack(side="left")
        self._bus_ids = {}
        self._rows = []

    def refresh(self):
        pid = None if self.session.is_admin else self.session.passenger_id
        entries = self.app.bookings.waiting_entries(passenger_id=pid)
        labels = {}
        for r in entries:
            labels[r["bus_label"]] = r["bus_id"]
        self._bus_ids = labels
        options = ["All buses"] + list(labels.keys())
        current = self.bus_box.get()
        self.bus_box.configure(values=options)
        if current not in options:
            self.bus_box.set("All buses")
        chosen = self._bus_ids.get(self.bus_box.get())
        if chosen is not None:
            entries = [r for r in entries if r["bus_id"] == chosen]
        self._rows = entries
        self.table.set_rows([(r["entry"].booking_id, (f"#{r['position']}", r["passenger_name"],
                                                      r["bus_label"], r["entry"].booking_id,
                                                      r["request_date"], r["status"]))
                             for r in entries])
        buses = len({r["bus_id"] for r in entries})
        self.summary.configure(text=f"{len(entries)} waiting · {buses} bus queue(s)")
        self._draw_queue()

    def _draw_queue(self):
        cv = self.queue_canvas
        cv.delete("all")
        chosen = self._bus_ids.get(self.bus_box.get())
        if chosen is None:
            bus_ids = list(dict.fromkeys(r["bus_id"] for r in self._rows))
            chosen = bus_ids[0] if bus_ids else None
        if chosen is None:
            cv.create_text(20, 55, text="Queue is empty – is_empty() = True", anchor="w",
                           fill=C["text_light"], font=font(10))
            return
        queue = self.app.bookings.queue_for(chosen)
        names = []
        for entry in queue:                       # traverse front -> rear
            b = self.app.bookings.index.search(entry.booking_id)
            names.append(b.passenger_name if b else entry.passenger_name)
        label = next((r["bus_label"] for r in self._rows if r["bus_id"] == chosen), "")
        cv.create_text(16, 14, text=f"Queue for {label}", anchor="w", fill=C["text"],
                       font=font(9, "bold"))
        x, y, w, h = 16, 36, 130, 46
        mine = self.session.display_name
        for i, name in enumerate(names):
            highlight = (not self.session.is_admin and name == mine)
            fill = C["primary"] if i == 0 else (C["secondary"] if highlight else C["card"])
            fg = "white" if i == 0 else C["text"]
            cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=C["primary"], width=2)
            cv.create_text(x + w / 2, y + 16, text=name, fill=fg, font=font(9, "bold"),
                           width=w - 10)
            cv.create_text(x + w / 2, y + 34, text=f"position {i + 1}", fill=fg, font=font(8))
            if i < len(names) - 1:
                cv.create_line(x + w, y + h / 2, x + w + 22, y + h / 2, arrow="last",
                               fill=C["text_muted"], width=2)
            x += w + 22
        cv.create_text(16, y + h + 14, text="FRONT (dequeue next)", anchor="w",
                       fill=C["primary"], font=font(8, "bold"))
        if names:
            cv.create_text(x - 22, y + h + 14, text="REAR (enqueue here)", anchor="e",
                           fill=C["text_muted"], font=font(8, "bold"))

    def remove(self):
        iid = self.table.selected()
        if iid is None:
            toast(self, "Select a waiting passenger first.", "warning")
            return
        booking = self.app.bookings.get_booking(iid)
        if not confirm(self, "Remove from waiting list",
                       f"Remove {booking.passenger_name} from the queue for "
                       f"{booking.bus_label}? Everyone behind moves up one place."):
            return
        try:
            self.app.bookings.cancel_booking(self.session, booking.booking_id,
                                             "Left the waiting list")
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        toast(self, f"{booking.passenger_name} removed from the waiting list.")
        self.ctx.refresh_all()
