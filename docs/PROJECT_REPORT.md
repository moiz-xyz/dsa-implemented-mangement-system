# SMARTBUS – Intelligent Bus Reservation & Route Management System

### Project Report – Data Structures and Algorithms

| | |
|---|---|
| **Project title** | SMARTBUS – Intelligent Bus Reservation & Route Management System |
| **Course** | Data Structures and Algorithms |
| **Language** | Python 3 |
| **Platform** | Desktop (Windows, Linux, macOS) – Tkinter GUI, SQLite database |

---

## Table of contents

1. [Introduction](#1-introduction)
2. [Problem statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Scope](#4-scope)
5. [Functional requirements](#5-functional-requirements)
6. [Non-functional requirements](#6-non-functional-requirements)
7. [System architecture](#7-system-architecture)
8. [Data structures and algorithms](#8-data-structures-and-algorithms)
9. [Database design](#9-database-design)
10. [User interface](#10-user-interface)
11. [Testing](#11-testing)
12. [Conclusion](#12-conclusion)
13. [Future improvements](#13-future-improvements)

---

## 1. Introduction

Intercity bus travel is one of the most common forms of transport. A bus company must manage its
fleet, plan routes between cities, sell tickets for specific seats, handle cancellations fairly
and understand its business through reports. Doing this by hand, or with a simple spreadsheet,
quickly leads to double-booked seats, lost waiting-list requests and slow lookups.

SMARTBUS is a desktop application that solves these problems. It was designed as a practical
demonstration of the data structures and algorithms studied in this course. Each structure
(arrays, linked lists, stacks, queues, hash tables and graphs) and each algorithm (searching,
sorting, BFS, DFS and Dijkstra's shortest path) was implemented **by hand in Python**, and each
one solves a real part of the reservation problem.

## 2. Problem statement

A bus reservation system must answer questions such as:

* *Which seats on this bus are free, and how do we make sure two people never get the same
  seat?*
* *In what order are the stops on a route, and how far is it from one stop to another?*
* *When a full bus has a cancellation, who should get the seat?*
* *How can a staff member quickly find a booking from its ID?*
* *What is the shortest road route between two cities when several routes overlap?*
* *How can a user safely undo a mistake?*

Each question matches a classic data-structure problem: indexed storage, ordered sequences,
fair scheduling, key-based lookup, shortest paths and reversing recent operations. The challenge
is to solve them **correctly** (no double bookings, fair queues), **efficiently** (fast lookups
and searches) and **persistently** (nothing is lost when the program closes).

## 3. Objectives

1. Implement the required data structures and algorithms manually, without relying on Python's
   built-in equivalents.
2. Use each implementation for a real task in the application, not only in isolated examples.
3. Store all information permanently in a relational database while keeping the in-memory
   structures synchronised with it.
4. Provide a modern, consistent graphical interface for administrators and passengers.
5. Provide a *DSA Lab* that visualises each data structure and algorithm step by step.
6. Verify correctness with automated tests.

## 4. Scope

**In scope**

* Two user roles: **administrator** and **passenger**.
* Management of buses, routes (with stops), passengers and bookings.
* Seat-level reservation with an interactive seat map.
* A waiting list per bus, with automatic seat allocation.
* Undo of recent booking operations.
* Route planning on a city network (BFS, DFS, Dijkstra).
* A dashboard, six reports and CSV export.
* An educational DSA Lab.

**Out of scope**

* Online payment, e-mail/SMS notifications and multi-computer networking.
* Pricing that changes with the travelled segment (every seat on a bus has one fixed fare).
* A seat being sold separately for different segments of the same trip.

## 5. Functional requirements

| ID | Requirement | Where it is met |
|---|---|---|
| FR-1 | Admin and passenger login with hashed passwords; passenger registration; logout | `services/auth_service.py`, `ui/login_window.py` |
| FR-2 | Dashboard with totals (buses, passengers, bookings, available/occupied seats, cancellations, waiting passengers, revenue) and charts | `services/report_service.py`, `ui/dashboard.py` |
| FR-3 | Add / edit / delete / view / search / sort buses; block deletion while active bookings exist | `services/bus_service.py`, `ui/bus_management.py` |
| FR-4 | Create routes, add/remove stops, edit details, show distance, show connected cities, shortest paths | `services/route_service.py`, `ui/route_management.py` |
| FR-5 | Register / edit / safely delete / search / sort passengers; booking history | `services/passenger_service.py`, `ui/passenger_management.py` |
| FR-6 | Search buses by departure city, destination, date, time, price and free seats; sort by cheapest, earliest, shortest distance, most seats | `BusService.search_buses`, `ui/passenger_panel.py` |
| FR-7 | Interactive seat selection (green/red/blue), total price, unique booking ID, confirmation; never allow double booking | `ui/seat_selection.py`, `BookingService.book_seats` |
| FR-8 | Create, view, search (by ID), cancel and track bookings (Confirmed / Cancelled / Waiting) | `services/booking_service.py`, `ui/booking_management.py` |
| FR-9 | Waiting list with queue position; automatic FIFO allocation on cancellation | `BookingService._sql_allocate`, `ui/waiting_list.py` |
| FR-10 | Reports: daily bookings, monthly revenue, passengers, bus occupancy, route popularity, cancellations; CSV export | `services/report_service.py`, `ui/reports.py` |
| FR-11 | Undo last action (book, cancel, change seat, join waiting list) | `BookingService.undo_last` |
| FR-12 | DSA Lab with demonstrations of all nine topics | `ui/dsa_lab.py` |

## 6. Non-functional requirements

| Category | How SMARTBUS satisfies it |
|---|---|
| **Correctness / consistency** | Every multi-step change runs in one SQLite transaction. Memory is updated only after commit. A partial UNIQUE index makes double booking impossible at database level |
| **Security** | PBKDF2-HMAC-SHA256 with a random 16-byte salt per user and 100,000 iterations; constant-time comparison; parameterised SQL only |
| **Usability** | Consistent theme, sidebar navigation, search bars, drop-down filters, empty states, toast notifications, confirmation dialogs for destructive actions |
| **Robustness** | All user input is validated (`utils/validators.py`); expected errors are shown as friendly messages; the UI catches every exception, so ordinary mistakes never crash the program |
| **Performance** | O(1) seat access and booking lookup; O(log n) binary search; O(n log n) default sorting; the full start-up load takes well under a second with the demo data |
| **Portability** | Pure Python standard library plus optional Matplotlib; label-based buttons look identical on Windows, Linux and macOS |
| **Maintainability** | Layered architecture (UI → services → data structures/algorithms → database); one class per concept; extensive comments |
| **Zero configuration** | The database is created and seeded automatically on first launch |

## 7. System architecture

SMARTBUS follows a **layered architecture**. Each layer uses only the layer below it.

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRESENTATION  (ui/)                                                  │
│  login · dashboard · buses · routes · passengers · bookings ·        │
│  seat selection · waiting list · reports · DSA Lab                   │
├──────────────────────────────────────────────────────────────────────┤
│  BUSINESS LOGIC  (services/)                                          │
│  AuthService · BusService · RouteService · PassengerService ·        │
│  BookingService · ReportService         (wired by SmartBusApp)        │
├───────────────────────────────┬──────────────────────────────────────┤
│  DATA STRUCTURES              │  ALGORITHMS                          │
│  (data_structures/)           │  (algorithms/)                       │
│  FixedArray, SeatMatrix,      │  linear/binary search,               │
│  RouteLinkedList, Stack,      │  5 sorting algorithms,               │
│  Queue, HashTable, Graph,     │  Dijkstra, route enumeration         │
│  MinHeap                      │                                      │
├───────────────────────────────┴──────────────────────────────────────┤
│  PERSISTENCE  (database/)   SQLite: schema.sql · database.py · seed.py│
└──────────────────────────────────────────────────────────────────────┘
```

**Start-up sequence.**

1. `main.py` creates the Tk window and `SmartBusApp`.
2. `Database.initialize()` executes `schema.sql` (idempotent) and seeds demo data if the
   database is empty.
3. `RouteService` loads every route into a `RouteLinkedList` and builds the `Graph`.
4. `BookingService` loads all bookings into the `HashTable`, builds a `SeatMatrix` for each bus,
   and rebuilds each bus's waiting `Queue` in `waiting_id` order.
5. The login window is shown. After login, the user's undo `Stack` is rebuilt from
   `booking_history`.

**Two-phase updates.** Every booking operation collects (a) the SQL statements and (b) small
"effect" functions that update memory. The SQL runs inside one transaction. Only if it commits
are the effects applied. This is how the database and the data structures are kept synchronised.

## 8. Data structures and algorithms

The detailed explanation, with diagrams and code, is in **`docs/DSA_EXPLANATION.md`**. This
section summarises the design decisions.

| # | Structure / algorithm | SMARTBUS problem | Why this choice | Complexity |
|---|---|---|---|---|
| 1 | **2-D array** (`SeatMatrix`) | Seat availability per bus | Fixed layout, direct O(1) indexing with `row = (s-1)//C`, `col = (s-1)%C` | access O(1), count O(n) |
| 2 | **Singly linked list** (`RouteLinkedList`) | Ordered stops of a route | Cheap insertion/removal of stops in the middle (re-link pointers, no shifting) | insert O(k), search O(n) |
| 3 | **Stack** (`Stack`) | Undo last action | Undo must reverse the most recent action → LIFO | push/pop O(1) |
| 4 | **Queue** (`Queue`) | Waiting list for full buses | Fairness requires first-come-first-served → FIFO | enqueue/dequeue O(1) |
| 5 | **Hash table** (`HashTable`) | Booking lookup by ID | Constant average-time lookup; separate chaining for collisions; resizing at load factor 0.75 | O(1) average |
| 6 | **Graph** (`Graph`) | City network formed by all routes | Overlapping routes form a network; adjacency list is memory-efficient for sparse graphs | BFS/DFS O(V+E) |
| 7 | **Dijkstra + MinHeap** | Shortest road distance | Optimal for non-negative weighted graphs | O((V+E) log V) |
| 8 | **Linear / binary search** | Filters / exact lookups | Linear for "contains" filters on unsorted data; binary for exact keys on sorted data | O(n) / O(log n) |
| 9 | **Bubble, selection, insertion, merge, quick sort** | Sorting every table | All five selectable from the UI to compare; merge sort is the stable default | O(n²) … O(n log n) |

**Key invariant (waiting list).** A passenger may only join a bus's queue when the bus is full,
and every freed seat is first offered to the queue. Therefore *"queue not empty ⇒ no free
seats"*. Undo operations are checked against this rule, so undo can never let anyone skip the
queue.

## 9. Database design

### Entity–relationship overview

```
users 1───1 passengers 1───* bookings *───1 buses *───1 routes 1───* route_stops
                               │  1
                               │
                               0..1
                          waiting_list            booking_history (log, rebuilds undo stacks)
```

### Tables

| Table | Main columns | Constraints |
|---|---|---|
| `users` | user_id, username, password_hash, salt, role, created_at | PK, UNIQUE username, CHECK role |
| `passengers` | passenger_id, user_id, full_name, email, phone, registration_date | PK, FK users (CASCADE), UNIQUE email |
| `routes` | route_id, route_name, description, created_at | PK, UNIQUE route_name |
| `route_stops` | stop_id, route_id, stop_order, stop_name, distance_from_prev | PK, FK routes (CASCADE), UNIQUE(route_id, stop_order), UNIQUE(route_id, stop_name), CHECK distance ≥ 0 |
| `buses` | bus_id, bus_name, bus_number, bus_type, total_seats, ticket_price, route_id, departure_time, arrival_time, travel_date, status | PK, UNIQUE bus_number, FK routes (RESTRICT), CHECK seats > 0, price > 0, status list |
| `bookings` | booking_id, passenger_id, bus_id, seat_number, from_city, to_city, amount, status, booking_date, travel_date, passenger_name, bus_label, route_name, cancelled_at, cancel_reason | PK, FKs (SET NULL), CHECK status, CHECK confirmed ⇒ seat not null |
| `waiting_list` | waiting_id, booking_id, passenger_id, bus_id, request_date, status, resolved_at | PK AUTOINCREMENT (= arrival order), UNIQUE booking_id |
| `booking_history` | history_id, user_id, action, booking_id, details (JSON), undoable, undone, created_at | PK, FK users (SET NULL) |

### Indexes

* `ux_bookings_active_seat`: a **partial unique index** on `(bus_id, seat_number) WHERE status =
  'Confirmed'`. It is the database-level guarantee against double booking, while still allowing
  many *cancelled* bookings for the same seat.
* `ix_bookings_passenger`, `ix_bookings_bus`, `ix_bookings_date`, `ix_bookings_status`,
  `ix_waiting_bus_status` and `ix_history_user` speed up the common queries.

### Design decisions

* **Snapshots** (`passenger_name`, `bus_label`, `route_name` in `bookings`) keep the history and
  reports correct after a passenger or bus is deleted (foreign keys use `ON DELETE SET NULL`).
* **Safe deletion.** Buses and passengers with *Confirmed* or *Waiting* bookings cannot be
  deleted. The admin can use *Cancel bus* to cancel all of a bus's bookings in one transaction
  first.
* **Transactions** use `BEGIN IMMEDIATE`, so the write lock is taken at the start of the
  transaction. Nested calls use SAVEPOINTs.

## 10. User interface

The interface is built with Tkinter/ttk and a custom theme (primary `#2563EB`, secondary
`#22D3EE`, success `#10B981`, background `#F8FAFC`, sidebar `#0F172A`, text `#1E293B`).

* **Login**: brand panel with an illustration, an Admin/Passenger switch, demo credentials and a
  registration dialog.
* **Main window**: dark sidebar with icons, breadcrumb, date, and an *Undo last action* button
  that shows how many actions are on the stack.
* **Reusable components** (`ui/components.py`): cards, statistic cards, data tables (striped,
  scrollable, column-click sorting with merge sort, empty states), search bars, list toolbars
  (filter + sort criterion + algorithm), modal dialogs, toast notifications and confirmation
  dialogs.
* **Seat map**: drawn on a canvas from the `SeatMatrix`. Hovering a seat shows its array index
  calculation.
* **Dashboard charts** (Matplotlib): daily bookings, monthly revenue, popular routes and bus
  occupancy, with hover tooltips.
* **DSA Lab**: nine tabs with a canvas, controls, an animation-speed slider, an operation log and
  a complexity table.

Screenshots are in `docs/screenshots/` and in the README.

## 11. Testing

### Automated tests

68 automated tests in `tests/` (run with `python -m pytest`):

| Area | Example test cases |
|---|---|
| Array | index ↔ seat conversion, padding cells, reserve twice raises an error, release a free seat raises an error, full bus |
| Linked list | insert at head / middle (distance split) / tail, delete head / middle (distance merged) / tail, search case-insensitively, wrong-direction distance returns `None` |
| Stack | LIFO order, pop/peek on an empty stack raise `StackUnderflowError`, bounded stack |
| Queue | FIFO order, empty queue errors, rear pointer reset after emptying, remove from middle |
| Hash table | insert/update/delete, missing keys, **all keys forced into one bucket** (collision chain of 20), resizing keeps all entries |
| Graph & Dijkstra | undirected connections, BFS/DFS orders, iterative DFS = recursive DFS, shortest path and distance, **unreachable city**, same-city path, alternative routes sorted |
| Searching & sorting | found/missing/empty, binary search uses ≤ ⌈log₂ n⌉ comparisons, all five sorts on 20 random lists plus empty, single, sorted and reversed inputs, `key` and `reverse` options, merge sort stability |
| Booking workflow | registration validation, invalid credentials, **duplicate seat prevented** (service and DB index), failed transaction leaves memory unchanged, cancel releases seat, passengers cannot cancel others' bookings, seat limit, change seat |
| Waiting list | join only when full, duplicate request refused, **cancellation allocates the seat to the first waiting passenger**, leaving the queue, adding seats serves the queue |
| Undo | empty stack, undo booking, undo cancellation, **undo refused when the seat was re-allocated**, undo seat change, **undo stack survives restart** |
| Persistence | **close and reopen the application**: bookings, seat maps and queue order are restored and FIFO allocation still works |
| Admin rules | bus with bookings cannot be deleted until cancelled; passenger safe delete keeps history; route edits update the linked list and graph and survive restart; bus search; all reports export to CSV |

**Result: 68 passed, 0 failed.**

### Manual / GUI testing

The complete workflow was run through the real Tkinter interface: registering a passenger,
searching Karachi → Lahore, selecting two seats, confirming, viewing *My Bookings* and the undo
stack, joining the waiting list of a full bus, signing in as admin, cancelling a seat on that bus
(the seat was automatically allocated to the first waiting passenger), and trying to undo the
cancellation (correctly refused). It also covered adding and editing a bus (including an invalid
price), refusing to delete a bus or passenger with active bookings, creating a route, inserting
and removing a stop, changing a seat and undoing it, editing a passenger (including an invalid
phone number), entering an invalid travel date, and every button in all nine DSA Lab tabs. No
exceptions occurred, and every invalid input produced a clear message.

## 12. Conclusion

SMARTBUS shows that the fundamental data structures studied in this course are practical tools,
not only theory:

* the **array** gives instant seat access and makes double booking easy to detect;
* the **linked list** makes route editing simple;
* the **queue** makes the waiting list fair;
* the **stack** makes undo natural;
* the **hash table** makes booking lookup instant;
* the **graph** and **Dijkstra's algorithm** turn separate routes into a connected network that
  can answer shortest-path questions;
* the **searching and sorting** algorithms show clear, measurable differences in efficiency,
  which the user can see directly in the interface.

Combining these in-memory structures with a transactional SQLite database gives a system that is
both efficient and reliable: data is never lost, and memory and storage always agree. The DSA
Lab turns the same code into a teaching tool, so each concept can be shown and explained live.

## 13. Future improvements

1. **Segment-based seat allocation**: let one seat be sold for Karachi → Sukkur and again for
   Sukkur → Lahore (an interval-scheduling problem).
2. **Distance-based pricing**: fare proportional to the travelled segment.
3. **Online payments and e-tickets** with QR codes.
4. **Notifications** (e-mail or SMS) when a waiting passenger receives a seat.
5. **Multi-user server version** with a client–server architecture and row-level locking.
6. **Priority waiting list** (for example, senior citizens first) using a priority queue
   instead of a plain FIFO queue.
7. **A* search** using geographic coordinates as the heuristic, for faster route planning on
   large networks.
8. **Redo** using a second stack.
9. **Multilingual interface** (English / Urdu).
10. **Dark mode** theme.
