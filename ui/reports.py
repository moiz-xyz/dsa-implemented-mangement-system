"""Reports & analytics: six database-driven reports with CSV export."""

import os
import tkinter as tk
from tkinter import filedialog

from ui.components import Card, DataTable, PageHeader, show_error, toast
from ui.theme import C, font
from utils.constants import EXPORT_DIR

NUMERIC_HINTS = ("revenue", "spent", "amount", "average_fare")


class ReportsPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        self.report = None
        header = PageHeader(self, "Reports & Analytics",
                            "Generated from live database records · export any report to CSV")
        header.pack(fill="x", pady=(0, 14))
        header.add_action("Export CSV", self.export, icon="chart")

        body = tk.Frame(self, bg=C["background"])
        body.pack(fill="both", expand=True)
        menu = Card(body, padding=10)
        menu.pack(side="left", fill="y", padx=(0, 12))
        tk.Label(menu.body, text="REPORTS", bg=C["card"], fg=C["text_light"],
                 font=font(8, "bold"), anchor="w").pack(fill="x", pady=(2, 6))
        self.menu_items = {}
        for name in self.app.reports.REPORTS:
            lbl = tk.Label(menu.body, text=name, bg=C["card"], fg=C["text"], font=font(10),
                           anchor="w", padx=12, pady=9, cursor="hand2", width=22)
            lbl.pack(fill="x", pady=1)
            lbl.bind("<Button-1>", lambda e, n=name: self.show(n))
            self.menu_items[name] = lbl

        self.card = Card(body, padding=14)
        self.card.pack(side="left", fill="both", expand=True)
        self.title = tk.Label(self.card.body, text="", bg=C["card"], fg=C["text"],
                              font=font(14, "bold"), anchor="w")
        self.title.pack(fill="x")
        self.summary = tk.Label(self.card.body, text="", bg=C["card"], fg=C["text_muted"],
                                font=font(10), anchor="w")
        self.summary.pack(fill="x", pady=(0, 10))
        self.table_holder = tk.Frame(self.card.body, bg=C["card"])
        self.table_holder.pack(fill="both", expand=True)
        self.current = self.app.reports.REPORTS[0]

    def refresh(self):
        self.show(self.current)

    def show(self, name):
        self.current = name
        for n, lbl in self.menu_items.items():
            active = n == name
            lbl.configure(bg=C["primary_light"] if active else C["card"],
                          fg=C["primary_dark"] if active else C["text"],
                          font=font(10, "bold" if active else "normal"))
        try:
            report = self.app.reports.build_report(name)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.report = report
        self.title.configure(text=report["title"])
        self.summary.configure(text=report["summary"])
        for w in self.table_holder.winfo_children():
            w.destroy()
        cols = []
        for key, heading in report["columns"]:
            numeric = any(h in key for h in NUMERIC_HINTS) or key in (
                "total", "confirmed", "cancelled", "waiting", "bookings", "buses", "passengers",
                "total_seats", "booked", "available", "rank")
            cols.append((key, heading, 90 if numeric else 150, "e" if numeric else "w"))
        table = DataTable(self.table_holder, cols, height=8, status_column=(
            "status" if any(k == "status" for k, _ in report["columns"]) else None),
            empty_text="No data for this report yet.")
        table.pack(fill="both", expand=True)
        rows = []
        for i, row in enumerate(report["rows"]):
            values = []
            for key, _ in report["columns"]:
                value = row.get(key, "")
                if any(h in key for h in NUMERIC_HINTS) and isinstance(value, (int, float)):
                    value = f"{value:,.0f}"
                values.append("" if value is None else value)
            rows.append((i, tuple(values)))
        table.set_rows(rows)

    def export(self):
        if self.report is None:
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        default = self.report["title"].lower().replace(" ", "_") + ".csv"
        path = filedialog.asksaveasfilename(parent=self, initialdir=EXPORT_DIR,
                                            initialfile=default, defaultextension=".csv",
                                            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        try:
            self.app.reports.export_csv(self.report, path)
        except OSError as exc:
            show_error(self, exc, "Export failed")
            return
        toast(self, f"Exported {len(self.report['rows'])} rows to {os.path.basename(path)}")
