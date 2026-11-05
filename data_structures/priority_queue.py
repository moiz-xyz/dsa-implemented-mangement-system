"""
MIN-HEAP PRIORITY QUEUE (used by Dijkstra's algorithm)
======================================================

The project brief allows Python's heapq here, but we implement our own
binary min-heap so the whole algorithm is visible.

A binary heap is a complete binary tree stored in an array where every
parent is <= its children. For the element at index i:

    parent      = (i - 1) // 2
    left child  = 2 * i + 1
    right child = 2 * i + 2

push : append at the end, then "sift up" while smaller than the parent.
pop  : take the root, move the last element to the root, then "sift down".
Both are O(log n) because the tree height is log2(n).
"""


class MinHeap:
    def __init__(self):
        self._heap = []        # dynamic array of (priority, counter, item)
        self._counter = 0      # tie-breaker keeps equal priorities in insertion order

    def push(self, priority, item):
        self._heap.append((priority, self._counter, item))
        self._counter += 1
        self._sift_up(len(self._heap) - 1)

    def pop(self):
        """Remove and return (priority, item) with the smallest priority."""
        if not self._heap:
            raise IndexError("pop from empty heap")
        last = self._heap.pop()
        if not self._heap:
            return last[0], last[2]
        root = self._heap[0]
        self._heap[0] = last
        self._sift_down(0)
        return root[0], root[2]

    def peek(self):
        if not self._heap:
            raise IndexError("peek at empty heap")
        return self._heap[0][0], self._heap[0][2]

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)

    def _less(self, i, j):
        a, b = self._heap[i], self._heap[j]
        return (a[0], a[1]) < (b[0], b[1])

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self._less(i, parent):
                self._swap(i, parent)
                i = parent
            else:
                break

    def _sift_down(self, i):
        n = len(self._heap)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            smallest = i
            if left < n and self._less(left, smallest):
                smallest = left
            if right < n and self._less(right, smallest):
                smallest = right
            if smallest == i:
                break
            self._swap(i, smallest)
            i = smallest
