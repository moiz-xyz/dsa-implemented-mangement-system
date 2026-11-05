"""
QUEUE (FIFO) – PASSENGER WAITING LIST
=====================================

A queue is "First In, First Out": people are served in the order they
arrived, like a ticket counter line.

When a bus is full, new passengers are enqueued on that bus's waiting
list. When a confirmed passenger cancels, the freed seat is given to the
passenger at the FRONT of the queue (dequeue).

Implementation: linked nodes with two pointers.

    front                               rear
      |                                   |
      v                                   v
   [Ali] -> [Ahmed] -> [Moiz] -> [Sara] -> None

    enqueue  adds at the rear   – O(1)
    dequeue  removes the front  – O(1)
    peek     reads the front    – O(1)

(Using a Python list with pop(0) would be O(n) because every remaining
element would shift left – the linked version avoids that.)
"""


class QueueEmptyError(IndexError):
    """Raised when dequeuing or peeking an empty queue."""


class _QueueNode:
    __slots__ = ("value", "next")

    def __init__(self, value):
        self.value = value
        self.next = None


class Queue:
    def __init__(self):
        self._front = None
        self._rear = None
        self._size = 0

    def enqueue(self, value):
        """Add a value at the rear – O(1)."""
        node = _QueueNode(value)
        if self._rear is None:
            self._front = self._rear = node
        else:
            self._rear.next = node
            self._rear = node
        self._size += 1

    def dequeue(self):
        """Remove and return the value at the front – O(1)."""
        if self._front is None:
            raise QueueEmptyError("dequeue from empty queue")
        node = self._front
        self._front = node.next
        if self._front is None:          # queue became empty
            self._rear = None
        self._size -= 1
        return node.value

    def peek(self):
        if self._front is None:
            raise QueueEmptyError("peek at empty queue")
        return self._front.value

    def is_empty(self):
        return self._front is None

    def size(self):
        return self._size

    def __len__(self):
        return self._size

    def __iter__(self):
        """Iterate from front to rear without modifying the queue."""
        node = self._front
        while node is not None:
            yield node.value
            node = node.next

    def position_of(self, predicate):
        """1-based queue position of the first value matching `predicate`, or -1. O(n)."""
        position = 1
        for value in self:
            if predicate(value):
                return position
            position += 1
        return -1

    def remove_where(self, predicate):
        """
        Remove the first value matching `predicate` (e.g. a passenger who
        leaves the waiting list) while keeping everyone else in order. O(n).
        Returns the removed value or None.
        """
        prev = None
        node = self._front
        while node is not None:
            if predicate(node.value):
                if prev is None:
                    self._front = node.next
                else:
                    prev.next = node.next
                if node is self._rear:
                    self._rear = prev
                self._size -= 1
                return node.value
            prev = node
            node = node.next
        return None

    def clear(self):
        self._front = self._rear = None
        self._size = 0

    def display(self):
        """Return values front-to-rear as a list (for printing/UI)."""
        return list(self)

    def __repr__(self):
        return "Queue(front -> " + " -> ".join(repr(v) for v in self) + " <- rear)"
