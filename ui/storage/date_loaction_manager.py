"""
ui/screens/storage/data_location_manager.py — V2.1 (مصحّح)
=============================================================
مدير موقع البيانات — يستخدم WorkspaceContext والـ Workspace API
بدل المسارات المكتوبة يدوياً.

يتيح للمستخدم:
- عرض موقع الـ Workspace الحالي وحجمه
- نقل كامل الـ Workspace لمكان جديد عبر src.workspace.migrate_workspace
- التحقق من المساحة الحرة قبل النقل
- رسائل واضحة للنجاح والفشل
"""

from __future__ import annotations

import pathlib
import shutil
import threading
from typing import Callable

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

from ui.theme    import COLORS, FONTS, RADIUS
from src.context  import WorkspaceContext
from src.workspace import migrate_workspace, fmt_size, WORKSPACE_DIRS


class DataLocationManager(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent           : parent widget
    ctx              : WorkspaceContext الحالي
    on_config_change : Callable[[dict], None] — بعد نجاح النقل
    """

    def __init__(self, parent, ctx: WorkspaceContext,
                 on_config_change: Callable = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._ctx               = ctx
        self._on_config_change  = on_config_change
        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="📂  مدير موقع البيانات",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr,
            text="تحكم في مكان حفظ قاعدة البيانات والملفات والإعدادات (Workspace)",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, sticky="w")

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Section 1: Current Location ──────────────────────
        _SecTitle(scroll, "📍  الموقع الحالي (Workspace)").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )
        self._current_card = _LocationCard(scroll, self._ctx.workspace.root)
        self._current_card.grid(row=1, column=0, sticky="ew", pady=(0, 24))

        # ── Section 2: Sub-folders ───────────────────────────
        _SecTitle(scroll, "🗂️  مكونات مساحة العمل").grid(
            row=2, column=0, sticky="w", pady=(0, 12)
        )
        self._folders_frame = ctk.CTkFrame(
            scroll, fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        self._folders_frame.grid(row=3, column=0, sticky="ew", pady=(0, 24))
        self._folders_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self._render_folders()

        # ── Section 3: Move ───────────────────────────────────
        _SecTitle(scroll, "🚚  نقل مساحة العمل إلى موقع جديد").grid(
            row=4, column=0, sticky="w", pady=(0, 12)
        )

        move_card = ctk.CTkFrame(
            scroll, fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        move_card.grid(row=5, column=0, sticky="ew", pady=(0, 16))
        move_card.grid_columnconfigure(0, weight=1)

        warn = ctk.CTkFrame(
            move_card, fg_color="#2a1f00",
            corner_radius=RADIUS["md"],
            border_width=1, border_color=COLORS["warning"],
        )
        warn.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))
        ctk.CTkLabel(
            warn,
            text="⚠️  سيتم نسخ كامل مساحة العمل إلى الموقع الجديد، التحقق منها،\n"
                 "     ثم حذفها من الموقع القديم. لا يمكن التراجع عن هذه العملية.",
            font=FONTS["body_sm"], text_color=COLORS["warning"],
            justify="right", anchor="w",
        ).pack(padx=16, pady=10, anchor="w")

        picker = ctk.CTkFrame(move_card, fg_color="transparent")
        picker.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        picker.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(picker, text="المسار الجديد",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self._new_path_var = tk.StringVar()
        ctk.CTkEntry(
            picker, textvariable=self._new_path_var,
            font=FONTS["body"], height=42,
            placeholder_text="اختر مجلداً أو اكتب المسار يدوياً...",
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            picker, text="📂  تصفح",
            font=FONTS["btn_sm"], height=42, width=110,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._browse_new_path,
        ).grid(row=1, column=1)

        quick = ctk.CTkFrame(move_card, fg_color="transparent")
        quick.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))
        ctk.CTkLabel(quick, text="مواقع سريعة:",
                     font=FONTS["label"], text_color=COLORS["text_muted"],
                     ).pack(side="left", padx=(0, 10))

        home = pathlib.Path.home()
        for label, path in [
            ("🖥️  سطح المكتب", home / "Desktop"  / "MZz-Workspace"),
            ("📁  المستندات",   home / "Documents" / "MZz-Workspace"),
            ("💾  القرص D",     pathlib.Path("D:/") / "MZz-Workspace"),
        ]:
            ctk.CTkButton(
                quick, text=label,
                font=FONTS["btn_sm"], height=30, width=140,
                corner_radius=RADIUS["sm"],
                fg_color=COLORS["accent_dim"], hover_color=COLORS["surface3"],
                text_color=COLORS["accent"],
                command=lambda p=path: self._new_path_var.set(str(p)),
            ).pack(side="left", padx=(0, 6))

        self._progress = ctk.CTkProgressBar(
            move_card, fg_color=COLORS["surface2"],
            progress_color=COLORS["accent"], height=8, corner_radius=4,
        )
        self._progress.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        self._progress.set(0)

        self._status_lbl = ctk.CTkLabel(
            move_card, text="",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._status_lbl.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 12))

        btn_row = ctk.CTkFrame(move_card, fg_color="transparent")
        btn_row.grid(row=5, column=0, sticky="e", padx=20, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="🔍  تحقق من المسار",
            font=FONTS["btn_sm"], height=42, width=160,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._validate_path,
        ).pack(side="left", padx=(0, 10))

        self._move_btn = ctk.CTkButton(
            btn_row, text="🚚  نقل البيانات",
            font=FONTS["btn_sm"], height=42, width=160,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._confirm_move,
        )
        self._move_btn.pack(side="left")

        # ── Section 4: History ────────────────────────────────
        _SecTitle(scroll, "🕓  سجل مواقع البيانات").grid(
            row=6, column=0, sticky="w", pady=(8, 12)
        )
        self._history_frame = ctk.CTkFrame(
            scroll, fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        self._history_frame.grid(row=7, column=0, sticky="ew", pady=(0, 20))
        self._history_frame.grid_columnconfigure(0, weight=1)
        self._render_history()

    # ── Folders Card ──────────────────────────────────────────

    def _render_folders(self) -> None:
        for w in self._folders_frame.winfo_children():
            w.destroy()

        ws = self._ctx.workspace
        sub_folders = [
            ("🗄️", "database", ws.database_dir, "mzz.db"),
            ("📁", "uploads",  ws.uploads_dir,   ""),
            ("💾", "backups",  ws.backups_dir,   ""),
            ("📋", "logs",     ws.logs_dir,      ""),
            ("⚙️", "config",   ws.config_dir,    "config.json"),
        ]

        for col, (icon, label, path, fname) in enumerate(sub_folders):
            full   = path / fname if fname else path
            exists = full.exists() if fname else path.exists()
            size   = fmt_size(_folder_size(path)) if path.exists() else "—"

            card = ctk.CTkFrame(
                self._folders_frame, fg_color=COLORS["surface2"],
                corner_radius=RADIUS["md"], border_width=1,
                border_color=COLORS["success"] if exists else COLORS["border"],
            )
            card.grid(row=0, column=col, padx=8, pady=16, sticky="nsew")

            ctk.CTkLabel(card, text=icon, font=(FONTS["body"][0], 24),
                         text_color=COLORS["accent"]).pack(pady=(12, 4))
            ctk.CTkLabel(card, text=label, font=FONTS["label"],
                         text_color=COLORS["text"]).pack()
            ctk.CTkLabel(
                card,
                text=f"{'✅' if exists else '❌'}  {size}",
                font=FONTS["caption"],
                text_color=COLORS["success"] if exists else COLORS["error"],
            ).pack(pady=(2, 12))

    # ── Validate ──────────────────────────────────────────────

    def _browse_new_path(self) -> None:
        path = filedialog.askdirectory(title="اختر مجلد مساحة العمل الجديد")
        if path:
            self._new_path_var.set(str(pathlib.Path(path) / "MZz-Workspace"))

    def _validate_path(self) -> None:
        raw = self._new_path_var.get().strip()
        if not raw:
            self._show_status("⚠️  الرجاء اختيار مسار أولاً", COLORS["warning"])
            return

        path = pathlib.Path(raw)
        if path == self._ctx.workspace.root:
            self._show_status("⚠️  المسار المختار هو نفس الموقع الحالي", COLORS["warning"])
            return
        if not path.parent.exists():
            self._show_status(f"❌  المسار الأب غير موجود: {path.parent}", COLORS["error"])
            return

        try:
            free = shutil.disk_usage(path.parent).free
            used = _folder_size(self._ctx.workspace.root)
            if free < used * 1.1:
                self._show_status(
                    f"❌  المساحة الحرة ({fmt_size(free)}) غير كافية "
                    f"— مطلوب: {fmt_size(int(used * 1.1))}",
                    COLORS["error"],
                )
                return
            self._show_status(
                f"✅  المسار صالح  ·  مساحة متاحة: {fmt_size(free)}  "
                f"·  حجم البيانات: {fmt_size(used)}",
                COLORS["success"],
            )
        except Exception as e:
            self._show_status(f"❌  خطأ في التحقق: {e}", COLORS["error"])

    # ── Confirm & Move ────────────────────────────────────────

    def _confirm_move(self) -> None:
        raw = self._new_path_var.get().strip()
        if not raw:
            self._show_status("⚠️  الرجاء اختيار مسار الوجهة أولاً", COLORS["warning"])
            return

        new_root = pathlib.Path(raw)
        if new_root == self._ctx.workspace.root:
            self._show_status("⚠️  المسار نفسه — لا حاجة للنقل", COLORS["warning"])
            return

        dlg = _ConfirmMoveDialog(
            self,
            src=self._ctx.workspace.root,
            dst=new_root,
            size=fmt_size(_folder_size(self._ctx.workspace.root)),
        )
        self.wait_window(dlg)
        if dlg.confirmed:
            self._start_move(new_root)

    def _start_move(self, new_root: pathlib.Path) -> None:
        self._move_btn.configure(state="disabled", text="⏳  جاري النقل...")
        self._progress.set(0)
        self._show_status("⏳  جاري نقل البيانات...", COLORS["warning"])

        # مهم على Windows: أغلق ملف الـ log قبل أي نقل/حذف لمجلد logs/
        self._ctx.workspace.close_logger()

        threading.Thread(
            target=self._do_move, args=(new_root,), daemon=True
        ).start()

    def _do_move(self, new_root: pathlib.Path) -> None:
        def on_progress(val: float, msg: str) -> None:
            self._ui(lambda: [
                self._progress.set(val),
                self._show_status(msg, COLORS["warning"] if val < 1 else COLORS["success"]),
            ])

        success, message = migrate_workspace(
            self._ctx.workspace, new_root, progress_cb=on_progress
        )

        if success:
            from src.workspace import load_workspace
            new_ws = load_workspace()
            self._ctx.__init__(new_ws)   # إعادة تهيئة الـ context على الموقع الجديد

            self._ui(lambda: [
                self._current_card.update_path(new_ws.root),
                self._render_folders(),
                self._render_history(),
                self._show_status(f"✅  {message}", COLORS["success"]),
                self._move_btn.configure(state="normal", text="🚚  نقل البيانات"),
            ])
            if self._on_config_change:
                self._ui(lambda: self._on_config_change(self._ctx.config))
        else:
            self._ui(lambda: [
                self._show_status(f"❌  {message}", COLORS["error"]),
                self._move_btn.configure(state="normal", text="🚚  نقل البيانات"),
            ])

    def _ui(self, fn: Callable) -> None:
        self.after(0, fn)

    def _show_status(self, msg: str, color: str) -> None:
        self._status_lbl.configure(text=msg, text_color=color)

    # ── History ───────────────────────────────────────────────

    def _render_history(self) -> None:
        for w in self._history_frame.winfo_children():
            w.destroy()

        history = self._ctx.config.get("data_location_history", [])
        if not history:
            ctk.CTkLabel(
                self._history_frame, text="لم يتم نقل البيانات بعد",
                font=FONTS["body"], text_color=COLORS["text_dim"],
            ).grid(row=0, column=0, pady=20)
            return

        hdr = ctk.CTkFrame(self._history_frame, fg_color=COLORS["surface2"], corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure((0, 1, 2), weight=1)
        for col, txt in enumerate(["من", "إلى", "التاريخ"]):
            ctk.CTkLabel(hdr, text=txt, font=FONTS["label"],
                         text_color=COLORS["text_muted"], anchor="w",
                         ).grid(row=0, column=col, padx=16, pady=8, sticky="w")

        for i, h in enumerate(history):
            bg  = COLORS["surface"] if i % 2 == 0 else COLORS["surface2"]
            row = ctk.CTkFrame(self._history_frame, fg_color=bg, corner_radius=0)
            row.grid(row=i + 1, column=0, sticky="ew")
            row.grid_columnconfigure((0, 1, 2), weight=1)
            for col, val in enumerate([
                h.get("from", "—"), h.get("to", "—"),
                h.get("moved_at", "—")[:16],
            ]):
                ctk.CTkLabel(row, text=val, font=FONTS["body_sm"],
                             text_color=COLORS["text"], anchor="w",
                             ).grid(row=0, column=col, padx=16, pady=8, sticky="w")


# ── Helpers ───────────────────────────────────────────────────

def _folder_size(path: pathlib.Path) -> int:
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except Exception:
        pass
    return total


class _LocationCard(ctk.CTkFrame):
    def __init__(self, parent, path: pathlib.Path) -> None:
        super().__init__(
            parent, fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"], border_width=2,
            border_color=COLORS["accent"],
        )
        self.grid_columnconfigure(1, weight=1)
        self._path_var = tk.StringVar()
        self._size_var = tk.StringVar()
        self._stat_var = tk.StringVar()
        self._build()
        self.update_path(path)

    def _build(self) -> None:
        ctk.CTkLabel(self, text="📂", font=(FONTS["body"][0], 36),
                     text_color=COLORS["accent"],
                     ).grid(row=0, column=0, rowspan=3, padx=24, pady=20)

        ctk.CTkLabel(self, text="موقع مساحة العمل الحالية",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=1, sticky="w", pady=(20, 2))
        ctk.CTkLabel(self, textvariable=self._path_var,
                     font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=1, column=1, sticky="w")

        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.grid(row=2, column=1, sticky="w", pady=(4, 20))
        ctk.CTkLabel(info_row, textvariable=self._size_var,
                     font=FONTS["body_sm"], text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(info_row, text="  ·  ", font=FONTS["body_sm"],
                     text_color=COLORS["text_dim"]).pack(side="left")
        ctk.CTkLabel(info_row, textvariable=self._stat_var,
                     font=FONTS["body_sm"], text_color=COLORS["success"]).pack(side="left")

        ctk.CTkButton(
            self, text="🗂️  فتح المجلد",
            font=FONTS["btn_sm"], height=36, width=130,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"], command=self._open_folder,
        ).grid(row=0, column=2, rowspan=3, padx=20)

    def update_path(self, path: pathlib.Path) -> None:
        self._current_path = path
        self._path_var.set(str(path))
        size  = _folder_size(path)
        files = sum(1 for _ in path.rglob("*") if _.is_file()) if path.exists() else 0
        self._size_var.set(f"الحجم: {fmt_size(size)}")
        self._stat_var.set(f"✅  {files} ملف" if path.exists() else "❌  المجلد غير موجود")

    def _open_folder(self) -> None:
        import os
        try:
            os.startfile(str(self._current_path))
        except Exception:
            pass


class _ConfirmMoveDialog(ctk.CTkToplevel):
    def __init__(self, parent, src: pathlib.Path,
                 dst: pathlib.Path, size: str) -> None:
        super().__init__(parent)
        self.confirmed = False
        self.title("تأكيد نقل البيانات")
        self.geometry("520x400")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self.resizable(False, False)
        self._build(src, dst, size)

    def _build(self, src, dst, size) -> None:
        hdr = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="⚠️  تأكيد نقل البيانات",
                     font=FONTS["heading"], text_color=COLORS["warning"], anchor="w",
                     ).pack(padx=24, pady=14)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)
        body.grid_columnconfigure(1, weight=1)

        for i, (label, value, color) in enumerate([
            ("📤  من:",    str(src), COLORS["text"]),
            ("📥  إلى:",   str(dst), COLORS["accent"]),
            ("💽  الحجم:", size,     COLORS["text"]),
        ]):
            ctk.CTkLabel(body, text=label, font=FONTS["label"],
                         text_color=COLORS["text_muted"], anchor="w",
                         ).grid(row=i, column=0, sticky="w", pady=6)
            ctk.CTkLabel(body, text=value, font=FONTS["body"],
                         text_color=color, anchor="w", wraplength=300,
                         ).grid(row=i, column=1, sticky="w", padx=(12, 0), pady=6)

        warn = ctk.CTkFrame(body, fg_color="#2a1f00", corner_radius=RADIUS["md"],
                            border_width=1, border_color=COLORS["warning"])
        warn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ctk.CTkLabel(
            warn,
            text="⚠️  سيتم:\n"
                 "   1. نسخ جميع البيانات إلى الموقع الجديد\n"
                 "   2. التحقق من سلامة النسخ\n"
                 "   3. حذف البيانات من الموقع القديم\n\n"
                 "   هذه العملية لا يمكن التراجع عنها!",
            font=FONTS["body_sm"], text_color=COLORS["warning"],
            justify="right", anchor="w",
        ).pack(padx=16, pady=12, anchor="w")

        self._agree_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            body, text="أفهم وأوافق على نقل البيانات",
            variable=self._agree_var, font=FONTS["body"],
            text_color=COLORS["text"], fg_color=COLORS["accent"],
            border_color=COLORS["border"], command=self._toggle_btn,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=16)
        ctk.CTkButton(btn_row, text="❌  إلغاء", font=FONTS["btn_sm"],
                      height=42, width=130, corner_radius=RADIUS["md"],
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left")
        self._confirm_btn = ctk.CTkButton(
            btn_row, text="🚚  تأكيد النقل", font=FONTS["btn_sm"],
            height=42, width=160, corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], text_color=COLORS["text_dim"],
            state="disabled", command=self._confirm,
        )
        self._confirm_btn.pack(side="right")

    def _toggle_btn(self) -> None:
        if self._agree_var.get():
            self._confirm_btn.configure(state="normal",
                                        fg_color=COLORS["accent"],
                                        text_color=COLORS["text_inverse"])
        else:
            self._confirm_btn.configure(state="disabled",
                                        fg_color=COLORS["surface3"],
                                        text_color=COLORS["text_dim"])

    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()


class _SecTitle(ctk.CTkLabel):
    def __init__(self, parent, text: str) -> None:
        super().__init__(parent, text=text, font=FONTS["heading"],
                         text_color=COLORS["text"], anchor="w")