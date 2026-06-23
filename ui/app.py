"""
ui/app.py
=========
Application entry point.

Flow
----
1. If data/config.json does not exist  →  show SetupScreen
2. After setup (or if already done)    →  show LoginScreen
3. After login                         →  show MainWindow
4. After logout                        →  back to LoginScreen

Run the full application:
    python -m ui.app
"""

from __future__ import annotations

import customtkinter as ctk

from ui.screens.setup_screen import SetupScreen, setup_complete
from ui.screens.login_screen import LoginScreen
from ui.screens.main_window  import MainWindow


def launch() -> None:
    """Start the MZz System application."""
    ctk.set_appearance_mode("dark")

    if not setup_complete():
        _run_setup()
    else:
        _run_login()


# ── Flow steps ───────────────────────────────────────────────

def _run_setup() -> None:
    app = SetupScreen(on_complete=lambda _: _run_login())
    app.mainloop()


def _run_login() -> None:
    app = LoginScreen(on_success=lambda config: _run_main(config))
    app.mainloop()


def _run_main(config: dict) -> None:
    app = MainWindow(config=config, on_logout=_run_login)
    app.mainloop()


# ── Entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    launch()
