"""
Admin dashboard: statistic cards, four analytics charts and recent bookings.
Every number is read from the database at refresh time (no placeholders).
"""

import tkinter as tk
from tkinter import ttk

from ui.components import Card, DataTable, PageHeader, ScrollableFrame, StatCard, card_title
from ui import theme
from ui.theme import C, font
from utils.helpers import format_currency

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.ticker
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except Exception:          # noqa: BLE001 – matplotlib is optional
    HAS_MPL = False

SERIES = C["primary"]      # single-series charts share one hue (no legend needed)
GRID = C["border"]


class ChartCard(Card):
    """A card holding one matplotlib chart with a hover tooltip."""

    def __init__(self, parent, title, subtitle):
        super().__init__(parent, padding=14)
        card_title(self.body, title, subtitle).pack(fill="x", pady=(0, 6))
        self.area = tk.Frame(self.body, bg=C["card"], height=230)
        self.area.pack(fill="both", expand=True)
        self.canvas = None
        self.loading = ttk.Progressbar(self.area, mode="indeterminate", length=160)
        self.loading_text = tk.Label(self.area, text="Loading chart…", bg=C["card"],
                                     fg=C["text_light"], font=font(9))

    def show_loading(self):
        self.loading_text.place(relx=0.5, rely=0.42, anchor="center")
        self.loading.place(relx=0.5, rely=0.55, anchor="center")
        self.loading.start(12)

    def hide_loading(self):
        self.loading.stop()
        self.loading.place_forget()
        self.loading_text.place_forget()

    def figure(self):
        fig = Figure(figsize=(5.2, 2.5), dpi=96, facecolor=C["card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(C["card"])
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=C["text_muted"], labelsize=8, length=0)
        return fig, ax

    def render(self, fig, hover_items):
        """hover_items: list of (artist, tooltip text)."""
        self.hide_loading()
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        fig.tight_layout(pad=0.6)
        self.canvas = FigureCanvasTkAgg(fig, master=self.area)
        self.canvas.get_tk_widget().configure(bg=C["card"], highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        ax = fig.axes[0]
        tip = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                          fontsize=8, color="white",
                          bbox=dict(boxstyle="round,pad=0.4", fc=C["sidebar"], ec="none"))
        tip.set_visible(False)

        def on_move(event):
            visible = False
            if event.inaxes == ax:
                for artist, text in hover_items:
                    hit, _ = artist.contains(event)
                    if hit:
                        tip.xy = (event.xdata, event.ydata)
                        tip.set_text(text)
                        visible = True
                        break
            if visible != tip.get_visible() or visible:
                tip.set_visible(visible)
                self.canvas.draw_idle()
        self.canvas.mpl_connect("motion_notify_event", on_move)
        self.canvas.draw()


class DashboardPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        PageHeader(self, "Dashboard", "Live overview of fleet, bookings and revenue") \
            .pack(fill="x", pady=(0, 14))
        header = self.winfo_children()[0]
        header.add_action("Refresh", self.refresh, "secondary")

        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner

        # ---- statistic cards (4 x 2 grid)
        grid = tk.Frame(body, bg=C["background"])
        grid.pack(fill="x")
        specs = [
            ("total_buses", "Total buses", C["primary"]),
            ("total_passengers", "Total passengers", C["secondary"]),
            ("total_bookings", "Total bookings", C["primary"]),
            ("total_revenue", "Ticket revenue", C["success"]),
            ("available_seats", "Available seats (upcoming)", C["success"]),
            ("occupied_seats", "Occupied seats (upcoming)", C["primary"]),
            ("cancelled_bookings", "Cancelled bookings", C["danger"]),
            ("waiting_passengers", "Waiting-list passengers", C["warning"]),
        ]
        self.cards = {}
        for key, label, accent in specs:
            self.cards[key] = StatCard(grid, label, "—", accent)
        self.stat_grid = grid

        # ---- charts (2 x 2)
        charts = tk.Frame(body, bg=C["background"])
        charts.pack(fill="both", expand=True)
        self.chart_daily = ChartCard(charts, "Daily bookings", "Bookings created per day, "
                                     "last 14 days")
        self.chart_revenue = ChartCard(charts, "Revenue", "Confirmed ticket revenue per month")
        self.chart_routes = ChartCard(charts, "Popular routes", "Confirmed bookings per route")
        self.chart_occupancy = ChartCard(charts, "Bus occupancy", "Seats booked on upcoming "
                                         "active buses")
        self.chart_grid = charts
        self._columns = None
        body.bind("<Configure>", self._reflow, add="+")

        # ---- recent bookings
        recent = Card(body, padding=14)
        recent.pack(fill="x", pady=(0, 6))
        card_title(recent.body, "Recent bookings",
                   "Newest first · read from the in-memory hash table, ordered with "
                   "merge sort").pack(fill="x", pady=(0, 8))
        self.recent = DataTable(recent.body, [
            ("id", "Booking ID", 110, "w"), ("passenger", "Passenger", 160, "w"),
            ("bus", "Bus", 200, "w"), ("seat", "Seat", 60, "center"),
            ("date", "Booked on", 150, "w"), ("amount", "Amount", 90, "e"),
            ("status", "Status", 100, "center")], height=8, status_column="status")
        self.recent.pack(fill="x")

    # ------------------------------------------------------------ responsive
    def _reflow(self, event):
        """4 stat columns / 2 chart columns on wide windows, 2 / 1 on narrow ones."""
        stat_cols, chart_cols = (4, 2) if event.width >= 900 else (2, 1)
        if self._columns == (stat_cols, chart_cols):
            return
        self._columns = (stat_cols, chart_cols)
        self._place(self.stat_grid, list(self.cards.values()), stat_cols, "stat")
        self._place(self.chart_grid, [self.chart_daily, self.chart_revenue,
                                      self.chart_routes, self.chart_occupancy], chart_cols,
                    "chart")

    @staticmethod
    def _place(frame, widgets, cols, group):
        for col in range(4):
            frame.grid_columnconfigure(col, weight=0, uniform="")
        for col in range(cols):
            frame.grid_columnconfigure(col, weight=1, uniform=group)
        for i, widget in enumerate(widgets):
            widget.grid(row=i // cols, column=i % cols, sticky="nsew",
                        padx=(0 if i % cols == 0 else 12, 0), pady=(0, 12))

    # ------------------------------------------------------------------ data
    def refresh(self):
        stats = self.app.reports.dashboard_stats()
        for key, card in self.cards.items():
            value = stats[key]
            card.set(format_currency(value) if key == "total_revenue" else f"{value:,}")
        self.cards["total_buses"].set(f"{stats['total_buses']:,}",
                                      f"{stats['active_buses']} active & upcoming")
        self.cards["total_bookings"].set(f"{stats['total_bookings']:,}",
                                         f"{stats['confirmed_bookings']:,} confirmed")
        self.cards["total_passengers"].set(f"{stats['total_passengers']:,}",
                                           f"{stats['routes']} routes in network")

        rows = []
        for b in self.app.bookings.list_bookings(sort_by="Booking date (newest)")[:10]:
            rows.append((b.booking_id, (b.booking_id, b.passenger_name, b.bus_label,
                                        b.seat_label, b.booking_date,
                                        format_currency(b.amount), b.status)))
        self.recent.set_rows(rows)

        if not HAS_MPL:
            for card in (self.chart_daily, self.chart_revenue, self.chart_routes,
                         self.chart_occupancy):
                card.hide_loading()
                tk.Label(card.area, text="Install matplotlib to see charts:\n"
                                         "pip install matplotlib", bg=C["card"],
                         fg=C["text_muted"]).pack(expand=True)
            return
        for card in (self.chart_daily, self.chart_revenue, self.chart_routes,
                     self.chart_occupancy):
            card.show_loading()
        # draw after the loading indicators are visible
        self.after(30, self._draw_charts)

    def _draw_charts(self):
        if not self.winfo_exists():
            return
        family = theme.FONT_FAMILY
        matplotlib.rcParams["font.family"] = [family, "DejaVu Sans"]
        self._daily()
        self._revenue()
        self._routes()
        self._occupancy()

    def _daily(self):
        data = self.app.reports.daily_bookings(14)
        fig, ax = self.chart_daily.figure()
        labels = [d["day"][8:10] + "/" + d["day"][5:7] for d in data]
        values = [d["bookings"] for d in data]
        bars = ax.bar(range(len(values)), values, width=0.55, color=SERIES, zorder=3)
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(labels, fontsize=7)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=5))
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        if values and max(values) > 0:
            top = values.index(max(values))
            ax.annotate(str(values[top]), (top, values[top]), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=8,
                        color=C["text"], fontweight="bold")
            ax.set_ylim(0, max(values) * 1.18)
        hover = [(bar, f"{d['day']}\n{d['bookings']} bookings") for bar, d in zip(bars, data)]
        self.chart_daily.render(fig, hover)

    def _revenue(self):
        data = self.app.reports.monthly_revenue(6)
        fig, ax = self.chart_revenue.figure()
        x = list(range(len(data)))
        values = [d["revenue"] / 1000 for d in data]
        ax.fill_between(x, values, color=SERIES, alpha=0.10, zorder=2)
        ax.plot(x, values, color=SERIES, linewidth=2, solid_capstyle="round", zorder=3)
        ax.scatter(x, values, s=42, color=SERIES, edgecolors=C["card"], linewidths=2, zorder=4)
        ax.set_xticks(x)
        ax.set_xticklabels([d["month"] for d in data], fontsize=7)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"{v:,.0f}K"))
        if values:
            ax.annotate(f"Rs. {data[-1]['revenue']:,.0f}", (x[-1], values[-1]),
                        xytext=(-6, 8), textcoords="offset points", ha="right", fontsize=8,
                        color=C["text"], fontweight="bold")
            ax.set_ylim(0, max(max(values) * 1.25, 1))
        # one invisible hit-target per month (bigger than the dot)
        hover = []
        for i, d in enumerate(data):
            target = ax.scatter([i], [values[i]], s=400, alpha=0)
            hover.append((target, f"{d['month']}\nRs. {d['revenue']:,.0f}\n"
                                  f"{d['confirmed']} confirmed"))
        self.chart_revenue.render(fig, hover)

    def _hbar(self, card, labels, values, tips, suffix=""):
        fig, ax = card.figure()
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(True)
        ax.spines["left"].set_color(GRID)
        y = list(range(len(values)))
        bars = ax.barh(y, values, height=0.5, color=SERIES, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8, color=C["text"])
        ax.invert_yaxis()
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        top = max(values) if values else 1
        ax.set_xlim(0, top * 1.18 if top else 1)
        for i, v in enumerate(values):
            ax.annotate(f"{v:,.0f}{suffix}", (v, i), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=8, color=C["text_muted"])
        card.render(fig, list(zip(bars, tips)))

    def _routes(self):
        data = self.app.reports.popular_routes(6)
        labels = [self._short(r["route_name"]) for r in data]
        values = [r["bookings"] for r in data]
        tips = [f"{r['route_name']}\n{r['bookings']} bookings\nRs. {r['revenue']:,.0f}"
                for r in data]
        self._hbar(self.chart_routes, labels, values, tips)

    def _occupancy(self):
        data = self.app.reports.bus_occupancy()[:8]
        labels = [r["bus_number"] for r in data]
        values = [r["occupancy"] for r in data]
        tips = [f"{r['bus_name']} · {r['travel_date']}\n{r['booked']}/{r['total_seats']} seats"
                f"\n{r['waiting']} waiting" for r in data]
        self._hbar(self.chart_occupancy, labels, values, tips, suffix="%")

    @staticmethod
    def _short(text, limit=24):
        return text if len(text) <= limit else text[:limit - 1] + "…"
