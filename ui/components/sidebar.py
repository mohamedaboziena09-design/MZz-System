"""
ui/components/sidebar.py
=========================
Sidebar navigation — updated to include Vehicles & Reports.
"""

from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from ui.theme import COLORS, FONTS, RADIUS, SIDEBAR_WIDTH

# Nav items: (key, icon, label, section_header_before)
NAV_ITEMS = [
    ("dashboard", "🏠", "لوحة التحكم",        "الرئيسية"),
    ("employees", "👔", "الموظفين",            "إدارة الأشخاص"),
    ("persons",   "👥", "العملاء والأشخاص",   None),
    ("vehicles",  "🚗", "السيارات",            "الأصول"),
    ("reports",   "📊", "التقارير",            "التقارير"),
    ("backup",    "💾", "النسخ الاحتياطي",    "التخزين — V2.1"),
    ("settings",  "⚙️", "الإعدادات",          None),
]


class Sidebar(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent       : parent widget
    on_navigate  : Callable[[str], None]
    on_logout    : Callable
    company_name : str
    """

    def __init__(
        self,
        parent,
        on_navigate:  Callable[[str], None],
        on_logout:    Callable,
        company_name: str = "MZz System",
    ) -> None:
        super().__init__(
            parent,
            width=SIDEBAR_WIDTH,
            fg_color=COLORS["sidebar_bg"],
            corner_radius=0,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._on_navigate  = on_navigate
        self._on_logout    = on_logout
        self._company_name = company_name
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active_key: str = ""

        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Logo ────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(
            self, fg_color=COLORS["surface"],
            corner_radius=0, height=64,
        )
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(
            logo_frame,
            text="MZz",
            font=FONTS["title"],
            text_color=COLORS["accent"],
            anchor="w",
        ).pack(side="left", padx=(20, 4), pady=16)

        ctk.CTkLabel(
            logo_frame,
            text="System",
            font=FONTS["subtitle"],
            text_color=COLORS["text_muted"],
            anchor="w",
        ).pack(side="left", pady=16)

        # Bottom border under logo
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"],
                     corner_radius=0).pack(fill="x")

        # ── Company name ─────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=self._company_name,
            font=FONTS["body_sm"],
            text_color=COLORS["text_dim"],
            anchor="w",
        ).pack(fill="x", padx=20, pady=(10, 4))

        # ── Nav items ────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        nav_frame.pack(fill="both", expand=True, pady=(4, 0))

        last_section = None
        for key, icon, label, section in NAV_ITEMS:
            # Section header
            if section and section != last_section:
                ctk.CTkLabel(
                    nav_frame,
                    text=section.upper(),
                    font=FONTS["caption"],
                    text_color=COLORS["text_dim"],
                    anchor="w",
                ).pack(fill="x", padx=20, pady=(14, 2))
                last_section = section

            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}  {label}",
                font=FONTS["body"],
                anchor="w",
                height=40,
                corner_radius=RADIUS["md"],
                fg_color="transparent",
                hover_color=COLORS["sidebar_item"],
                text_color=COLORS["text_muted"],
                border_width=0,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", padx=10, pady=1)
            self._buttons[key] = btn

        # ── Bottom: version + logout ─────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        bottom.pack(fill="x", side="bottom", padx=10, pady=12)

        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"],
                     corner_radius=0).pack(fill="x", side="bottom")

        ctk.CTkButton(
            bottom,
            text="  🚪  تسجيل الخروج",
            font=FONTS["body"],
            anchor="w",
            height=40,
            corner_radius=RADIUS["md"],
            fg_color="transparent",
            hover_color=COLORS["error_dim"],
            text_color=COLORS["text_muted"],
            command=self._on_logout,
        ).pack(fill="x")

        ctk.CTkLabel(
            bottom,
            text="MZz System  V1.2",
            font=FONTS["caption"],
            text_color=COLORS["text_dim"],
            anchor="w",
        ).pack(fill="x", padx=8, pady=(6, 0))

    # ── Navigation ────────────────────────────────────────────

    def _navigate(self, key: str) -> None:
        self.set_active(key)
        self._on_navigate(key)

    def set_active(self, key: str) -> None:
        """Highlight the active nav item."""
        if self._active_key and self._active_key in self._buttons:
            self._buttons[self._active_key].configure(
                fg_color="transparent",
                text_color=COLORS["text_muted"],
            )
        self._active_key = key
        if key in self._buttons:
            self._buttons[key].configure(
                fg_color=COLORS["accent_dim"],
                text_color=COLORS["accent"],
            )