"""
ui/screens/setup_screen.py — V2.1
===================================
شاشة الإعداد الأولي — تظهر مرة واحدة فقط بعد اختيار Workspace.
تحفظ البيانات مباشرة في Workspace/config/config.json
"""

from __future__ import annotations

import hashlib
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from ui.theme    import COLORS, FONTS, RADIUS
from src.context import WorkspaceContext


class SetupScreen(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent     : parent widget
    ctx        : WorkspaceContext
    on_complete: Callable — يُستدعى بعد حفظ الإعداد
    """

    def __init__(self, parent, ctx: WorkspaceContext,
                 on_complete: Callable) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._ctx         = ctx
        self._on_complete = on_complete
        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0)
        center.grid_columnconfigure(0, weight=1)

        # Logo
        ctk.CTkLabel(
            center, text="MZz",
            font=(FONTS["logo"][0], 52, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=0, column=0, pady=(0, 4))

        ctk.CTkLabel(
            center, text="System V2.1  —  الإعداد الأولي",
            font=FONTS["subtitle"], text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, pady=(0, 28))

        # Card
        card = ctk.CTkFrame(
            center,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS["xl"],
            border_width=1, border_color=COLORS["border"],
            width=520,
        )
        card.grid(row=2, column=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="⚙️  إعداد النظام",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=32, pady=(28, 4))

        ctk.CTkLabel(
            card,
            text="أدخل بيانات شركتك وحساب المدير. "
                 "يمكن تعديلها لاحقاً من الإعدادات.",
            font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
            wraplength=440,
        ).grid(row=1, column=0, sticky="w", padx=32, pady=(0, 20))

        # Workspace info
        ws_info = ctk.CTkFrame(
            card, fg_color=COLORS["accent_dim"],
            corner_radius=RADIUS["md"],
            border_width=1, border_color=COLORS["accent"],
        )
        ws_info.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 20))
        ctk.CTkLabel(
            ws_info,
            text=f"📂  مساحة العمل:  {self._ctx.workspace.root}",
            font=FONTS["body_sm"], text_color=COLORS["accent"], anchor="w",
        ).pack(padx=16, pady=10)

        # ── Company Name ──────────────────────────────────────
        _Label(card, "اسم الشركة *").grid(
            row=3, column=0, sticky="w", padx=32, pady=(0, 4))
        self._company_var = tk.StringVar()
        self._company_entry = _Entry(card, self._company_var,
                                     placeholder="مثال: MZz-Hub")
        self._company_entry.grid(row=4, column=0, sticky="ew",
                                 padx=32, pady=(0, 14))

        # ── Username ──────────────────────────────────────────
        _Label(card, "اسم المستخدم *").grid(
            row=5, column=0, sticky="w", padx=32, pady=(0, 4))
        self._user_var = tk.StringVar()
        self._user_entry = _Entry(card, self._user_var,
                                   placeholder="مثال: admin")
        self._user_entry.grid(row=6, column=0, sticky="ew",
                               padx=32, pady=(0, 14))

        # ── Password ──────────────────────────────────────────
        _Label(card, "كلمة المرور *  (8 أحرف على الأقل)").grid(
            row=7, column=0, sticky="w", padx=32, pady=(0, 4))
        self._pass_var = tk.StringVar()
        self._pass_entry = _Entry(card, self._pass_var,
                                   placeholder="••••••••", show="•")
        self._pass_entry.grid(row=8, column=0, sticky="ew",
                               padx=32, pady=(0, 4))

        # Password strength bar
        self._strength_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._strength_frame.grid(row=9, column=0, sticky="ew",
                                  padx=32, pady=(0, 4))
        self._strength_frame.grid_columnconfigure(0, weight=1)
        self._strength_bar = ctk.CTkProgressBar(
            self._strength_frame, height=4,
            fg_color=COLORS["surface3"],
            progress_color=COLORS["error"],
        )
        self._strength_bar.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._strength_bar.set(0)
        self._strength_lbl = ctk.CTkLabel(
            self._strength_frame, text="",
            font=FONTS["caption"], text_color=COLORS["text_dim"], anchor="w",
        )
        self._strength_lbl.grid(row=1, column=0, sticky="w")
        self._pass_var.trace_add("write", lambda *_: self._update_strength())

        # ── Confirm Password ──────────────────────────────────
        _Label(card, "تأكيد كلمة المرور *").grid(
            row=10, column=0, sticky="w", padx=32, pady=(8, 4))
        self._confirm_var = tk.StringVar()
        self._confirm_entry = _Entry(card, self._confirm_var,
                                      placeholder="••••••••", show="•")
        self._confirm_entry.grid(row=11, column=0, sticky="ew",
                                  padx=32, pady=(0, 14))
        self._confirm_entry.bind("<Return>", lambda _: self._submit())

        # ── Error Banner ──────────────────────────────────────
        self._err_lbl = ctk.CTkLabel(
            card, text="",
            font=FONTS["body_sm"], text_color=COLORS["error"],
            fg_color=COLORS["error_dim"], corner_radius=RADIUS["md"],
            height=36,
        )

        # ── Submit Button ─────────────────────────────────────
        self._submit_btn = ctk.CTkButton(
            card, text="💾  حفظ وبدء التشغيل",
            font=FONTS["btn"], height=50,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._submit,
        )
        self._submit_btn.grid(row=13, column=0, sticky="ew",
                              padx=32, pady=(4, 28))

        # Focus
        self._company_entry.focus()

    # ── Password Strength ─────────────────────────────────────

    def _update_strength(self) -> None:
        pw    = self._pass_var.get()
        score = sum([
            len(pw) >= 8,
            any(c.isupper()       for c in pw),
            any(c.isdigit()       for c in pw),
            any(c in "!@#$%^&*-_" for c in pw),
        ])
        levels = [
            (0,  0.0,  COLORS["surface3"],  ""),
            (1,  0.25, COLORS["error"],     "ضعيفة جداً"),
            (2,  0.50, COLORS["warning"],   "ضعيفة"),
            (3,  0.75, COLORS["warning"],   "متوسطة"),
            (4,  1.0,  COLORS["success"],   "قوية ✓"),
        ]
        for min_score, val, color, label in reversed(levels):
            if score >= min_score:
                self._strength_bar.configure(progress_color=color)
                self._strength_bar.set(val)
                self._strength_lbl.configure(
                    text=f"قوة كلمة المرور: {label}" if label else "",
                    text_color=color,
                )
                break

    # ── Submit ────────────────────────────────────────────────

    def _submit(self) -> None:
        self._err_lbl.grid_forget()

        company  = self._company_var.get().strip()
        username = self._user_var.get().strip()
        password = self._pass_var.get()
        confirm  = self._confirm_var.get()

        # Validate
        errors = []
        if not company:
            errors.append("اسم الشركة مطلوب")
        if not username:
            errors.append("اسم المستخدم مطلوب")
        elif len(username) < 3:
            errors.append("اسم المستخدم يجب أن يكون 3 أحرف على الأقل")
        if not password:
            errors.append("كلمة المرور مطلوبة")
        elif len(password) < 8:
            errors.append("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        elif password != confirm:
            errors.append("كلمتا المرور غير متطابقتين")

        if errors:
            self._show_error(" · ".join(errors))
            return

        # Save
        self._submit_btn.configure(state="disabled", text="⏳  جاري الحفظ...")
        try:
            pw_hash = hashlib.sha256(password.encode()).hexdigest()

            # قراءة الـ config الحالي ودمج البيانات
            config = self._ctx.config
            config.update({
                "company_name":   company,
                "admin_username": username,
                "admin_password": pw_hash,
                "setup_complete": True,
            })
            # حفظ في Workspace/config/config.json
            self._ctx.save_config(config)
            self._ctx.log(
                f"Setup completed. Company: {company}, User: {username}"
            )

            self._submit_btn.configure(
                text="✅  تم الحفظ بنجاح!",
                fg_color=COLORS["success"],
            )
            self.after(800, self._on_complete)

        except Exception as e:
            self._show_error(f"خطأ في الحفظ: {e}")
            self._submit_btn.configure(
                state="normal", text="💾  حفظ وبدء التشغيل"
            )

    def _show_error(self, msg: str) -> None:
        self._err_lbl.configure(text=f"  ✗  {msg}")
        self._err_lbl.grid(row=12, column=0, sticky="ew",
                           padx=32, pady=(0, 8))


# ── Helpers ───────────────────────────────────────────────────

class _Label(ctk.CTkLabel):
    def __init__(self, parent, text: str) -> None:
        super().__init__(
            parent, text=text,
            font=FONTS["label"],
            text_color=COLORS["text_muted"],
            anchor="w",
        )


class _Entry(ctk.CTkEntry):
    def __init__(self, parent, var: tk.StringVar,
                 placeholder: str = "", show: str = "") -> None:
        super().__init__(
            parent,
            textvariable=var,
            font=FONTS["body"],
            height=44,
            placeholder_text=placeholder,
            show=show,
            fg_color=COLORS["surface2"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        )