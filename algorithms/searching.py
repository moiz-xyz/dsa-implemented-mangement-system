"""
SEARCHING ALGORITHMS
====================

1. Linear Search – O(n)
   Check every element from left to right until the target is found.
   Works on ANY list (sorted or not).

2. Binary Search – O(log n)
   Works ONLY on a SORTED list. Look at the middle element:
     * equal   -> found
     * smaller -> the target must be in the right half
     * larger  -> the target must be in the left half
   Each step halves the search space, so 1,000,000 items need at most
   about 20 comparisons (2^20 ≈ 1,000,000).

Both functions accept an optional `key` function, so we can search lists of
objects (buses, passengers, bookings) by any field, and they return a
SearchResult that also reports how many comparisons were made – this lets
the DSA Lab compare the two algorithms.
"""

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    index: int                      # -1 when not found
    comparisons: int
    steps: list = field(default_factory=list)

    @property
    def found(self):
        return self.index != -1


def _identity(x):
    return x


def linear_search(items, target, key=None, record=False):
    """Return SearchResult with the index of the first element whose key == target."""
    key = key or _identity
    comparisons = 0
    steps = []
    for i in range(len(items)):
        comparisons += 1
        value = key(items[i])
        if record:
            steps.append({"index": i, "value": value, "match": value == target})
        if value == target:
            return SearchResult(i, comparisons, steps)
    return SearchResult(-1, comparisons, steps)


def linear_search_all(items, predicate):
    """
    Return every element for which predicate(element) is True.
    Used for flexible filters such as "name contains 'ali'" – something binary
    search cannot do because it needs an exact, ordered key.
    """
    matches = []
    for i in range(len(items)):
        if predicate(items[i]):
            matches.append(items[i])
    return matches


def binary_search(sorted_items, target, key=None, record=False):
    """
    Iterative binary search on a list sorted in ascending order of key(item).
    Returns SearchResult (index -1 if missing).
    """
    key = key or _identity
    low, high = 0, len(sorted_items) - 1
    comparisons = 0
    steps = []
    while low <= high:
        mid = (low + high) // 2
        value = key(sorted_items[mid])
        comparisons += 1
        if record:
            steps.append({"low": low, "mid": mid, "high": high, "value": value,
                          "match": value == target})
        if value == target:
            return SearchResult(mid, comparisons, steps)
        if value < target:
            low = mid + 1           # discard left half
        else:
            high = mid - 1          # discard right half
    return SearchResult(-1, comparisons, steps)


def binary_search_prefix(sorted_items, prefix, key=None):
    """
    Return all items whose key starts with `prefix` (keys must be sorted).
    Binary search finds the first candidate in O(log n), then we scan forward
    only while the prefix still matches.
    """
    key = key or _identity
    low, high = 0, len(sorted_items)
    while low < high:                       # lower-bound binary search
        mid = (low + high) // 2
        if key(sorted_items[mid]) < prefix:
            low = mid + 1
        else:
            high = mid
    result = []
    i = low
    while i < len(sorted_items) and str(key(sorted_items[i])).startswith(prefix):
        result.append(sorted_items[i])
        i += 1
    return result


COMPLEXITY = {
    "Linear Search": {"best": "O(1)", "average": "O(n)", "worst": "O(n)", "space": "O(1)",
                      "requires_sorted": False},
    "Binary Search": {"best": "O(1)", "average": "O(log n)", "worst": "O(log n)",
                      "space": "O(1)", "requires_sorted": True},
}
