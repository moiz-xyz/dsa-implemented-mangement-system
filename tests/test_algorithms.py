import random
import unittest

from algorithms.searching import (binary_search, binary_search_prefix, linear_search,
                                  linear_search_all)
from algorithms.sorting import ALGORITHMS, SortStats, merge_sort, sort_items
from data_structures.priority_queue import MinHeap


class TestSearching(unittest.TestCase):
    def test_linear_search(self):
        data = [7, 3, 9, 1]
        self.assertEqual(linear_search(data, 9).index, 2)
        self.assertEqual(linear_search(data, 9).comparisons, 3)
        missing = linear_search(data, 4)
        self.assertFalse(missing.found)
        self.assertEqual(missing.comparisons, 4)
        self.assertEqual(linear_search([], 1).index, -1)

    def test_binary_search(self):
        data = list(range(0, 1000, 5))
        self.assertEqual(binary_search(data, 500).index, 100)
        self.assertFalse(binary_search(data, 501).found)
        self.assertLessEqual(binary_search(data, 995).comparisons, 8)   # log2(200) ≈ 7.6
        self.assertEqual(binary_search([], 3).index, -1)
        self.assertEqual(binary_search([3], 3).index, 0)

    def test_search_with_key_and_prefix(self):
        people = [{"n": "ahmed"}, {"n": "ali"}, {"n": "moiz"}, {"n": "sara"}]
        self.assertEqual(binary_search(people, "moiz", key=lambda p: p["n"]).index, 2)
        self.assertEqual(len(binary_search_prefix(people, "a", key=lambda p: p["n"])), 2)
        self.assertEqual(len(linear_search_all(people, lambda p: "a" in p["n"])), 3)

    def test_binary_beats_linear_on_large_data(self):
        data = list(range(100000))
        self.assertLess(binary_search(data, 99999).comparisons,
                        linear_search(data, 99999).comparisons)


class TestSorting(unittest.TestCase):
    def test_all_algorithms_random_data(self):
        rng = random.Random(1)
        for _ in range(20):
            data = [rng.randint(-50, 50) for _ in range(rng.randint(0, 40))]
            expected = list(data)
            # reference: simple manual check of non-decreasing order + same multiset
            for name, info in ALGORITHMS.items():
                result = info["fn"](data)
                self.assertEqual(len(result), len(expected), name)
                for i in range(len(result) - 1):
                    self.assertLessEqual(result[i], result[i + 1], name)
                self.assertEqual(sorted(result), sorted(expected), name)  # test oracle only

    def test_empty_single_sorted_reverse(self):
        for name, info in ALGORITHMS.items():
            fn = info["fn"]
            self.assertEqual(fn([]), [], name)
            self.assertEqual(fn([5]), [5], name)
            self.assertEqual(fn([1, 2, 3, 4]), [1, 2, 3, 4], name)
            self.assertEqual(fn([4, 3, 2, 1]), [1, 2, 3, 4], name)
            self.assertEqual(fn([1, 3, 2], reverse=True), [3, 2, 1], name)

    def test_key_and_original_unchanged(self):
        buses = [("B", 300), ("A", 100), ("C", 200)]
        original = list(buses)
        for name in ALGORITHMS:
            self.assertEqual([b[0] for b in sort_items(buses, key=lambda b: b[1],
                                                       algorithm=name)], ["A", "C", "B"])
        self.assertEqual(buses, original)

    def test_merge_sort_is_stable(self):
        items = [("x", 1), ("y", 0), ("z", 1), ("w", 0)]
        self.assertEqual(merge_sort(items, key=lambda t: t[1]),
                         [("y", 0), ("w", 0), ("x", 1), ("z", 1)])

    def test_stats_and_steps(self):
        stats = SortStats()
        steps = []
        ALGORITHMS["Bubble Sort"]["fn"]([3, 1, 2], stats=stats,
                                        on_step=lambda a, i, t: steps.append(a))
        self.assertGreater(stats.comparisons, 0)
        self.assertEqual(steps[-1], [1, 2, 3])
        with self.assertRaises(ValueError):
            sort_items([1], algorithm="Bogo Sort")


class TestMinHeap(unittest.TestCase):
    def test_heap_order(self):
        h = MinHeap()
        for p in [5, 1, 4, 2, 3]:
            h.push(p, f"item{p}")
        out = [h.pop()[0] for _ in range(5)]
        self.assertEqual(out, [1, 2, 3, 4, 5])
        with self.assertRaises(IndexError):
            h.pop()


if __name__ == "__main__":
    unittest.main()
