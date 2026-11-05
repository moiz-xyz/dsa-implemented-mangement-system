"""
Admin navigation: the pages an administrator can open, in sidebar order.
Each entry is (key, label, icon name, factory(parent, ctx) -> page).
"""


def _dashboard(parent, ctx):
    from ui.dashboard import DashboardPage
    return DashboardPage(parent, ctx)


def _buses(parent, ctx):
    from ui.bus_management import BusManagementPage
    return BusManagementPage(parent, ctx)


def _routes(parent, ctx):
    from ui.route_management import RouteManagementPage
    return RouteManagementPage(parent, ctx)


def _passengers(parent, ctx):
    from ui.passenger_management import PassengerManagementPage
    return PassengerManagementPage(parent, ctx)


def _bookings(parent, ctx):
    from ui.booking_management import BookingManagementPage
    return BookingManagementPage(parent, ctx)


def _waiting(parent, ctx):
    from ui.waiting_list import WaitingListPage
    return WaitingListPage(parent, ctx)


def _reports(parent, ctx):
    from ui.reports import ReportsPage
    return ReportsPage(parent, ctx)


def _lab(parent, ctx):
    from ui.dsa_lab import DSALabPage
    return DSALabPage(parent, ctx)


ADMIN_PAGES = [
    ("dashboard", "Dashboard", "dashboard", _dashboard),
    ("buses", "Bus Management", "bus", _buses),
    ("routes", "Routes & Network", "route", _routes),
    ("passengers", "Passengers", "users", _passengers),
    ("bookings", "Bookings", "ticket", _bookings),
    ("waiting", "Waiting List", "queue", _waiting),
    ("reports", "Reports", "chart", _reports),
    ("lab", "DSA Lab", "lab", _lab),
]
