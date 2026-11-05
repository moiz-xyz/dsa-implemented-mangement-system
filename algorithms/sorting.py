"""
SORTING ALGORITHMS (all implemented by hand)
============================================

Every function has the same signature:

    sort_fn(items, key=None, reverse=False, on_step=None) -> new sorted list

* items    – any list (it is NOT modified; a copy is sorted)
* key      – function extracting the value to compare (e.g. bus.price)
* reverse  – True for descending order
* on_step  – optional callback used by the DSA Lab visualiser. It receives
             (array_snapshot, highlighted_indices, description).

The module-level dict ALGORITHMS lets the UI offer the algorithms in a
drop-down together with their complexities.

| Algorithm      | Best       | Average    | Worst      | Space    | Stable |
|----------------|------------|------------|------------|----------|--------|
| Bubble Sort    | O(n)       | O(n²)      | O(n²)      | O(1)     | Yes    |
| Selection Sort | O(n²)      | O(n²)      | O(n²)      | O(1)     | No     |
| Insertion Sort | O(n)       | O(n²)      | O(n²)      | O(1)     | Yes    |
| Merge Sort     | O(n log n) | O(n log n) | O(n log n) | O(n)     | Yes    |
| Quick Sort     | O(n log n) | O(n log n) | O(n²)      | O(log n) | No     |
"""


class SortStats:
    """Counts comparisons and swaps/writes so algorithms can be compared."""

    def __init__(self):
        self.comparisons = 0
        self.swaps = 0

    def __repr__(self):
        return f"SortStats(comparisons={self.comparisons}, swaps={self.swaps})"


class _Sorter:
    """Shared helper: key extraction, ordering direction and step reporting."""

    def __init__(self, items, key, reverse, on_step, stats):
        self.a = list(items)                  # work on a copy
        self.key = key or (lambda x: x)
        self.reverse = reverse
        self.on_step = on_step
        self.stats = stats if stats is not None else SortStats()

    def before(self, x, y):
        """True if x must come strictly before y in the final order."""
        self.stats.comparisons += 1
        kx, ky = self.key(x), self.key(y)
        return kx > ky if self.reverse else kx < ky

    def swap(self, i, j):
        self.a[i], self.a[j] = self.a[j], self.a[i]
        self.stats.swaps += 1

    def step(self, indices, text):
        if self.on_step is not None:
            self.on_step(list(self.a), tuple(indices), text)


# ---------------------------------------------------------------- Bubble
def bubble_sort(items, key=None, reverse=False, on_step=None, stats=None):
    """
    Repeatedly walk through the list swapping neighbours that are out of
    order. After pass k the k largest elements have "bubbled" to the end.
    If a whole pass makes no swap the list is already sorted (best case O(n)).
    """
    s = _Sorter(items, key, reverse, on_step, stats)
    n = len(s.a)
    for end in range(n - 1, 0, -1):
        swapped = False
        for i in range(end):
            s.step((i, i + 1), f"Compare positions {i} and {i + 1}")
            if s.before(s.a[i + 1], s.a[i]):
                s.swap(i, i + 1)
                swapped = True
                s.step((i, i + 1), f"Swap positions {i} and {i + 1}")
        if not swapped:
            break
    s.step((), "Sorted")
    return s.a


# ------------------------------------------------------------- Selection
def selection_sort(items, key=None, reverse=False, on_step=None, stats=None):
    """
    For each position i, find the smallest element in the unsorted part
    a[i..n-1] and swap it into position i.
    """
    s = _Sorter(items, key, reverse, on_step, stats)
    n = len(s.a)
    for i in range(n - 1):
        smallest = i
        for j in range(i + 1, n):
            s.step((smallest, j), f"Compare current minimum (pos {smallest}) with pos {j}")
            if s.before(s.a[j], s.a[smallest]):
                smallest = j
        if smallest != i:
            s.swap(i, smallest)
            s.step((i, smallest), f"Move minimum to position {i}")
    s.step((), "Sorted")
    return s.a


# ------------------------------------------------------------- Insertion
def insertion_sort(items, key=None, reverse=False, on_step=None, stats=None):
    """
    Build the sorted list one element at a time: take the next element and
    shift larger elements one place right until its correct spot is found
    (like sorting playing cards in your hand).
    """
    s = _Sorter(items, key, reverse, on_step, stats)
    for i in range(1, len(s.a)):
        current = s.a[i]
        j = i - 1
        s.step((i,), f"Insert element from position {i}")
        while j >= 0 and s.before(current, s.a[j]):
            s.a[j + 1] = s.a[j]          # shift right
            s.stats.swaps += 1
            s.step((j, j + 1), f"Shift position {j} right")
            j -= 1
        s.a[j + 1] = current
        s.step((j + 1,), f"Place element at position {j + 1}")
    s.step((), "Sorted")
    return s.a


# ----------------------------------------------------------------- Merge
def merge_sort(items, key=None, reverse=False, on_step=None, stats=None):
    """
    Divide and conquer:
      1. split the list into two halves,
      2. sort each half recursively,
      3. merge the two sorted halves into one sorted list.
    The list is halved log n times and each level merges n elements,
    giving O(n log n) in every case. Needs O(n) extra memory for merging.
    """
    s = _Sorter(items, key, reverse, on_step, stats)

    def sort_range(lo, hi):           # sorts s.a[lo:hi]
        if hi - lo <= 1:
            return
        mid = (lo + hi) // 2
        sort_range(lo, mid)
        sort_range(mid, hi)
        merge(lo, mid, hi)

    def merge(lo, mid, hi):
        left = s.a[lo:mid]
        right = s.a[mid:hi]
        i = j = 0
        k = lo
        while i < len(left) and j < len(right):
            # take from the right only if strictly smaller -> stable sort
            if s.before(right[j], left[i]):
                s.a[k] = right[j]
                j += 1
            else:
                s.a[k] = left[i]
                i += 1
            s.stats.swaps += 1
            k += 1
        while i < len(left):
            s.a[k] = left[i]
            i += 1
            k += 1
        while j < len(right):
            s.a[k] = right[j]
            j += 1
            k += 1
        s.step(tuple(range(lo, hi)), f"Merge positions {lo}-{hi - 1}")

    sort_range(0, len(s.a))
    s.step((), "Sorted")
    return s.a


# ----------------------------------------------------------------- Quick
def quick_sort(items, key=None, reverse=False, on_step=None, stats=None):
    """
    Divide and conquer:
      1. choose a pivot (we use the middle element to avoid the O(n²) worst
         case on already-sorted data),
      2. partition: move smaller elements left of the pivot, larger right,
      3. recursively sort both sides.
    Average O(n log n), worst O(n²) if pivots are always extreme.
    The recursion always handles the smaller side first so the call stack
    stays O(log n).
    """
    s = _Sorter(items, key, reverse, on_step, stats)

    def partition(lo, hi):            # Lomuto partition on s.a[lo..hi]
        mid = (lo + hi) // 2
        s.swap(mid, hi)               # move pivot to the end
        pivot = s.a[hi]
        store = lo
        for i in range(lo, hi):
            s.step((i, hi), f"Compare position {i} with pivot")
            if s.before(s.a[i], pivot):
                if i != store:
                    s.swap(i, store)
                    s.step((i, store), f"Swap positions {i} and {store}")
                store += 1
        s.swap(store, hi)             # put pivot in its final place
        s.step((store,), f"Pivot placed at position {store}")
        return store

    def sort_range(lo, hi):
        while lo < hi:
            p = partition(lo, hi)
            if p - lo < hi - p:
                sort_range(lo, p - 1)
                lo = p + 1
            else:
                sort_range(p + 1, hi)
                hi = p - 1

    sort_range(0, len(s.a) - 1)
    s.step((), "Sorted")
    return s.a


ALGORITHMS = {
    "Bubble Sort": {"fn": bubble_sort, "best": "O(n)", "average": "O(n²)", "worst": "O(n²)",
                    "space": "O(1)", "stable": True,
                    "idea": "Swap adjacent out-of-order pairs; largest values bubble to the end."},
    "Selection Sort": {"fn": selection_sort, "best": "O(n²)", "average": "O(n²)",
                       "worst": "O(n²)", "space": "O(1)", "stable": False,
                       "idea": "Repeatedly select the minimum of the unsorted part."},
    "Insertion Sort": {"fn": insertion_sort, "best": "O(n)", "average": "O(n²)",
                       "worst": "O(n²)", "space": "O(1)", "stable": True,
                       "idea": "Insert each element into the sorted prefix by shifting."},
    "Merge Sort": {"fn": merge_sort, "best": "O(n log n)", "average": "O(n log n)",
                   "worst": "O(n log n)", "space": "O(n)", "stable": True,
                   "idea": "Split in halves, sort recursively, merge sorted halves."},
    "Quick Sort": {"fn": quick_sort, "best": "O(n log n)", "average": "O(n log n)",
                   "worst": "O(n²)", "space": "O(log n)", "stable": False,
                   "idea": "Partition around a pivot, then sort each side recursively."},
}

ALGORITHM_NAMES = tuple(ALGORITHMS.keys())
DEFAULT_ALGORITHM = "Merge Sort"


def sort_items(items, key=None, reverse=False, algorithm=DEFAULT_ALGORITHM, stats=None):
    """Dispatch to the chosen algorithm by name (used by the services/UI)."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown sorting algorithm: {algorithm}")
    return ALGORITHMS[algorithm]["fn"](items, key=key, reverse=reverse, stats=stats)
