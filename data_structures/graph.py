"""
GRAPH – CITY AND ROUTE NETWORK
==============================

Cities are VERTICES; a road between two cities is a weighted EDGE whose
weight is the distance in km. Roads work both ways, so the graph is
undirected (each edge is stored in both cities' lists).

Adjacency list representation
-----------------------------
    Karachi   : [(Hyderabad, 165)]
    Hyderabad : [(Karachi, 165), (Nawabshah, 135), (Sukkur, 330)]
    Sukkur    : [(Hyderabad, 330), (Nawabshah, 140), (Multan, 450)]
    ...

The adjacency list uses O(V + E) memory – much less than a V x V matrix
for a sparse road network.

Traversals
----------
* BFS (Breadth-First Search) visits cities level by level using our custom
  FIFO Queue. Good for "which cities can I reach and in how few hops?".
* DFS (Depth-First Search) goes as deep as possible first using our custom
  LIFO Stack (an iterative version) – a recursive version is also given.

Both run in O(V + E).
"""

from data_structures.queue import Queue
from data_structures.stack import Stack


class Graph:
    def __init__(self):
        # vertex name -> list of [neighbour, weight] pairs
        self._adj = {}

    # ----------------------------------------------------------- vertices
    def add_city(self, city):
        if city not in self._adj:
            self._adj[city] = []

    def remove_city(self, city):
        if city not in self._adj:
            raise KeyError(f"City '{city}' is not in the network.")
        for neighbour, _ in self._adj[city]:
            self._adj[neighbour] = [e for e in self._adj[neighbour] if e[0] != city]
        del self._adj[city]

    def has_city(self, city):
        return city in self._adj

    def cities(self):
        return list(self._adj.keys())

    def __len__(self):
        return len(self._adj)

    # -------------------------------------------------------------- edges
    def add_connection(self, a, b, distance):
        """
        Add (or update) an undirected road a <-> b. If a road already exists
        we keep the shorter distance, because several bus routes may share a
        road segment.
        """
        if a == b:
            raise ValueError("A city cannot be connected to itself.")
        if distance <= 0:
            raise ValueError("Distance must be positive.")
        self.add_city(a)
        self.add_city(b)
        for source, target in ((a, b), (b, a)):
            for edge in self._adj[source]:
                if edge[0] == target:
                    edge[1] = min(edge[1], distance)
                    break
            else:
                self._adj[source].append([target, distance])

    def remove_connection(self, a, b):
        if not self.has_connection(a, b):
            raise KeyError(f"No connection between {a} and {b}.")
        self._adj[a] = [e for e in self._adj[a] if e[0] != b]
        self._adj[b] = [e for e in self._adj[b] if e[0] != a]

    def has_connection(self, a, b):
        return a in self._adj and any(e[0] == b for e in self._adj[a])

    def neighbors(self, city):
        if city not in self._adj:
            raise KeyError(f"City '{city}' is not in the network.")
        return [(n, w) for n, w in self._adj[city]]

    def weight(self, a, b):
        for n, w in self._adj.get(a, []):
            if n == b:
                return w
        return None

    def edges(self):
        """Each undirected edge once, as (a, b, distance)."""
        seen = set()
        result = []
        for a, lst in self._adj.items():
            for b, w in lst:
                key = (a, b) if a < b else (b, a)
                if key not in seen:
                    seen.add(key)
                    result.append((key[0], key[1], w))
        return result

    def edge_count(self):
        return len(self.edges())

    # ---------------------------------------------------------- traversals
    def bfs(self, start):
        """Breadth-first order of cities reachable from `start`."""
        if start not in self._adj:
            raise KeyError(f"City '{start}' is not in the network.")
        visited = {start}
        order = []
        queue = Queue()
        queue.enqueue(start)
        while not queue.is_empty():
            city = queue.dequeue()            # FIFO: oldest discovered first
            order.append(city)
            for neighbour, _ in self._adj[city]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.enqueue(neighbour)
        return order

    def bfs_levels(self, start):
        """city -> number of hops from start (computed with BFS)."""
        if start not in self._adj:
            raise KeyError(f"City '{start}' is not in the network.")
        level = {start: 0}
        queue = Queue()
        queue.enqueue(start)
        while not queue.is_empty():
            city = queue.dequeue()
            for neighbour, _ in self._adj[city]:
                if neighbour not in level:
                    level[neighbour] = level[city] + 1
                    queue.enqueue(neighbour)
        return level

    def dfs(self, start):
        """Depth-first order using an explicit custom Stack (iterative)."""
        if start not in self._adj:
            raise KeyError(f"City '{start}' is not in the network.")
        visited = set()
        order = []
        stack = Stack()
        stack.push(start)
        while not stack.is_empty():
            city = stack.pop()                # LIFO: newest discovered first
            if city in visited:
                continue
            visited.add(city)
            order.append(city)
            # Push neighbours in reverse so the first neighbour is explored
            # first – this matches the recursive version's order.
            neighbours = self._adj[city]
            for i in range(len(neighbours) - 1, -1, -1):
                if neighbours[i][0] not in visited:
                    stack.push(neighbours[i][0])
        return order

    def dfs_recursive(self, start, visited=None, order=None):
        if start not in self._adj:
            raise KeyError(f"City '{start}' is not in the network.")
        if visited is None:
            visited, order = set(), []
        visited.add(start)
        order.append(start)
        for neighbour, _ in self._adj[start]:
            if neighbour not in visited:
                self.dfs_recursive(neighbour, visited, order)
        return order

    def connected_destinations(self, start):
        """All cities reachable from start (excluding start itself)."""
        return [c for c in self.bfs(start) if c != start]

    def is_reachable(self, a, b):
        if a not in self._adj or b not in self._adj:
            return False
        return b in self.bfs(a)

    def display(self):
        lines = []
        for city, lst in self._adj.items():
            neighbours = ", ".join(f"{n} ({w:.0f} km)" for n, w in lst) or "no connections"
            lines.append(f"{city}: {neighbours}")
        return lines

    def __repr__(self):
        return f"Graph(cities={len(self._adj)}, roads={self.edge_count()})"
