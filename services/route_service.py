"""
Route service – keeps SQLite route_stops and in-memory structures in sync.

* Every route is loaded into a custom RouteLinkedList (models.Route.stops).
* All routes together form the city network Graph: consecutive stops of a
  route become a weighted edge.
* Shortest paths use our Dijkstra implementation.

Editing workflow: the UI calls add_stop / remove_stop, which modify the
linked list first (so the linked list enforces the rules) and then
persist the whole list to route_stops in one transaction.
"""

import sqlite3

from algorithms.searching import linear_search, linear_search_all
from algorithms.shortest_path import dijkstra, find_all_routes
from algorithms.sorting import sort_items, DEFAULT_ALGORITHM
from data_structures.graph import Graph
from data_structures.linked_list import RouteLinkedList
from models.route import Route
from utils import validators
from utils.exceptions import BookingError, NotFoundError, ValidationError
from utils.helpers import now_str


class RouteService:
    def __init__(self, db):
        self.db = db
        self._routes = {}        # route_id -> Route (with linked list)
        self.graph = Graph()
        self.reload()

    # ------------------------------------------------------------- loading
    def reload(self):
        self._routes = {}
        for row in self.db.query("SELECT * FROM routes ORDER BY route_id"):
            self._routes[row["route_id"]] = Route(row["route_id"], row["route_name"],
                                                  row["description"], RouteLinkedList())
        # stop_order is the persisted position of each node in the list
        for row in self.db.query("SELECT * FROM route_stops ORDER BY route_id, stop_order"):
            route = self._routes.get(row["route_id"])
            if route is not None:
                route.stops.append(row["stop_name"], row["distance_from_prev"])
        self._rebuild_graph()

    def _rebuild_graph(self):
        """Build the city graph from the linked lists of all routes."""
        graph = Graph()
        for route in self._routes.values():
            prev = None
            for node in route.stops.traverse():
                graph.add_city(node.name)
                if prev is not None and node.distance > 0:
                    graph.add_connection(prev.name, node.name, node.distance)
                prev = node
        self.graph = graph

    def _persist_stops(self, route):
        """Write the linked list back to route_stops (atomic replace), then refresh graph."""
        self._write_stops(route)
        self._rebuild_graph()

    def _write_stops(self, route):
        with self.db.transaction():
            self.db.execute("DELETE FROM route_stops WHERE route_id = ?", (route.route_id,))
            order = 0
            for node in route.stops.traverse():
                self.db.execute("INSERT INTO route_stops (route_id, stop_order, stop_name, "
                                "distance_from_prev) VALUES (?, ?, ?, ?)",
                                (route.route_id, order, node.name, node.distance))
                order += 1

    # ------------------------------------------------------------- queries
    def list_routes(self, sort_by=None, algorithm=DEFAULT_ALGORITHM, query="", stats=None):
        routes = list(self._routes.values())
        if query:
            q = query.strip().lower()
            routes = linear_search_all(
                routes, lambda r: q in r.route_name.lower() or
                any(q in name.lower() for name in r.stops.stop_names()))
        keys = {
            "distance": lambda r: r.total_distance,
            "name": lambda r: r.route_name.lower(),
            "stops": lambda r: r.stop_count,
        }
        if sort_by in keys:
            routes = sort_items(routes, key=keys[sort_by], algorithm=algorithm, stats=stats)
        return routes

    def get(self, route_id):
        route = self._routes.get(route_id)
        if route is None:
            raise NotFoundError("Route not found.")
        return route

    def find_by_name(self, name):
        routes = list(self._routes.values())
        result = linear_search(routes, name.strip().lower(), key=lambda r: r.route_name.lower())
        return routes[result.index] if result.found else None

    def all_cities(self):
        cities = self.graph.cities()
        return sort_items(cities, key=str.lower, algorithm="Merge Sort")

    # ------------------------------------------------------------ mutations
    def create_route(self, name, description, stops):
        """
        stops: list of (city, distance_from_previous). At least two stops.
        The stops are first loaded into a RouteLinkedList, which rejects
        duplicates and negative distances.
        """
        name = validators.require(name, "Route name")
        if len(stops) < 2:
            raise ValidationError("A route needs at least two stops.")
        linked = RouteLinkedList()
        for i, (city, dist) in enumerate(stops):
            city = validators.validate_city(city, f"Stop {i + 1}")
            dist = 0 if i == 0 else validators.validate_positive_float(dist, f"Distance to {city}")
            try:
                linked.append(city, dist)
            except ValueError as exc:
                raise ValidationError(str(exc)) from None
        try:
            with self.db.transaction():
                cur = self.db.execute("INSERT INTO routes (route_name, description, created_at) "
                                      "VALUES (?, ?, ?)", (name, description or "", now_str()))
                route = Route(cur.lastrowid, name, description or "", linked)
                self._write_stops(route)
        except sqlite3.IntegrityError:
            raise ValidationError(f"A route named '{name}' already exists.") from None
        # Only touch memory after the database commit succeeded.
        self._routes[route.route_id] = route
        self._rebuild_graph()
        return route

    def update_details(self, route_id, name, description):
        route = self.get(route_id)
        name = validators.require(name, "Route name")
        try:
            with self.db.transaction():
                self.db.execute("UPDATE routes SET route_name = ?, description = ? "
                                "WHERE route_id = ?", (name, description or "", route_id))
                self.db.execute("UPDATE bookings SET route_name = ? WHERE route_name = ?",
                                (name, route.route_name))
        except sqlite3.IntegrityError:
            raise ValidationError(f"A route named '{name}' already exists.") from None
        route.route_name = name
        route.description = description or ""
        return route

    def add_stop(self, route_id, city, distance, position=None, distance_to_next=None):
        """Insert a stop into the route's linked list and persist."""
        route = self.get(route_id)
        city = validators.validate_city(city, "Stop name")
        distance = validators.validate_positive_float(distance, "Distance from previous stop")
        if distance_to_next not in (None, ""):
            distance_to_next = validators.validate_positive_float(distance_to_next,
                                                                  "Distance to next stop")
        else:
            distance_to_next = None
        if position is None:
            position = len(route.stops)
        backup = route.stops.to_list()
        try:
            route.stops.insert_at(position, city, distance, distance_to_next)
            self._persist_stops(route)
        except (ValueError, IndexError) as exc:
            route.stops = RouteLinkedList.from_pairs(backup)
            raise ValidationError(str(exc)) from None
        except Exception:
            route.stops = RouteLinkedList.from_pairs(backup)
            raise
        return route

    def remove_stop(self, route_id, city):
        route = self.get(route_id)
        if len(route.stops) <= 2:
            raise ValidationError("A route must keep at least two stops.")
        self._ensure_not_in_use_for_structure(route_id, city)
        backup = route.stops.to_list()
        try:
            route.stops.delete(city)
            self._persist_stops(route)
        except ValueError as exc:
            route.stops = RouteLinkedList.from_pairs(backup)
            raise ValidationError(str(exc)) from None
        except Exception:
            route.stops = RouteLinkedList.from_pairs(backup)
            raise
        return route

    def _ensure_not_in_use_for_structure(self, route_id, removed_city):
        """A stop cannot be removed if active bookings board/alight there."""
        count = self.db.query_value(
            "SELECT COUNT(*) FROM bookings b JOIN buses u ON u.bus_id = b.bus_id "
            "WHERE u.route_id = ? AND b.status IN ('Confirmed','Waiting') "
            "AND (b.from_city = ? OR b.to_city = ?)", (route_id, removed_city, removed_city), 0)
        if count:
            raise BookingError(f"{count} active booking(s) start or end at {removed_city}. "
                               "Cancel them before removing this stop.")

    def delete_route(self, route_id):
        self.get(route_id)
        buses = self.db.query_value("SELECT COUNT(*) FROM buses WHERE route_id = ?", (route_id,), 0)
        if buses:
            raise BookingError(f"{buses} bus(es) are assigned to this route. "
                               "Reassign or delete them first.")
        with self.db.transaction():
            self.db.execute("DELETE FROM routes WHERE route_id = ?", (route_id,))
        del self._routes[route_id]
        self._rebuild_graph()

    # --------------------------------------------------------------- graph
    def connected_cities(self, city):
        if not self.graph.has_city(city):
            raise NotFoundError(f"{city} is not in the route network.")
        levels = self.graph.bfs_levels(city)
        result = [(c, levels[c]) for c in self.graph.bfs(city) if c != city]
        return result

    def shortest_path(self, source, target):
        if not source or not target:
            raise ValidationError("Please choose both a departure and a destination city.")
        if source == target:
            raise ValidationError("Departure and destination must be different cities.")
        for city in (source, target):
            if not self.graph.has_city(city):
                raise NotFoundError(f"{city} is not in the route network.")
        return dijkstra(self.graph, source, target)

    def alternative_routes(self, source, target, limit=6):
        return find_all_routes(self.graph, source, target, max_routes=limit)

    def routes_through(self, source, target):
        """Routes whose linked list visits `source` before `target`, with segment distance."""
        result = []
        for route in self._routes.values():
            distance = route.stops.distance_between(source, target)
            if distance is not None:
                result.append((route, distance))
        return result
