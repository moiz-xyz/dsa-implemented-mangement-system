"""
HASH TABLE – FAST BOOKING LOOKUP
================================

Problem: given a booking ID such as "SB-7KQ2MX", find the booking quickly.
Scanning every booking would be O(n). A hash table turns the key into an
array index directly, giving O(1) average-case lookup.

How it works
------------
1. A hash function converts the key (string) into a large integer.
   We use the polynomial rolling hash:

        h = 0
        for each character ch:  h = (h * 31 + code(ch)) mod 2^32

2. The bucket index is  h mod capacity.
3. Each bucket holds the head of a small linked list ("chain").

Collision handling – SEPARATE CHAINING
--------------------------------------
Two different keys can land in the same bucket (a *collision*). Instead of
overwriting, we link the new entry in front of the existing chain:

    bucket 0: None
    bucket 1: [SB-A2|...] -> [SB-Q9|...] -> None     <- collision chain
    bucket 2: [SB-K7|...] -> None

Searching a bucket walks only its short chain.

Load factor & resizing
----------------------
load factor = number of entries / number of buckets.
When it exceeds 0.75 we double the capacity and re-insert ("rehash")
every entry. This keeps chains short, so lookups stay O(1) on average.

Complexities:     average   worst (everything collides)
    insert          O(1)        O(n)
    search          O(1)        O(n)
    delete          O(1)        O(n)
"""

from data_structures.custom_array import FixedArray


class _Entry:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_entry=None):
        self.key = key
        self.value = value
        self.next = next_entry


class HashTable:
    def __init__(self, capacity=16, max_load_factor=0.75, auto_resize=True):
        if capacity < 1:
            raise ValueError("Capacity must be at least 1.")
        self._capacity = capacity
        self._buckets = FixedArray(capacity)       # array of chain heads
        self._size = 0
        self._max_load = max_load_factor
        self._auto_resize = auto_resize

    # -------------------------------------------------------------- hashing
    @staticmethod
    def hash_code(key):
        """Polynomial rolling hash of the key's text form."""
        h = 0
        for ch in str(key):
            h = (h * 31 + ord(ch)) % 4294967296     # keep it within 32 bits
        return h

    def bucket_index(self, key):
        return self.hash_code(key) % self._capacity

    # ----------------------------------------------------------- operations
    def insert(self, key, value):
        """Insert or update key -> value. Average O(1)."""
        index = self.bucket_index(key)
        node = self._buckets[index]
        while node is not None:                 # update if key already present
            if node.key == key:
                node.value = value
                return
            node = node.next
        # Prepend to the chain (O(1)).
        self._buckets[index] = _Entry(key, value, self._buckets[index])
        self._size += 1
        if self._auto_resize and self.load_factor() > self._max_load:
            self._resize(self._capacity * 2)

    def search(self, key, default=None):
        """Return the value for key, or `default` if missing. Average O(1)."""
        node = self._buckets[self.bucket_index(key)]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        return default

    def search_trace(self, key):
        """
        Like search, but also returns the steps taken – used by the DSA Lab
        to visualise the lookup. Returns (bucket_index, compared_keys, value).
        """
        index = self.bucket_index(key)
        compared = []
        node = self._buckets[index]
        while node is not None:
            compared.append(node.key)
            if node.key == key:
                return index, compared, node.value
            node = node.next
        return index, compared, None

    def contains(self, key):
        index = self.bucket_index(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    __contains__ = contains

    def delete(self, key):
        """Remove key. Returns the removed value; raises KeyError if missing."""
        index = self.bucket_index(key)
        prev = None
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                if prev is None:
                    self._buckets[index] = node.next
                else:
                    prev.next = node.next
                self._size -= 1
                return node.value
            prev = node
            node = node.next
        raise KeyError(key)

    def _resize(self, new_capacity):
        """Allocate a bigger bucket array and rehash every entry – O(n)."""
        old_buckets = self._buckets
        self._capacity = new_capacity
        self._buckets = FixedArray(new_capacity)
        self._size = 0
        for head in old_buckets:
            node = head
            while node is not None:
                index = self.bucket_index(node.key)
                self._buckets[index] = _Entry(node.key, node.value, self._buckets[index])
                self._size += 1
                node = node.next

    def clear(self):
        self._buckets = FixedArray(self._capacity)
        self._size = 0

    # ------------------------------------------------------------ inspection
    def __len__(self):
        return self._size

    @property
    def capacity(self):
        return self._capacity

    def load_factor(self):
        return self._size / self._capacity

    def items(self):
        for head in self._buckets:
            node = head
            while node is not None:
                yield node.key, node.value
                node = node.next

    def keys(self):
        for key, _ in self.items():
            yield key

    def values(self):
        for _, value in self.items():
            yield value

    def chain_lengths(self):
        lengths = []
        for head in self._buckets:
            length = 0
            node = head
            while node is not None:
                length += 1
                node = node.next
            lengths.append(length)
        return lengths

    def stats(self):
        lengths = self.chain_lengths()
        used = 0
        longest = 0
        collisions = 0
        for length in lengths:
            if length > 0:
                used += 1
                collisions += length - 1
            if length > longest:
                longest = length
        return {
            "capacity": self._capacity,
            "size": self._size,
            "load_factor": round(self.load_factor(), 3),
            "used_buckets": used,
            "collisions": collisions,
            "longest_chain": longest,
        }

    def display(self):
        """Return one text line per bucket, e.g. '[3] SB-A -> SB-B'."""
        lines = []
        for i, head in enumerate(self._buckets):
            keys = []
            node = head
            while node is not None:
                keys.append(str(node.key))
                node = node.next
            lines.append(f"[{i}] " + (" -> ".join(keys) if keys else "empty"))
        return lines

    def buckets_snapshot(self):
        """List of lists of (key, value) per bucket – used by the visualiser."""
        snapshot = []
        for head in self._buckets:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            snapshot.append(chain)
        return snapshot

    def __repr__(self):
        return f"HashTable(size={self._size}, capacity={self._capacity})"
