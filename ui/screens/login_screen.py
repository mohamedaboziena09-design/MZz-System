"""
ui/screens/login_screen.py
==========================
Login screen — validates username + password against data/config.json.
Includes "Forgot Password" flow — resets password after verifying company name.
"""

from __future__ import annotations

import hashlib
import json
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk
from ui.theme import COLORS, FONTS, RADIUS
from ui.components.field import Field
from ui.components.divider import Divider
from ui.screens.setup_screen import load_config, CONFIG_PATH


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Login Screen ─────────────────────────────────────────────

class LoginScreen(ctk.CTk):
    def __init__(self, on_success: Callable[[dict], None]) -> None:
        super().__init__()
        self._on_success = on_success
        self._config     = load_config()
        self._attempts   = 0

        ctk.set_appearance_mode("dark")
        self.title("MZz System — Login")
        self.geometry("440x560")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self._center(440, 560)
        self._build_login()

    # ──────────────────────────────────────────────────────────
    # Login View
    # ──────────────────────────────────────────────────────────

    def _build_login(self) -> None:
        self._clear()

        outer = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=40, pady=40)

        # Brand
        ctk.CTkLabel(outer, text="MZz", font=FONTS["logo"],
                     text_color=COLORS["accent"]).pack(anchor="w")
        ctk.CTkLabel(outer, text=self._config.get("company_name", "System V1"),
                     font=FONTS["subtitle"],
                     text_color=COLORS["text_muted"]).pack(anchor="w")

        Divider(outer).pack(fill="x", pady=(20, 28))

        ctk.CTkLabel(outer, text="Welcome back",
                     font=FONTS["title"], text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(outer, text="Sign in to continue.",
                     font=FONTS["body"], text_color=COLORS["text_muted"],
                     ).pack(anchor="w", pady=(4, 24))

        # Card
        card = ctk.CTkFrame(outer, fg_color=COLORS["surface"],
                             corner_radius=RADIUS["lg"],
                             border_width=1, border_color=COLORS["border"])
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=24)

        self._username = tk.StringVar()
        self._password = tk.StringVar()

        self._f_user = Field(inner, "Username", self._username,
                             placeholder="Enter your username")
        self._f_user.pack(fill="x", pady=(0, 14))

        self._f_pass = Field(inner, "Password", self._password,
                             placeholder="Enter your password", show="•")
        self._f_pass.pack(fill="x")

        # Error banner
        self._err_banner = ctk.CTkLabel(
            outer, text="", font=FONTS["body_sm"],
            text_color=COLORS["error"], fg_color=COLORS["error_dim"],
            corner_radius=RADIUS["md"], height=36,
        )

        # Sign In button
        self._btn = ctk.CTkButton(
            outer, text="Sign In  →",
            font=FONTS["btn"], height=46,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._login,
        )
        self._btn.pack(fill="x", pady=(20, 0))

        # Forgot password link
        ctk.CTkButton(
            outer,
            text="Forgot password?",
            font=FONTS["caption"],
            fg_color="transparent",
            hover_color=COLORS["surface2"],
            text_color=COLORS["text_dim"],
            height=28,
            command=self._build_reset,
        ).pack(pady=(10, 0))

        self.bind("<Return>", lambda _: self._login())
        self._f_user.focus()

    def _login(self) -> None:
        if self._btn.cget("state") == "disabled":
            return

        username = self._username.get().strip()
        password = self._password.get()

        self._f_user.clear_error()
        self._f_pass.clear_error()
        self._hide_banner()

        if not username:
            self._f_user.show_error("Username is required.")
            return
        if not password:
            self._f_pass.show_error("Password is required.")
            return

        if (username == self._config["admin_username"] and
                _hash(password) == self._config["admin_password"]):
            self._btn.configure(text="✓  Signing in…",
                                 fg_color=COLORS["success"], state="disabled")
            self.after(600, self._proceed)
        else:
            self._attempts += 1
            self._show_banner(
                f"  ✗  Incorrect username or password.  (Attempt {self._attempts})"
            )
            self._password.set("")
            self._f_pass.focus()

    def _proceed(self) -> None:
        self.destroy()
        self._on_success(self._config)

    # ──────────────────────────────────────────────────────────
    # Reset Password View
    # ──────────────────────────────────────────────────────────

    def _build_reset(self) -> None:
        self._clear()
        self.unbind("<Return>")

        outer = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=40, pady=40)

        # Brand
        ctk.CTkLabel(outer, text="MZz", font=FONTS["logo"],
                     text_color=COLORS["accent"]).pack(anchor="w")
        ctk.CTkLabel(outer, text=self._config.get("company_name", "System V1"),
                     font=FONTS["subtitle"],
                     text_color=COLORS["text_muted"]).pack(anchor="w")

        Divider(outer).pack(fill="x", pady=(20, 28))

        ctk.CTkLabel(outer, text="Reset Password",
                     font=FONTS["title"], text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(outer,
                     text="Verify your company name to set a new password.",
                     font=FONTS["body"], text_color=COLORS["text_muted"],
                     wraplength=360, justify="left",
                     ).pack(anchor="w", pady=(4, 24))

        # Card
        card = ctk.CTkFrame(outer, fg_color=COLORS["surface"],
                             corner_radius=RADIUS["lg"],
                             border_width=1, border_color=COLORS["border"])
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=24)

        self._r_company  = tk.StringVar()
        self._r_password = tk.StringVar()
        self._r_confirm  = tk.StringVar()

        self._rf_company  = Field(inner, "Company Name", self._r_company,
                                  placeholder="Enter your company name")
        self._rf_company.pack(fill="x", pady=(0, 14))

        self._rf_password = Field(inner, "New Password", self._r_password,
                                  placeholder="At least 6 characters", show="•")
        self._rf_password.pack(fill="x", pady=(0, 14))

        self._rf_confirm  = Field(inner, "Confirm New Password", self._r_confirm,
                                  placeholder="Repeat new password", show="•")
        self._rf_confirm.pack(fill="x")

        # Success / error banner
        self._reset_banner = ctk.CTkLabel(
            outer, text="", font=FONTS["body_sm"],
            text_color=COLORS["error"], fg_color=COLORS["error_dim"],
            corner_radius=RADIUS["md"], height=36,
        )

        # Reset button
        self._reset_btn = ctk.CTkButton(
            outer, text="Reset Password  →",
            font=FONTS["btn"], height=46,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._do_reset,
        )
        self._reset_btn.pack(fill="x", pady=(20, 0))

        # Back link
        ctk.CTkButton(
            outer,
            text="← Back to Login",
            font=FONTS["caption"],
            fg_color="transparent",
            hover_color=COLORS["surface2"],
            text_color=COLORS["text_dim"],
            height=28,
            command=self._build_login,
        ).pack(pady=(10, 0))

        self.bind("<Return>", lambda _: self._do_reset())
        self._rf_company.focus()

    def _do_reset(self) -> None:
        company  = self._r_company.get().strip()
        password = self._r_password.get()
        confirm  = self._r_confirm.get()

        self._rf_company.clear_error()
        self._rf_password.clear_error()
        self._rf_confirm.clear_error()
        self._reset_banner.pack_forget()

        ok = True

        # Verify company name (case-insensitive)
        if not company:
            self._rf_company.show_error("Company name is required.")
            ok = False
        elif company.lower() != self._config.get("company_name", "").lower():
            self._rf_company.show_error("Company name does not match our records.")
            ok = False

        if len(password) < 6:
            self._rf_password.show_error("Password must be at least 6 characters.")
            ok = False

        if password != confirm:
            self._rf_confirm.show_error("Passwords do not match.")
            ok = False

        if not ok:
            return

        # Save new password
        self._config["admin_password"] = _hash(password)
        CONFIG_PATH.write_text(
            json.dumps(self._config, indent=2), encoding="utf-8"
        )

        # Success feedback → back to login
        self._reset_btn.configure(
            text="✓  Password Updated",
            fg_color=COLORS["success"],
            state="disabled",
        )
        self.after(1000, self._build_login)

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    def _clear(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()

    def _show_banner(self, msg: str) -> None:
        self._err_banner.configure(text=msg)
        self._err_banner.pack(fill="x", pady=(14, 0))

    def _hide_banner(self) -> None:
        self._err_banner.pack_forget()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
