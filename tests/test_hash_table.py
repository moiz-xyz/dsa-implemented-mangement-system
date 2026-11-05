import unittest

from data_structures.hash_table import HashTable


class TestHashTable(unittest.TestCase):
    def test_insert_search_update_delete(self):
        h = HashTable()
        h.insert("SB-AAA", 1)
        h.insert("SB-BBB", 2)
        self.assertEqual(h.search("SB-AAA"), 1)
        h.insert("SB-AAA", 10)                # update, not duplicate
        self.assertEqual(len(h), 2)
        self.assertEqual(h.search("SB-AAA"), 10)
        self.assertEqual(h.delete("SB-AAA"), 10)
        self.assertIsNone(h.search("SB-AAA"))
        self.assertFalse(h.contains("SB-AAA"))

    def test_missing_keys(self):
        h = HashTable()
        self.assertIsNone(h.search("missing"))
        self.assertEqual(h.search("missing", "default"), "default")
        with self.assertRaises(KeyError):
            h.delete("missing")

    def test_collisions_with_separate_chaining(self):
        h = HashTable(capacity=1, auto_resize=False)   # every key collides
        for i in range(20):
            h.insert(f"K{i}", i)
        stats = h.stats()
        self.assertEqual(stats["longest_chain"], 20)
        self.assertEqual(stats["collisions"], 19)
        for i in range(20):
            self.assertEqual(h.search(f"K{i}"), i)
        h.delete("K10")                                  # delete from middle of chain
        self.assertIsNone(h.search("K10"))
        self.assertEqual(h.search("K11"), 11)

    def test_resize_keeps_entries(self):
        h = HashTable(capacity=4)
        for i in range(100):
            h.insert(i, i * i)
        self.assertGreater(h.capacity, 4)
        self.assertLessEqual(h.load_factor(), 0.75)
        for i in range(100):
            self.assertEqual(h.search(i), i * i)

    def test_trace_and_display(self):
        h = HashTable(capacity=5, auto_resize=False)
        h.insert("A", 1)
        bucket, compared, value = h.search_trace("A")
        self.assertEqual(bucket, h.bucket_index("A"))
        self.assertEqual(compared, ["A"])
        self.assertEqual(value, 1)
        self.assertEqual(len(h.display()), 5)


if __name__ == "__main__":
    unittest.main()
