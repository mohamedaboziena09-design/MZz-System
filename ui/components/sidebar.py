"""
ui/components/sidebar.py
========================
Main navigation sidebar used inside MainWindow.

Items are defined as a list of (icon, label, screen_key) tuples.
The active item is highlighted; clicking calls the navigate callback.
"""

from __future__ import annotations

from typing import Callable
import customtkinter as ctk
from ui.theme import COLORS, FONTS, SIDEBAR_WIDTH, RADIUS

# Navigation items: (icon, label, screen_key)
NAV_ITEMS = [
    ("⊞",  "Dashboard",  "dashboard"),
    ("👤", "Persons",    "persons"),
    ("👥", "Employees",  "employees"),
    ("📄", "Reports",    "reports"),
    ("⚙",  "Settings",  "settings"),
]


class Sidebar(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent      : parent widget
    on_navigate : Callable[[str], None]
        Called with the screen_key when a nav item is clicked.
    on_logout   : Callable[[], None]
        Called when the Logout button is clicked.
    company_name : str
        Displayed at the top of the sidebar.
    """

    def __init__(
        self,
        parent,
        on_navigate: Callable[[str], None],
        on_logout: Callable[[], None],
        company_name: str = "MZz System",
    ) -> None:
        super().__init__(
            parent,
            width=SIDEBAR_WIDTH,
            fg_color=COLORS["sidebar_bg"],
            corner_radius=0,
        )
        self.pack_propagate(False)

        self._on_navigate  = on_navigate
        self._on_logout    = on_logout
        self._active_key   = "dashboard"
        self._buttons: dict[str, ctk.CTkButton] = {}

        self._build(company_name)

    # ──────────────────────────────────────────────────────────
    # Build
    # ──────────────────────────────────────────────────────────

    def _build(self, company_name: str) -> None:
        # ── Brand ────────────────────────────────────────────
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(24, 8))

        ctk.CTkLabel(
            brand,
            text="MZz",
            font=FONTS["heading"],
            text_color=COLORS["accent"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand,
            text=company_name,
            font=FONTS["caption"],
            text_color=COLORS["text_dim"],
            anchor="w",
            wraplength=SIDEBAR_WIDTH - 32,
        ).pack(anchor="w")

        # ── Divider ──────────────────────────────────────────
        ctk.CTkFrame(
            self, height=1, fg_color=COLORS["border"]
        ).pack(fill="x", padx=16, pady=(12, 16))

        # ── Nav items ────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8)

        for icon, label, key in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}   {label}",
                anchor="w",
                height=40,
                corner_radius=RADIUS["md"],
                fg_color="transparent",
                hover_color=COLORS["surface3"],
                text_color=COLORS["text_muted"],
                font=FONTS["body"],
                command=lambda k=key: self._click(k),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[key] = btn

        # ── Spacer ───────────────────────────────────────────
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # ── Logout ───────────────────────────────────────────
        ctk.CTkFrame(
            self, height=1, fg_color=COLORS["border"]
        ).pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            self,
            text="  ⏻   Logout",
            anchor="w",
            height=40,
            corner_radius=RADIUS["md"],
            fg_color="transparent",
            hover_color=COLORS["error_dim"],
            text_color=COLORS["text_muted"],
            font=FONTS["body"],
            command=self._on_logout,
        ).pack(fill="x", padx=8, pady=(0, 16))

    # ──────────────────────────────────────────────────────────
    # State
    # ──────────────────────────────────────────────────────────

    def _click(self, key: str) -> None:
        self.set_active(key)
        self._on_navigate(key)

    def set_active(self, key: str) -> None:
        """Highlight the active nav item."""
        # Reset previous
        if self._active_key in self._buttons:
            self._buttons[self._active_key].configure(
                fg_color="transparent",
                text_color=COLORS["text_muted"],
                font=FONTS["body"],
            )
        # Activate new
        self._active_key = key
        if key in self._buttons:
            self._buttons[key].configure(
                fg_color=COLORS["accent_dim"],
                text_color=COLORS["accent"],
                font=FONTS["body_sm"],
            )
