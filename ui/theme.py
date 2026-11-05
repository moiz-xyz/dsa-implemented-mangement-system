"""
Visual theme: fonts, colours and ttk styles shared by every screen.

We start from ttk's 'clam' theme (the most customisable built-in theme on
all platforms) and restyle it with the SMARTBUS palette, so the app does
not look like default Tkinter.
"""

import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from utils.constants import COLORS, ICON_DIR

C = COLORS
FONT_FAMILY = "TkDefaultFont"
_PREFERRED = ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Ubuntu", "Noto Sans",
              "Cantarell", "DejaVu Sans", "Liberation Sans", "Arial", "Helvetica")
MONO_FAMILY = "TkFixedFont"
_PREFERRED_MONO = ("Cascadia Mono", "Consolas", "SF Mono", "Menlo", "Ubuntu Mono",
                   "DejaVu Sans Mono", "Liberation Mono", "Courier New")

_icon_cache = {}


def font(size=10, weight="normal"):
    return (FONT_FAMILY, size, weight)


def mono(size=10, weight="normal"):
    return (MONO_FAMILY, size, weight)


def icon(name, variant=""):
    """Load assets/icons/<name><variant>.png once; returns None if missing."""
    key = f"{name}{variant}"
    if key not in _icon_cache:
        path = os.path.join(ICON_DIR, f"{key}.png")
        try:
            _icon_cache[key] = tk.PhotoImage(file=path) if os.path.exists(path) else None
        except tk.TclError:
            _icon_cache[key] = None
    return _icon_cache[key]


def setup_theme(root):
    global FONT_FAMILY, MONO_FAMILY
    available = set(tkfont.families(root))
    for family in _PREFERRED:
        if family in available:
            FONT_FAMILY = family
            break
    for family in _PREFERRED_MONO:
        if family in available:
            MONO_FAMILY = family
            break

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=FONT_FAMILY, size=10)
        except tk.TclError:
            pass

    root.configure(bg=C["background"])
    root.option_add("*Font", font(10))
    root.option_add("*TCombobox*Listbox.font", font(10))
    root.option_add("*TCombobox*Listbox.selectBackground", C["primary"])
    root.option_add("*TCombobox*Listbox.selectForeground", "white")

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=C["background"], foreground=C["text"], font=font(10),
                    bordercolor=C["border"], focuscolor=C["primary"], lightcolor=C["border"],
                    darkcolor=C["border"], troughcolor=C["background"])

    # ---- Treeview (tables)
    style.configure("Treeview", background=C["card"], fieldbackground=C["card"],
                    foreground=C["text"], rowheight=32, borderwidth=0, font=font(10),
                    relief="flat")
    style.map("Treeview", background=[("selected", C["primary_light"])],
              foreground=[("selected", C["text"])])
    style.configure("Treeview.Heading", background="#F1F5F9", foreground=C["text_muted"],
                    font=font(9, "bold"), relief="flat", borderwidth=0, padding=(10, 8))
    style.map("Treeview.Heading", background=[("active", "#E2E8F0")])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # ---- Inputs
    style.configure("TEntry", fieldbackground=C["input_bg"], foreground=C["text"],
                    bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"],
                    padding=(10, 7), insertcolor=C["text"])
    style.map("TEntry", bordercolor=[("focus", C["primary"])],
              lightcolor=[("focus", C["primary"])], darkcolor=[("focus", C["primary"])])
    style.configure("TCombobox", fieldbackground=C["input_bg"], background=C["input_bg"],
                    foreground=C["text"], bordercolor=C["border"], lightcolor=C["border"],
                    darkcolor=C["border"], arrowcolor=C["text_muted"], padding=(10, 6))
    style.map("TCombobox", fieldbackground=[("readonly", C["input_bg"])],
              selectbackground=[("readonly", C["input_bg"])],
              selectforeground=[("readonly", C["text"])],
              bordercolor=[("focus", C["primary"])])
    style.configure("TSpinbox", fieldbackground=C["input_bg"], bordercolor=C["border"],
                    arrowcolor=C["text_muted"], padding=(8, 6))

    # ---- Scrollbars
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background="#CBD5E1", troughcolor=C["card"],
                        bordercolor=C["card"], arrowcolor=C["text_muted"], gripcount=0,
                        lightcolor="#CBD5E1", darkcolor="#CBD5E1", arrowsize=12)
        style.map(f"{orient}.TScrollbar", background=[("active", "#94A3B8")])

    # ---- Notebook (tabs)
    style.configure("TNotebook", background=C["background"], borderwidth=0,
                    tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=C["background"], foreground=C["text_muted"],
                    padding=(16, 9), borderwidth=0, font=font(10, "bold"))
    style.map("TNotebook.Tab", background=[("selected", C["card"])],
              foreground=[("selected", C["primary"])],
              lightcolor=[("selected", C["card"])], bordercolor=[("selected", C["border"])])

    # ---- Misc
    style.configure("TProgressbar", background=C["primary"], troughcolor=C["primary_light"],
                    bordercolor=C["primary_light"], lightcolor=C["primary"],
                    darkcolor=C["primary"], thickness=6)
    style.configure("Seat.Horizontal.TProgressbar", thickness=8)
    style.configure("TCheckbutton", background=C["card"], foreground=C["text"])
    style.configure("TRadiobutton", background=C["card"], foreground=C["text"])
    style.configure("TScale", background=C["card"], troughcolor=C["primary_light"])
    style.configure("TPanedwindow", background=C["background"])
    return style
