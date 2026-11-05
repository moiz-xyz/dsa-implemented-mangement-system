import unittest

from data_structures.stack import Stack, StackUnderflowError


class TestStack(unittest.TestCase):
    def test_push_pop_lifo(self):
        s = Stack()
        for item in "ABC":
            s.push(item)
        self.assertEqual(s.size(), 3)
        self.assertEqual(s.peek(), "C")
        self.assertEqual(s.pop(), "C")
        self.assertEqual(s.pop(), "B")
        self.assertEqual(s.display(), ["A"])

    def test_empty_stack(self):
        s = Stack()
        self.assertTrue(s.is_empty())
        with self.assertRaises(StackUnderflowError):
            s.pop()
        with self.assertRaises(StackUnderflowError):
            s.peek()

    def test_bounded_stack_drops_oldest(self):
        s = Stack(max_size=3)
        for i in range(5):
            s.push(i)
        self.assertEqual(s.display(), [4, 3, 2])


if __name__ == "__main__":
    unittest.main()
