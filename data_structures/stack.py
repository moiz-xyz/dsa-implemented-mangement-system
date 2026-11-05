"""
STACK (LIFO) – BOOKING HISTORY AND UNDO
=======================================

A stack is "Last In, First Out": the most recently added item is the first
one removed – like a pile of plates.

SMARTBUS pushes every booking operation (book, cancel, change seat, join
waiting list) onto a stack. "Undo Last Action" pops the top operation and
reverses it.

Implementation: a linked list of nodes where `top` points to the newest
node. push and pop only touch the top, so both are O(1).

        top
         |
         v
     [Cancel SB-X] -> [Book SB-Y] -> [Book SB-Z] -> None
"""


class StackUnderflowError(IndexError):
    """Raised when popping or peeking an empty stack."""


class _StackNode:
    __slots__ = ("value", "below")

    def __init__(self, value, below=None):
        self.value = value
        self.below = below


class Stack:
    def __init__(self, max_size=None):
        self._top = None
        self._size = 0
        self._max_size = max_size   # optional bound (oldest items are dropped)

    def push(self, value):
        """Place a value on top of the stack – O(1)."""
        self._top = _StackNode(value, self._top)
        self._size += 1
        if self._max_size is not None and self._size > self._max_size:
            self._drop_bottom()

    def _drop_bottom(self):
        # Walk to the second-to-last node and cut off the bottom one.
        node = self._top
        while node.below is not None and node.below.below is not None:
            node = node.below
        node.below = None
        self._size -= 1

    def pop(self):
        """Remove and return the top value – O(1)."""
        if self._top is None:
            raise StackUnderflowError("pop from empty stack")
        node = self._top
        self._top = node.below
        self._size -= 1
        return node.value

    def peek(self):
        """Return the top value without removing it – O(1)."""
        if self._top is None:
            raise StackUnderflowError("peek at empty stack")
        return self._top.value

    def is_empty(self):
        return self._top is None

    def size(self):
        return self._size

    def __len__(self):
        return self._size

    def __iter__(self):
        """Iterate from top to bottom."""
        node = self._top
        while node is not None:
            yield node.value
            node = node.below

    def clear(self):
        self._top = None
        self._size = 0

    def display(self):
        """Return items from top to bottom as a list (for printing/UI)."""
        return list(self)

    def __repr__(self):
        return "Stack(top -> " + " -> ".join(repr(v) for v in self) + ")"
