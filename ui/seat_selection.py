"""
Interactive seat reservation.

The seat map is drawn directly from the bus's SeatMatrix (the custom 2-D
array). Hovering a seat shows how its seat number maps to an array index:

    seat 14 -> index 13 -> row = 13 // 4 = 3, column = 13 % 4 = 1

Colours: green = available, red = booked, blue = selected.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from data_structures.custom_array import SeatMatrix
from ui.components import Badge, Button, Dialog, combo, show_error, toast
from ui.theme import C, font, mono
from utils.constants import MAX_SEATS_PER_PASSENGER_PER_BUS
from utils.helpers import format_currency, format_distance

SEAT_W, SEAT_H, GAP, AISLE = 44, 38, 8, 30


class SeatSelectionDialog(Dialog):
    """
    mode="book":   choose seats and confirm a new booking (or join waiting list)
    mode="change": choose exactly one new seat for an existing booking
    """

    def __init__(self, parent, ctx, bus_id, mode="book", booking=None, from_city=None,
                 to_city=None, passenger_id=None, on_done=None):
        self.ctx = ctx
        self.app = ctx.app
        self.session = ctx.session
        self.bus = self.app.buses.get(bus_id)
        self.route = self.app.routes.get(self.bus.route_id)
        self.matrix = self.app.bookings.seat_map(bus_id)
        self.mode = mode
        self.booking = booking
        self.on_done = on_done
        self._from_hint, self._to_hint = from_city, to_city
        self._preset_passenger = passenger_id
        self.selected = []
        self.cells = {}
        title = "Change seat" if mode == "change" else "Select your seats"
        super().__init__(parent, f"{title} — {self.bus.label}", width=940, height=660)

        body = self.body
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # ---------------------------------------------------------- seat map
        left = tk.Frame(body, bg=C["card"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        legend = tk.Frame(left, bg=C["card"])
        legend.pack(fill="x", pady=(0, 8))
        for color, text in ((C["seat_available"], "Available"), (C["seat_booked"], "Booked"),
                            (C["seat_selected"], "Selected")):
            tk.Frame(legend, bg=color, width=14, height=14).pack(side="left", padx=(0, 5))
            tk.Label(legend, text=text, bg=C["card"], fg=C["text_muted"],
                     font=font(9)).pack(side="left", padx=(0, 16))
        holder = tk.Frame(left, bg="#F1F5F9", highlightthickness=1,
                          highlightbackground=C["border"])
        holder.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(holder, bg="#F1F5F9", highlightthickness=0)
        vbar = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(
            -1 if e.delta > 0 else 1, "units"))
        self.hover_info = tk.Label(left, text="Hover a seat to see its 2-D array position.",
                                   bg=C["card"], fg=C["text_muted"], font=mono(9), anchor="w",
                                   justify="left", wraplength=540)
        self.hover_info.pack(fill="x", pady=(8, 0))

        # ------------------------------------------------------ summary panel
        right = tk.Frame(body, bg=C["card"])
        right.grid(row=0, column=1, sticky="nsew")
        self._build_summary(right)

        if mode == "change":
            self.confirm_btn = self.add_button("Change seat", self._confirm_change)
        else:
            self.confirm_btn = self.add_button("Confirm booking", self._confirm_booking)
        self.add_button("Close", self.destroy, "secondary")
        self._update_summary()
        self.show()

    # ------------------------------------------------------------- summary
    def _build_summary(self, parent):
        b = self.bus
        tk.Label(parent, text=b.bus_name, bg=C["card"], fg=C["text"],
                 font=font(14, "bold"), anchor="w").pack(fill="x")
        tk.Label(parent, text=f"{b.bus_number} · {b.bus_type} · {b.total_seats} seats",
                 bg=C["card"], fg=C["text_muted"], font=font(9), anchor="w").pack(fill="x")
        tk.Label(parent, text=f"{b.travel_date}   {b.departure_time} → {b.arrival_time}",
                 bg=C["card"], fg=C["text"], font=font(10, "bold"),
                 anchor="w").pack(fill="x", pady=(8, 0))
        tk.Label(parent, text=self.route.path_text(), bg=C["card"], fg=C["text_muted"],
                 font=font(9), anchor="w", justify="left", wraplength=320).pack(fill="x")

        stops = self.route.stops.stop_names()
        trip = tk.Frame(parent, bg=C["card"])
        trip.pack(fill="x", pady=(12, 4))
        if self.mode == "change":
            tk.Label(trip, text=f"Booking {self.booking.booking_id} · current seat "
                                f"{self.booking.seat_number}", bg=C["card"], fg=C["text"],
                     font=font(10, "bold"), anchor="w").pack(fill="x")
            self.from_box = self.to_box = None
        else:
            row = tk.Frame(trip, bg=C["card"])
            row.pack(fill="x")
            for i, (label, attr) in enumerate((("Boarding", "from_box"),
                                               ("Destination", "to_box"))):
                cell = tk.Frame(row, bg=C["card"])
                cell.pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 8, 0))
                tk.Label(cell, text=label, bg=C["card"], fg=C["text"], font=font(9, "bold"),
                         anchor="w").pack(fill="x")
                box = combo(cell, stops, width=14)
                box.pack(fill="x")
                setattr(self, attr, box)
            self.from_box.set(self._initial(stops, self._from_hint, 0))
            self.to_box.set(self._initial(stops, self._to_hint, -1))
            self.from_box.bind("<<ComboboxSelected>>", lambda e: self._update_summary())
            self.to_box.bind("<<ComboboxSelected>>", lambda e: self._update_summary())

        self.passenger_box = None
        if self.session.is_admin and self.mode == "book":
            tk.Label(parent, text="Passenger", bg=C["card"], fg=C["text"], font=font(9, "bold"),
                     anchor="w").pack(fill="x", pady=(8, 0))
            people = self.app.passengers.list_passengers(sort_by="Name (A → Z)")
            self._people = {f"{p.full_name} — {p.email}": p.passenger_id for p in people}
            self.passenger_box = combo(parent, list(self._people.keys()), width=34)
            self.passenger_box.pack(fill="x")
            if self._preset_passenger is not None:
                for label, pid in self._people.items():
                    if pid == self._preset_passenger:
                        self.passenger_box.set(label)

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=12)
        self.distance_label = self._summary_row(parent, "Distance")
        self.seats_label = self._summary_row(parent, "Selected seats")
        self.price_label = self._summary_row(parent, "Price per seat")
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=8)
        total_row = tk.Frame(parent, bg=C["card"])
        total_row.pack(fill="x")
        tk.Label(total_row, text="Total", bg=C["card"], fg=C["text"],
                 font=font(12, "bold")).pack(side="left")
        self.total_label = tk.Label(total_row, text="", bg=C["card"], fg=C["primary"],
                                    font=font(16, "bold"))
        self.total_label.pack(side="right")

        avail = self.matrix.available_count()
        self.status_frame = tk.Frame(parent, bg=C["card"])
        self.status_frame.pack(fill="x", pady=(14, 0))
        occupancy = tk.Frame(self.status_frame, bg=C["card"])
        occupancy.pack(fill="x")
        tk.Label(occupancy, text=f"{avail} of {self.matrix.total_seats} seats available",
                 bg=C["card"], fg=C["text_muted"], font=font(9)).pack(side="left")
        bar = ttk.Progressbar(self.status_frame, maximum=self.matrix.total_seats,
                              value=self.matrix.occupied_count(),
                              style="Seat.Horizontal.TProgressbar")
        bar.pack(fill="x", pady=(4, 0))

        if self.matrix.is_full() and self.mode == "book":
            queue = self.app.bookings.queue_for(self.bus.bus_id)
            note = tk.Frame(self.status_frame, bg=C["warning_light"])
            note.pack(fill="x", pady=(12, 0))
            tk.Label(note, text=f"This bus is fully booked. {queue.size()} passenger(s) are "
                                "waiting. Join the FIFO waiting list and you will get the next "
                                "free seat automatically.", bg=C["warning_light"],
                     fg="#92400E", font=font(9), wraplength=300, justify="left",
                     anchor="w").pack(fill="x", padx=10, pady=(8, 6))
            Button(note, "Join waiting list", self._join_waiting, variant="primary",
                   small=True).pack(anchor="w", padx=10, pady=(0, 10))

    @staticmethod
    def _initial(stops, hint, default_index):
        if hint:
            for s in stops:
                if s.lower() == hint.lower():
                    return s
        return stops[default_index]

    def _summary_row(self, parent, label):
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=C["card"], fg=C["text_muted"], font=font(10)).pack(
            side="left")
        value = tk.Label(row, text="", bg=C["card"], fg=C["text"], font=font(10, "bold"),
                         wraplength=200, justify="right")
        value.pack(side="right")
        return value

    def _update_summary(self):
        seats = ", ".join(str(s) for s in self.selected) or "—"
        self.seats_label.configure(text=seats)
        self.price_label.configure(text=format_currency(self.bus.ticket_price))
        count = len(self.selected)
        self.total_label.configure(text=format_currency(self.bus.ticket_price * count))
        if self.from_box is not None:
            dist = self.route.stops.distance_between(self.from_box.get(), self.to_box.get())
            self.distance_label.configure(text=format_distance(dist) if dist is not None
                                          else "invalid direction")
        else:
            self.distance_label.configure(text=format_distance(self.route.total_distance))
        self.confirm_btn.set_enabled(count > 0)

    # ---------------------------------------------------------------- draw
    def _draw(self):
        cv = self.canvas
        cv.delete("all")
        self.cells = {}
        m = self.matrix
        cols = m.columns
        half = cols // 2 if cols > 2 else 1
        width = cols * SEAT_W + (cols - 1) * GAP + AISLE
        x0 = max((cv.winfo_width() - width) // 2, 16)
        y0 = 70
        # bus outline and driver area
        body_h = m.rows * (SEAT_H + GAP) + 90
        cv.create_rectangle(x0 - 18, 14, x0 + width + 18, y0 + body_h - 70, fill="white",
                            outline=C["border"], width=2)
        cv.create_text(x0, 40, text="FRONT", anchor="w", fill=C["text_light"],
                       font=font(8, "bold"))
        cv.create_oval(x0 + width - 34, 26, x0 + width - 6, 54, outline=C["text_light"],
                       width=3)                                           # steering wheel
        grid = m.to_matrix()
        current = self.booking.seat_number if self.booking else None
        for r in range(m.rows):
            for c in range(cols):
                status = grid[r][c]
                if status == SeatMatrix.NO_SEAT:
                    continue
                seat = m.seat_number(r, c)
                x = x0 + c * (SEAT_W + GAP) + (AISLE if c >= half else 0)
                y = y0 + r * (SEAT_H + GAP)
                if seat in self.selected:
                    fill = C["seat_selected"]
                elif status == SeatMatrix.BOOKED:
                    fill = C["seat_booked"]
                else:
                    fill = C["seat_available"]
                outline = C["sidebar"] if seat == current else ""
                rect = cv.create_rectangle(x, y, x + SEAT_W, y + SEAT_H, fill=fill,
                                           outline=outline, width=3 if outline else 0)
                cv.create_rectangle(x + 6, y + SEAT_H - 6, x + SEAT_W - 6, y + SEAT_H - 2,
                                    fill="white", outline="", stipple="gray50")
                text = cv.create_text(x + SEAT_W / 2, y + SEAT_H / 2 - 2, text=str(seat),
                                      fill="white", font=font(10, "bold"))
                for item in (rect, text):
                    cv.tag_bind(item, "<Button-1>", lambda e, s=seat: self._toggle(s))
                    cv.tag_bind(item, "<Enter>", lambda e, s=seat, rr=r, cc=c: self._hover(
                        s, rr, cc))
                self.cells[seat] = rect
        cv.configure(scrollregion=(0, 0, x0 + width + 40, y0 + body_h - 50))

    def _hover(self, seat, r, c):
        status = self.matrix.get_status(seat)
        word = {0: "available", 1: "booked"}.get(status, "")
        self.hover_info.configure(
            text=f"Seat {seat} → index {seat - 1} → array[{r}][{c}] = {status} ({word})\n"
                 f"row = {seat - 1} // {self.matrix.columns} = {r},  "
                 f"col = {seat - 1} % {self.matrix.columns} = {c}")
        self.canvas.configure(cursor="hand2" if status == 0 else "X_cursor")

    def _toggle(self, seat):
        if seat in self.selected:
            self.selected.remove(seat)
        elif not self.matrix.is_available(seat):
            toast(self, f"Seat {seat} is already booked.", "error")
            return
        elif self.mode == "change":
            self.selected = [seat]
        elif len(self.selected) >= MAX_SEATS_PER_PASSENGER_PER_BUS:
            toast(self, f"You can select up to {MAX_SEATS_PER_PASSENGER_PER_BUS} seats.",
                  "warning")
            return
        else:
            self.selected.append(seat)
        self._draw()
        self._update_summary()

    # -------------------------------------------------------------- actions
    def _passenger_id(self):
        if self.passenger_box is None:
            return None
        label = self.passenger_box.get()
        return self._people.get(label)

    def _confirm_booking(self):
        try:
            bookings = self.app.bookings.book_seats(
                self.session, self.bus.bus_id, list(self.selected),
                passenger_id=self._passenger_id(), from_city=self.from_box.get(),
                to_city=self.to_box.get())
        except Exception as exc:          # noqa: BLE001
            show_error(self, exc)
            # the seat map may have changed – redraw from the live array
            self.selected = [s for s in self.selected if self.matrix.is_available(s)]
            self._draw()
            self._update_summary()
            return
        self.destroy()
        ConfirmationDialog(self.master, self.app, bookings,
                           "Booking confirmed", "Your seats are reserved.")
        if self.on_done:
            self.on_done()

    def _join_waiting(self):
        try:
            booking, position = self.app.bookings.join_waiting_list(
                self.session, self.bus.bus_id, passenger_id=self._passenger_id(),
                from_city=self.from_box.get(), to_city=self.to_box.get())
        except Exception as exc:          # noqa: BLE001
            show_error(self, exc)
            return
        self.destroy()
        ConfirmationDialog(self.master, self.app, [booking], "Added to waiting list",
                           f"You are number {position} in the queue. A seat will be "
                           "allocated automatically when one becomes free.")
        if self.on_done:
            self.on_done()

    def _confirm_change(self):
        try:
            self.app.bookings.change_seat(self.session, self.booking.booking_id,
                                          self.selected[0])
        except Exception as exc:          # noqa: BLE001
            show_error(self, exc)
            return
        self.destroy()
        toast(self.master, f"Booking {self.booking.booking_id} moved to seat "
                           f"{self.selected[0]}.")
        if self.on_done:
            self.on_done()


def open_seat_selection(parent, ctx, bus_id, from_city=None, to_city=None, passenger_id=None,
                        on_done=None):
    return SeatSelectionDialog(parent, ctx, bus_id, from_city=from_city, to_city=to_city,
                               passenger_id=passenger_id, on_done=on_done)


class ConfirmationDialog(Dialog):
    """Shows booking ID(s) and a printable confirmation with a Save option."""

    def __init__(self, parent, app, bookings, title, subtitle):
        super().__init__(parent, title, width=560)
        self.app = app
        tk.Label(self.body, text=subtitle, bg=C["card"], fg=C["text_muted"], font=font(10),
                 anchor="w", wraplength=500, justify="left").pack(fill="x")
        ids = tk.Frame(self.body, bg=C["card"])
        ids.pack(fill="x", pady=10)
        for b in bookings:
            row = tk.Frame(ids, bg=C["primary_light"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=b.booking_id, bg=C["primary_light"], fg=C["primary_dark"],
                     font=mono(13, "bold")).pack(side="left", padx=12, pady=6)
            seat_text = f"Seat {b.seat_number}" if b.seat_number else "Waiting list"
            tk.Label(row, text=seat_text, bg=C["primary_light"], fg=C["text"],
                     font=font(10)).pack(side="left")
            Badge(row, b.status).pack(side="right", padx=12)
        self.text = "\n\n".join(app.bookings.confirmation_text(b) for b in bookings)
        box = tk.Text(self.body, height=12, font=mono(9), bg="#F8FAFC", fg=C["text"],
                      relief="flat", highlightthickness=1, highlightbackground=C["border"],
                      padx=10, pady=8)
        box.insert("1.0", self.text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)
        self.add_button("Done", self.destroy)
        self.add_button("Save as text…", self._save, "secondary")
        self.add_button("Copy", self._copy, "secondary")
        self.show()

    def _save(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt",
                                            initialfile="smartbus_ticket.txt",
                                            filetypes=[("Text file", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.text)
            toast(self, f"Saved to {os.path.basename(path)}")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.text)
        toast(self, "Confirmation copied to clipboard.")


def show_booking_details(parent, app, booking):
    ConfirmationDialog(parent, app, [booking], f"Booking {booking.booking_id}",
                       f"{booking.passenger_name} · {booking.bus_label}")
