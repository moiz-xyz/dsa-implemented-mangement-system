import unittest

from data_structures.linked_list import RouteLinkedList


def sample():
    return RouteLinkedList.from_pairs([("Karachi", 0), ("Hyderabad", 165), ("Nawabshah", 130),
                                       ("Sukkur", 185), ("Multan", 450), ("Lahore", 340)])


class TestRouteLinkedList(unittest.TestCase):
    def test_traverse_and_total(self):
        route = sample()
        self.assertEqual(len(route), 6)
        self.assertEqual(route.stop_names()[0], "Karachi")
        self.assertEqual(route.stop_names()[-1], "Lahore")
        self.assertEqual(route.total_distance(), 1270)
        self.assertIn("Karachi", route.display())

    def test_search_and_position(self):
        route = sample()
        self.assertEqual(route.position_of("Sukkur"), 3)
        self.assertEqual(route.position_of("sukkur"), 3)      # case-insensitive
        self.assertEqual(route.position_of("Quetta"), -1)
        self.assertIsNotNone(route.search("Multan"))
        self.assertIsNone(route.search("Quetta"))

    def test_insert_middle_splits_distance(self):
        route = sample()
        route.insert_after("Sukkur", "Rahim Yar Khan", 175, distance_to_next=290)
        self.assertEqual(route.position_of("Rahim Yar Khan"), 4)
        self.assertEqual(route.search("Multan").distance, 290)
        self.assertEqual(len(route), 7)

    def test_insert_head_and_tail(self):
        route = sample()
        route.insert_at(0, "Thatta", 100)
        self.assertEqual(route.first_stop(), "Thatta")
        self.assertEqual(route.search("Karachi").distance, 100)
        route.insert_at(len(route), "Islamabad", 375)
        self.assertEqual(route.last_stop(), "Islamabad")

    def test_insert_invalid(self):
        route = sample()
        with self.assertRaises(ValueError):
            route.append("Karachi", 10)                 # duplicate
        with self.assertRaises(IndexError):
            route.insert_at(99, "X", 1)
        with self.assertRaises(ValueError):
            route.insert_after("Karachi", "Kotri", 500)  # longer than the segment

    def test_delete_head_middle_tail(self):
        route = sample()
        total = route.total_distance()
        route.delete("Nawabshah")                        # middle: distance merged
        self.assertEqual(route.search("Sukkur").distance, 315)
        self.assertEqual(route.total_distance(), total)
        route.delete("Karachi")                          # head
        self.assertEqual(route.first_stop(), "Hyderabad")
        self.assertEqual(route.head.distance, 0)
        route.delete("Lahore")                           # tail
        self.assertEqual(route.last_stop(), "Multan")
        self.assertEqual(len(route), 3)
        with self.assertRaises(ValueError):
            route.delete("Quetta")

    def test_distance_between(self):
        route = sample()
        self.assertEqual(route.distance_between("Hyderabad", "Sukkur"), 315)
        self.assertIsNone(route.distance_between("Lahore", "Karachi"))   # wrong direction
        self.assertIsNone(route.distance_between("Karachi", "Quetta"))

    def test_empty_list(self):
        route = RouteLinkedList()
        self.assertTrue(route.is_empty())
        self.assertEqual(route.total_distance(), 0)
        self.assertIsNone(route.first_stop())


if __name__ == "__main__":
    unittest.main()
