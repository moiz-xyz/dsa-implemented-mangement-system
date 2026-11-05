"""
DIJKSTRA'S SHORTEST PATH ALGORITHM
==================================

Goal: find the route with the smallest total distance between two cities
in the weighted road network (all distances are positive).

Idea
----
1. Give every city a tentative distance: 0 for the source, infinity for
   the rest.
2. Put the source into a min-priority queue (our MinHeap).
3. Repeatedly take the city U with the smallest tentative distance. That
   distance is now FINAL (no shorter way can exist because all edges are
   positive).
4. "Relax" every road U -> V: if dist[U] + weight < dist[V], we found a
   shorter way to V, so update dist[V], remember previous[V] = U and push V.
5. Stop when the target is settled (or the queue is empty).

The path is rebuilt by following previous[] backwards from the target to
the source; we push those cities onto our custom Stack and pop them to get
the path in forward order.

Time complexity with a binary heap:  O((V + E) log V)
Space complexity:                    O(V)
"""

from data_structures.priority_queue import MinHeap
from data_structures.stack import Stack
from algorithms.sorting import merge_sort

INFINITY = float("inf")


class DijkstraResult:
    def __init__(self, source, target, distances, previous, steps):
        self.source = source
        self.target = target
        self.distances = distances
        self.previous = previous
        self.steps = steps
        self.path = reconstruct_path(previous, source, target) if target else []
        self.distance = distances.get(target, INFINITY) if target else None

    @property
    def reachable(self):
        return bool(self.path)

    def __repr__(self):
        return f"DijkstraResult({' -> '.join(self.path)}, {self.distance})"


def reconstruct_path(previous, source, target):
    """Follow previous[] pointers back from target; reverse using a Stack."""
    if target not in previous and target != source:
        return []
    stack = Stack()
    city = target
    while city is not None:
        stack.push(city)
        if city == source:
            break
        city = previous.get(city)
    else:
        return []                 # chain ended before reaching source
    path = []
    while not stack.is_empty():
        path.append(stack.pop())
    return path if path and path[0] == source else []


def dijkstra(graph, source, target=None):
    """
    Run Dijkstra from `source`. If `target` is given we stop as soon as it
    is settled. Returns DijkstraResult. `steps` records each settle/relax
    action for the DSA Lab visualiser.
    """
    if not graph.has_city(source):
        raise KeyError(f"City '{source}' is not in the network.")
    if target is not None and not graph.has_city(target):
        raise KeyError(f"City '{target}' is not in the network.")

    distances = {city: INFINITY for city in graph.cities()}
    previous = {}
    distances[source] = 0
    settled = set()
    steps = []

    heap = MinHeap()
    heap.push(0, source)

    while not heap.is_empty():
        dist_u, u = heap.pop()
        if u in settled:
            continue                  # stale heap entry – a shorter one was used already
        settled.add(u)
        steps.append({"type": "settle", "city": u, "distance": dist_u})
        if u == target:
            break
        for v, weight in graph.neighbors(u):
            if v in settled:
                continue
            candidate = dist_u + weight
            if candidate < distances[v]:          # relaxation
                old = distances[v]
                distances[v] = candidate
                previous[v] = u
                heap.push(candidate, v)
                steps.append({"type": "relax", "from": u, "to": v, "old": old,
                              "new": candidate})

    return DijkstraResult(source, target, distances, previous, steps)


def path_distance(graph, path):
    total = 0
    for i in range(len(path) - 1):
        w = graph.weight(path[i], path[i + 1])
        if w is None:
            return None
        total += w
    return total


def find_all_routes(graph, source, target, max_routes=8, max_stops=12):
    """
    Enumerate simple paths (no repeated city) from source to target using
    depth-first backtracking, then order them by distance with our merge
    sort. Used to COMPARE alternative routes against Dijkstra's answer.
    Exponential in the worst case, so we cap the number of results.
    """
    if not graph.has_city(source) or not graph.has_city(target):
        return []
    routes = []
    path = [source]
    on_path = {source}

    def explore(city, distance):
        if len(routes) >= max_routes * 4:      # safety cap on search effort
            return
        if city == target:
            routes.append((list(path), distance))
            return
        if len(path) > max_stops:
            return
        for neighbour, weight in graph.neighbors(city):
            if neighbour not in on_path:
                path.append(neighbour)
                on_path.add(neighbour)
                explore(neighbour, distance + weight)
                path.pop()                      # backtrack
                on_path.remove(neighbour)

    explore(source, 0)
    ordered = merge_sort(routes, key=lambda r: r[1])
    return ordered[:max_routes]


COMPLEXITY = {
    "time": "O((V + E) log V) with a binary min-heap",
    "space": "O(V) for distance, previous and the heap",
    "note": "Requires non-negative edge weights.",
}
