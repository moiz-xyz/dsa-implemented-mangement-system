"""
SINGLY LINKED LIST – BUS ROUTE MANAGEMENT
=========================================

A bus route is an ordered chain of stops:

    Karachi -> Hyderabad -> Nawabshah -> Sukkur -> Multan -> Lahore

Each stop is a StopNode holding
    * name      – the stop / city name
    * distance  – kilometres from the PREVIOUS stop (0 for the first stop)
    * next      – reference (pointer) to the next StopNode, or None

    head
     |
     v
  [Karachi|0|*]-->[Hyderabad|165|*]-->[Nawabshah|135|*]--> ... -->[Lahore|340|None]

Why a linked list?  Inserting or removing a stop in the middle of a route
only requires changing one or two `next` pointers – no elements have to be
shifted as they would in an array.

Complexities (n = number of stops):
    append ........... O(n)  (O(1) with the tail pointer we keep)
    insert_at(pos) ... O(pos)
    delete(name) ..... O(n)
    search(name) ..... O(n)
    traverse ......... O(n)
    total_distance ... O(n)

No Python list is used to store the stops – only node references.
"""


class StopNode:
    __slots__ = ("name", "distance", "next")

    def __init__(self, name, distance=0.0, next_node=None):
        self.name = name
        self.distance = float(distance)
        self.next = next_node

    def __repr__(self):
        return f"StopNode({self.name!r}, {self.distance})"


class RouteLinkedList:
    """Singly linked list of StopNode objects."""

    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0

    # ----------------------------------------------------------------- basics
    def __len__(self):
        return self._size

    def is_empty(self):
        return self.head is None

    def __iter__(self):
        return self.traverse()

    def traverse(self):
        """Visit every node from head to tail – O(n)."""
        current = self.head
        while current is not None:
            yield current
            current = current.next

    @staticmethod
    def _same(a, b):
        return a.strip().lower() == b.strip().lower()

    # -------------------------------------------------------------- insertion
    def append(self, name, distance=0.0):
        """Add a stop at the end of the route."""
        if self.search(name) is not None:
            raise ValueError(f"Stop '{name}' already exists on this route.")
        if distance < 0:
            raise ValueError("Distance cannot be negative.")
        node = StopNode(name, 0.0 if self.head is None else distance)
        if self.head is None:
            self.head = self.tail = node
        else:
            self.tail.next = node       # link old tail to the new node
            self.tail = node
        self._size += 1
        return node

    def insert_at(self, position, name, distance, distance_to_next=None):
        """
        Insert a new stop so that it ends up at index `position` (0-based).

        `distance` is the distance from the previous stop to the new stop.
        `distance_to_next` is the distance from the new stop to the stop that
        used to follow. If it is omitted we assume the new stop lies on the
        existing road and use (old distance - distance).
        """
        if position < 0 or position > self._size:
            raise IndexError(f"Position must be between 0 and {self._size}.")
        if self.search(name) is not None:
            raise ValueError(f"Stop '{name}' already exists on this route.")
        if distance < 0 or (distance_to_next is not None and distance_to_next < 0):
            raise ValueError("Distance cannot be negative.")

        if position == self._size:                       # insert at the end
            return self.append(name, distance)

        if position == 0:                                # insert a new head
            old_head = self.head
            node = StopNode(name, 0.0, old_head)
            # the old head now has a previous stop, so it needs a distance
            old_head.distance = distance_to_next if distance_to_next is not None else distance
            self.head = node
            self._size += 1
            return node

        # Walk to the node just BEFORE the insertion point: O(position)
        prev = self.head
        for _ in range(position - 1):
            prev = prev.next
        following = prev.next

        if distance_to_next is None:
            distance_to_next = following.distance - distance
            if distance_to_next <= 0:
                raise ValueError(
                    f"Distance from {prev.name} to {name} must be less than the current "
                    f"{prev.name} -> {following.name} distance ({following.distance:.0f} km), "
                    "or provide the distance to the next stop.")

        node = StopNode(name, distance, following)       # new -> following
        prev.next = node                                 # prev -> new
        following.distance = distance_to_next
        self._size += 1
        return node

    def insert_after(self, existing_name, name, distance, distance_to_next=None):
        position = self.position_of(existing_name)
        if position == -1:
            raise ValueError(f"Stop '{existing_name}' is not on this route.")
        return self.insert_at(position + 1, name, distance, distance_to_next)

    # --------------------------------------------------------------- deletion
    def delete(self, name):
        """
        Remove the stop called `name`.

        When a middle stop is removed, the bus now drives directly from the
        previous stop to the next one, so we add the removed stop's distance
        to the next node (A-5km-B-7km-C  ->  A-12km-C). Total distance is
        preserved. Returns the removed node.
        """
        prev = None
        current = self.head
        while current is not None and not self._same(current.name, name):
            prev = current
            current = current.next

        if current is None:
            raise ValueError(f"Stop '{name}' is not on this route.")

        if prev is None:                         # deleting the head
            self.head = current.next
            if self.head is not None:
                self.head.distance = 0.0
        else:
            prev.next = current.next             # bypass the removed node
            if current.next is not None:
                current.next.distance += current.distance

        if current is self.tail:
            self.tail = prev
        current.next = None
        self._size -= 1
        return current

    # ---------------------------------------------------------------- queries
    def search(self, name):
        """Linear search through the chain – O(n). Returns the node or None."""
        for node in self.traverse():
            if self._same(node.name, name):
                return node
        return None

    def position_of(self, name):
        """0-based index of a stop, or -1 if not found."""
        index = 0
        for node in self.traverse():
            if self._same(node.name, name):
                return index
            index += 1
        return -1

    def get_at(self, position):
        if position < 0 or position >= self._size:
            raise IndexError("Position out of range.")
        current = self.head
        for _ in range(position):
            current = current.next
        return current

    def total_distance(self):
        total = 0.0
        for node in self.traverse():
            total += node.distance
        return total

    def distance_between(self, start, end):
        """
        Distance travelled from `start` to `end` along the route, or None if
        either stop is missing or `end` does not come after `start`.
        """
        inside = False
        total = 0.0
        for node in self.traverse():
            if inside:
                total += node.distance
                if self._same(node.name, end):
                    return total
            elif self._same(node.name, start):
                inside = True
        return None

    def first_stop(self):
        return self.head.name if self.head else None

    def last_stop(self):
        return self.tail.name if self.tail else None

    def stop_names(self):
        return [node.name for node in self.traverse()]

    def to_list(self):
        """List of (name, distance_from_previous) tuples – for display/saving."""
        return [(node.name, node.distance) for node in self.traverse()]

    def display(self):
        if self.head is None:
            return "(empty route)"
        parts = [self.head.name]
        for node in self.traverse():
            if node is self.head:
                continue
            parts.append(f"--{node.distance:.0f} km--> {node.name}")
        return " ".join(parts)

    def __repr__(self):
        return f"RouteLinkedList({self.display()})"

    @classmethod
    def from_pairs(cls, pairs):
        route = cls()
        for name, distance in pairs:
            route.append(name, distance)
        return route
