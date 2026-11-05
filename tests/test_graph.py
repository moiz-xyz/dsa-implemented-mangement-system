import unittest

from algorithms.shortest_path import dijkstra, find_all_routes
from data_structures.graph import Graph


def network():
    g = Graph()
    g.add_connection("Karachi", "Hyderabad", 165)
    g.add_connection("Hyderabad", "Sukkur", 330)
    g.add_connection("Hyderabad", "Nawabshah", 130)
    g.add_connection("Nawabshah", "Sukkur", 185)
    g.add_connection("Sukkur", "Multan", 450)
    g.add_connection("Multan", "Lahore", 340)
    g.add_city("Gwadar")                     # isolated city
    return g


class TestGraph(unittest.TestCase):
    def test_add_remove_connections(self):
        g = network()
        self.assertTrue(g.has_connection("Karachi", "Hyderabad"))
        self.assertTrue(g.has_connection("Hyderabad", "Karachi"))   # undirected
        g.add_connection("Karachi", "Hyderabad", 160)               # keeps shorter
        self.assertEqual(g.weight("Karachi", "Hyderabad"), 160)
        g.remove_connection("Karachi", "Hyderabad")
        self.assertFalse(g.has_connection("Karachi", "Hyderabad"))
        with self.assertRaises(KeyError):
            g.remove_connection("Karachi", "Lahore")
        with self.assertRaises(ValueError):
            g.add_connection("A", "A", 5)

    def test_bfs_and_dfs(self):
        g = network()
        bfs = g.bfs("Karachi")
        self.assertEqual(bfs[0], "Karachi")
        self.assertEqual(bfs[1], "Hyderabad")
        self.assertEqual(set(bfs), {"Karachi", "Hyderabad", "Sukkur", "Nawabshah",
                                    "Multan", "Lahore"})
        self.assertEqual(g.dfs("Karachi"), g.dfs_recursive("Karachi"))
        self.assertEqual(g.bfs_levels("Karachi")["Sukkur"], 2)
        self.assertEqual(g.connected_destinations("Gwadar"), [])
        self.assertNotIn("Gwadar", bfs)

    def test_dijkstra_shortest_path(self):
        g = network()
        result = dijkstra(g, "Karachi", "Lahore")
        # Hyderabad -> Nawabshah -> Sukkur (315 km) beats the direct road (330 km).
        self.assertEqual(result.path, ["Karachi", "Hyderabad", "Nawabshah", "Sukkur",
                                       "Multan", "Lahore"])
        self.assertEqual(result.distance, 165 + 130 + 185 + 450 + 340)

    def test_dijkstra_unreachable(self):
        g = network()
        result = dijkstra(g, "Karachi", "Gwadar")
        self.assertFalse(result.reachable)
        self.assertEqual(result.path, [])
        self.assertEqual(result.distance, float("inf"))
        with self.assertRaises(KeyError):
            dijkstra(g, "Karachi", "Atlantis")

    def test_dijkstra_same_city(self):
        result = dijkstra(network(), "Multan", "Multan")
        self.assertEqual(result.path, ["Multan"])
        self.assertEqual(result.distance, 0)

    def test_alternative_routes_sorted(self):
        routes = find_all_routes(network(), "Karachi", "Lahore")
        self.assertEqual(len(routes), 2)
        self.assertLessEqual(routes[0][1], routes[1][1])
        self.assertEqual(routes[0][1], dijkstra(network(), "Karachi", "Lahore").distance)


if __name__ == "__main__":
    unittest.main()
