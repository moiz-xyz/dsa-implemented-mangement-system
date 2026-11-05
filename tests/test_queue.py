import unittest

from data_structures.queue import Queue, QueueEmptyError


class TestQueue(unittest.TestCase):
    def test_fifo_order(self):
        q = Queue()
        for name in ("Ali", "Ahmed", "Moiz"):
            q.enqueue(name)
        self.assertEqual(q.size(), 3)
        self.assertEqual(q.peek(), "Ali")
        self.assertEqual(q.dequeue(), "Ali")
        self.assertEqual(q.display(), ["Ahmed", "Moiz"])

    def test_empty_queue(self):
        q = Queue()
        self.assertTrue(q.is_empty())
        with self.assertRaises(QueueEmptyError):
            q.dequeue()
        with self.assertRaises(QueueEmptyError):
            q.peek()
        q.enqueue(1)
        q.dequeue()
        self.assertTrue(q.is_empty())
        q.enqueue(2)                       # rear pointer must be reset correctly
        self.assertEqual(q.peek(), 2)

    def test_remove_and_position(self):
        q = Queue()
        for name in ("Ali", "Ahmed", "Moiz", "Sara"):
            q.enqueue(name)
        self.assertEqual(q.position_of(lambda x: x == "Moiz"), 3)
        self.assertEqual(q.remove_where(lambda x: x == "Sara"), "Sara")   # rear
        q.enqueue("Zain")
        self.assertEqual(q.display(), ["Ali", "Ahmed", "Moiz", "Zain"])
        self.assertEqual(q.remove_where(lambda x: x == "Ali"), "Ali")     # front
        self.assertIsNone(q.remove_where(lambda x: x == "Nobody"))
        self.assertEqual(q.position_of(lambda x: x == "Nobody"), -1)


if __name__ == "__main__":
    unittest.main()
