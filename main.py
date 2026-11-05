"""
SMARTBUS – Intelligent Bus Reservation & Route Management System
Entry point:  python main.py

On the first launch the SQLite database (data/smartbus.db) is created and
filled with demo data automatically.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _require_tkinter():
    import importlib.util
    if importlib.util.find_spec("tkinter") is None or importlib.util.find_spec("_tkinter") is None:
        print("Tkinter is not available for this Python installation.\n"
              "  • Ubuntu/Debian:  sudo apt install python3-tk\n"
              "  • Fedora:         sudo dnf install python3-tkinter\n"
              "  • macOS (brew):   brew install python-tk\n"
              "  • Windows:        re-run the Python installer and tick 'tcl/tk and IDLE'.")
        sys.exit(1)


class SmartBusGUI:
    """Switches between the login screen and the main application window."""

    def __init__(self, db_path=None):
        import tkinter as tk
        from services.app_context import SmartBusApp
        from ui.theme import setup_theme
        from utils.constants import APP_TITLE

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        # Small enough for 1280x720 laptops; the layout adapts below ~1240 px.
        self.root.minsize(min(960, sw - 40), min(600, sh - 80))
        w, h = min(1366, sw - 80), min(840, sh - 100)
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max((sh - h) // 2 - 20, 0)}")
        # The window keeps the size WE give it: it must never grow to fit its
        # content (that is what pushed the right edge off small screens).
        self.root.pack_propagate(False)
        self.root.grid_propagate(False)
        if sw <= 1440 or sh <= 900:          # laptop screens: start maximised
            self._maximise()
        setup_theme(self.root)
        self.app = SmartBusApp(db_path)
        self.view = None
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.show_login()

    def _maximise(self):
        try:
            if self.root.tk.call("tk", "windowingsystem") == "x11":
                self.root.attributes("-zoomed", True)
            else:                                    # Windows ("win32") and macOS
                self.root.state("zoomed")
        except Exception:      # noqa: BLE001 – not supported by this window manager
            pass

    def _swap(self, view):
        if self.view is not None:
            self.view.destroy()
        self.view = view
        self.view.pack(fill="both", expand=True)

    def show_login(self):
        from ui.login_window import LoginView
        self._swap(LoginView(self.root, self.app, on_login=self.show_main))

    def show_main(self, session):
        from ui.main_window import MainWindow
        self._swap(MainWindow(self.root, self.app, session, on_logout=self.show_login))

    def quit(self):
        self.app.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    _require_tkinter()
    SmartBusGUI().run()


if __name__ == "__main__":
    main()
