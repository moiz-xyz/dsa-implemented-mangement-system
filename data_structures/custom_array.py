"""
ARRAY – BUS SEAT MANAGEMENT
===========================

This module contains two classes:

1. FixedArray
   A *static* (fixed-size) array. Memory for all slots is reserved once in
   the constructor and the size never changes afterwards – exactly like an
   array in C/Java. There is deliberately **no** append/insert/remove: you
   can only read or write a slot by its index.

   (Internally the slots live in a Python list created with [fill] * n.
   We only use it as a block of n memory cells; all array behaviour –
   bounds checking, traversal, counting – is written by hand below.)

2. SeatMatrix
   A two-dimensional array (an array of FixedArray rows) that models the
   physical seat layout of a bus.

   Seat status codes:
       0  = AVAILABLE
       1  = BOOKED
      -1  = NO_SEAT   (empty cell in the last row when capacity is not a
                       multiple of the number of columns)

   Indexing (row-major order)
   --------------------------
   Seats are numbered 1, 2, 3 ... left-to-right, top-to-bottom.
   For a bus with C columns:

       index  = seat_number - 1          (0-based position)
       row    = index // C               (integer division)
       column = index %  C               (remainder)

   and the reverse mapping is   seat_number = row * C + column + 1

   Example with C = 4: seat 10 -> index 9 -> row 2, column 1.
   Looking up any seat is therefore O(1): we compute the position with
   arithmetic instead of searching.

   Traversal
   ---------
   To count available seats we visit every cell with two nested loops
   (outer loop over rows, inner loop over columns). This is O(R x C) = O(n)
   where n is the number of seats.
"""


class FixedArray:
    """A fixed-capacity array with bounds-checked index access."""

    def __init__(self, capacity, fill=None):
        if not isinstance(capacity, int) or capacity < 0:
            raise ValueError("Array capacity must be a non-negative integer.")
        self._capacity = capacity
        self._slots = [fill] * capacity   # reserve all memory cells at once

    def _check_index(self, index):
        if not isinstance(index, int):
            raise TypeError("Array index must be an integer.")
        if index < 0 or index >= self._capacity:
            raise IndexError(f"Index {index} out of range 0..{self._capacity - 1}.")

    def __getitem__(self, index):          # O(1)
        self._check_index(index)
        return self._slots[index]

    def __setitem__(self, index, value):   # O(1)
        self._check_index(index)
        self._slots[index] = value

    def __len__(self):
        return self._capacity

    def __iter__(self):                    # O(n) traversal
        for i in range(self._capacity):
            yield self._slots[i]

    def fill(self, value):
        for i in range(self._capacity):
            self._slots[i] = value

    def count(self, value):
        """Linear traversal counting cells equal to `value` – O(n)."""
        total = 0
        for i in range(self._capacity):
            if self._slots[i] == value:
                total += 1
        return total

    def to_list(self):
        return [self._slots[i] for i in range(self._capacity)]

    def __repr__(self):
        return f"FixedArray({self.to_list()})"


class SeatMatrix:
    """2-D array of seat statuses for one bus."""

    AVAILABLE = 0
    BOOKED = 1
    NO_SEAT = -1

    def __init__(self, total_seats, columns=4):
        if total_seats <= 0:
            raise ValueError("A bus must have at least one seat.")
        if columns <= 0:
            raise ValueError("Columns must be positive.")
        self._total = total_seats
        self._cols = columns
        # Number of rows = ceiling(total / columns) without importing math.
        self._rows = (total_seats + columns - 1) // columns

        # Build the 2-D array: an outer array whose cells are row arrays.
        self._grid = FixedArray(self._rows)
        for r in range(self._rows):
            row = FixedArray(columns, self.AVAILABLE)
            for c in range(columns):
                if r * columns + c + 1 > total_seats:
                    row[c] = self.NO_SEAT          # padding cell, not a real seat
            self._grid[r] = row

    # ------------------------------------------------------------------ info
    @property
    def total_seats(self):
        return self._total

    @property
    def rows(self):
        return self._rows

    @property
    def columns(self):
        return self._cols

    # -------------------------------------------------------------- indexing
    def position_of(self, seat_number):
        """Convert a seat number (1-based) to (row, column) – O(1)."""
        if not isinstance(seat_number, int) or not 1 <= seat_number <= self._total:
            raise IndexError(f"Seat {seat_number} does not exist on this bus (1-{self._total}).")
        index = seat_number - 1
        return index // self._cols, index % self._cols

    def seat_number(self, row, column):
        """Convert (row, column) back to a seat number – O(1)."""
        number = row * self._cols + column + 1
        if not 0 <= row < self._rows or not 0 <= column < self._cols or number > self._total:
            raise IndexError("No seat at that position.")
        return number

    def get_status(self, seat_number):
        r, c = self.position_of(seat_number)
        return self._grid[r][c]

    def is_available(self, seat_number):
        return self.get_status(seat_number) == self.AVAILABLE

    # ------------------------------------------------------------ operations
    def reserve(self, seat_number):
        """Mark a seat as booked. Raises ValueError if it is already booked."""
        r, c = self.position_of(seat_number)
        if self._grid[r][c] == self.BOOKED:
            raise ValueError(f"Seat {seat_number} is already booked.")
        self._grid[r][c] = self.BOOKED

    def release(self, seat_number):
        """Mark a booked seat as available again (after a cancellation)."""
        r, c = self.position_of(seat_number)
        if self._grid[r][c] != self.BOOKED:
            raise ValueError(f"Seat {seat_number} is not booked.")
        self._grid[r][c] = self.AVAILABLE

    def load_booked(self, seat_numbers):
        """Mark many seats as booked (used when rebuilding from the database)."""
        for seat in seat_numbers:
            r, c = self.position_of(seat)
            self._grid[r][c] = self.BOOKED

    # ------------------------------------------------------------- traversal
    def _count(self, status):
        """Row-by-row, column-by-column traversal of the 2-D array – O(n)."""
        total = 0
        for r in range(self._rows):
            row = self._grid[r]
            for c in range(self._cols):
                if row[c] == status:
                    total += 1
        return total

    def available_count(self):
        return self._count(self.AVAILABLE)

    def occupied_count(self):
        return self._count(self.BOOKED)

    def is_full(self):
        return self.available_count() == 0

    def _seats_with(self, status):
        result = []
        for r in range(self._rows):
            for c in range(self._cols):
                if self._grid[r][c] == status:
                    result.append(r * self._cols + c + 1)
        return result

    def available_seats(self):
        return self._seats_with(self.AVAILABLE)

    def booked_seats(self):
        return self._seats_with(self.BOOKED)

    def first_available(self):
        """Return the lowest-numbered free seat, or None if the bus is full."""
        for r in range(self._rows):
            for c in range(self._cols):
                if self._grid[r][c] == self.AVAILABLE:
                    return r * self._cols + c + 1
        return None

    def to_matrix(self):
        """Return a plain list-of-lists copy for display purposes."""
        return [self._grid[r].to_list() for r in range(self._rows)]

    def display(self):
        """Text rendering, e.g.  [01:0] [02:1] | [03:0] [04:0]"""
        lines = []
        half = self._cols // 2
        for r in range(self._rows):
            cells = []
            for c in range(self._cols):
                if c == half and self._cols > 1:
                    cells.append("|")
                status = self._grid[r][c]
                if status == self.NO_SEAT:
                    cells.append("  --  ")
                else:
                    cells.append(f"[{r * self._cols + c + 1:02d}:{status}]")
            lines.append(" ".join(cells))
        return "\n".join(lines)

    def __repr__(self):
        return (f"SeatMatrix(total={self._total}, rows={self._rows}, cols={self._cols}, "
                f"available={self.available_count()})")
