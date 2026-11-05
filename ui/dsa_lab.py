"""
DSA LAB / ALGORITHM VISUALIZER
==============================

One tab per topic. Every demo uses the SAME classes and functions as the
real application (data_structures/ and algorithms/), so what the teacher
sees here is exactly the code that runs the booking system.

Each tab has:
  * a canvas that draws the structure,
  * controls to perform operations,
  * an operation log (step by step),
  * a complexity table.
Animations are driven by Tk's `after()` timer; the speed slider controls
the delay between steps.
"""

import random
import time
import tkinter as tk
from tkinter import ttk

from algorithms.searching import COMPLEXITY as SEARCH_COMPLEXITY
from algorithms.searching import binary_search, linear_search
from algorithms.shortest_path import dijkstra, find_all_routes
from algorithms.sorting import ALGORITHMS, SortStats
from data_structures.custom_array import SeatMatrix
from data_structures.graph import Graph
from data_structures.hash_table import HashTable
from data_structures.linked_list import RouteLinkedList
from data_structures.queue import Queue, QueueEmptyError
from data_structures.stack import Stack, StackUnderflowError
from ui.components import Button, FlowFrame, PageHeader, auto_wrap, combo, toast
from ui.route_management import CITY_COORDS, LABEL_LEFT
from ui.theme import C, font, mono

CANVAS_BG = "#F8FAFC"


# =========================================================================
# Base tab
# =========================================================================
class LabTab(tk.Frame):
    TITLE = ""
    IDEA = ""
    COMPLEXITY = []          # list of (operation, complexity)

    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        self.ctx = ctx
        self.app = ctx.app
        self._job = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        intro = tk.Frame(self, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"])
        intro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 10))
        tk.Label(intro, text=self.TITLE, bg=C["card"], fg=C["text"], font=font(12, "bold"),
                 anchor="w").pack(fill="x", padx=14, pady=(10, 0))
        auto_wrap(tk.Label(intro, text=self.IDEA, bg=C["card"], fg=C["text_muted"],
                           font=font(9), anchor="w")).pack(fill="x", padx=14, pady=(2, 10))

        stage = tk.Frame(self, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"])
        stage.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        # Control rows wrap onto extra lines when the window is narrow.
        self.controls = FlowFrame(stage, bg=C["card"], hgap=6)
        self.controls.pack(fill="x", padx=12, pady=(12, 6))
        self.controls2 = FlowFrame(stage, bg=C["card"], hgap=6)   # optional second row
        self.controls2.pack(fill="x", padx=12, pady=(0, 6))
        self.canvas = tk.Canvas(stage, bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.canvas.bind("<Configure>", lambda e: self.draw())

        side = tk.Frame(self, bg=C["card"], highlightthickness=1,
                        highlightbackground=C["border"], width=260)
        side.grid(row=1, column=1, sticky="nsew")
        side.grid_propagate(False)
        side.pack_propagate(False)
        tk.Label(side, text="Time complexity", bg=C["card"], fg=C["text"],
                 font=font(10, "bold"), anchor="w").pack(fill="x", padx=12, pady=(12, 4))
        table = tk.Frame(side, bg=C["card"])
        table.pack(fill="x", padx=12)
        for i, (op, cx) in enumerate(self.COMPLEXITY):
            bg = C["row_alt"] if i % 2 else C["card"]
            row = tk.Frame(table, bg=bg)
            row.pack(fill="x")
            tk.Label(row, text=op, bg=bg, fg=C["text"], font=font(9), anchor="w").pack(
                side="left", padx=6, pady=3)
            tk.Label(row, text=cx, bg=bg, fg=C["primary"], font=mono(9, "bold")).pack(
                side="right", padx=6)
        speed = tk.Frame(side, bg=C["card"])
        speed.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(speed, text="Animation delay  (fast ← → slow)", bg=C["card"],
                 fg=C["text_muted"], font=font(9), anchor="w").pack(fill="x")
        self.speed = tk.IntVar(value=450)
        tk.Scale(speed, from_=60, to=1200, variable=self.speed, orient="horizontal",
                 showvalue=False, bg=C["primary"], troughcolor=C["primary_light"],
                 activebackground=C["primary_dark"], highlightthickness=0, bd=0,
                 sliderrelief="flat", sliderlength=18, width=10).pack(fill="x", pady=(4, 0))
        tk.Label(side, text="Operation log", bg=C["card"], fg=C["text"], font=font(10, "bold"),
                 anchor="w").pack(fill="x", padx=12, pady=(12, 4))
        self.log_box = tk.Text(side, font=mono(9), bg=CANVAS_BG, fg=C["text"], relief="flat",
                               wrap="word", highlightthickness=1,
                               highlightbackground=C["border"], padx=8, pady=6)
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.log_box.tag_configure("head", foreground=C["primary"], font=mono(9, "bold"))
        Button(side, "Clear log", self.clear_log, "ghost", small=True).pack(anchor="e",
                                                                            padx=12, pady=(0, 10))
        self.build_controls(self.controls)

    # --------------------------------------------------------------- helpers
    def build_controls(self, frame):
        pass

    def draw(self):
        pass

    def refresh(self):
        self.draw()

    def log(self, text, head=False):
        self.log_box.insert("end", text + "\n", "head" if head else ())
        self.log_box.see("end")

    def clear_log(self):
        self.log_box.delete("1.0", "end")

    def entry(self, parent, width=10, default=""):
        e = ttk.Entry(parent, width=width)
        if default:
            e.insert(0, default)
        self.put(parent, e)
        return e

    @staticmethod
    def put(parent, widget, gap=6):
        """Place a control in a FlowFrame (wrapping row) or a normal frame."""
        if isinstance(parent, FlowFrame):
            parent.add(widget, gap=gap)
        else:
            widget.pack(side="left", padx=(0, gap))
        return widget

    def label(self, parent, text):
        self.put(parent, tk.Label(parent, text=text, bg=C["card"], fg=C["text_muted"],
                                  font=font(9)), gap=4)

    def button(self, parent, text, cmd, variant="secondary"):
        b = Button(parent, text, cmd, variant, small=True)
        self.put(parent, b)
        return b

    def animate(self, steps, render, done=None):
        """Play `steps` one after another, calling render(step) for each."""
        self.stop()

        def run(i=0):
            if not self.winfo_exists():
                return
            if i >= len(steps):
                self._job = None
                if done:
                    done()
                return
            render(steps[i])
            self._job = self.after(int(self.speed.get()), run, i + 1)
        run()

    def stop(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def box(self, x, y, w, h, text, fill=C["card"], outline=C["primary"], fg=C["text"],
            sub=None, bold=True):
        cv = self.canvas
        cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=outline, width=2)
        cv.create_text(x + w / 2, y + (h / 2 - 7 if sub else h / 2), text=text, fill=fg,
                       font=font(9, "bold" if bold else "normal"), width=w - 6)
        if sub:
            cv.create_text(x + w / 2, y + h / 2 + 10, text=sub, fill=fg, font=font(7))


# =========================================================================
# 1. Array
# =========================================================================
class ArrayLab(LabTab):
    TITLE = "1 · Array – bus seat matrix"
    IDEA = ("Seats live in a 2-D array (rows × columns). Seat number → index with arithmetic: "
            "index = seat − 1, row = index // columns, col = index % columns. Reading or "
            "writing one seat is O(1); counting free seats needs a full traversal O(n).")
    COMPLEXITY = [("Access seat[r][c]", "O(1)"), ("Reserve / release", "O(1)"),
                  ("Seat → (row, col)", "O(1)"), ("Count available", "O(n)"),
                  ("Find first free seat", "O(n)"), ("Space", "O(n)")]

    def build_controls(self, f):
        self.matrix = SeatMatrix(20, 4)
        self.highlight = None
        self.label(f, "Seat no.")
        self.seat = self.entry(f, 5, "7")
        self.button(f, "Reserve", self.reserve, "primary")
        self.button(f, "Release", self.release)
        self.button(f, "Traverse & count", self.traverse)
        self.button(f, "Random fill", self.random_fill)
        self.button(f, "Reset", self.reset)

    def _seat(self):
        try:
            return int(self.seat.get())
        except ValueError:
            toast(self, "Enter a seat number.", "warning")
            return None

    def reserve(self):
        s = self._seat()
        if s is None:
            return
        try:
            r, c = self.matrix.position_of(s)
            self.matrix.reserve(s)
            self.log(f"reserve({s}): index {s - 1} → [{r}][{c}] = 1", head=True)
        except (ValueError, IndexError) as exc:
            self.log(f"reserve({s}) ✗ {exc}")
        self.highlight = s
        self.draw()

    def release(self):
        s = self._seat()
        if s is None:
            return
        try:
            r, c = self.matrix.position_of(s)
            self.matrix.release(s)
            self.log(f"release({s}): [{r}][{c}] = 0", head=True)
        except (ValueError, IndexError) as exc:
            self.log(f"release({s}) ✗ {exc}")
        self.highlight = s
        self.draw()

    def random_fill(self):
        self.reset(log=False)
        for s in random.sample(range(1, 21), 9):
            self.matrix.reserve(s)
        self.log("Random fill: 9 seats booked", head=True)
        self.draw()

    def reset(self, log=True):
        self.stop()
        self.matrix = SeatMatrix(20, 4)
        self.highlight = None
        if log:
            self.log("New 5 × 4 seat array (all 0)", head=True)
        self.draw()

    def traverse(self):
        steps = []
        count = 0
        for r in range(self.matrix.rows):
            for c in range(self.matrix.columns):
                seat = self.matrix.seat_number(r, c)
                if self.matrix.is_available(seat):
                    count += 1
                steps.append((seat, r, c, count))
        self.log("Traversal: for r in rows: for c in cols: …", head=True)

        def render(step):
            seat, r, c, cnt = step
            self.highlight = seat
            self.draw()
            self.log(f"visit [{r}][{c}] seat {seat} → value "
                     f"{self.matrix.get_status(seat)}  available so far = {cnt}")
        self.animate(steps, render, lambda: self.log(
            f"Done: {self.matrix.available_count()} available, "
            f"{self.matrix.occupied_count()} occupied"))

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        m = self.matrix
        x0, y0, w, h, gap = 70, 50, 74, 46, 10
        for c in range(m.columns):
            cv.create_text(x0 + c * (w + gap) + w / 2 + (24 if c >= 2 else 0), 30,
                           text=f"col {c}", fill=C["text_light"], font=font(8))
        grid = m.to_matrix()
        for r in range(m.rows):
            cv.create_text(36, y0 + r * (h + gap) + h / 2, text=f"row {r}", fill=C["text_light"],
                           font=font(8))
            for c in range(m.columns):
                seat = m.seat_number(r, c)
                v = grid[r][c]
                x = x0 + c * (w + gap) + (24 if c >= 2 else 0)
                y = y0 + r * (h + gap)
                fill = C["seat_booked"] if v == 1 else C["seat_available"]
                outline = C["sidebar"] if seat == self.highlight else fill
                cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=outline,
                                    width=4 if seat == self.highlight else 1)
                cv.create_text(x + w / 2, y + 15, text=f"seat {seat}", fill="white",
                               font=font(9, "bold"))
                cv.create_text(x + w / 2, y + 32, text=f"[{r}][{c}] = {v}", fill="white",
                               font=mono(8))
        right = x0 + 4 * (w + gap) + 60
        cv.create_text(right, y0, anchor="nw", fill=C["text"], font=mono(9), text=(
            "0 = Available (green)\n1 = Booked (red)\n\n"
            f"available = {m.available_count()}\noccupied  = {m.occupied_count()}\n\n"
            "seat 14 → index 13\nrow = 13 // 4 = 3\ncol = 13 %  4 = 1"))


# =========================================================================
# 2. Linked list
# =========================================================================
class LinkedListLab(LabTab):
    TITLE = "2 · Singly linked list – bus route"
    IDEA = ("Each StopNode stores (name, distance from previous, next). Insertion and deletion "
            "only re-link pointers – no shifting like an array – but reaching position k "
            "requires walking k nodes from the head.")
    COMPLEXITY = [("Insert at head", "O(1)"), ("Insert at position k", "O(k)"),
                  ("Append (tail pointer)", "O(1)"), ("Delete by name", "O(n)"),
                  ("Search", "O(n)"), ("Total distance", "O(n)")]

    def build_controls(self, f):
        self.reset(log=False)
        self.label(f, "Stop")
        self.name = self.entry(f, 11, "Rohri")
        self.label(f, "km")
        self.dist = self.entry(f, 5, "60")
        self.label(f, "pos")
        self.pos = self.entry(f, 3, "3")
        self.button(f, "Insert at", self.insert, "primary")
        self.button(f, "Delete", self.delete)
        self.button(f, "Search", self.search)
        self.button(f, "Total km", self.total)
        self.button(f, "Reset", self.reset)

    def reset(self, log=True):
        self.stop()
        self.route = RouteLinkedList.from_pairs([("Karachi", 0), ("Hyderabad", 165),
                                                 ("Nawabshah", 130), ("Sukkur", 185),
                                                 ("Multan", 450), ("Lahore", 340)])
        self.highlight = None
        self.found = None
        if log:
            self.log("Route reset: Karachi → … → Lahore", head=True)
            self.draw()

    def insert(self):
        try:
            pos = int(self.pos.get())
            dist = float(self.dist.get())
            name = self.name.get().strip().title()
            if not name:
                raise ValueError("Enter a stop name.")
            if 0 < pos < len(self.route):
                prev = self.route.get_at(pos - 1)
                nxt = prev.next
                remaining = nxt.distance - dist
                self.route.insert_at(pos, name, dist,
                                     remaining if remaining > 0 else nxt.distance)
                self.log(f"insert_at({pos}, {name}): walk {pos - 1} step(s) to {prev.name}; "
                         f"new.next = {nxt.name}; {prev.name}.next = new", head=True)
            else:
                self.route.insert_at(pos, name, dist)
                self.log(f"insert_at({pos}, {name}) "
                         f"{'as new head' if pos == 0 else 'at tail'}", head=True)
            self.highlight = name
        except (ValueError, IndexError) as exc:
            self.log(f"insert ✗ {exc}")
        self.draw()

    def delete(self):
        name = self.name.get().strip()
        try:
            node = self.route.delete(name)
            self.log(f"delete({node.name}): previous.next = removed.next; its "
                     f"{node.distance:.0f} km merged into the next node", head=True)
        except ValueError as exc:
            self.log(f"delete ✗ {exc}")
        self.highlight = None
        self.draw()

    def search(self):
        target = self.name.get().strip()
        nodes = list(self.route.traverse())
        self.log(f"search({target}): start at head", head=True)

        def render(i):
            node = nodes[i]
            self.highlight = node.name
            self.draw()
            match = node.name.lower() == target.lower()
            self.log(f"  node {i}: {node.name} {'== target ✓' if match else '≠ target'}")
            if match:
                self.stop()
                self.log(f"Found at position {i} after {i + 1} comparison(s)")
        self.animate(list(range(len(nodes))), render,
                     lambda: self.log("Reached None – not found"))

    def total(self):
        nodes = list(self.route.traverse())
        acc = [0]
        self.log("total_distance(): sum node.distance while walking", head=True)

        def render(i):
            acc[0] += nodes[i].distance
            self.highlight = nodes[i].name
            self.draw()
            self.log(f"  + {nodes[i].distance:.0f} ({nodes[i].name}) = {acc[0]:.0f} km")
        self.animate(list(range(len(nodes))), render,
                     lambda: self.log(f"Total = {self.route.total_distance():.0f} km"))

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        width = max(cv.winfo_width(), 600)
        x, y, w, h, gap = 20, 50, 110, 56, 40
        per_row = max((width - 40) // (w + gap), 1)
        cv.create_text(20, 22, text="head", anchor="w", fill=C["primary"], font=font(9, "bold"))
        for i, node in enumerate(self.route.traverse()):
            col, row = i % per_row, i // per_row
            x = 20 + col * (w + gap)
            yy = y + row * (h + 60)
            hl = node.name == self.highlight
            self.box(x, yy, w, h, node.name, fill=C["primary"] if hl else C["card"],
                     fg="white" if hl else C["text"], sub=f"{node.distance:.0f} km  |  next")
            if node.next is not None:
                if col == per_row - 1:
                    cv.create_line(x + w / 2, yy + h, x + w / 2, yy + h + 30, 20 + w / 2,
                                   yy + h + 30, 20 + w / 2, yy + h + 60, arrow="last",
                                   fill=C["text_muted"], width=2)
                else:
                    cv.create_line(x + w, yy + h / 2, x + w + gap, yy + h / 2, arrow="last",
                                   fill=C["text_muted"], width=2)
            else:
                cv.create_text(x + w + 18, yy + h / 2, text="None", fill=C["text_light"],
                               font=mono(8))
        cv.create_text(20, max(cv.winfo_height(), 300) - 20, anchor="w", fill=C["text_muted"],
                       font=mono(9), text=f"length = {len(self.route)}   total = "
                                          f"{self.route.total_distance():.0f} km")


# =========================================================================
# 3. Stack
# =========================================================================
class StackLab(LabTab):
    TITLE = "3 · Stack (LIFO) – undo history"
    IDEA = ("The last operation pushed is the first one popped – exactly what Undo needs. "
            "Implemented with linked nodes: push and pop only touch the top pointer.")
    COMPLEXITY = [("push", "O(1)"), ("pop", "O(1)"), ("peek", "O(1)"),
                  ("is_empty / size", "O(1)"), ("display", "O(n)")]

    def build_controls(self, f):
        self.stack = Stack()
        self.flash = None
        self.label(f, "Value")
        self.value = self.entry(f, 14, "Book SB-1")
        self.button(f, "Push", self.push, "primary")
        self.button(f, "Pop", self.pop)
        self.button(f, "Peek", self.peek)
        self.button(f, "Demo: A, B, C, pop", self.demo)
        self.button(f, "Clear", self.clear)

    def push(self, value=None):
        value = value or self.value.get().strip() or "item"
        self.stack.push(value)
        self.flash = value
        self.log(f"push({value}) → size {self.stack.size()}", head=True)
        self.draw()

    def pop(self):
        try:
            value = self.stack.pop()
            self.log(f"pop() → {value}", head=True)
        except StackUnderflowError:
            self.log("pop() ✗ stack is empty (underflow)")
        self.flash = None
        self.draw()

    def peek(self):
        try:
            self.log(f"peek() → {self.stack.peek()} (not removed)", head=True)
            self.flash = self.stack.peek()
        except StackUnderflowError:
            self.log("peek() ✗ stack is empty")
        self.draw()

    def clear(self):
        self.stack.clear()
        self.log("clear()", head=True)
        self.draw()

    def demo(self):
        self.clear()
        steps = [("push", "A"), ("push", "B"), ("push", "C"), ("pop", None)]
        self.animate(steps, lambda s: self.push(s[1]) if s[0] == "push" else self.pop())

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        h = max(cv.winfo_height(), 360)
        x, w, bh = 120, 200, 40
        base = h - 40
        cv.create_line(x - 10, base, x + w + 10, base, fill=C["text_muted"], width=3)
        items = list(self.stack)[::-1]                # bottom -> top
        for i, value in enumerate(items):
            y = base - (i + 1) * (bh + 6)
            top = i == len(items) - 1
            self.box(x, y, w, bh, str(value), fill=C["primary"] if top else C["card"],
                     fg="white" if top else C["text"])
            if top:
                cv.create_text(x + w + 20, y + bh / 2, text="← top", anchor="w",
                               fill=C["primary"], font=font(10, "bold"))
        if not items:
            cv.create_text(x + w / 2, base - 30, text="empty stack (top = None)",
                           fill=C["text_light"], font=font(10))
        cv.create_text(x + w + 120, 40, anchor="nw", fill=C["text"], font=mono(9),
                       text=f"size()     = {self.stack.size()}\n"
                            f"is_empty() = {self.stack.is_empty()}\n\n"
                            "SMARTBUS pushes BOOK,\nCANCEL, CHANGE and\nWAITLIST operations.\n"
                            "Undo pops the top one.")


# =========================================================================
# 4. Queue
# =========================================================================
class QueueLab(LabTab):
    TITLE = "4 · Queue (FIFO) – waiting list"
    IDEA = ("First come, first served: passengers join at the REAR (enqueue) and the FRONT "
            "passenger receives the next free seat (dequeue). Front and rear pointers make "
            "both operations O(1).")
    COMPLEXITY = [("enqueue", "O(1)"), ("dequeue", "O(1)"), ("peek", "O(1)"),
                  ("is_empty / size", "O(1)"), ("position lookup", "O(n)")]

    def build_controls(self, f):
        self.queue = Queue()
        self.label(f, "Passenger")
        self.value = self.entry(f, 14, "Sara")
        self.button(f, "Enqueue", self.enqueue, "primary")
        self.button(f, "Dequeue", self.dequeue)
        self.button(f, "Peek", self.peek)
        self.button(f, "Demo: Ali, Ahmed, Moiz, dequeue", self.demo)
        self.button(f, "Clear", self.clear)

    def enqueue(self, value=None):
        value = value or self.value.get().strip() or "passenger"
        self.queue.enqueue(value)
        self.log(f"enqueue({value}) → size {self.queue.size()}", head=True)
        self.draw()

    def dequeue(self):
        try:
            value = self.queue.dequeue()
            self.log(f"dequeue() → {value} gets the freed seat", head=True)
        except QueueEmptyError:
            self.log("dequeue() ✗ queue is empty")
        self.draw()

    def peek(self):
        try:
            self.log(f"peek() → {self.queue.peek()} is next", head=True)
        except QueueEmptyError:
            self.log("peek() ✗ queue is empty")

    def clear(self):
        self.queue.clear()
        self.log("clear()", head=True)
        self.draw()

    def demo(self):
        self.clear()
        steps = [("e", "Ali"), ("e", "Ahmed"), ("e", "Moiz"), ("d", None)]
        self.animate(steps, lambda s: self.enqueue(s[1]) if s[0] == "e" else self.dequeue())

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        x, y, w, h, gap = 30, 110, 110, 54, 26
        items = list(self.queue)
        for i, value in enumerate(items):
            front = i == 0
            self.box(x, y, w, h, str(value), fill=C["primary"] if front else C["card"],
                     fg="white" if front else C["text"], sub=f"position {i + 1}")
            if i < len(items) - 1:
                cv.create_line(x + w, y + h / 2, x + w + gap, y + h / 2, arrow="last",
                               fill=C["text_muted"], width=2)
            x += w + gap
        if items:
            cv.create_text(30, y - 18, text="FRONT → dequeue", anchor="w", fill=C["primary"],
                           font=font(9, "bold"))
            cv.create_text(x - gap, y + h + 18, text="REAR ← enqueue", anchor="e",
                           fill=C["text_muted"], font=font(9, "bold"))
        else:
            cv.create_text(30, y + h / 2, text="empty queue (front = rear = None)", anchor="w",
                           fill=C["text_light"], font=font(10))
        cv.create_text(30, 30, anchor="nw", fill=C["text"], font=mono(9),
                       text=f"size() = {self.queue.size()}    is_empty() = "
                            f"{self.queue.is_empty()}")


# =========================================================================
# 5. Hash table
# =========================================================================
class HashLab(LabTab):
    TITLE = "5 · Hash table – booking lookup (separate chaining)"
    IDEA = ("hash(key) = Σ ch·31^k mod 2^32, bucket = hash % capacity. Colliding keys share a "
            "bucket as a linked chain. A small table (7 buckets, no resize) makes collisions "
            "easy to see; the real booking index resizes when the load factor passes 0.75.")
    COMPLEXITY = [("insert (average)", "O(1)"), ("search (average)", "O(1)"),
                  ("delete (average)", "O(1)"), ("worst case (all collide)", "O(n)"),
                  ("resize / rehash", "O(n)")]

    def build_controls(self, f):
        self.table = HashTable(7, auto_resize=False)
        self.focus = None
        self.compared = []
        self.label(f, "Key")
        self.key = self.entry(f, 12, "SB-DEMO1")
        self.label(f, "Value")
        self.value = self.entry(f, 10, "Ali")
        self.button(f, "Insert", self.insert, "primary")
        self.button(f, "Search", self.search)
        self.button(f, "Delete", self.delete)
        self.button(f, "Load 12 real bookings", self.load_real)
        self.button(f, "Clear", self.clear)

    def insert(self):
        key = self.key.get().strip().upper()
        if not key:
            return
        h = HashTable.hash_code(key)
        index = self.table.bucket_index(key)
        existed = self.table.contains(key)
        self.table.insert(key, self.value.get().strip())
        self.focus, self.compared = index, []
        chain = self.table.chain_lengths()[index]
        self.log(f"insert({key}): hash = {h}, {h} % {self.table.capacity} = bucket {index}"
                 + (" (updated)" if existed else (" – collision! chain length "
                                                  f"{chain}" if chain > 1 else "")), head=True)
        self.draw()

    def search(self):
        key = self.key.get().strip().upper()
        bucket, compared, value = self.table.search_trace(key)
        self.log(f"search({key}) → bucket {bucket}", head=True)
        steps = list(range(1, len(compared) + 1)) or [0]

        def render(n):
            self.focus, self.compared = bucket, compared[:n]
            self.draw()
            if n:
                k = compared[n - 1]
                self.log(f"  compare {k} {'== ✓' if k == key else '≠'}")
        self.animate(steps, render, lambda: self.log(
            f"Result: {value!r} after {len(compared)} comparison(s)" if value is not None
            else f"Not found after {len(compared)} comparison(s)"))

    def delete(self):
        key = self.key.get().strip().upper()
        try:
            self.table.delete(key)
            self.log(f"delete({key}): unlink entry from bucket {self.table.bucket_index(key)}",
                     head=True)
        except KeyError:
            self.log(f"delete({key}) ✗ key not found")
        self.focus, self.compared = None, []
        self.draw()

    def load_real(self):
        bookings = list(self.app.bookings.index.values())[:12]
        for b in bookings:
            self.table.insert(b.booking_id, b.passenger_name)
        self.log(f"Inserted {len(bookings)} real booking IDs from the SMARTBUS index",
                 head=True)
        if bookings:
            self.key.delete(0, "end")
            self.key.insert(0, bookings[0].booking_id)
        self.draw()

    def clear(self):
        self.table = HashTable(7, auto_resize=False)
        self.focus, self.compared = None, []
        self.log("New empty table with 7 buckets", head=True)
        self.draw()

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        x0, y0, bh = 20, 20, 40
        for i, chain in enumerate(self.table.buckets_snapshot()):
            y = y0 + i * (bh + 10)
            focus = i == self.focus
            self.box(x0, y, 60, bh, f"[{i}]", fill=C["primary"] if focus else C["card"],
                     fg="white" if focus else C["text"])
            x = x0 + 80
            if not chain:
                cv.create_text(x, y + bh / 2, text="None", anchor="w", fill=C["text_light"],
                               font=mono(8))
            for key, value in chain:
                hit = key in self.compared
                fill = C["secondary"] if hit else C["card"]
                self.box(x, y, 120, bh, str(key), fill=fill, sub=str(value)[:14])
                cv.create_line(x - 20, y + bh / 2, x, y + bh / 2, arrow="last",
                               fill=C["text_muted"])
                x += 140
        st = self.table.stats()
        cv.create_text(20, y0 + 7 * (bh + 10) + 10, anchor="nw", fill=C["text"], font=mono(9),
                       text=f"size = {st['size']}   capacity = {st['capacity']}   load factor = "
                            f"{st['load_factor']}   collisions = {st['collisions']}   longest "
                            f"chain = {st['longest_chain']}")


# =========================================================================
# Graph helpers shared by BFS/DFS and Dijkstra tabs
# =========================================================================
def copy_graph(source):
    g = Graph()
    for city in source.cities():
        g.add_city(city)
    for a, b, w in source.edges():
        g.add_connection(a, b, w)
    return g


def map_positions(graph, w, h, pad=40, left_pad=90):
    cities = graph.cities()
    known = [CITY_COORDS[c] for c in cities if c in CITY_COORDS] or [(0, 0), (1, 1)]
    min_x, max_x = min(p[0] for p in known), max(p[0] for p in known)
    min_y, max_y = min(p[1] for p in known), max(p[1] for p in known)
    pos = {}
    extra = 0
    for c in cities:
        if c in CITY_COORDS:
            lon, lat = CITY_COORDS[c]
            pos[c] = (left_pad + (lon - min_x) / ((max_x - min_x) or 1) *
                      (w - left_pad - pad - 60),
                      h - pad - (lat - min_y) / ((max_y - min_y) or 1) * (h - 2 * pad))
        else:
            pos[c] = (w - 50, pad + extra * 34)
            extra += 1
    return pos


def draw_graph(cv, graph, colors=None, labels=None, path=(), edge_hl=()):
    cv.delete("all")
    w, h = max(cv.winfo_width(), 400), max(cv.winfo_height(), 320)
    pos = map_positions(graph, w, h)
    colors = colors or {}
    labels = labels or {}
    path_edges = {(path[i], path[i + 1]) for i in range(len(path) - 1)}
    path_edges |= {(b, a) for a, b in path_edges}
    hl = set(edge_hl) | {(b, a) for a, b in edge_hl}
    for a, b, dist in graph.edges():
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if (a, b) in path_edges:
            color, width = C["primary"], 4
        elif (a, b) in hl:
            color, width = C["warning"], 3
        else:
            color, width = "#CBD5E1", 2
        cv.create_line(x1, y1, x2, y2, fill=color, width=width)
        cv.create_text((x1 + x2) / 2, (y1 + y2) / 2 - 8, text=f"{dist:.0f}",
                       fill=C["text_light"], font=font(7))
    for city, (x, y) in pos.items():
        fill = colors.get(city, C["card"])
        cv.create_oval(x - 10, y - 10, x + 10, y + 10, fill=fill, outline=C["primary"], width=2)
        left = city in LABEL_LEFT
        dx, anchor = (-13, "e") if left else (13, "w")
        cv.create_text(x + dx, y - 9, text=city, anchor=anchor, fill=C["text"], font=font(8))
        if city in labels:
            cv.create_text(x + dx, y + 7, text=labels[city], anchor=anchor, fill=C["primary"],
                           font=mono(8, "bold"))


# =========================================================================
# 6. Graph BFS / DFS
# =========================================================================
class GraphLab(LabTab):
    TITLE = "6 · Graph – BFS and DFS on the city network"
    IDEA = ("Cities are vertices, roads are weighted edges (adjacency list). BFS explores level "
            "by level with a FIFO queue; DFS dives deep first with a LIFO stack. Visit numbers "
            "appear next to each city. Add or remove a road to see traversals change.")
    COMPLEXITY = [("add city / connection", "O(1)"), ("remove connection", "O(deg)"),
                  ("BFS", "O(V + E)"), ("DFS", "O(V + E)"), ("Space (adjacency list)",
                                                            "O(V + E)")]

    def build_controls(self, f):
        self.graph = copy_graph(self.app.routes.graph)
        self.colors, self.labels, self.edges_hl = {}, {}, []
        self.label(f, "Start")
        self.start = combo(f, sorted_cities(self.graph), width=13)
        self.start.set("Karachi" if self.graph.has_city("Karachi") else "")
        self.put(f, self.start)
        self.button(f, "BFS", lambda: self.run("bfs"), "primary")
        self.button(f, "DFS", lambda: self.run("dfs"), "primary")
        self.button(f, "Reset", self.reset)
        f2 = self.controls2
        self.label(f2, "Road")
        self.a = combo(f2, sorted_cities(self.graph), width=13)
        self.a.set("Quetta" if self.graph.has_city("Quetta") else self.a.get())
        self.put(f2, self.a)
        self.b = combo(f2, sorted_cities(self.graph), width=13)
        self.b.set("Multan" if self.graph.has_city("Multan") else self.b.get())
        self.put(f2, self.b)
        self.label(f2, "km")
        self.km = self.entry(f2, 5, "520")
        self.button(f2, "Add road", self.add_edge)
        self.button(f2, "Remove road", self.remove_edge)

    def reset(self):
        self.stop()
        self.graph = copy_graph(self.app.routes.graph)
        self.colors, self.labels, self.edges_hl = {}, {}, []
        self.log("Graph reset to the live SMARTBUS network", head=True)
        self.draw()

    def add_edge(self):
        try:
            self.graph.add_connection(self.a.get(), self.b.get(), float(self.km.get()))
            self.log(f"add_connection({self.a.get()}, {self.b.get()}, {self.km.get()})",
                     head=True)
        except (ValueError, KeyError) as exc:
            self.log(f"add_connection ✗ {exc}")
        self.draw()

    def remove_edge(self):
        try:
            self.graph.remove_connection(self.a.get(), self.b.get())
            self.log(f"remove_connection({self.a.get()}, {self.b.get()})", head=True)
        except KeyError as exc:
            self.log(f"remove_connection ✗ {exc}")
        self.draw()

    def run(self, kind):
        start = self.start.get()
        if not self.graph.has_city(start):
            toast(self, "Choose a start city.", "warning")
            return
        steps = bfs_steps(self.graph, start) if kind == "bfs" else dfs_steps(self.graph, start)
        name = "Queue" if kind == "bfs" else "Stack"
        self.log(f"{kind.upper()} from {start} (uses our {name} class)", head=True)
        self.colors, self.labels, self.edges_hl = {}, {}, []

        def render(step):
            city, order, frontier, edge = step
            self.colors[city] = C["primary"]
            for f_city in frontier:
                self.colors.setdefault(f_city, C["secondary"])
            self.labels[city] = f"#{order}"
            if edge:
                self.edges_hl.append(edge)
            self.draw()
            self.log(f"visit #{order}: {city:<14} {name.lower()} = [{', '.join(frontier)}]")
        expected = self.graph.bfs(start) if kind == "bfs" else self.graph.dfs(start)
        self.animate(steps, render, lambda: self.log("Order: " + " → ".join(expected)))

    def draw(self):
        draw_graph(self.canvas, self.graph, self.colors, self.labels, edge_hl=self.edges_hl)


def sorted_cities(graph):
    from algorithms.sorting import merge_sort
    return merge_sort(graph.cities(), key=str.lower)


def bfs_steps(graph, start):
    """BFS with snapshots: (city, order, queue contents, tree edge)."""
    visited = {start}
    parent = {start: None}
    q = Queue()
    q.enqueue(start)
    steps, order = [], 0
    while not q.is_empty():
        city = q.dequeue()
        order += 1
        for n, _ in graph.neighbors(city):
            if n not in visited:
                visited.add(n)
                parent[n] = city
                q.enqueue(n)
        edge = (parent[city], city) if parent[city] else None
        steps.append((city, order, list(q), edge))
    return steps


def dfs_steps(graph, start):
    """Iterative DFS with snapshots, same order as Graph.dfs."""
    visited = set()
    parent = {start: None}
    s = Stack()
    s.push(start)
    steps, order = [], 0
    while not s.is_empty():
        city = s.pop()
        if city in visited:
            continue
        visited.add(city)
        order += 1
        nbrs = graph.neighbors(city)
        for i in range(len(nbrs) - 1, -1, -1):
            if nbrs[i][0] not in visited:
                parent[nbrs[i][0]] = city
                s.push(nbrs[i][0])
        edge = (parent[city], city) if parent.get(city) else None
        steps.append((city, order, list(s), edge))
    return steps


# =========================================================================
# 7. Dijkstra
# =========================================================================
class DijkstraLab(LabTab):
    TITLE = "7 · Dijkstra's shortest path"
    IDEA = ("Repeatedly settle the unsettled city with the smallest tentative distance (taken "
            "from our MinHeap), then relax its roads: if dist[u] + w < dist[v], update v. "
            "Blue = settled, cyan = tentative; the final path is highlighted.")
    COMPLEXITY = [("Overall", "O((V+E) log V)"), ("Heap push / pop", "O(log V)"),
                  ("Relax one edge", "O(1)"), ("Path reconstruction", "O(V)"),
                  ("Space", "O(V)")]

    def build_controls(self, f):
        cities = sorted_cities(self.app.routes.graph)
        self.label(f, "From")
        self.src = combo(f, cities, width=13)
        self.src.set("Karachi" if "Karachi" in cities else (cities[0] if cities else ""))
        self.put(f, self.src)
        self.label(f, "To")
        self.dst = combo(f, cities, width=13)
        self.dst.set("Peshawar" if "Peshawar" in cities else (cities[-1] if cities else ""))
        self.put(f, self.dst)
        self.button(f, "Run Dijkstra (animated)", self.run, "primary")
        self.button(f, "Compare routes", self.compare)
        self.colors, self.labels, self.path = {}, {}, []

    def run(self):
        graph = self.app.routes.graph
        src, dst = self.src.get(), self.dst.get()
        if src == dst or not graph.has_city(src) or not graph.has_city(dst):
            toast(self, "Choose two different cities.", "warning")
            return
        result = dijkstra(graph, src, dst)
        self.colors, self.labels, self.path = {src: C["secondary"]}, {src: "0"}, []
        self.log(f"dijkstra({src} → {dst}); dist[{src}] = 0, others = ∞", head=True)

        def render(step):
            if step["type"] == "settle":
                self.colors[step["city"]] = C["primary"]
                self.log(f"settle {step['city']} (dist {step['distance']:.0f})")
            else:
                self.colors.setdefault(step["to"], C["secondary"])
                if self.colors[step["to"]] != C["primary"]:
                    self.colors[step["to"]] = C["secondary"]
                self.labels[step["to"]] = f"{step['new']:.0f}"
                old = "∞" if step["old"] == float("inf") else f"{step['old']:.0f}"
                self.log(f"   relax {step['from']}→{step['to']}: {old} → {step['new']:.0f}")
            self.draw()

        def done():
            self.path = result.path
            self.draw()
            if result.reachable:
                self.log(f"Shortest: {' → '.join(result.path)} = {result.distance:.0f} km",
                         head=True)
            else:
                self.log("Unreachable – no path exists", head=True)
        self.animate(result.steps, render, done)

    def compare(self):
        graph = self.app.routes.graph
        src, dst = self.src.get(), self.dst.get()
        routes = find_all_routes(graph, src, dst, max_routes=6)
        self.log(f"Alternative routes {src} → {dst} (DFS backtracking + merge sort)",
                 head=True)
        if not routes:
            self.log("  none")
        best = routes[0][1] if routes else 0
        for i, (p, d) in enumerate(routes, 1):
            self.log(f"  {i}. {d:.0f} km (+{d - best:.0f})  {' → '.join(p)}")
        if routes:
            self.path = routes[0][0]
            self.draw()

    def draw(self):
        draw_graph(self.canvas, self.app.routes.graph, self.colors, self.labels, self.path)


# =========================================================================
# 8. Linear vs binary search
# =========================================================================
class SearchLab(LabTab):
    TITLE = "8 · Linear search vs binary search"
    IDEA = ("Linear search checks items one by one (works on any list). Binary search needs a "
            "SORTED list and halves the range each step using low / mid / high. Try a target, "
            "then run the benchmark on 100,000 items.")
    COMPLEXITY = [("Linear – best", SEARCH_COMPLEXITY["Linear Search"]["best"]),
                  ("Linear – worst", SEARCH_COMPLEXITY["Linear Search"]["worst"]),
                  ("Binary – best", SEARCH_COMPLEXITY["Binary Search"]["best"]),
                  ("Binary – worst", SEARCH_COMPLEXITY["Binary Search"]["worst"]),
                  ("Binary precondition", "sorted data")]

    def build_controls(self, f):
        self.new_data(log=False)
        self.label(f, "Target")
        self.target = self.entry(f, 6, str(self.data[11]))
        self.button(f, "Linear search", self.linear, "primary")
        self.button(f, "Binary search", self.binary, "primary")
        self.button(f, "New data", self.new_data)
        self.button(f, "Benchmark 100k", self.benchmark)
        self.button(f, "Search passengers", self.passengers)

    def new_data(self, log=True):
        self.data = sorted_unique(random.sample(range(1, 200), 24))
        self.state = {}
        if log:
            self.log("New sorted list of 24 numbers", head=True)
            self.draw()

    def _target(self):
        try:
            return int(self.target.get())
        except ValueError:
            toast(self, "Enter a whole number.", "warning")
            return None

    def linear(self):
        t = self._target()
        if t is None:
            return
        result = linear_search(self.data, t, record=True)
        self.log(f"linear_search({t})", head=True)

        def render(step):
            self.state = {"cur": step["index"], "done": set(range(step["index"])),
                          "match": step["match"]}
            self.draw()
            self.log(f"  a[{step['index']}] = {step['value']} "
                     f"{'✓' if step['match'] else '≠'}")
        self.animate(result.steps, render, lambda: self.log(
            f"{'Found at ' + str(result.index) if result.found else 'Not found'} · "
            f"{result.comparisons} comparisons"))

    def binary(self):
        t = self._target()
        if t is None:
            return
        result = binary_search(self.data, t, record=True)
        self.log(f"binary_search({t}) on sorted list", head=True)

        def render(step):
            self.state = {"low": step["low"], "high": step["high"], "cur": step["mid"],
                          "match": step["match"]}
            self.draw()
            rel = "==" if step["match"] else ("<" if step["value"] < t else ">")
            self.log(f"  low={step['low']} mid={step['mid']} high={step['high']}  "
                     f"a[mid]={step['value']} {rel} {t}")
        self.animate(result.steps, render, lambda: self.log(
            f"{'Found at ' + str(result.index) if result.found else 'Not found'} · "
            f"{result.comparisons} comparisons"))

    def benchmark(self):
        n = 100_000
        data = list(range(0, n * 2, 2))
        targets = [random.randrange(0, n * 2) for _ in range(200)]
        lin_c = bin_c = 0
        t0 = time.perf_counter()
        for t in targets:
            lin_c += linear_search(data, t).comparisons
        t1 = time.perf_counter()
        for t in targets:
            bin_c += binary_search(data, t).comparisons
        t2 = time.perf_counter()
        self.log(f"Benchmark: {len(targets)} searches in {n:,} sorted items", head=True)
        self.log(f"  Linear: avg {lin_c / len(targets):,.0f} comparisons, "
                 f"{(t1 - t0) * 1000 / len(targets):.2f} ms each")
        self.log(f"  Binary: avg {bin_c / len(targets):.1f} comparisons, "
                 f"{(t2 - t1) * 1000 / len(targets):.4f} ms each")
        self.log(f"  log2({n:,}) ≈ 17 → binary search is ~{lin_c / max(bin_c, 1):,.0f}× fewer "
                 "comparisons")

    def passengers(self):
        name = "Moiz Ahmed"
        people = self.app.passengers.list_passengers(sort_by="Name (A → Z)")
        lin = linear_search(people, name.lower(), key=lambda p: p.name_key)
        bins = binary_search(people, name.lower(), key=lambda p: p.name_key)
        self.log(f"Find '{name}' among {len(people)} real passengers", head=True)
        self.log(f"  linear: index {lin.index}, {lin.comparisons} comparisons")
        self.log(f"  binary: index {bins.index}, {bins.comparisons} comparisons (list sorted "
                 "by merge sort first)")

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        width = max(cv.winfo_width(), 600)
        w = min(46, (width - 40) / max(len(self.data), 1) - 4)
        x0, y = 20, 90
        st = self.state
        for i, v in enumerate(self.data):
            x = x0 + i * (w + 4)
            fill = C["card"]
            if "low" in st and not st["low"] <= i <= st["high"]:
                fill = "#E2E8F0"                             # discarded half
            if i in st.get("done", ()):
                fill = "#E2E8F0"
            if i == st.get("cur"):
                fill = C["success"] if st.get("match") else C["warning"]
            cv.create_rectangle(x, y, x + w, y + 44, fill=fill, outline=C["primary"])
            cv.create_text(x + w / 2, y + 22, text=str(v), fill=C["text"],
                           font=font(9 if w >= 34 else 7, "bold"))
            cv.create_text(x + w / 2, y + 56, text=str(i), fill=C["text_light"], font=font(7))
            for key, label in (("low", "low"), ("high", "high"), ("cur", "mid")):
                if st.get(key) == i and ("low" in st or key == "cur"):
                    cv.create_text(x + w / 2, y - 12 - (12 if key == "cur" else 0),
                                   text=label if "low" in st else "i", fill=C["primary"],
                                   font=font(8, "bold"))
        cv.create_text(20, y + 90, anchor="nw", fill=C["text_muted"], font=mono(9),
                       text="Grey = eliminated · orange = current comparison · green = match")


def sorted_unique(values):
    from algorithms.sorting import merge_sort
    result = []
    for v in merge_sort(values):
        if not result or result[-1] != v:
            result.append(v)
    return result


# =========================================================================
# 9. Sorting
# =========================================================================
class SortLab(LabTab):
    TITLE = "9 · Sorting algorithms"
    IDEA = ("Pick an algorithm and watch the bars move. Orange bars are being compared or "
            "moved. 'Compare all' runs the five algorithms on the same 1,500 random numbers "
            "and reports comparisons, moves and time.")
    COMPLEXITY = [(name, f"{info['average']} avg") for name, info in ALGORITHMS.items()] + \
        [("Merge sort space", "O(n)")]

    def build_controls(self, f):
        self.values = random.sample(range(5, 100), 18)
        self.highlight = ()
        self.label(f, "Algorithm")
        self.algo = combo(f, list(ALGORITHMS.keys()), width=14)
        self.algo.set("Bubble Sort")
        self.put(f, self.algo)
        self.label(f, "Size")
        self.size = ttk.Spinbox(f, from_=5, to=40, width=4)
        self.size.set(18)
        self.put(f, self.size)
        self.button(f, "Shuffle", self.shuffle)
        self.button(f, "Sort (animated)", self.run, "primary")
        self.button(f, "Compare all", self.compare_all)
        self.button(self.controls2, "Sort real buses by price", self.sort_buses)

    def shuffle(self):
        self.stop()
        try:
            n = max(5, min(40, int(self.size.get())))
        except ValueError:
            n = 18
        self.values = random.sample(range(5, 100), n)
        self.highlight = ()
        self.log(f"Original: {self.values}", head=True)
        self.draw()

    def run(self):
        name = self.algo.get()
        info = ALGORITHMS[name]
        steps = []
        stats = SortStats()
        result = info["fn"](self.values, stats=stats,
                            on_step=lambda arr, idx, text: steps.append((arr, idx, text)))
        self.log(f"{name}: {info['idea']}", head=True)
        self.log(f"Original: {self.values}")
        counter = [0]

        def render(step):
            arr, idx, text = step
            self.values, self.highlight = arr, idx
            counter[0] += 1
            self.draw()
            if counter[0] % 4 == 1 or text == "Sorted" or "Pivot" in text or "Merge" in text:
                self.log(f"  {text}")

        def done():
            self.highlight = ()
            self.values = result
            self.draw()
            self.log(f"Sorted:   {result}", head=True)
            self.log(f"{stats.comparisons} comparisons, {stats.swaps} swaps/moves · best "
                     f"{info['best']}, average {info['average']}, worst {info['worst']}, space "
                     f"{info['space']}, {'stable' if info['stable'] else 'not stable'}")
        # long animations are sampled so they finish in a reasonable time
        if len(steps) > 400:
            stride = len(steps) // 400 + 1
            steps = steps[::stride] + [steps[-1]]
        self.animate(steps, render, done)

    def compare_all(self):
        data = [random.randint(0, 100000) for _ in range(1500)]
        self.log("Compare all on the same 1,500 random numbers", head=True)
        for name, info in ALGORITHMS.items():
            stats = SortStats()
            t0 = time.perf_counter()
            info["fn"](data, stats=stats)
            ms = (time.perf_counter() - t0) * 1000
            self.log(f"  {name:<15} {stats.comparisons:>9,} cmp {stats.swaps:>9,} mov "
                     f"{ms:>7.1f} ms")

    def sort_buses(self):
        name = self.algo.get()
        buses = self.app.buses.all_buses()
        stats = SortStats()
        ordered = ALGORITHMS[name]["fn"](buses, key=lambda b: b.ticket_price, stats=stats)
        self.log(f"{name} on {len(buses)} real buses by ticket price", head=True)
        for b in ordered[:8]:
            self.log(f"  Rs. {b.ticket_price:>6,.0f}  {b.label}")
        self.log(f"  … {stats.comparisons} comparisons")
        self.values = [int(b.ticket_price / 100) for b in ordered]
        self.highlight = ()
        self.draw()

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        w, h = max(cv.winfo_width(), 500), max(cv.winfo_height(), 300)
        n = len(self.values)
        if not n:
            return
        top = max(self.values)
        slot = (w - 40) / n
        bar = max(min(slot - 4, 28), 2)
        for i, v in enumerate(self.values):
            x = 20 + i * slot + (slot - bar) / 2
            bh = (h - 70) * v / top
            fill = C["warning"] if i in self.highlight else C["primary"]
            cv.create_rectangle(x, h - 30 - bh, x + bar, h - 30, fill=fill, outline="")
            if n <= 30:
                cv.create_text(x + bar / 2, h - 30 - bh - 8, text=str(v), fill=C["text_muted"],
                               font=font(7))
        cv.create_line(16, h - 30, w - 16, h - 30, fill=C["border"])


# =========================================================================
# Page
# =========================================================================
class DSALabPage(tk.Frame):
    TABS = [("Array", ArrayLab), ("Linked List", LinkedListLab), ("Stack", StackLab),
            ("Queue", QueueLab), ("Hash Table", HashLab), ("Graph BFS/DFS", GraphLab),
            ("Dijkstra", DijkstraLab), ("Search", SearchLab), ("Sorting", SortLab)]

    def __init__(self, parent, ctx):
        super().__init__(parent, bg=C["background"])
        PageHeader(self, "DSA Lab · Algorithm Visualizer",
                   "Interactive demonstrations of every data structure and algorithm used in "
                   "SMARTBUS").pack(fill="x", pady=(0, 6))
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tabs = []
        for name, cls in self.TABS:
            tab = cls(self.nb, ctx)
            self.nb.add(tab, text=name)
            self.tabs.append(tab)
        self.nb.bind("<<NotebookTabChanged>>", self._changed)

    def _changed(self, _):
        for tab in self.tabs:
            tab.stop()
        self.tabs[self.nb.index("current")].draw()

    def refresh(self):
        self.tabs[self.nb.index("current")].draw()
