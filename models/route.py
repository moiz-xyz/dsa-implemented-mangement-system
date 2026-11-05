"""Route model – wraps the custom RouteLinkedList."""

from dataclasses import dataclass, field

from data_structures.linked_list import RouteLinkedList


@dataclass
class Route:
    route_id: int
    route_name: str
    description: str = ""
    stops: RouteLinkedList = field(default_factory=RouteLinkedList)

    @property
    def source(self):
        return self.stops.first_stop() or "-"

    @property
    def destination(self):
        return self.stops.last_stop() or "-"

    @property
    def total_distance(self):
        return self.stops.total_distance()

    @property
    def stop_count(self):
        return len(self.stops)

    def path_text(self):
        return " → ".join(self.stops.stop_names())
