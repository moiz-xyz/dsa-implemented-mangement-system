"""Login screen (admin / passenger) and passenger registration dialog."""

import tkinter as tk
from tkinter import ttk

from ui.components import Button, Dialog, PlaceholderEntry, labeled, show_error, toast
from ui.theme import C, font
from utils.constants import (APP_NAME, APP_TAGLINE, DEFAULT_ADMIN_PASSWORD,
                             DEFAULT_ADMIN_USERNAME, DEFAULT_PASSENGER_PASSWORD, ROLE_ADMIN,
                             ROLE_PASSENGER)


class LoginView(tk.Frame):
    def __init__(self, parent, app, on_login):
        super().__init__(parent, bg=C["background"])
        self.app = app
        self.on_login = on_login
        self.role = tk.StringVar(value=ROLE_ADMIN)

        self.grid_columnconfigure(0, weight=5, uniform="halves")
        self.grid_columnconfigure(1, weight=6, uniform="halves")
        self.grid_rowconfigure(0, weight=1)

        self._build_brand()
        self._build_form()

    # ----------------------------------------------------------- left side
    def _build_brand(self):
        panel = tk.Frame(self, bg=C["sidebar"])
        panel.grid(row=0, column=0, sticky="nsew")
        self.brand_canvas = tk.Canvas(panel, bg=C["sidebar"], highlightthickness=0)
        self.brand_canvas.pack(fill="both", expand=True)
        self.brand_canvas.bind("<Configure>", self._draw_brand)

    def _draw_brand(self, event=None):
        cv = self.brand_canvas
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        # soft decorative circles
        cv.create_oval(w - 260, -120, w + 140, 280, fill="#13203D", outline="")
        cv.create_oval(-160, h - 260, 220, h + 120, fill="#13203D", outline="")
        x0 = 56
        cv.create_text(x0, 70, text=APP_NAME, anchor="w", fill="white", font=font(30, "bold"))
        cv.create_rectangle(x0, 98, x0 + 54, 102, fill=C["secondary"], outline="")
        cv.create_text(x0, 130, text=APP_TAGLINE, anchor="w", fill=C["sidebar_text"],
                       font=font(12), width=w - 2 * x0)

        # simple bus illustration
        bx, by = x0, h * 0.36
        bw = min(w - 2 * x0, 380)
        bh = bw * 0.42
        cv.create_rectangle(bx, by + bh + 26, bx + bw, by + bh + 28, fill="#334155", outline="")
        self._round_rect(cv, bx, by, bx + bw, by + bh, 22, fill=C["primary"])
        self._round_rect(cv, bx + bw * 0.06, by + bh * 0.14, bx + bw * 0.94, by + bh * 0.5, 10,
                         fill="#93C5FD")
        for i in range(1, 5):
            xx = bx + bw * 0.06 + i * (bw * 0.88 / 5)
            cv.create_line(xx, by + bh * 0.14, xx, by + bh * 0.5, fill=C["primary"], width=4)
        cv.create_rectangle(bx, by + bh * 0.62, bx + bw, by + bh * 0.68, fill=C["secondary"],
                            outline="")
        for wx in (bx + bw * 0.22, bx + bw * 0.78):
            cv.create_oval(wx - 26, by + bh - 22, wx + 26, by + bh + 30, fill="#0B1220",
                           outline="")
            cv.create_oval(wx - 11, by + bh - 7, wx + 11, by + bh + 15, fill="#64748B",
                           outline="")

    @staticmethod
    def _round_rect(cv, x1, y1, x2, y2, r, **kw):
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
                  x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return cv.create_polygon(points, smooth=True, outline="", **kw)

    # ---------------------------------------------------------- right side
    def _build_form(self):
        holder = tk.Frame(self, bg=C["background"])
        holder.grid(row=0, column=1, sticky="nsew")
        card = tk.Frame(holder, bg=C["card"], highlightthickness=1,
                        highlightbackground=C["border"])
        card.place(relx=0.5, rely=0.5, anchor="center", width=420)
        body = tk.Frame(card, bg=C["card"])
        body.pack(fill="both", expand=True, padx=36, pady=32)

        tk.Label(body, text="Welcome back", bg=C["card"], fg=C["text"],
                 font=font(20, "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text="Sign in to manage buses, routes and reservations.",
                 bg=C["card"], fg=C["text_muted"], font=font(10), anchor="w").pack(fill="x")

        # segmented role switch
        seg = tk.Frame(body, bg="#F1F5F9", highlightthickness=1,
                       highlightbackground=C["border"])
        seg.pack(fill="x", pady=(22, 18))
        self.role_buttons = {}
        for role, text in ((ROLE_ADMIN, "Admin"), (ROLE_PASSENGER, "Passenger")):
            lbl = tk.Label(seg, text=text, font=font(10, "bold"), pady=8, cursor="hand2")
            lbl.pack(side="left", fill="x", expand=True, padx=3, pady=3)
            lbl.bind("<Button-1>", lambda e, r=role: self._set_role(r))
            self.role_buttons[role] = lbl

        self.user_field = labeled(body, "Username", lambda p: PlaceholderEntry(p, "admin"))
        self.user_field.pack(fill="x", pady=(0, 12))
        self.pass_field = labeled(body, "Password",
                                  lambda p: PlaceholderEntry(p, "••••••", show="•"))
        self.pass_field.pack(fill="x")

        self.error = tk.Label(body, text="", bg=C["card"], fg=C["danger"], font=font(9),
                              anchor="w", wraplength=340, justify="left")
        self.error.pack(fill="x", pady=(8, 4))

        Button(body, "Sign in", self._login).pack(fill="x", pady=(4, 10))
        self.register_link = tk.Label(body, text="New passenger? Create an account →",
                                      bg=C["card"], fg=C["primary"], cursor="hand2",
                                      font=font(10, "bold"))
        self.register_link.bind("<Button-1>", lambda e: RegisterDialog(self, self.app,
                                                                       self._registered))

        self.demo = tk.Label(body, text="", bg=C["primary_light"], fg=C["primary_dark"],
                             font=font(9), justify="left", anchor="w", padx=12, pady=8)
        self.demo.pack(fill="x", pady=(16, 0))

        for field in (self.user_field.widget, self.pass_field.widget):
            field.bind("<Return>", lambda e: self._login())
        self._set_role(ROLE_ADMIN)

    def _set_role(self, role):
        self.role.set(role)
        for r, lbl in self.role_buttons.items():
            active = r == role
            lbl.configure(bg=C["card"] if active else "#F1F5F9",
                          fg=C["primary"] if active else C["text_muted"])
        label = self.user_field.winfo_children()[0]
        if role == ROLE_ADMIN:
            label.configure(text="Username")
            self.register_link.pack_forget()
            self.demo.configure(text=f"Demo admin:  {DEFAULT_ADMIN_USERNAME}  /  "
                                     f"{DEFAULT_ADMIN_PASSWORD}")
        else:
            label.configure(text="Email")
            self.register_link.pack(before=self.demo)
            self.demo.configure(text=f"Demo passenger:  ali.khan@example.com  /  "
                                     f"{DEFAULT_PASSENGER_PASSWORD}")
        self.error.configure(text="")

    def _login(self):
        try:
            session = self.app.auth.login(self.user_field.widget.get(),
                                          self.pass_field.widget.get(), self.role.get())
        except Exception as exc:     # noqa: BLE001
            self.error.configure(text=str(exc))
            return
        self.on_login(session)

    def _registered(self, passenger):
        self._set_role(ROLE_PASSENGER)
        self.user_field.widget.set(passenger.email)
        self.pass_field.widget.focus_set()
        toast(self, f"Account created for {passenger.full_name}. Please sign in.")


class RegisterDialog(Dialog):
    """Self-registration for passengers (also reused by admins)."""

    def __init__(self, parent, app, on_done, title="Create passenger account"):
        super().__init__(parent, title, width=460)
        self.app = app
        self.on_done = on_done
        self.fields = {}
        for key, label, hint, show in (
                ("name", "Full name", "e.g. Ali Khan", None),
                ("email", "Email", "used to sign in", None),
                ("phone", "Phone number", "e.g. 03001234567", None),
                ("password", "Password", "at least 6 characters", "•"),
                ("confirm", "Confirm password", None, "•")):
            f = labeled(self.body, label, lambda p, s=show: ttk.Entry(p, show=s or ""),
                        hint=hint)
            f.pack(fill="x", pady=5)
            self.fields[key] = f.widget
        self.add_button("Create account", self._submit)
        self.add_button("Cancel", self.destroy, "secondary")
        self.show()
        self.fields["name"].focus_set()

    def _submit(self):
        f = {k: w.get() for k, w in self.fields.items()}
        try:
            passenger = self.app.passengers.register(f["name"], f["email"], f["phone"],
                                                     f["password"], f["confirm"])
        except Exception as exc:     # noqa: BLE001
            show_error(self, exc)
            return
        self.destroy()
        self.on_done(passenger)
