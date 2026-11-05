# SMARTBUS – Data Structures & Algorithms Explained

This document explains every data structure and algorithm in SMARTBUS in plain language. For
each one you will find:

* **Why** it was chosen for this problem
* **Where** it is used in the application (file and screen)
* **How** it works, with a small picture and the key code
* Its **operations** and their **time complexity**
* A **practical SMARTBUS example**

> **Important principle.** SQLite stores the data *permanently*. The custom data structures do
> the *work* while the program runs. When SMARTBUS starts, it reads the database and builds the
> structures. When something changes, it first saves the change in a database transaction, and
> only if that succeeds does it update the structures in memory. This "two-phase" approach
> (see `BookingService._run` in `services/booking_service.py`) means memory and database can
> never disagree.

---

## Contents

1. [Array – bus seat management](#1-array--bus-seat-management)
2. [Singly linked list – bus routes](#2-singly-linked-list--bus-routes)
3. [Stack – booking history and undo](#3-stack--booking-history-and-undo)
4. [Queue – passenger waiting list](#4-queue--passenger-waiting-list)
5. [Hash table – fast booking lookup](#5-hash-table--fast-booking-lookup)
6. [Graph – city network, BFS and DFS](#6-graph--city-network-bfs-and-dfs)
7. [Dijkstra's shortest path (with a min-heap)](#7-dijkstras-shortest-path)
8. [Searching – linear vs binary](#8-searching--linear-vs-binary)
9. [Sorting – five algorithms](#9-sorting--five-algorithms)
10. [How the structures work together](#10-how-the-structures-work-together)
11. [Summary table](#11-summary-table)

A quick note on **Big-O notation**: O(1) means "constant time, the same speed no matter how
much data", O(n) means "time grows in proportion to the number of items", O(log n) means "time
grows very slowly, because each step halves the work", and O(n²) means "doubling the data makes
it about four times slower".

---

## 1. Array – bus seat management

**File:** `data_structures/custom_array.py` (`FixedArray`, `SeatMatrix`)
**Used in:** seat-selection screen, bus occupancy counts, booking rules, DSA Lab → *Array*

### Why an array?

A bus has a **fixed** number of seats arranged in **rows and columns**. That is exactly what a
two-dimensional array models. The seat number tells us *directly* where the seat is, so we never
have to search for it.

### How it works

`FixedArray` reserves all memory slots once and never grows. It has no `append` or `insert`, and
every index is bounds-checked, like an array in C or Java. `SeatMatrix` is an array of
`FixedArray` rows:

```
Seat status codes:   0 = Available    1 = Booked    -1 = no seat (padding)

           col 0  col 1 | col 2  col 3        (aisle between columns 1 and 2)
row 0     [  0  ][  1  ]|[  0  ][  0  ]       seats  1  2 |  3  4
row 1     [  1  ][  0  ]|[  0  ][  1  ]       seats  5  6 |  7  8
row 2     [  0  ][  0  ]|[ -1  ][ -1  ]       seats  9 10 | (a 10-seat bus has 2 padding cells)
```

**Indexing (row-major order).** For a bus with `C` columns:

```
index  = seat_number - 1
row    = index // C          (integer division)
column = index %  C          (remainder)
seat_number = row * C + column + 1
```

*Example:* seat 14 on a 4-column bus → index 13 → row 13 // 4 = **3**, column 13 % 4 = **1**,
so it lives in `grid[3][1]`. This is pure arithmetic and takes **O(1)** time.

**Traversal.** To count free seats, we visit every cell with two nested loops:

```python
def _count(self, status):
    total = 0
    for r in range(self._rows):          # every row
        row = self._grid[r]
        for c in range(self._cols):      # every column in that row
            if row[c] == status:
                total += 1
    return total
```

### Operations

| Operation | Method | Complexity |
|---|---|---|
| Seat number → (row, col) | `position_of(seat)` | O(1) |
| Read a seat's status | `get_status(seat)` | O(1) |
| Reserve a seat (prevents duplicates) | `reserve(seat)` – raises if already 1 | O(1) |
| Release a seat after cancellation | `release(seat)` | O(1) |
| Count available / occupied | `available_count()`, `occupied_count()` | O(n) |
| List free seats / first free seat | `available_seats()`, `first_available()` | O(n) |
| Memory | | O(n) |

### SMARTBUS example

When you open the seat map for *Indus Express*, the screen reads `SeatMatrix.to_matrix()` and
paints each cell green (0) or red (1). Hovering seat 14 shows
`Seat 14 → index 13 → array[3][1] = 0 (available)`. When you confirm, `reserve(14)` sets the
cell to 1. If someone else booked it a moment earlier, `reserve` refuses, and so does the
database's UNIQUE index.

---

## 2. Singly linked list – bus routes

**File:** `data_structures/linked_list.py` (`StopNode`, `RouteLinkedList`)
**Used in:** Routes & Network screen, bus search (stop order and segment distance), graph
construction, DSA Lab → *Linked List*

### Why a linked list?

A route is an **ordered chain** of stops, and administrators often **insert or remove stops in
the middle**. In an array, inserting in the middle means shifting every later element one place.
In a linked list we only change one or two `next` references.

### How it works

Each node stores the stop name, the distance from the **previous** stop, and a reference to the
next node:

```
head
 │
 ▼
[Karachi|0|•]──►[Hyderabad|165|•]──►[Nawabshah|130|•]──►[Sukkur|185|•]──►[Multan|450|•]──►[Lahore|340|None]
```

No Python list is used to hold the stops; the chain exists only through `next` references. We
also keep a `tail` reference so appending is O(1).

**Insertion in the middle** (`insert_at`): walk to the node *before* the position, then re-link.

```python
prev = self.head
for _ in range(position - 1):      # walk position-1 steps
    prev = prev.next
following = prev.next
node = StopNode(name, distance, following)   # new.next = following
prev.next = node                             # prev.next = new
following.distance = distance_to_next        # fix the next leg's distance
```

**Deletion** (`delete`): find the node and its predecessor, then bypass it:
`prev.next = current.next`. Because the bus now drives straight from the previous stop to the
next one, the removed distance is **added** to the next node, so the total distance stays
correct. Example: A –5 km– B –7 km– C becomes A –12 km– C.

### Operations

| Operation | Method | Complexity |
|---|---|---|
| Append stop | `append` | O(1) (tail pointer) |
| Insert at position k | `insert_at(k, …)` | O(k) |
| Insert after a named stop | `insert_after` | O(n) |
| Delete a stop | `delete(name)` | O(n) |
| Search for a stop | `search(name)` | O(n) |
| Position of a stop | `position_of(name)` | O(n) |
| Traverse / display | `traverse()`, `display()` | O(n) |
| Total distance | `total_distance()` | O(n) |
| Distance between two stops (in order) | `distance_between(a, b)` | O(n) |

### SMARTBUS example

Searching **Karachi → Multan** asks every route's linked list
`distance_between("Karachi", "Multan")`. The *Karachi – Lahore Express* returns 930 km, and the
*Karachi – Multan Southern* returns 960 km. A route that visits Multan *before* Karachi returns
`None`, because direction matters, so it is not shown. The database table `route_stops` saves
each node with its `stop_order`, and the list is rebuilt in that order at start-up.

---

## 3. Stack – booking history and undo

**File:** `data_structures/stack.py` (`Stack`)
**Used in:** *Undo last action* button (top bar), undo panel on the Bookings page, DSA Lab →
*Stack*, path reconstruction in Dijkstra, iterative DFS

### Why a stack?

Undo must reverse the **most recent** action first. That is the definition of **LIFO – Last In,
First Out**, which is what a stack does.

### How it works

The stack is a chain of nodes where `top` points to the newest one:

```
top ──► [CANCEL SB-X] ──► [CHANGE SB-Y 3→7] ──► [BOOK SB-Z] ──► None
```

`push` creates a node that points to the old top. `pop` moves `top` one node down. Both touch
only the top, so both are O(1). An optional `max_size` keeps only the most recent 25 actions.

### What each entry stores (so it can be reversed)

| Action | Details stored | How undo reverses it |
|---|---|---|
| `BOOK` | booking IDs, seats, bus | cancel those bookings and free the seats (freed seats go to the waiting queue) |
| `CANCEL` | booking ID, previous status, seat, who received the seat | restore the booking on the same seat **only if that seat is still free and nobody is waiting** |
| `CHANGE` | old seat, new seat | move back to the old seat if it is still free |
| `WAITLIST` | booking ID, bus | leave the waiting list |

**Safety rules.** Undo never double-books a seat and never lets someone skip the waiting queue.
If a cancelled seat has already been given to a waiting passenger, undoing the cancellation is
refused with an explanation, and that entry is removed from the stack.

**After a restart.** Each entry is also stored in the `booking_history` table. When the user
signs in again, the last 25 entries that have not been undone are pushed back in their original
order, so the stack looks exactly as it did before.

### Operations

| Operation | Complexity |
|---|---|
| `push`, `pop`, `peek`, `is_empty`, `size` | O(1) |
| `display` (top → bottom) | O(n) |

---

## 4. Queue – passenger waiting list

**File:** `data_structures/queue.py` (`Queue`)
**Used in:** Waiting List screen, automatic seat allocation in `BookingService`, BFS, DSA Lab →
*Queue*

### Why a queue?

A waiting list is fair only if people are served **in the order they arrived**: **FIFO – First
In, First Out**.

### How it works

Linked nodes with two references, `front` (served next) and `rear` (where newcomers join):

```
front                                   rear
  │                                       │
  ▼                                       ▼
[Sara] ──► [Ahmed] ──► [Moiz] ──► [Zara] ──► None
```

`enqueue` attaches a node after `rear`, and `dequeue` removes the node at `front`. Both are O(1).
(A Python list with `pop(0)` would be O(n), because every remaining element shifts left.)

### The real-world workflow (implemented in `services/booking_service.py`)

1. All seats of *Capital Shuttle* are booked (`SeatMatrix.is_full()` is `True`).
2. A passenger asks for a ticket. The seat screen offers **Join waiting list**, which calls
   `enqueue`, and the request is saved in the `waiting_list` table.
3. Someone with a confirmed seat cancels.
4. In the **same database transaction**, SMARTBUS cancels that booking, takes the passenger at the
   **front** of the queue, confirms their booking on the freed seat, and marks the waiting entry
   *Allocated*.
5. After the commit, memory is updated: the seat is released and re-reserved in the array, and
   `dequeue()` removes the allocated passenger.

The rule "you can only join a queue when the bus is full", together with "every freed seat goes
to the queue first", guarantees an invariant: **if the queue is not empty, the bus has no free
seats.**

**Persistence.** `waiting_list.waiting_id` is an AUTOINCREMENT number, so it records arrival
order. At start-up, entries are enqueued in `waiting_id` order, which rebuilds exactly the same
FIFO queue.

### Operations

| Operation | Complexity |
|---|---|
| `enqueue`, `dequeue`, `peek`, `is_empty`, `size` | O(1) |
| `position_of` (queue position of a passenger) | O(n) |
| `remove_where` (passenger leaves the list) | O(n) |
| `display` | O(n) |

---

## 5. Hash table – fast booking lookup

**File:** `data_structures/hash_table.py` (`HashTable`)
**Used in:** booking index (`booking_id → Booking`), lookup box on the Bookings page, unique
booking-ID generation, and as the container for seat maps, queues and undo stacks. DSA Lab →
*Hash Table*

### Why a hash table?

SMARTBUS holds hundreds of bookings. Finding one by scanning the whole list is O(n). A hash table
converts the key straight into an array position, so lookup is **O(1) on average**, no matter how
many bookings exist.

### How it works

1. **Hash function** (polynomial rolling hash):

   ```python
   h = 0
   for ch in str(key):
       h = (h * 31 + ord(ch)) % 4294967296     # keep it in 32 bits
   bucket = h % capacity
   ```

2. **Buckets.** The buckets form a `FixedArray`. Each bucket holds the head of a small linked
   chain of `(key, value)` entries.
3. **Collisions: separate chaining.** When two keys land in the same bucket, the new entry is
   linked in front of the chain instead of overwriting the old one:

   ```
   [0] SB-RENXFY ─► SB-7ALPSR ─► SB-CX62YL      ← collisions share bucket 0
   [1] SB-6R65XH
   [2] None
   ```

4. **Load factor and resizing.** Load factor = entries ÷ buckets. When it rises above 0.75, the
   table doubles its capacity and re-inserts every entry ("rehashing"). This keeps chains short,
   which is why the average lookup stays O(1).

### Operations

| Operation | Average | Worst (all keys collide) |
|---|---|---|
| `insert` / update | O(1) | O(n) |
| `search` | O(1) | O(n) |
| `delete` | O(1) | O(n) |
| resize (rare) | O(n) | O(n) |

### SMARTBUS example

Typing `SB-7KQ2MX` into the lookup box shows, for example, *"Found in bucket 211 after 1
comparison(s) · 3.2 µs"*. The Bookings page also shows live statistics such as
*"355 bookings in 512 buckets · load factor 0.69 · longest chain 4"*. The test
`test_collisions_with_separate_chaining` forces every key into one bucket (capacity 1) to prove
that chaining still finds every entry.

---

## 6. Graph – city network, BFS and DFS

**File:** `data_structures/graph.py` (`Graph`)
**Used in:** Routes & Network → *City Network* tab, passenger *Route Planner*, DSA Lab →
*Graph BFS/DFS*

### Why a graph?

Cities connected by roads form a **network**, not a line. Several routes share cities (for
example Hyderabad, Sukkur and Multan), and a journey may combine roads from different routes. A
graph is the natural model: **cities are vertices** and **roads are weighted edges** (weight =
distance in km).

### How it works

An **adjacency list**: each city maps to the list of its neighbours and distances. Roads go both
ways, so every edge is stored in both cities' lists (an undirected graph).

```
Karachi   : [(Hyderabad, 165), (Khuzdar, 390)]
Hyderabad : [(Karachi, 165), (Nawabshah, 130), (Sukkur, 330)]
Sukkur    : [(Nawabshah, 185), (Multan, 450), (Hyderabad, 330), (Rahim Yar Khan, 175), (Quetta, 390)]
...
```

Memory is O(V + E), much smaller than a V × V matrix for a sparse road network.

The graph is **built from the route linked lists**: each pair of consecutive stops becomes an
edge. When an admin edits a route, the graph is rebuilt automatically.

**BFS (Breadth-First Search)** uses our **Queue**. It visits the start city, then all cities one
road away, then those two roads away, and so on. It answers "which cities can I reach, and in how
few hops?".

```python
queue.enqueue(start); visited = {start}
while not queue.is_empty():
    city = queue.dequeue()
    order.append(city)
    for neighbour, _ in self._adj[city]:
        if neighbour not in visited:
            visited.add(neighbour); queue.enqueue(neighbour)
```

**DFS (Depth-First Search)** uses our **Stack**. It follows one road as far as possible before
backtracking. A recursive version (`dfs_recursive`) is included too, and the tests check that
both give the same order.

### Operations

| Operation | Complexity |
|---|---|
| `add_city`, `add_connection` | O(1) amortised (O(deg) to check for duplicates) |
| `remove_connection` | O(deg) |
| `neighbors` | O(deg) |
| `bfs`, `dfs`, `connected_destinations` | O(V + E) |
| `display` | O(V + E) |

---

## 7. Dijkstra's shortest path

**Files:** `algorithms/shortest_path.py` (`dijkstra`, `reconstruct_path`, `find_all_routes`),
`data_structures/priority_queue.py` (`MinHeap`)
**Used in:** *Shortest path* button (Routes & Network, Route Planner), DSA Lab → *Dijkstra*

### Why Dijkstra?

BFS finds the path with the fewest **roads**, but passengers care about the fewest
**kilometres**. Dijkstra's algorithm finds the minimum-distance path in a graph with non-negative
weights.

### How it works

1. Set `dist[source] = 0` and `dist[every other city] = ∞`.
2. Put the source into a **min-priority queue** (our `MinHeap`).
3. Repeat: remove the city **u** with the smallest tentative distance. Its distance is now
   **final** ("settled"), because all roads are positive, so no later path can be shorter.
4. **Relax** every road u → v: if `dist[u] + w < dist[v]`, we have found a shorter way to v, so
   update `dist[v]`, record `previous[v] = u`, and push v into the heap.
5. Stop when the destination is settled.
6. **Rebuild the path** by following `previous[]` back from the destination. We push those
   cities onto our **Stack** and pop them to get the forward order.

The **MinHeap** is a binary heap stored in an array. For index i, the parent is `(i-1)//2` and the
children are `2i+1` and `2i+2`. `push` "sifts up" and `pop` "sifts down", each in O(log n). The
brief allowed `heapq`, but we wrote our own so the whole algorithm can be seen.

### Comparing routes

`find_all_routes` uses DFS **backtracking** to list simple paths between two cities and orders
them by distance with our **merge sort**. The UI shows each alternative's distance and how much
longer it is than the best one. This confirms Dijkstra's answer is the first row.

*Example (demo network):* Karachi → Lahore. Dijkstra returns Karachi → Hyderabad → Nawabshah →
Sukkur → Multan → Lahore = **1,270 km**. The alternatives include 1,285 km via Rahim Yar Khan and
Bahawalpur, and 1,285 km via the direct Hyderabad–Sukkur road.

### Complexity

| | |
|---|---|
| Time | **O((V + E) log V)** with a binary heap |
| Space | O(V) for `dist`, `previous` and the heap |
| Requirement | No negative edge weights |
| Unreachable destination | `path = []`, `distance = ∞` (tested) |

---

## 8. Searching – linear vs binary

**File:** `algorithms/searching.py`
**Used in:** every search box (linear), bus-number and email lookup (binary), DSA Lab → *Search*

### Linear search – O(n)

Check the items one by one from the start. It works on **any** list, sorted or not, and it is the
only option for flexible filters such as "name *contains* 'ali'". All filters in SMARTBUS use
`linear_search_all`.

### Binary search – O(log n)

Works only on a **sorted** list. Look at the middle element:

* equal → found
* middle < target → discard the left half (`low = mid + 1`)
* middle > target → discard the right half (`high = mid - 1`)

Each step halves the remaining range, so 100,000 items need at most about **17** comparisons
(2¹⁷ = 131,072).

### SMARTBUS examples

* **Bus Management → "Exact lookup by bus number"** first sorts all buses by number with merge
  sort, then binary-searches. The message shows the number of comparisons.
* **Passengers → "Exact email lookup"** works the same way, sorting by email.
* **DSA Lab → Search → "Benchmark 100k"** runs 200 random searches on 100,000 sorted items. In
  our run, linear search averaged about **75,000** comparisons and binary search about **16**.

| | Best | Average | Worst | Needs sorted data |
|---|---|---|---|---|
| Linear | O(1) | O(n) | O(n) | No |
| Binary | O(1) | O(log n) | O(log n) | **Yes** |

---

## 9. Sorting – five algorithms

**File:** `algorithms/sorting.py`
**Used in:** every table with a *Sort by* menu (buses, routes, passengers, bookings, bus search
results), reports, DSA Lab → *Sorting*

Every algorithm has the same interface:
`fn(items, key=None, reverse=False, on_step=None, stats=None)`. It returns a **new** sorted
list, counts comparisons and swaps in `stats`, and can report each step to the visualiser.
Each table has an **Algorithm** drop-down, so you can sort the same data with bubble sort and
then with merge sort and compare the comparison counts shown under the table.

What SMARTBUS sorts: buses by **ticket price** and **departure time**, passengers
**alphabetically**, bookings by **booking date**, routes by **distance**, and search results by
**cheapest / earliest / shortest distance / most seats**.

### Bubble sort

Walk through the list swapping neighbours that are out of order. After each pass, the largest
remaining value has "bubbled" to the end. If a pass makes no swaps, the list is sorted, so the
best case is O(n).

### Selection sort

For each position i, find the smallest value in the unsorted part and swap it into position i.
It always does about n²/2 comparisons, even on sorted input.

### Insertion sort

Take the next value and shift larger values one place to the right until its correct place is
found, like sorting playing cards in your hand. It is very fast on nearly sorted data (O(n) best
case).

### Merge sort

Divide and conquer: split the list in half, sort each half recursively, then **merge** the two
sorted halves. There are log n levels of splitting and each level merges n items, so it is
**O(n log n) in every case**. It needs O(n) extra memory and is **stable** (equal items keep
their order). It is the default algorithm in SMARTBUS for this reason.

### Quick sort

Choose a **pivot** (we use the middle element, to avoid the O(n²) worst case on already-sorted
data). **Partition** smaller values to the left and larger to the right, then sort each side. The
average is O(n log n). We always recurse into the smaller side first, which keeps the call stack
at O(log n).

### Complexity table

| Algorithm | Best | Average | Worst | Extra space | Stable |
|---|---|---|---|---|---|
| Bubble | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Selection | O(n²) | O(n²) | O(n²) | O(1) | No |
| Insertion | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Merge | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Quick | O(n log n) | O(n log n) | O(n²) | O(log n) | No |

**DSA Lab → Sorting → "Compare all"** sorts the same 1,500 random numbers with all five
algorithms and prints the comparisons, moves and milliseconds for each. In our run, bubble and
selection sort made about **1.1 million** comparisons, insertion sort about **560,000**, while
merge sort needed about **14,000** and quick sort about **17,000**.

---

## 10. How the structures work together

Here is what happens when a passenger cancels a seat on a full bus:

```
Cancel SB-ABC123
   │
   ├─ HashTable.search("SB-ABC123")          O(1)   find the booking
   ├─ BEGIN TRANSACTION
   │    ├─ UPDATE bookings → Cancelled
   │    ├─ Queue: look at the front passenger  O(1)
   │    ├─ UPDATE their booking → Confirmed on the freed seat
   │    ├─ UPDATE waiting_list → Allocated
   │    └─ INSERT booking_history (CANCEL …)
   ├─ COMMIT
   └─ apply to memory (only after commit):
        ├─ SeatMatrix.release(seat); SeatMatrix.reserve(seat)   O(1)
        ├─ Queue.dequeue()                                     O(1)
        └─ Stack.push(CANCEL entry)                            O(1)
```

If anything fails (for example a database error), SQLite rolls everything back and memory is not
touched.

## 11. Summary table

| Data structure / algorithm | Real problem it solves in SMARTBUS | Key complexity |
|---|---|---|
| 2-D array | Seat layout, O(1) seat access, preventing double booking | O(1) access |
| Singly linked list | Ordered route stops with easy insert/remove | O(k) insert |
| Stack | Undo the most recent operation | O(1) push/pop |
| Queue | Fair, first-come-first-served waiting list | O(1) enqueue/dequeue |
| Hash table | Instant booking lookup by ID | O(1) average |
| Graph (adjacency list) | City network across all routes | O(V + E) traversal |
| BFS / DFS | Reachable cities, traversal orders | O(V + E) |
| Min-heap | Priority queue for Dijkstra | O(log n) push/pop |
| Dijkstra | Shortest road distance between cities | O((V + E) log V) |
| Linear search | Flexible "contains" filters | O(n) |
| Binary search | Exact lookups on sorted data | O(log n) |
| Bubble / Selection / Insertion sort | Teaching comparison, selectable in every table | O(n²) |
| Merge sort | Default stable sort for tables and reports | O(n log n) |
| Quick sort | Fast average-case sorting | O(n log n) avg |
