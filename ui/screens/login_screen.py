"""
ui/screens/login_screen.py — V2.1
يستخدم SessionGuard للتحقق والجلسات.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk

from ui.theme    import COLORS, FONTS, RADIUS
from src.context import WorkspaceContext
from src.session import SessionGuard, InvalidCredentials, Session


class LoginScreen(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent   : parent widget
    ctx      : WorkspaceContext
    on_login : Callable[[Session], None]
    """

    def __init__(self, parent, ctx: WorkspaceContext,
                 on_login: Callable[[Session], None]) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._ctx      = ctx
        self._on_login = on_login
        self._guard    = SessionGuard(ctx)

        self._build()
        self._check_saved_session()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0)
        center.grid_columnconfigure(0, weight=1)

        # Logo
        ctk.CTkLabel(center, text="MZz",
                     font=(FONTS["logo"][0], 52, "bold"),
                     text_color=COLORS["accent"],
                     ).grid(row=0, column=0, pady=(0, 2))

        ctk.CTkLabel(center,
                     text=f"System V2.1  ·  {self._ctx.config.get('company_name','')}",
                     font=FONTS["body"], text_color=COLORS["text_muted"],
                     ).grid(row=1, column=0, pady=(0, 32))

        # Card
        card = ctk.CTkFrame(center, fg_color=COLORS["surface"],
                            corner_radius=RADIUS["xl"],
                            border_width=1, border_color=COLORS["border"],
                            width=400)
        card.grid(row=2, column=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="تسجيل الدخول",
                     font=FONTS["title"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=0, sticky="w", padx=32, pady=(28, 20))

        # Username
        ctk.CTkLabel(card, text="اسم المستخدم",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=1, column=0, sticky="w", padx=32, pady=(0, 4))
        self._user_var = tk.StringVar()
        self._user_entry = ctk.CTkEntry(
            card, textvariable=self._user_var,
            font=FONTS["body"], height=44,
            placeholder_text="أدخل اسم المستخدم",
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        )
        self._user_entry.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 14))

        # Password
        ctk.CTkLabel(card, text="كلمة المرور",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=3, column=0, sticky="w", padx=32, pady=(0, 4))
        self._pass_var = tk.StringVar()
        self._pass_entry = ctk.CTkEntry(
            card, textvariable=self._pass_var,
            font=FONTS["body"], height=44, show="•",
            placeholder_text="••••••••",
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        )
        self._pass_entry.grid(row=4, column=0, sticky="ew", padx=32, pady=(0, 8))
        self._pass_entry.bind("<Return>", lambda _: self._submit())

        # Remember me
        self._remember_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            card, text="تذكرني", variable=self._remember_var,
            font=FONTS["body_sm"], text_color=COLORS["text_muted"],
            fg_color=COLORS["accent"], border_color=COLORS["border"],
        ).grid(row=5, column=0, sticky="w", padx=32, pady=(0, 14))

        # Error label
        self._err_lbl = ctk.CTkLabel(
            card, text="",
            font=FONTS["body_sm"], text_color=COLORS["error"],
            fg_color=COLORS["error_dim"], corner_radius=RADIUS["md"],
            height=36,
        )

        # Login button
        self._login_btn = ctk.CTkButton(
            card, text="دخول",
            font=FONTS["btn"], height=48,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._submit,
        )
        self._login_btn.grid(row=7, column=0, sticky="ew",
                             padx=32, pady=(0, 28))

        # Session info
        self._session_lbl = ctk.CTkLabel(
            card, text="",
            font=FONTS["caption"], text_color=COLORS["text_dim"],
        )
        self._session_lbl.grid(row=8, column=0, pady=(0, 16))

        # Workspace path
        ctk.CTkLabel(
            center,
            text=f"📂  {self._ctx.workspace.root}",
            font=FONTS["caption"], text_color=COLORS["text_dim"],
        ).grid(row=3, column=0, pady=(16, 0))

        self._card = card

    # ── Auto-login ────────────────────────────────────────────

    def _check_saved_session(self) -> None:
        """تحقق من وجود جلسة محفوظة وصالحة."""
        if self._guard.has_saved_session():
            session = self._guard.restore()
            remaining = session.time_remaining()
            hours = int(remaining.total_seconds() // 3600)
            mins  = int((remaining.total_seconds() % 3600) // 60)
            self._session_lbl.configure(
                text=f"🔐  جلسة نشطة — {session.username}  "
                     f"({hours}س {mins}د متبقية)",
                text_color=COLORS["success"],
            )
            self._user_var.set(session.username)
            # Auto-login بعد 1.5 ثانية
            self.after(1500, lambda: self._on_login(session))

    # ── Submit ────────────────────────────────────────────────

    def _submit(self) -> None:
        self._err_lbl.grid_forget()
        username = self._user_var.get().strip()
        password = self._pass_var.get()

        if not username or not password:
            self._show_error("أدخل اسم المستخدم وكلمة المرور")
            return

        self._login_btn.configure(state="disabled", text="⏳  جاري التحقق...")

        try:
            session = self._guard.login(
                username, password,
                remember=self._remember_var.get(),
            )
            self._login_btn.configure(
                text="✓  تم الدخول",
                fg_color=COLORS["success"],
            )
            self.after(400, lambda: self._on_login(session))

        except InvalidCredentials:
            self._show_error("اسم المستخدم أو كلمة المرور غير صحيحة")
            self._login_btn.configure(state="normal", text="دخول")
            self._pass_var.set("")
            self._pass_entry.focus()

        except Exception as e:
            self._show_error(f"خطأ: {e}")
            self._login_btn.configure(state="normal", text="دخول")

    def _show_error(self, msg: str) -> None:
        self._err_lbl.configure(text=f"  ✗  {msg}")
        self._err_lbl.grid(row=6, column=0, sticky="ew",
                           padx=32, pady=(0, 10))