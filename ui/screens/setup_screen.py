"""
ui/screens/setup_screen.py
==========================
First-run setup wizard.
Saves  data/config.json  and calls on_complete(config) when done.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk
from ui.theme import COLORS, FONTS, RADIUS
from ui.components.field import Field
from ui.components.divider import Divider

CONFIG_PATH = pathlib.Path(__file__).parent.parent.parent / "data" / "config.json"


def setup_complete() -> bool:
    return CONFIG_PATH.exists()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class SetupScreen(ctk.CTk):
    def __init__(self, on_complete: Optional[Callable[[dict], None]] = None) -> None:
        super().__init__()
        self._on_complete = on_complete
        ctk.set_appearance_mode("dark")
        self.title("MZz System — Initial Setup")
        self.geometry("520x750")
        self.resizable(True, True)
        self.minsize(480, 700)
        self.configure(fg_color=COLORS["bg"])
        self._center(520, 750)
        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["border"],
        )
        scroll.pack(fill="both", expand=True)
        outer = ctk.CTkFrame(scroll, fg_color=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=40, pady=40)

        # Title
        ctk.CTkLabel(outer, text="MZz", font=FONTS["logo"],
                     text_color=COLORS["accent"]).pack(anchor="w")
        ctk.CTkLabel(outer, text="System V1", font=FONTS["subtitle"],
                     text_color=COLORS["text_muted"]).pack(anchor="w")

        Divider(outer).pack(fill="x", pady=(20, 28))

        ctk.CTkLabel(outer, text="Initial Setup", font=FONTS["title"],
                     text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(outer,
                     text="Configure your workspace once before you begin.",
                     font=FONTS["body"], text_color=COLORS["text_muted"]
                     ).pack(anchor="w", pady=(4, 24))

        # Card
        card = ctk.CTkFrame(outer, fg_color=COLORS["surface"],
                             corner_radius=RADIUS["lg"],
                             border_width=1, border_color=COLORS["border"])
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=24)

        self._company  = tk.StringVar()
        self._username = tk.StringVar()
        self._password = tk.StringVar()
        self._confirm  = tk.StringVar()

        self._f_company  = Field(inner, "Company Name",    self._company,
                                 placeholder="e.g. Al-Nour Corporation")
        self._f_company.pack(fill="x", pady=(0, 14))

        self._f_username = Field(inner, "Admin Username",  self._username,
                                 placeholder="e.g. admin")
        self._f_username.pack(fill="x", pady=(0, 14))

        self._f_password = Field(inner, "Password",        self._password,
                                 placeholder="At least 6 characters", show="•")
        self._f_password.pack(fill="x", pady=(0, 14))

        self._f_confirm  = Field(inner, "Confirm Password", self._confirm,
                                 placeholder="Repeat password", show="•")
        self._f_confirm.pack(fill="x")

        # Submit
        self._btn = ctk.CTkButton(
            outer, text="Complete Setup  →",
            font=FONTS["btn"], height=46,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._submit,
        )
        self._btn.pack(fill="x", pady=(20, 0))

        ctk.CTkLabel(outer,
                     text="This screen will not appear again after setup is complete.",
                     font=FONTS["caption"], text_color=COLORS["text_dim"],
                     wraplength=420, justify="left",
                     ).pack(anchor="w", pady=(10, 0))

        # Bind Enter key
        self.bind("<Return>", lambda _: self._submit())
        self._f_company.focus()

    def _submit(self) -> None:
        company  = self._company.get().strip()
        username = self._username.get().strip()
        password = self._password.get()
        confirm  = self._confirm.get()

        for f in (self._f_company, self._f_username, self._f_password, self._f_confirm):
            f.clear_error()

        ok = True
        if not company:
            self._f_company.show_error("Company name is required.")
            ok = False
        if not username:
            self._f_username.show_error("Username is required.")
            ok = False
        elif not re.match(r"^[A-Za-z0-9_]{3,32}$", username):
            self._f_username.show_error("3–32 chars: letters, numbers, underscore only.")
            ok = False
        if len(password) < 6:
            self._f_password.show_error("Password must be at least 6 characters.")
            ok = False
        if password != confirm:
            self._f_confirm.show_error("Passwords do not match.")
            ok = False
        if not ok:
            return

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "company_name":   company,
            "admin_username": username,
            "admin_password": _hash(password),
            "setup_complete": True,
        }
        CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")

        self._btn.configure(text="✓  Setup Complete",
                            fg_color=COLORS["success"], state="disabled")
        self.after(700, self._proceed, config)

    def _proceed(self, config: dict) -> None:
        self.destroy()
        if self._on_complete:
            self._on_complete(config)

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
