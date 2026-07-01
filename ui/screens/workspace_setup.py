"""
ui/screens/workspace_setup.py
===============================
شاشة اختيار الـ Workspace — تظهر مرة واحدة فقط عند أول تشغيل
أو عند فقدان الـ Workspace.

الخطوات:
    1. ترحيب + شرح المفهوم
    2. اختيار المسار
    3. تأكيد وإنشاء
"""

from __future__ import annotations

import pathlib
import shutil
from typing import Callable

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

from ui.theme import COLORS, FONTS, RADIUS
from src.workspace import (
    create_workspace, fmt_size, Workspace, WORKSPACE_DIRS
)


class WorkspaceSetupScreen(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent     : parent widget
    on_done    : Callable[[Workspace], None] — بعد إنشاء الـ Workspace
    """

    def __init__(self, parent, on_done: Callable[[Workspace], None]) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._on_done   = on_done
        self._step      = 0
        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        # Center container
        self._center = ctk.CTkFrame(self, fg_color="transparent")
        self._center.grid(row=0, column=0)
        self._center.grid_columnconfigure(0, weight=1)
        self._show_step_1()

    # ════════════════════════════════════════════════════════
    # STEP 1: Welcome & Explain
    # ════════════════════════════════════════════════════════

    def _show_step_1(self) -> None:
        self._clear()

        # Logo
        ctk.CTkLabel(
            self._center, text="MZz",
            font=(FONTS["logo"][0], 52, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=0, column=0, pady=(0, 4))

        ctk.CTkLabel(
            self._center, text="System  V2.1",
            font=FONTS["subtitle"], text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, pady=(0, 32))

        # Card
        card = ctk.CTkFrame(
            self._center,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS["xl"],
            border_width=1, border_color=COLORS["border"],
            width=560,
        )
        card.grid(row=2, column=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="📂  اختيار مساحة العمل",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=32, pady=(28, 4))

        ctk.CTkLabel(
            card,
            text="قبل البدء، نحتاج لاختيار مكان حفظ بيانات النظام.",
            font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=32, pady=(0, 24))

        # Concept explanation
        items = [
            ("🗄️", "قاعدة البيانات",  "جميع سجلات الموظفين والأشخاص والسيارات"),
            ("📁", "الملفات والصور",   "المستندات والصور المرفقة"),
            ("💾", "النسخ الاحتياطي", "نسخ احتياطية تلقائية ويدوية"),
            ("📋", "السجلات",          "سجلات نشاط النظام"),
            ("⚙️", "الإعدادات",        "إعدادات الشركة والحساب"),
        ]
        for i, (icon, title, desc) in enumerate(items):
            row_f = ctk.CTkFrame(card, fg_color=COLORS["surface2"],
                                 corner_radius=RADIUS["md"])
            row_f.grid(row=i + 2, column=0, sticky="ew",
                       padx=32, pady=3)
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row_f, text=icon,
                         font=(FONTS["body"][0], 20),
                         text_color=COLORS["accent"], width=40,
                         ).grid(row=0, column=0, padx=12, pady=10)
            ctk.CTkLabel(row_f, text=title,
                         font=FONTS["label"], text_color=COLORS["text"], anchor="w",
                         ).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(row_f, text=desc,
                         font=FONTS["caption"], text_color=COLORS["text_muted"],
                         anchor="w",
                         ).grid(row=0, column=2, sticky="e", padx=12)

        # Info box
        info = ctk.CTkFrame(card, fg_color=COLORS["accent_dim"],
                            corner_radius=RADIUS["md"],
                            border_width=1, border_color=COLORS["accent"])
        info.grid(row=8, column=0, sticky="ew", padx=32, pady=(16, 0))
        ctk.CTkLabel(
            info,
            text="💡  هذا الفصل يضمن أن تحديثات التطبيق لن تمس بياناتك أبداً.",
            font=FONTS["body_sm"], text_color=COLORS["accent"], anchor="w",
        ).pack(padx=16, pady=10)

        # Button
        ctk.CTkButton(
            card, text="التالي  →",
            font=FONTS["btn"], height=48, corner_radius=RADIUS["lg"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._show_step_2,
        ).grid(row=9, column=0, sticky="ew", padx=32, pady=(20, 28))

    # ════════════════════════════════════════════════════════
    # STEP 2: Choose Path
    # ════════════════════════════════════════════════════════

    def _show_step_2(self) -> None:
        self._clear()

        card = ctk.CTkFrame(
            self._center,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS["xl"],
            border_width=1, border_color=COLORS["border"],
            width=580,
        )
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="📍  اختر موقع مساحة العمل",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=32, pady=(28, 4))

        ctk.CTkLabel(
            card,
            text="اختر مجلداً لحفظ بيانات النظام. يمكن تغييره لاحقاً من الإعدادات.",
            font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=32, pady=(0, 20))

        # Path entry
        path_frame = ctk.CTkFrame(card, fg_color="transparent")
        path_frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 8))
        path_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(path_frame, text="مسار مساحة العمل",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self._path_var = tk.StringVar()
        self._path_entry = ctk.CTkEntry(
            path_frame, textvariable=self._path_var,
            font=FONTS["body"], height=44,
            placeholder_text="مثال: C:\\Users\\Mohamed\\Documents\\MZz-Workspace",
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        )
        self._path_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            path_frame, text="📂",
            font=FONTS["btn"], height=44, width=50,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._browse,
        ).grid(row=1, column=1)

        # Quick options
        ctk.CTkLabel(card, text="أو اختر موقعاً مقترحاً:",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=3, column=0, sticky="w", padx=32, pady=(12, 8))

        home = pathlib.Path.home()
        suggestions = [
            ("🖥️  سطح المكتب",    home / "Desktop"   / "MZz-Workspace"),
            ("📁  المستندات",      home / "Documents"  / "MZz-Workspace"),
            ("💾  D:\\MZz",        pathlib.Path("D:/") / "MZz-Workspace"),
            ("🏠  المجلد الرئيسي", home / "MZz-Workspace"),
        ]

        sug_frame = ctk.CTkFrame(card, fg_color="transparent")
        sug_frame.grid(row=4, column=0, sticky="ew", padx=32, pady=(0, 16))

        for i, (label, path) in enumerate(suggestions):
            col = i % 2
            row = i // 2
            ctk.CTkButton(
                sug_frame, text=label,
                font=FONTS["body_sm"], height=38, corner_radius=RADIUS["md"],
                fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
                text_color=COLORS["text"], border_width=1,
                border_color=COLORS["border"],
                command=lambda p=path: self._select_suggestion(p),
            ).grid(row=row, column=col, padx=(0, 6) if col == 0 else (6, 0),
                   pady=4, sticky="ew")
        sug_frame.grid_columnconfigure((0, 1), weight=1)

        # Preview card
        self._preview_card = ctk.CTkFrame(
            card, fg_color=COLORS["surface2"],
            corner_radius=RADIUS["md"],
            border_width=1, border_color=COLORS["border"],
        )
        self._preview_card.grid(row=5, column=0, sticky="ew",
                                padx=32, pady=(0, 8))
        self._preview_card.grid_columnconfigure(0, weight=1)
        self._preview_lbl = ctk.CTkLabel(
            self._preview_card,
            text="اختر مساراً لمعاينة هيكل مساحة العمل",
            font=FONTS["body_sm"], text_color=COLORS["text_dim"],
        )
        self._preview_lbl.grid(row=0, column=0, pady=16)
        self._path_var.trace_add("write", lambda *_: self._update_preview())

        # Status
        self._status_lbl = ctk.CTkLabel(
            card, text="", font=FONTS["body_sm"],
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._status_lbl.grid(row=6, column=0, sticky="w", padx=32)

        # Buttons
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=7, column=0, sticky="ew", padx=32, pady=(8, 28))
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="←  رجوع",
            font=FONTS["btn_sm"], height=44, width=110,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
            command=self._show_step_1,
        ).grid(row=0, column=0)

        self._next_btn = ctk.CTkButton(
            btn_row, text="إنشاء مساحة العمل  →",
            font=FONTS["btn"], height=44,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._show_step_3,
        )
        self._next_btn.grid(row=0, column=1, sticky="e")

    def _browse(self) -> None:
        path = filedialog.askdirectory(title="اختر مجلد مساحة العمل")
        if path:
            self._path_var.set(str(pathlib.Path(path) / "MZz-Workspace"))

    def _select_suggestion(self, path: pathlib.Path) -> None:
        self._path_var.set(str(path))

    def _update_preview(self) -> None:
        raw = self._path_var.get().strip()
        if not raw:
            self._preview_lbl.configure(
                text="اختر مساراً لمعاينة هيكل مساحة العمل",
                text_color=COLORS["text_dim"],
            )
            return

        path = pathlib.Path(raw)

        # Check free space
        try:
            parent = path if path.exists() else path.parent
            while not parent.exists() and parent != parent.parent:
                parent = parent.parent
            free = shutil.disk_usage(parent).free
            free_str = fmt_size(free)
            status_color = COLORS["success"] if free > 100 * 1024 * 1024 \
                else COLORS["warning"]
            self._status_lbl.configure(
                text=f"💽  مساحة حرة: {free_str}",
                text_color=status_color,
            )
        except Exception:
            self._status_lbl.configure(text="", text_color=COLORS["text_muted"])

        # Preview tree
        tree = f"📂  {path.name}/\n"
        for d in WORKSPACE_DIRS:
            parts = d.split("/")
            indent = "    " * len(parts)
            icon   = "📁" if len(parts) == 1 else "  └─"
            tree  += f"{indent}{icon}  {parts[-1]}/\n"

        self._preview_lbl.configure(
            text=tree.strip(),
            text_color=COLORS["text"],
            font=FONTS["code"],
            justify="left",
        )

    # ════════════════════════════════════════════════════════
    # STEP 3: Confirm & Create
    # ════════════════════════════════════════════════════════

    def _show_step_3(self) -> None:
        raw = self._path_var.get().strip()
        if not raw:
            self._status_lbl.configure(
                text="❌  الرجاء اختيار مسار أولاً",
                text_color=COLORS["error"],
            )
            return

        self._chosen_path = pathlib.Path(raw)
        self._clear()

        card = ctk.CTkFrame(
            self._center,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS["xl"],
            border_width=1, border_color=COLORS["border"],
            width=520,
        )
        card.grid(row=0, column=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="✅  تأكيد إنشاء مساحة العمل",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=32, pady=(28, 20))

        # Summary
        summary_items = [
            ("📂  المسار",    str(self._chosen_path)),
            ("🗄️  DB",        str(self._chosen_path / "database" / "mzz.db")),
            ("📁  Uploads",   str(self._chosen_path / "uploads")),
            ("💾  Backups",   str(self._chosen_path / "backups")),
            ("📋  Logs",      str(self._chosen_path / "logs")),
            ("⚙️  Config",    str(self._chosen_path / "config")),
        ]

        for i, (label, value) in enumerate(summary_items):
            bg = COLORS["surface2"] if i % 2 == 0 else COLORS["surface"]
            row_f = ctk.CTkFrame(card, fg_color=bg, corner_radius=0)
            row_f.grid(row=i + 1, column=0, sticky="ew", padx=32)
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row_f, text=label, font=FONTS["label"],
                         text_color=COLORS["text_muted"], width=120, anchor="w",
                         ).grid(row=0, column=0, padx=12, pady=9, sticky="w")
            ctk.CTkLabel(row_f, text=value, font=FONTS["body_sm"],
                         text_color=COLORS["text"], anchor="w", wraplength=320,
                         ).grid(row=0, column=1, padx=8, pady=9, sticky="w")

        # Progress
        self._prog = ctk.CTkProgressBar(
            card, fg_color=COLORS["surface2"],
            progress_color=COLORS["accent"], height=8, corner_radius=4,
        )
        self._prog.grid(row=8, column=0, sticky="ew", padx=32, pady=(16, 4))
        self._prog.set(0)

        self._create_lbl = ctk.CTkLabel(
            card, text="",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._create_lbl.grid(row=9, column=0, sticky="w", padx=32, pady=(0, 12))

        # Buttons
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=10, column=0, sticky="ew", padx=32, pady=(4, 28))
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="←  تغيير المسار",
            font=FONTS["btn_sm"], height=44, width=130,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
            command=self._show_step_2,
        ).grid(row=0, column=0)

        self._create_btn = ctk.CTkButton(
            btn_row, text="🚀  إنشاء وبدء التشغيل",
            font=FONTS["btn"], height=44,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["success"], hover_color="#27ae60",
            text_color=COLORS["text_inverse"],
            command=self._do_create,
        )
        self._create_btn.grid(row=0, column=1, sticky="e")

    def _do_create(self) -> None:
        self._create_btn.configure(state="disabled", text="⏳  جاري الإنشاء...")
        self._prog.set(0.3)
        self._create_lbl.configure(
            text="جاري إنشاء مجلدات مساحة العمل...",
            text_color=COLORS["text_muted"],
        )
        try:
            ws = create_workspace(self._chosen_path)
            self._prog.set(0.8)
            self._create_lbl.configure(
                text="جاري التحقق من المجلدات...",
            )
            ws.ensure_dirs()
            self._prog.set(1.0)
            self._create_lbl.configure(
                text="✅  تم إنشاء مساحة العمل بنجاح!",
                text_color=COLORS["success"],
            )
            ws.log("Workspace initialized successfully.")
            self.after(800, lambda: self._on_done(ws))
        except Exception as e:
            self._create_lbl.configure(
                text=f"❌  فشل الإنشاء: {e}",
                text_color=COLORS["error"],
            )
            self._create_btn.configure(
                state="normal", text="🚀  إنشاء وبدء التشغيل"
            )

    # ── Helpers ───────────────────────────────────────────────

    def _clear(self) -> None:
        for w in self._center.winfo_children():
            w.destroy()