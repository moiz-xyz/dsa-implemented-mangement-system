"""
Main application shell: sidebar navigation, top bar and the content area.

Pages are created lazily the first time they are opened and cached. Each
page exposes `refresh()` which reloads its data whenever it is shown.
"""

import tkinter as tk
from datetime import date

from ui import theme
from ui.components import Button, confirm, safe, show_error, toast
from ui.theme import C, font
from utils.constants import APP_NAME
from utils.helpers import initials


class MainWindow(tk.Frame):
    def __init__(self, parent, app, session, on_logout):
        super().__init__(parent, bg=C["background"])
        self.app = app
        self.session = session
        self.on_logout = on_logout
        self.pages = {}
        self.nav_items = {}
        self.current = None
        self.compact = False
        self._wide_only = []          # widgets hidden in compact (small-screen) mode

        if session.is_admin:
            from ui.admin_panel import ADMIN_PAGES as PAGES
        else:
            from ui.passenger_panel import PASSENGER_PAGES as PAGES
        self.page_specs = {key: (label, icon, factory) for key, label, icon, factory in PAGES}

        self._build_sidebar(PAGES)
        right = tk.Frame(self, bg=C["background"])
        right.pack(side="left", fill="both", expand=True)
        self._build_topbar(right)
        self.content = tk.Frame(right, bg=C["background"])
        self.content.pack(fill="both", expand=True, padx=28, pady=(8, 22))

        self.navigate(PAGES[0][0])
        self.bind("<Configure>", self._on_resize)

    # ---------------------------------------------------------- responsive
    COMPACT_BELOW = 1240      # window width (px) under which the sidebar shrinks

    def _on_resize(self, event):
        if event.widget is self:
            compact = event.width < self.COMPACT_BELOW
            if compact != self.compact:
                self.set_compact(compact)

    def set_compact(self, compact):
        """Icon-only sidebar on small screens gives the pages ~165 px more room."""
        self.compact = compact
        self.side.configure(width=72 if compact else 236)
        for widget, pack_args in self._wide_only:
            if compact:
                widget.pack_forget()
            else:
                args = dict(pack_args)
                if args.get("before", 1) is None:          # "MENU" goes back above the nav
                    args["before"] = next(iter(self.nav_items.values()))
                widget.pack(**args)
        self.logo.pack_configure(padx=16 if compact else 22)
        self.bottom.pack_configure(padx=4 if compact else 16)
        for row in list(self.nav_items.values()) + [self.logout_row]:
            icon_lbl, text_lbl = row.parts[1], row.parts[2]
            if compact:
                text_lbl.pack_forget()
                icon_lbl.pack_configure(padx=(10, 10))
            else:
                icon_lbl.pack_configure(padx=(12, 8))
                text_lbl.pack(side="left", fill="x", expand=True)
        self.content.pack_configure(padx=16 if compact else 28)
        self.topbar.pack_configure(padx=16 if compact else 28)

    # ------------------------------------------------------------- sidebar
    def _build_sidebar(self, pages):
        side = tk.Frame(self, bg=C["sidebar"], width=236)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.side = side

        logo = tk.Frame(side, bg=C["sidebar"])
        logo.pack(fill="x", padx=22, pady=(24, 26))
        self.logo = logo
        mark = tk.Label(logo, image=theme.icon("bus", "_white"), bg=C["primary"],
                        width=34, height=34)
        mark.pack(side="left")
        text = tk.Frame(logo, bg=C["sidebar"])
        text.pack(side="left", padx=10)
        self._wide_only.append((text, {"side": "left", "padx": 10}))
        tk.Label(text, text=APP_NAME, bg=C["sidebar"], fg="white",
                 font=font(14, "bold")).pack(anchor="w")
        tk.Label(text, text="Admin console" if self.session.is_admin else "Passenger portal",
                 bg=C["sidebar"], fg=C["sidebar_muted"], font=font(8)).pack(anchor="w")

        menu = tk.Label(side, text="MENU", bg=C["sidebar"], fg=C["sidebar_muted"],
                        font=font(8, "bold"), anchor="w")
        menu.pack(fill="x", padx=24, pady=(0, 6))
        self._wide_only.append((menu, {"fill": "x", "padx": 24, "pady": (0, 6),
                                       "before": None}))
        for key, label, icon_name, _ in pages:
            self.nav_items[key] = self._nav_button(side, key, label, icon_name)

        # user card at the bottom
        bottom = tk.Frame(side, bg=C["sidebar"])
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        self.bottom = bottom
        tk.Frame(bottom, bg=C["sidebar_hover"], height=1).pack(fill="x", pady=(0, 14))
        user = tk.Frame(bottom, bg=C["sidebar"])
        user.pack(fill="x")
        tk.Label(user, text=initials(self.session.display_name), bg=C["secondary"],
                 fg=C["sidebar"], font=font(10, "bold"), width=3, pady=6).pack(side="left")
        info = tk.Frame(user, bg=C["sidebar"])
        info.pack(side="left", padx=10, fill="x", expand=True)
        self._wide_only.append((info, {"side": "left", "padx": 10, "fill": "x",
                                       "expand": True}))
        tk.Label(info, text=self.session.display_name, bg=C["sidebar"], fg="white",
                 font=font(10, "bold"), anchor="w").pack(fill="x")
        tk.Label(info, text=self.session.username, bg=C["sidebar"], fg=C["sidebar_muted"],
                 font=font(8), anchor="w").pack(fill="x")
        logout = self._nav_button(bottom, "__logout", "Log out", "logout",
                                  command=self._logout)
        logout.pack_configure(pady=(12, 0), padx=0)
        self.logout_row = logout

    def _nav_button(self, parent, key, label, icon_name, command=None):
        row = tk.Frame(parent, bg=C["sidebar"], cursor="hand2")
        row.pack(fill="x", padx=8, pady=2)
        img = theme.icon(icon_name)
        icon_lbl = tk.Label(row, image=img, bg=C["sidebar"], width=22)
        icon_lbl.pack(side="left", padx=(12, 8), pady=9)
        text_lbl = tk.Label(row, text=label, bg=C["sidebar"], fg=C["sidebar_text"],
                            font=font(10), anchor="w")
        text_lbl.pack(side="left", fill="x", expand=True)
        row.parts = (row, icon_lbl, text_lbl)
        row.icon_name = icon_name
        action = command or (lambda k=key: self.navigate(k))

        def enter(_):
            if self.current != key:
                for w in row.parts:
                    w.configure(bg=C["sidebar_hover"])

        def leave(_):
            if self.current != key:
                for w in row.parts:
                    w.configure(bg=C["sidebar"])
        for w in row.parts:
            w.bind("<Button-1>", lambda e: action())
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
        return row

    def _highlight(self, key):
        for k, row in self.nav_items.items():
            active = k == key
            bg = C["sidebar_active"] if active else C["sidebar"]
            for w in row.parts:
                w.configure(bg=bg)
            row.parts[1].configure(image=theme.icon(row.icon_name, "_white" if active else ""))
            row.parts[2].configure(fg="white" if active else C["sidebar_text"],
                                   font=font(10, "bold" if active else "normal"))

    # -------------------------------------------------------------- topbar
    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=C["background"])
        bar.pack(fill="x", padx=28, pady=(18, 4))
        self.topbar = bar
        right = tk.Frame(bar, bg=C["background"])
        right.pack(side="right")
        self.crumb = tk.Label(bar, text="", bg=C["background"], fg=C["text_muted"],
                              font=font(9), anchor="w")
        self.crumb.pack(side="left")
        today = tk.Label(right, text=date.today().strftime("%A, %d %B %Y"), bg=C["background"],
                         fg=C["text_muted"], font=font(9))
        today.pack(side="left", padx=(0, 14))
        self.undo_btn = Button(right, "Undo last action", self.undo, variant="secondary",
                               icon="undo", small=True)
        self.undo_btn.pack(side="left")
        self.undo_hint = tk.Label(right, text="", bg=C["background"], fg=C["text_light"],
                                  font=font(8))
        self.undo_hint.pack(side="left", padx=(8, 0))
        self._wide_only.append((today, {"side": "left", "padx": (0, 14), "before":
                                        self.undo_btn}))
        self.refresh_undo()

    def refresh_undo(self):
        """Show how many operations are on the user's undo stack."""
        try:
            preview = self.app.bookings.undo_preview(self.session)
        except Exception:      # noqa: BLE001
            preview = []
        self.undo_btn.set_enabled(bool(preview))
        self.undo_hint.configure(text=f"{len(preview)} on stack" if preview else "stack empty")

    def undo(self):
        preview = self.app.bookings.undo_preview(self.session)
        if not preview:
            toast(self, "Nothing to undo – the stack is empty.", "info")
            return
        if not confirm(self, "Undo last action",
                       f"Undo the most recent action?\n\n{preview[0]}", danger=False):
            return
        try:
            message = self.app.bookings.undo_last(self.session)
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc, "Undo not possible")
            self.refresh_undo()
            return
        toast(self, message)
        self.refresh_all()

    # ---------------------------------------------------------- navigation
    def navigate(self, key, **kwargs):
        label, _, factory = self.page_specs[key]
        if self.current and self.current in self.pages:
            self.pages[self.current].pack_forget()
        if key not in self.pages:
            page = safe(self, factory, self.content, self)
            if page is None:
                return
            self.pages[key] = page
        page = self.pages[key]
        page.pack(fill="both", expand=True)
        self.current = key
        self._highlight(key)
        self.crumb.configure(text=f"{APP_NAME}  /  {label}")
        if hasattr(page, "on_show"):
            safe(self, page.on_show, **kwargs)
        elif hasattr(page, "refresh"):
            safe(self, page.refresh)

    def refresh_all(self):
        """Data changed: refresh the visible page; others refresh when shown."""
        self.refresh_undo()
        for message in self.app.bookings.drain_notifications():
            toast(self, message, "info")
        page = self.pages.get(self.current)
        if page is not None and hasattr(page, "refresh"):
            safe(self, page.refresh)

    def _logout(self):
        if confirm(self, "Log out", "Do you want to log out of SMARTBUS?", danger=False):
            self.on_logout()
