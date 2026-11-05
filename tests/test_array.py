import unittest

from data_structures.custom_array import FixedArray, SeatMatrix


class TestFixedArray(unittest.TestCase):
    def test_fixed_size_and_bounds(self):
        arr = FixedArray(3, 0)
        self.assertEqual(len(arr), 3)
        arr[2] = 7
        self.assertEqual(arr[2], 7)
        with self.assertRaises(IndexError):
            arr[3] = 1
        with self.assertRaises(IndexError):
            _ = arr[-1]

    def test_count_and_iteration(self):
        arr = FixedArray(5, 1)
        arr[0] = 0
        self.assertEqual(arr.count(1), 4)
        self.assertEqual(list(arr), [0, 1, 1, 1, 1])


class TestSeatMatrix(unittest.TestCase):
    def test_layout_and_indexing(self):
        m = SeatMatrix(10, 4)               # 3 rows, last row has 2 padding cells
        self.assertEqual(m.rows, 3)
        self.assertEqual(m.position_of(1), (0, 0))
        self.assertEqual(m.position_of(10), (2, 1))
        self.assertEqual(m.seat_number(2, 1), 10)
        self.assertEqual(m.to_matrix()[2], [0, 0, -1, -1])
        with self.assertRaises(IndexError):
            m.position_of(11)
        with self.assertRaises(IndexError):
            m.seat_number(2, 2)

    def test_reserve_release_and_counts(self):
        m = SeatMatrix(8, 4)
        m.reserve(3)
        m.reserve(8)
        self.assertFalse(m.is_available(3))
        self.assertEqual(m.occupied_count(), 2)
        self.assertEqual(m.available_count(), 6)
        self.assertEqual(m.booked_seats(), [3, 8])
        m.release(3)
        self.assertTrue(m.is_available(3))
        self.assertEqual(m.first_available(), 1)

    def test_prevent_duplicate_reservation(self):
        m = SeatMatrix(4, 4)
        m.reserve(2)
        with self.assertRaises(ValueError):
            m.reserve(2)
        with self.assertRaises(ValueError):
            m.release(1)

    def test_full_bus(self):
        m = SeatMatrix(3, 3)
        for s in (1, 2, 3):
            m.reserve(s)
        self.assertTrue(m.is_full())
        self.assertIsNone(m.first_available())


if __name__ == "__main__":
    unittest.main()
