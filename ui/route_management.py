"""
Route management (linked lists) and the city network (graph).

* "Routes & Stops" tab – every route is a custom singly linked list. The
  canvas draws the nodes and `next` pointers; stops can be inserted at any
  position or removed, and the change is saved to SQLite immediately.
* "City Network" tab – the graph built from all routes. Run BFS, DFS and
  Dijkstra's shortest path and compare alternative routes.
"""

import time
import tkinter as tk
from tkinter import ttk

from algorithms.shortest_path import COMPLEXITY as DIJKSTRA_COMPLEXITY
from algorithms.sorting import SortStats
from ui.components import (auto_wrap, Button, Card, DataTable, Dialog, ListToolbar, PageHeader,
                           card_title, combo, confirm, labeled, show_error, sort_info_text,
                           toast)
from ui.theme import C, font, mono
from utils.helpers import format_distance

ROUTE_SORTS = {"Distance (shortest)": "distance", "Name (A → Z)": "name",
               "Number of stops": "stops"}

# Approximate (longitude, latitude) used to draw a schematic map of Pakistan.
CITY_COORDS = {
    "Karachi": (67.0, 24.86), "Hyderabad": (68.37, 25.4), "Nawabshah": (68.41, 26.24),
    "Sukkur": (68.86, 27.7), "Rahim Yar Khan": (70.3, 28.42), "Bahawalpur": (71.68, 29.4),
    "Multan": (71.52, 30.16), "Lahore": (74.35, 31.52), "Faisalabad": (73.08, 31.42),
    "Gujranwala": (74.19, 32.16), "Jhelum": (73.73, 32.94), "Rawalpindi": (72.95, 33.45),
    "Islamabad": (73.3, 33.85), "Peshawar": (71.58, 34.0), "Quetta": (67.0, 30.18),
    "Khuzdar": (66.6, 27.8), "Attock": (72.36, 33.77),
}
# Cities whose map label is drawn on the LEFT of the dot to avoid overlaps.
LABEL_LEFT = {"Rawalpindi", "Faisalabad", "Peshawar", "Karachi", "Khuzdar", "Multan",
              "Quetta", "Attock"}


class RouteManagementPage(tk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        header = PageHeader(self, "Routes & Network",
                            "Routes are linked lists of stops; together they form the city graph")
        header.pack(fill="x", pady=(0, 10))
        header.add_action("New route", self.new_route, icon="route")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.routes_tab = tk.Frame(nb, bg=C["background"])
        self.network = NetworkPanel(nb, ctx)
        nb.add(self.routes_tab, text="Routes & Stops (Linked List)")
        nb.add(self.network, text="City Network (Graph · BFS · DFS · Dijkstra)")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.network.refresh()
                if nb.index("current") == 1 else None)
        self._build_routes_tab()
        self.selected_route = None

    # ------------------------------------------------------------ routes tab
    def _build_routes_tab(self):
        tab = self.routes_tab
        tab.grid_columnconfigure(0, weight=5)
        tab.grid_columnconfigure(1, weight=6)
        tab.grid_rowconfigure(0, weight=1)

        left = Card(tab, padding=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(10, 0))
        self.toolbar = ListToolbar(left.body, self.refresh, list(ROUTE_SORTS.keys()),
                                   placeholder="Route or city…", wrap=True)
        self.toolbar.search.entry.configure(width=16)
        self.toolbar.pack(fill="x", pady=(0, 8))
        self.info = auto_wrap(tk.Label(left.body, text="", bg=C["card"], fg=C["text_light"],
                             font=font(8), anchor="w"))
        self.info.pack(fill="x")
        self.table = DataTable(left.body, [
            ("name", "Route", 200, "w"), ("stops", "Stops", 50, "center"),
            ("dist", "Distance", 80, "e"), ("ends", "From → To", 170, "w")], height=8,
            on_select=self._on_select, empty_text="No routes found.")
        self.table.pack(fill="both", expand=True, pady=(6, 0))
        buttons = tk.Frame(left.body, bg=C["card"])
        buttons.pack(fill="x", pady=(10, 0))
        Button(buttons, "Edit details", self.edit_route, "secondary").pack(side="left")
        Button(buttons, "Delete route", self.delete_route, "danger").pack(side="right")

        right = Card(tab, padding=14)
        right.grid(row=0, column=1, sticky="nsew", pady=(10, 0))
        self.detail_title = card_title(right.body, "Select a route",
                                       "The linked list of its stops will appear here.")
        self.detail_title.pack(fill="x")
        holder = tk.Frame(right.body, bg="#F8FAFC", highlightthickness=1,
                          highlightbackground=C["border"])
        holder.pack(fill="x", pady=10)
        self.ll_canvas = tk.Canvas(holder, height=128, bg="#F8FAFC", highlightthickness=0)
        hbar = ttk.Scrollbar(holder, orient="horizontal", command=self.ll_canvas.xview)
        self.ll_canvas.configure(xscrollcommand=hbar.set)
        self.ll_canvas.pack(fill="x")
        hbar.pack(fill="x")

        self.stops = DataTable(right.body, [
            ("pos", "Position", 70, "center"), ("stop", "Stop", 160, "w"),
            ("dist", "From previous", 110, "e"), ("cum", "Cumulative", 110, "e")], height=7,
            empty_text="No stops.")
        self.stops.pack(fill="both", expand=True)

        form = tk.Frame(right.body, bg=C["card"])
        form.pack(fill="x", pady=(10, 0))
        for col in range(4):
            form.grid_columnconfigure(col, weight=1)
        self.new_stop = labeled(form, "New stop", lambda p: ttk.Entry(p, width=14))
        self.new_stop.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.position = labeled(form, "Insert", lambda p: combo(p, [], width=16))
        self.position.grid(row=0, column=1, sticky="ew", padx=6)
        self.dist_prev = labeled(form, "Km (prev.)", lambda p: ttk.Entry(p, width=8))
        self.dist_prev.grid(row=0, column=2, sticky="ew", padx=6)
        self.dist_next = labeled(form, "Km (next, opt.)", lambda p: ttk.Entry(p, width=8))
        self.dist_next.grid(row=0, column=3, sticky="ew", padx=(6, 0))
        btns = tk.Frame(right.body, bg=C["card"])
        btns.pack(fill="x", pady=(10, 0))
        Button(btns, "Insert stop", self.add_stop).pack(side="left")
        Button(btns, "Remove selected stop", self.remove_stop, "danger").pack(side="right")
        tk.Label(right.body, text="Insert = O(position) pointer walk · Delete/Search = O(n) · "
                                  "removing a middle stop merges its distance into the next "
                                  "node", bg=C["card"], fg=C["text_light"], font=font(8),
                 anchor="w", wraplength=520, justify="left").pack(fill="x", pady=(8, 0))

    def refresh(self):
        stats = SortStats()
        start = time.perf_counter()
        routes = self.app.routes.list_routes(ROUTE_SORTS.get(self.toolbar.sort_by),
                                             self.toolbar.algorithm, self.toolbar.query,
                                             stats=stats)
        elapsed = (time.perf_counter() - start) * 1000
        self.table.set_rows([(r.route_id, (r.route_name, r.stop_count,
                                           format_distance(r.total_distance),
                                           f"{r.source} → {r.destination}")) for r in routes])
        self.info.configure(text=sort_info_text(len(routes), self.toolbar.algorithm, stats,
                                                elapsed, "routes"))
        if self.selected_route is None and routes:
            self.selected_route = routes[0].route_id
        if self.selected_route is not None:
            self.table.select(self.selected_route)
            self._show_route(self.selected_route)

    def _on_select(self, iid):
        if iid is not None:
            self.selected_route = int(iid)
            self._show_route(self.selected_route)

    def _show_route(self, route_id):
        try:
            route = self.app.routes.get(route_id)
        except Exception:      # noqa: BLE001 – route deleted
            return
        title, subtitle = self.detail_title.winfo_children()
        title.configure(text=route.route_name)
        subtitle.configure(text=f"{route.description or 'No description'} · "
                                f"{route.stop_count} nodes · total "
                                f"{format_distance(route.total_distance)}")
        rows = []
        cum = 0
        names = []
        for i, node in enumerate(route.stops.traverse()):      # linked-list traversal
            cum += node.distance
            names.append(node.name)
            rows.append((node.name, (i, node.name, format_distance(node.distance) if i else "—",
                                     format_distance(cum))))
        self.stops.set_rows(rows)
        options = ["At start (new head)"] + [f"After {n}" for n in names]
        self.position.widget.configure(values=options)
        self.position.widget.set(options[-1])
        self._draw_list(route)

    def _draw_list(self, route, highlight=None):
        cv = self.ll_canvas
        cv.delete("all")
        x, y, w, h, gap = 16, 30, 118, 54, 46
        cv.create_text(x, 12, text="head", anchor="w", fill=C["primary"], font=font(8, "bold"))
        for i, node in enumerate(route.stops.traverse()):
            fill = C["primary"] if node.name == highlight else C["card"]
            fg = "white" if node.name == highlight else C["text"]
            cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=C["primary"], width=2)
            cv.create_line(x + w - 26, y, x + w - 26, y + h, fill=C["primary"])
            cv.create_text(x + 8, y + 17, text=node.name, anchor="w", fill=fg,
                           font=font(9, "bold"), width=w - 36)
            cv.create_text(x + 8, y + 38, text=f"{node.distance:.0f} km", anchor="w",
                           fill=C["text_muted"] if fill == C["card"] else "white",
                           font=font(8))
            cv.create_text(x + w - 13, y + h / 2, text="•" if node.next else "∅",
                           fill=C["primary"] if fill == C["card"] else "white",
                           font=font(11, "bold"))
            if node.next is not None:
                cv.create_line(x + w - 13, y + h / 2, x + w + gap, y + h / 2, arrow="last",
                               fill=C["text_muted"], width=2)
                cv.create_text(x + w + gap / 2, y + h / 2 - 12,
                               text=f"{node.next.distance:.0f}", fill=C["text_light"],
                               font=font(8))
            x += w + gap
        cv.create_text(16, y + h + 22, text="Each box = StopNode(name, distance, next)",
                       anchor="w", fill=C["text_light"], font=font(8))
        cv.configure(scrollregion=(0, 0, x + 20, 120))

    def _route_or_warn(self):
        if self.selected_route is None:
            toast(self, "Please select a route first.", "warning")
            return None
        return self.selected_route

    def add_stop(self):
        route_id = self._route_or_warn()
        if route_id is None:
            return
        choice = self.position.widget.get()
        if choice.startswith("At start"):
            position = 0
        else:
            route = self.app.routes.get(route_id)
            position = route.stops.position_of(choice.replace("After ", "", 1)) + 1
        try:
            route = self.app.routes.add_stop(route_id, self.new_stop.widget.get(),
                                             self.dist_prev.widget.get(), position,
                                             self.dist_next.widget.get())
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        name = route.stops.get_at(position).name
        for entry in (self.new_stop.widget, self.dist_prev.widget, self.dist_next.widget):
            entry.delete(0, "end")
        self.refresh()
        self._draw_list(route, highlight=name)        # highlight the new node
        toast(self, f"{name} inserted at position {position} and saved.")

    def remove_stop(self):
        route_id = self._route_or_warn()
        if route_id is None:
            return
        stop = self.stops.selected()
        if not stop:
            toast(self, "Select a stop in the table to remove it.", "warning")
            return
        if not confirm(self, "Remove stop", f"Remove {stop} from this route?"):
            return
        try:
            self.app.routes.remove_stop(route_id, stop)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.refresh()
        toast(self, f"{stop} removed; the next stop's distance was merged.")

    def new_route(self):
        RouteDialog(self, self.app, None, self._route_saved)

    def edit_route(self):
        route_id = self._route_or_warn()
        if route_id is not None:
            RouteDialog(self, self.app, self.app.routes.get(route_id), self._route_saved)

    def _route_saved(self, route):
        self.selected_route = route.route_id
        self.refresh()
        toast(self, f"Route '{route.route_name}' saved.")

    def delete_route(self):
        route_id = self._route_or_warn()
        if route_id is None:
            return
        route = self.app.routes.get(route_id)
        if not confirm(self, "Delete route", f"Delete route '{route.route_name}'?"):
            return
        try:
            self.app.routes.delete_route(route_id)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.selected_route = None
        self.refresh()
        toast(self, "Route deleted.")


class RouteDialog(Dialog):
    """Create a route (name, description and initial stops) or edit its details."""

    def __init__(self, parent, app, route, on_saved):
        super().__init__(parent, "Edit route" if route else "New route", width=560)
        self.app = app
        self.route = route
        self.on_saved = on_saved
        self.name = labeled(self.body, "Route name", lambda p: ttk.Entry(p))
        self.name.pack(fill="x", pady=4)
        self.desc = labeled(self.body, "Description", lambda p: ttk.Entry(p))
        self.desc.pack(fill="x", pady=4)
        self.stops_text = None
        if route:
            self.name.widget.insert(0, route.route_name)
            self.desc.widget.insert(0, route.description)
            tk.Label(self.body, text="Add or remove stops from the Routes & Stops panel.",
                     bg=C["card"], fg=C["text_muted"], font=font(9)).pack(anchor="w", pady=6)
        else:
            tk.Label(self.body, text="Stops – one per line as  City, km from previous  "
                                     "(first stop has no distance)",
                     bg=C["card"], fg=C["text"], font=font(9, "bold")).pack(anchor="w",
                                                                           pady=(8, 2))
            self.stops_text = tk.Text(self.body, height=7, font=mono(10), relief="flat",
                                      highlightthickness=1, highlightbackground=C["border"])
            self.stops_text.insert("1.0", "Lahore\nSheikhupura, 40\nSargodha, 140")
            self.stops_text.pack(fill="x")
        self.add_button("Save route", self._save)
        self.add_button("Cancel", self.destroy, "secondary")
        self.show()

    def _save(self):
        try:
            if self.route:
                route = self.app.routes.update_details(self.route.route_id,
                                                       self.name.widget.get(),
                                                       self.desc.widget.get())
            else:
                stops = []
                for i, line in enumerate(self.stops_text.get("1.0", "end").splitlines()):
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    stops.append((parts[0], parts[1] if len(parts) > 1 else (0 if not stops
                                                                             else "")))
                route = self.app.routes.create_route(self.name.widget.get(),
                                                     self.desc.widget.get(), stops)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.destroy()
        self.on_saved(route)


class NetworkPanel(tk.Frame):
    """Graph explorer: map, BFS / DFS / connected cities, Dijkstra + alternatives."""

    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        self.highlight_path = []
        self.visit_order = []
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        left = Card(self, padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(10, 0))
        card_title(left.body, "Plan a journey",
                   "Dijkstra finds the minimum-distance path across all routes").pack(fill="x")
        row = tk.Frame(left.body, bg=C["card"])
        row.pack(fill="x", pady=10)
        self.src = labeled(row, "From", lambda p: combo(p, [], width=16))
        self.src.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.dst = labeled(row, "To", lambda p: combo(p, [], width=16))
        self.dst.pack(side="left", fill="x", expand=True, padx=(6, 0))
        btns = tk.Frame(left.body, bg=C["card"])
        btns.pack(fill="x")
        Button(btns, "Shortest path", self.shortest, small=True).pack(side="left")
        Button(btns, "BFS", lambda: self.traverse("bfs"), "secondary", small=True).pack(
            side="left", padx=6)
        Button(btns, "DFS", lambda: self.traverse("dfs"), "secondary", small=True).pack(
            side="left")
        Button(btns, "Reachable cities", self.connected, "secondary", small=True).pack(
            side="left", padx=6)

        self.result = tk.Label(left.body, text="", bg=C["primary_light"], fg=C["text"],
                               font=font(10), justify="left", anchor="w", wraplength=380,
                               padx=10, pady=8)
        self.result.pack(fill="x", pady=(12, 8))
        tk.Label(left.body, text="Route comparison (DFS backtracking, ordered by merge sort)",
                 bg=C["card"], fg=C["text"], font=font(9, "bold"), anchor="w").pack(fill="x")
        self.alts = DataTable(left.body, [("rank", "#", 30, "center"),
                                          ("path", "Path", 260, "w"),
                                          ("dist", "Distance", 75, "e"),
                                          ("diff", "vs best", 65, "e")], height=6,
                              empty_text="Choose two cities and press Shortest path.")
        self.alts.pack(fill="both", expand=True)
        tk.Label(left.body, text=f"Dijkstra: {DIJKSTRA_COMPLEXITY['time']} · BFS/DFS: "
                                 "O(V + E)", bg=C["card"], fg=C["text_light"], font=font(8),
                 anchor="w").pack(fill="x", pady=(6, 0))

        right = Card(self, padding=10)
        right.grid(row=0, column=1, sticky="nsew", pady=(10, 0))
        self.map_title = tk.Label(right.body, text="Network map", bg=C["card"], fg=C["text"],
                                  font=font(12, "bold"), anchor="w")
        self.map_title.pack(fill="x")
        self.map = tk.Canvas(right.body, bg="#F8FAFC", highlightthickness=0)
        self.map.pack(fill="both", expand=True, pady=(6, 0))
        self.map.bind("<Configure>", lambda e: self.draw())

    def refresh(self):
        cities = self.app.routes.all_cities()
        for box in (self.src.widget, self.dst.widget):
            box.configure(values=cities)
        if cities and not self.src.widget.get():
            self.src.widget.set("Karachi" if "Karachi" in cities else cities[0])
            self.dst.widget.set("Islamabad" if "Islamabad" in cities else cities[-1])
        self.draw()

    # --------------------------------------------------------------- actions
    def shortest(self):
        src, dst = self.src.widget.get(), self.dst.widget.get()
        try:
            result = self.app.routes.shortest_path(src, dst)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.visit_order = []
        if not result.reachable:
            self.highlight_path = []
            self.result.configure(text=f"No connection exists between {src} and {dst}.")
            self.alts.set_rows([])
            self.draw()
            return
        self.highlight_path = result.path
        settled = sum(1 for s in result.steps if s["type"] == "settle")
        self.result.configure(text=f"Shortest path: {' → '.join(result.path)}\n"
                                   f"Total distance: {format_distance(result.distance)} · "
                                   f"{len(result.path) - 1} legs · {settled} cities settled")
        alts = self.app.routes.alternative_routes(src, dst)
        best = alts[0][1] if alts else result.distance
        self.alts.set_rows([(i, (i + 1, " → ".join(p), format_distance(d),
                                 "best" if d == best else f"+{d - best:.0f}"))
                            for i, (p, d) in enumerate(alts)])
        self.draw()

    def traverse(self, kind):
        src = self.src.widget.get()
        if not self.app.routes.graph.has_city(src):
            toast(self, "Choose a starting city.", "warning")
            return
        graph = self.app.routes.graph
        order = graph.bfs(src) if kind == "bfs" else graph.dfs(src)
        self.visit_order = order
        self.highlight_path = []
        name = "Breadth-first (queue)" if kind == "bfs" else "Depth-first (stack)"
        self.result.configure(text=f"{name} order from {src}:\n" + " → ".join(order))
        self.draw()

    def connected(self):
        src = self.src.widget.get()
        try:
            cities = self.app.routes.connected_cities(src)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.visit_order = [src] + [c for c, _ in cities]
        self.highlight_path = []
        text = ", ".join(f"{c} ({h} hop{'s' if h > 1 else ''})" for c, h in cities)
        self.result.configure(text=f"{len(cities)} destinations reachable from {src}:\n{text}")
        self.draw()

    # ------------------------------------------------------------------ map
    def _positions(self, w, h):
        graph = self.app.routes.graph
        cities = graph.cities()
        known = [CITY_COORDS[c] for c in cities if c in CITY_COORDS]
        if not known:
            known = [(0, 0), (1, 1)]
        min_x = min(p[0] for p in known)
        max_x = max(p[0] for p in known)
        min_y = min(p[1] for p in known)
        max_y = max(p[1] for p in known)
        pad = 50
        pos = {}
        unknown = [c for c in cities if c not in CITY_COORDS]
        for c in cities:
            if c in CITY_COORDS:
                lon, lat = CITY_COORDS[c]
                left = 90                       # room for labels drawn left of a dot
                x = left + (lon - min_x) / ((max_x - min_x) or 1) * (w - left - pad - 40)
                y = h - pad - (lat - min_y) / ((max_y - min_y) or 1) * (h - 2 * pad)
                pos[c] = (x, y)
        for i, c in enumerate(unknown):            # admin-added cities: right edge column
            pos[c] = (w - 30, pad + i * 36)
        return pos

    def draw(self):
        cv = self.map
        cv.delete("all")
        w, h = max(cv.winfo_width(), 300), max(cv.winfo_height(), 300)
        graph = self.app.routes.graph
        pos = self._positions(w, h)
        path_edges = set()
        for i in range(len(self.highlight_path) - 1):
            a, b = self.highlight_path[i], self.highlight_path[i + 1]
            path_edges.add((a, b))
            path_edges.add((b, a))
        for a, b, dist in graph.edges():
            (x1, y1), (x2, y2) = pos[a], pos[b]
            on_path = (a, b) in path_edges
            cv.create_line(x1, y1, x2, y2, fill=C["primary"] if on_path else "#CBD5E1",
                           width=4 if on_path else 2)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            cv.create_rectangle(mx - 16, my - 8, mx + 16, my + 8, fill="#F8FAFC", outline="")
            cv.create_text(mx, my, text=f"{dist:.0f}", fill=C["primary"] if on_path
                           else C["text_light"], font=font(7, "bold" if on_path else "normal"))
        order_index = {c: i + 1 for i, c in enumerate(self.visit_order)}
        for city, (x, y) in pos.items():
            in_path = city in self.highlight_path
            visited = city in order_index
            r = 9 if in_path or visited else 6
            fill = C["primary"] if in_path else (C["secondary"] if visited else C["card"])
            cv.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=C["primary"], width=2)
            if visited and not in_path:
                cv.create_text(x, y, text=str(order_index[city]), fill=C["sidebar"],
                               font=font(7, "bold"))
            left = city in LABEL_LEFT
            cv.create_text(x - 12 if left else x + 12, y - 10, text=city,
                           anchor="e" if left else "w", fill=C["text"],
                           font=font(8, "bold" if in_path else "normal"))
        self.map_title.configure(text=f"Network map · {len(graph)} cities · "
                                      f"{graph.edge_count()} roads (adjacency list)")
