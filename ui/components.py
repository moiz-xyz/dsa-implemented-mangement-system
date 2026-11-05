"""
Reusable UI components so every screen looks and behaves the same.

Buttons are built from tk.Label rather than tk.Button because macOS ignores
background colours on native buttons; a Label-based button looks identical
on Windows, Linux and macOS.
"""

import traceback
import tkinter as tk
from tkinter import messagebox, ttk

from algorithms.sorting import merge_sort
from ui import theme
from ui.theme import C, font
from utils.exceptions import SmartBusError

BUTTON_STYLES = {
    "primary": (C["primary"], "white", C["primary_dark"]),
    "secondary": (C["card"], C["text"], "#F1F5F9"),
    "danger": (C["danger"], "white", C["danger_dark"]),
    "success": (C["success"], "white", "#059669"),
    "ghost": (C["background"], C["primary"], C["primary_light"]),
    "dark": (C["sidebar_hover"], "white", "#334155"),
}


# =========================================================================
# Error handling
# =========================================================================
def show_error(parent, exc, title="Something went wrong"):
    if isinstance(exc, SmartBusError):
        messagebox.showerror(title if title != "Something went wrong" else "Cannot continue",
                             str(exc), parent=parent)
    else:
        traceback.print_exc()
        messagebox.showerror(title, f"An unexpected error occurred:\n{exc}", parent=parent)


def safe(parent, fn, *args, **kwargs):
    """Run fn; show a friendly dialog instead of crashing on any error."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:        # noqa: BLE001 – UI boundary, never crash
        show_error(parent, exc)
        return None


def confirm(parent, title, message, danger=True):
    return messagebox.askyesno(title, message, parent=parent,
                               icon="warning" if danger else "question")


# =========================================================================
# Buttons
# =========================================================================
class Button(tk.Label):
    def __init__(self, parent, text, command=None, variant="primary", icon=None, width=None,
                 small=False, **kw):
        bg, fg, hover = BUTTON_STYLES[variant]
        self._colors = (bg, fg, hover)
        self._command = command
        self._enabled = True
        image = theme.icon(icon, "_white" if variant in ("primary", "danger", "success", "dark")
                           else "_blue") if icon else None
        pad = (12, 5) if small else (16, 8)
        super().__init__(parent, text=text, bg=bg, fg=fg, cursor="hand2",
                         font=font(9 if small else 10, "bold"), padx=pad[0], pady=pad[1],
                         image=image, compound="left" if image else "none", **kw)
        if image is not None:
            self.configure(text=f" {text}")
            self.image = image
        if width:
            self.configure(width=width)
        if variant == "secondary":
            self.configure(highlightthickness=1, highlightbackground=C["border"])
        self.bind("<Enter>", lambda e: self._enabled and self.configure(bg=hover))
        self.bind("<Leave>", lambda e: self.configure(bg=bg if self._enabled else "#CBD5E1"))
        self.bind("<ButtonRelease-1>", self._click)

    def _click(self, event):
        if not self._enabled or self._command is None:
            return
        # only fire if the pointer is still over the button
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self._command()

    def set_enabled(self, enabled):
        self._enabled = enabled
        bg, fg, _ = self._colors
        self.configure(bg=bg if enabled else "#CBD5E1", fg=fg if enabled else "white",
                       cursor="hand2" if enabled else "arrow")

    def set_command(self, command):
        self._command = command


# =========================================================================
# Containers
# =========================================================================
# Responsive helpers
# =========================================================================
def auto_wrap(label, margin=4):
    """Make a Label re-wrap its text whenever its width changes."""
    def on_resize(event):
        width = max(event.width - margin, 60)
        if int(float(label.cget("wraplength") or 0)) != width:
            label.configure(wraplength=width)
    label.configure(justify="left")
    label.bind("<Configure>", on_resize, add="+")
    return label


class FlowFrame(tk.Frame):
    """
    Lays children out left-to-right and wraps them onto a new line when the
    frame becomes too narrow – like text wrapping, but for toolbars.
    Children must be created with this frame as parent and added with add().
    """

    def __init__(self, parent, bg=C["card"], hgap=8, vgap=8):
        super().__init__(parent, bg=bg, height=34, width=200)
        self.hgap, self.vgap = hgap, vgap
        self._items = []
        self._width = 0
        self.bind("<Configure>", self._on_configure)

    def add(self, widget, gap=None, newline=False):
        self._items.append((widget, self.hgap if gap is None else gap, newline))
        self.after_idle(self.relayout)
        return widget

    def _on_configure(self, event):
        if event.width != self._width:
            self._width = event.width
            self.relayout()

    def relayout(self):
        if not self.winfo_exists():
            return
        width = max(self.winfo_width(), 1)
        rows, row, x = [], [], 0
        for widget, gap, newline in self._items:
            w = widget.winfo_reqwidth()
            if row and (newline or x + w > width):
                rows.append(row)
                row, x = [], 0
            row.append((widget, x))
            x += w + gap
        if row:
            rows.append(row)
        y = 0
        for row in rows:
            height = max(widget.winfo_reqheight() for widget, _ in row)
            for widget, wx in row:
                widget.place(x=wx, y=y + (height - widget.winfo_reqheight()) // 2)
            y += height + self.vgap
        total = max(y - self.vgap, 1)
        if int(self.cget("height")) != total:
            self.configure(height=total)


def labeled_inline(flow, text, widget_factory, bg=C["card"]):
    """'Label: widget' kept together as one unit inside a FlowFrame."""
    group = tk.Frame(flow, bg=bg)
    tk.Label(group, text=text, bg=bg, fg=C["text_muted"], font=font(9)).pack(
        side="left", padx=(0, 4))
    widget = widget_factory(group)
    widget.pack(side="left")
    flow.add(group, gap=14)
    return widget


# =========================================================================
class Card(tk.Frame):
    """White panel with a 1px border – the basic building block of each page."""

    def __init__(self, parent, padding=16, **kw):
        super().__init__(parent, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"], highlightcolor=C["border"], **kw)
        self.body = tk.Frame(self, bg=C["card"])
        self.body.pack(fill="both", expand=True, padx=padding, pady=padding)


def card_title(parent, title, subtitle=None):
    frame = tk.Frame(parent, bg=C["card"])
    tk.Label(frame, text=title, bg=C["card"], fg=C["text"], font=font(12, "bold"),
             anchor="w").pack(fill="x")
    if subtitle:
        auto_wrap(tk.Label(frame, text=subtitle, bg=C["card"], fg=C["text_muted"],
                           font=font(9), anchor="w", justify="left")).pack(fill="x")
    return frame


class PageHeader(tk.Frame):
    def __init__(self, parent, title, subtitle=""):
        super().__init__(parent, bg=C["background"])
        # actions are packed FIRST so they always keep their space; the title
        # area takes what is left and its subtitle wraps when narrow.
        self.actions = tk.Frame(self, bg=C["background"])
        self.actions.pack(side="right", anchor="n")
        left = tk.Frame(self, bg=C["background"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=title, bg=C["background"], fg=C["text"], font=font(18, "bold"),
                 anchor="w").pack(fill="x")
        if subtitle:
            auto_wrap(tk.Label(left, text=subtitle, bg=C["background"], fg=C["text_muted"],
                               font=font(10), anchor="w")).pack(fill="x")

    def add_action(self, text, command, variant="primary", icon=None):
        btn = Button(self.actions, text, command, variant=variant, icon=icon)
        btn.pack(side="left", padx=(8, 0))
        return btn


class StatCard(tk.Frame):
    def __init__(self, parent, label, value, accent=C["primary"], note=""):
        super().__init__(parent, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"], highlightcolor=C["border"])
        tk.Frame(self, bg=accent, width=4).pack(side="left", fill="y")
        body = tk.Frame(self, bg=C["card"])
        body.pack(side="left", fill="both", expand=True, padx=14, pady=12)
        tk.Label(body, text=label, bg=C["card"], fg=C["text_muted"], font=font(9),
                 anchor="w").pack(fill="x")
        self.value_label = tk.Label(body, text=value, bg=C["card"], fg=C["text"],
                                    font=font(19, "bold"), anchor="w")
        self.value_label.pack(fill="x")
        self.note_label = tk.Label(body, text=note, bg=C["card"], fg=C["text_light"],
                                   font=font(8), anchor="w")
        self.note_label.pack(fill="x")

    def set(self, value, note=None):
        self.value_label.configure(text=value)
        if note is not None:
            self.note_label.configure(text=note)


class ScrollableFrame(tk.Frame):
    """A frame with a vertical scrollbar; put content in `.inner`."""

    def __init__(self, parent, bg=C["background"]):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._window, width=e.width))
        for widget in (self.canvas, self.inner):
            widget.bind("<Enter>", self._bind_wheel)
            widget.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

    def _unbind_wheel(self, _):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        delta = event.delta
        step = -1 if delta > 0 else 1
        if abs(delta) >= 120:                 # Windows reports multiples of 120
            step = int(-delta / 120)
        self.canvas.yview_scroll(step * 2, "units")


# =========================================================================
# Inputs
# =========================================================================
class PlaceholderEntry(ttk.Entry):
    def __init__(self, parent, placeholder="", textvariable=None, show=None, **kw):
        self.var = textvariable or tk.StringVar()
        super().__init__(parent, textvariable=self.var, **kw)
        self._placeholder = placeholder
        self._show = show
        self._showing = False
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self._focus_out()

    def _focus_in(self, _=None):
        if self._showing:
            self._showing = False
            self.delete(0, "end")
            self.configure(foreground=C["text"])
            if self._show:
                self.configure(show=self._show)

    def _focus_out(self, _=None):
        if not super().get() and self._placeholder:
            self._showing = True
            self.configure(show="", foreground=C["text_light"])
            self.insert(0, self._placeholder)

    def get(self):
        return "" if self._showing else super().get()

    def set(self, value):
        self._focus_in()
        self.delete(0, "end")
        self.insert(0, value)
        if self.focus_get() is not self:
            self._focus_out()


class SearchBar(tk.Frame):
    """Search entry with an icon; calls on_change(text) after typing stops."""

    def __init__(self, parent, placeholder="Search…", on_change=None, width=28, bg=C["card"]):
        super().__init__(parent, bg=bg)
        img = theme.icon("search", "_blue")
        if img:
            lbl = tk.Label(self, image=img, bg=bg)
            lbl.image = img
            lbl.pack(side="left", padx=(0, 6))
        self.entry = PlaceholderEntry(self, placeholder, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        self._on_change = on_change
        self._job = None
        self.entry.bind("<KeyRelease>", self._schedule)

    def _schedule(self, _):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self._fire)

    def _fire(self):
        self._job = None
        if self._on_change:
            self._on_change(self.get())

    def get(self):
        return self.entry.get().strip()


def labeled(parent, text, widget_factory, bg=C["card"], hint=None):
    """Create 'Label above input' and return the input widget."""
    frame = tk.Frame(parent, bg=bg)
    tk.Label(frame, text=text, bg=bg, fg=C["text"], font=font(9, "bold"),
             anchor="w").pack(fill="x", pady=(0, 3))
    widget = widget_factory(frame)
    widget.pack(fill="x")
    if hint:
        tk.Label(frame, text=hint, bg=bg, fg=C["text_light"], font=font(8),
                 anchor="w").pack(fill="x")
    frame.widget = widget
    return frame


def combo(parent, values, width=20, var=None, readonly=True):
    var = var or tk.StringVar()
    box = ttk.Combobox(parent, values=list(values), textvariable=var, width=width,
                       state="readonly" if readonly else "normal")
    box.var = var
    if values and not var.get():
        box.current(0)
    return box


# =========================================================================
# Table
# =========================================================================
class DataTable(tk.Frame):
    """
    Treeview wrapper with striped rows, scrollbars, an empty state and
    clickable headers. Header-click sorting uses our own merge sort.
    columns: list of (key, heading, width, anchor)
    """

    def __init__(self, parent, columns, height=12, on_select=None, on_double=None,
                 empty_text="No records to display.", status_column=None):
        super().__init__(parent, bg=C["card"])
        self.columns = columns
        self.keys = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=self.keys, show="headings", height=height,
                                 selectmode="browse")
        # Column widths are "preferred" widths. The real widths are recomputed
        # whenever the table is resized (see _fit_columns), so a table never
        # forces the window to be wider than the screen.
        self._preferred = {key: width for key, _, width, _ in columns}
        for key, heading, width, anchor in columns:
            self.tree.heading(key, text=heading, anchor=anchor,
                              command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=max(int(width * 0.4), 36), minwidth=36,
                             anchor=anchor, stretch=False)
        self._fit_width = 0
        self.tree.bind("<Configure>", self._fit_columns, add="+")
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.tag_configure("odd", background=C["card"])
        self.tree.tag_configure("even", background=C["row_alt"])
        # Only rows that need attention are tinted; normal rows keep the text colour.
        for status, color in (("Cancelled", C["text_light"]), ("Completed", C["text_light"]),
                              ("Waiting", "#B45309"), ("Maintenance", "#B45309")):
            self.tree.tag_configure(f"status_{status}", foreground=color)
        self.status_column = status_column

        self.empty = tk.Label(self, text=empty_text, bg=C["card"], fg=C["text_light"],
                              font=font(10))
        self._rows = []
        self._sort_state = (None, False)
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: on_select(self.selected()))
        if on_double:
            self.tree.bind("<Double-1>", lambda e: self.selected() and on_double(self.selected()))

    def _fit_columns(self, event):
        """
        Responsive columns. With spare width every column grows in proportion.
        When space is short, only the long free-text columns (left-aligned,
        preferred width >= 150 px: names of buses, routes, emails…) shrink –
        down to 60 % – so IDs, dates and numbers stay fully readable. If it
        still doesn't fit, the horizontal scrollbar takes over.
        """
        available = event.width
        if available <= 1 or available == self._fit_width:
            return
        self._fit_width = available
        anchors = {key: anchor for key, _, _, anchor in self.columns}
        flex = [k for k in self.keys if anchors[k] == "w" and self._preferred[k] >= 150]
        total = sum(self._preferred.values())
        if available >= total:
            scale = {k: available / total for k in self.keys}
        else:
            fixed = total - sum(self._preferred[k] for k in flex)
            flex_total = sum(self._preferred[k] for k in flex) or 1
            ratio = max((available - fixed) / flex_total, 0.6)
            scale = {k: (ratio if k in flex else 1.0) for k in self.keys}
        widths = {k: max(int(self._preferred[k] * scale[k]), 36) for k in self.keys}
        spare = available - sum(widths.values()) - 2
        if spare > 0:                       # last column absorbs rounding error
            widths[self.keys[-1]] += spare
        for key in self.keys:
            self.tree.column(key, width=widths[key])

    def set_rows(self, rows):
        """rows: list of (iid, values_tuple)."""
        self._rows = list(rows)
        self._render()

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        status_index = self.keys.index(self.status_column) if self.status_column else None
        for i, (iid, values) in enumerate(self._rows):
            tags = ["even" if i % 2 else "odd"]
            if status_index is not None:
                tags.append(f"status_{values[status_index]}")
            self.tree.insert("", "end", iid=str(iid), values=values, tags=tags)
        if self._rows:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def sort_by(self, key):
        index = self.keys.index(key)
        last_key, desc = self._sort_state
        desc = not desc if last_key == key else False
        self._sort_state = (key, desc)

        def sort_key(row):
            value = row[1][index]
            text = str(value).replace(",", "").replace("Rs.", "").replace("%", "") \
                .replace("km", "").strip()
            try:
                return (0, float(text), "")
            except ValueError:
                return (1, 0, str(value).lower())
        self._rows = merge_sort(self._rows, key=sort_key, reverse=desc)
        for k, heading, _, _ in self.columns:
            arrow = (" ▼" if desc else " ▲") if k == key else ""
            self.tree.heading(k, text=heading + arrow)
        self._render()

    def selected(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def select(self, iid):
        iid = str(iid)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)


# =========================================================================
# Feedback
# =========================================================================
class Toast:
    """Small notification that slides in at the bottom-right and fades away."""
    _current = None
    KINDS = {"success": (C["success"], "✓"), "error": (C["danger"], "!"),
             "info": (C["primary"], "i"), "warning": (C["warning"], "!")}

    @classmethod
    def show(cls, root, message, kind="success", duration=3500):
        if cls._current is not None:
            try:
                cls._current.destroy()
            except tk.TclError:
                pass
        color, symbol = cls.KINDS.get(kind, cls.KINDS["info"])
        frame = tk.Frame(root, bg=C["sidebar"], highlightthickness=0)
        tk.Frame(frame, bg=color, width=5).pack(side="left", fill="y")
        tk.Label(frame, text=symbol, bg=color, fg="white", font=font(10, "bold"),
                 width=2).pack(side="left", padx=(10, 0), pady=12)
        tk.Label(frame, text=message, bg=C["sidebar"], fg="white", font=font(10),
                 wraplength=360, justify="left").pack(side="left", padx=12, pady=12)
        frame.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        frame.lift()
        cls._current = frame
        root.after(duration, lambda: frame.winfo_exists() and frame.destroy())


def toast(widget, message, kind="success"):
    Toast.show(widget.winfo_toplevel(), message, kind)


class EmptyState(tk.Frame):
    def __init__(self, parent, title, message="", bg=C["card"]):
        super().__init__(parent, bg=bg)
        tk.Label(self, text="○", bg=bg, fg=C["border"], font=font(30)).pack(pady=(20, 4))
        tk.Label(self, text=title, bg=bg, fg=C["text"], font=font(12, "bold")).pack()
        if message:
            tk.Label(self, text=message, bg=bg, fg=C["text_muted"], font=font(10),
                     wraplength=420, justify="center").pack(pady=(2, 20))


class Dialog(tk.Toplevel):
    """Modal dialog with a title bar, body frame and a button row."""

    def __init__(self, parent, title, width=480, height=None):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=C["card"])
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        header = tk.Frame(self, bg=C["card"])
        header.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(header, text=title, bg=C["card"], fg=C["text"], font=font(14, "bold"),
                 anchor="w").pack(fill="x")
        self.body = tk.Frame(self, bg=C["card"])
        self.body.pack(fill="both", expand=True, padx=24, pady=6)
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", pady=(10, 0))
        self.buttons = tk.Frame(self, bg=C["card"])
        self.buttons.pack(fill="x", padx=24, pady=14)
        self.result = None
        self._width, self._height = width, height
        self.bind("<Escape>", lambda e: self.destroy())

    def add_button(self, text, command, variant="primary"):
        btn = Button(self.buttons, text, command, variant=variant)
        btn.pack(side="right", padx=(8, 0))
        return btn

    def show(self):
        """Centre over the parent window and make modal."""
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        w = max(self._width, self.winfo_reqwidth())
        h = self._height or self.winfo_reqheight()
        # never larger than the screen (small laptops are common)
        w = min(w, self.winfo_screenwidth() - 40)
        h = min(h, self.winfo_screenheight() - 90)
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + max((parent.winfo_height() - h) // 2, 20)
        x = min(max(x, 0), self.winfo_screenwidth() - w)
        y = min(max(y, 0), self.winfo_screenheight() - h - 40)
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()
        return self


class Badge(tk.Label):
    COLORS = {"Confirmed": (C["success_light"], "#047857"),
              "Cancelled": (C["danger_light"], "#B91C1C"),
              "Waiting": (C["warning_light"], "#B45309"),
              "Active": (C["success_light"], "#047857"),
              "info": (C["primary_light"], C["primary_dark"])}

    def __init__(self, parent, text, kind=None):
        bg, fg = self.COLORS.get(kind or text, self.COLORS["info"])
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font(8, "bold"), padx=8, pady=2)


def separator(parent, bg=C["border"], pady=10):
    line = tk.Frame(parent, bg=bg, height=1)
    line.pack(fill="x", pady=pady)
    return line


class ListToolbar(tk.Frame):
    """
    Search box + optional filter + "sort by" + "algorithm" drop-downs.
    The algorithm drop-down lets the user choose which of OUR sorting
    algorithms orders the table; the info label reports comparisons.
    The controls sit in a FlowFrame, so they wrap onto extra lines on small
    screens instead of being cut off.
    """

    def __init__(self, parent, on_change, sort_options, filter_label=None, filter_values=None,
                 placeholder="Search…", bg=C["card"], wrap=False):
        from algorithms.sorting import ALGORITHM_NAMES, DEFAULT_ALGORITHM
        super().__init__(parent, bg=bg)
        self.on_change = on_change
        flow = FlowFrame(self, bg=bg)
        flow.pack(fill="x")
        self.search = SearchBar(flow, placeholder, on_change=lambda _: on_change(), bg=bg,
                                width=22)
        flow.add(self.search, gap=14)
        self.filter_box = None
        if filter_values:
            self.filter_box = labeled_inline(flow, filter_label,
                                             lambda p: combo(p, filter_values, width=11), bg)
            self.filter_box.bind("<<ComboboxSelected>>", lambda e: on_change())
        self.sort_box = labeled_inline(flow, "Sort by",
                                       lambda p: combo(p, sort_options, width=21), bg)
        self.sort_box.bind("<<ComboboxSelected>>", lambda e: on_change())
        self.algo_box = labeled_inline(flow, "Algorithm",
                                       lambda p: combo(p, ALGORITHM_NAMES, width=13), bg)
        self.algo_box.set(DEFAULT_ALGORITHM)
        self.algo_box.bind("<<ComboboxSelected>>", lambda e: on_change())

    @property
    def query(self):
        return self.search.get()

    @property
    def filter(self):
        return self.filter_box.get() if self.filter_box else None

    @property
    def sort_by(self):
        return self.sort_box.get()

    @property
    def algorithm(self):
        return self.algo_box.get()


def sort_info_text(count, algorithm, stats, elapsed_ms, noun="records"):
    return (f"{count} {noun} · sorted with {algorithm}: {stats.comparisons:,} comparisons, "
            f"{stats.swaps:,} swaps/moves · {elapsed_ms:.2f} ms")
