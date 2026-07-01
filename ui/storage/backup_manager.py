"""
ui/screens/storage/backup_manager.py — V2.1 (مصحّح)
======================================================
نظام النسخ الاحتياطي — يستخدم WorkspaceContext.
كل المسارات (db, uploads, config, backups) تُقرأ من ctx.workspace
بدل مسارات ثابتة مكتوبة يدوياً.
"""

from __future__ import annotations

import json
import pathlib
import threading
import zipfile
from datetime import datetime
from typing import Callable

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

from ui.theme    import COLORS, FONTS, RADIUS
from src.context import WorkspaceContext


class BackupManagerScreen(ctk.CTkFrame):
    def __init__(self, parent, ctx: WorkspaceContext) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._ctx      = ctx
        self._auto_job = None
        ctx.backup_dir.mkdir(parents=True, exist_ok=True)
        self._build()
        self._load_backups()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="💾  مدير النسخ الاحتياطي",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        tab = ctk.CTkTabview(
            self,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface2"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["surface2"],
            segmented_button_unselected_hover_color=COLORS["surface3"],
            text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            corner_radius=RADIUS["lg"],
        )
        tab.grid(row=1, column=0, sticky="nsew")

        tab.add("📦  نسخ احتياطي")
        tab.add("📋  سجل النسخ")
        tab.add("⚙️  جدولة تلقائية")

        self._build_backup_tab(tab.tab("📦  نسخ احتياطي"))
        self._build_list_tab(tab.tab("📋  سجل النسخ"))
        self._build_schedule_tab(tab.tab("⚙️  جدولة تلقائية"))

    # ════════════════════════════════════════════════════════
    # TAB 1: Manual Backup
    # ════════════════════════════════════════════════════════

    def _build_backup_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure((0, 1), weight=1)

        opt_card = ctk.CTkFrame(
            tab, fg_color=COLORS["surface2"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        opt_card.grid(row=0, column=0, columnspan=2,
                      sticky="ew", padx=20, pady=(20, 16))
        opt_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            opt_card, text="خيارات النسخ الاحتياطي",
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 12), sticky="w")

        self._backup_db      = tk.BooleanVar(value=True)
        self._backup_uploads = tk.BooleanVar(value=True)
        self._backup_config  = tk.BooleanVar(value=True)

        for row, (var, label, desc) in enumerate([
            (self._backup_db,      "🗄️  قاعدة البيانات", "mzz.db — كل سجلات النظام"),
            (self._backup_uploads, "📁  ملفات الرفع",     "الصور والمستندات المرفقة"),
            (self._backup_config,  "⚙️  الإعدادات",       "config.json — إعدادات النظام"),
        ], start=1):
            f = ctk.CTkFrame(opt_card, fg_color="transparent")
            f.grid(row=row, column=row % 2, sticky="ew", padx=20, pady=6)
            ctk.CTkCheckBox(
                f, text=label, variable=var,
                font=FONTS["body"], text_color=COLORS["text"],
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                border_color=COLORS["border"],
            ).pack(anchor="w")
            ctk.CTkLabel(f, text=desc, font=FONTS["caption"],
                         text_color=COLORS["text_dim"], anchor="w",
                         ).pack(anchor="w", padx=(24, 0))

        dest_frame = ctk.CTkFrame(opt_card, fg_color="transparent")
        dest_frame.grid(row=4, column=0, columnspan=2,
                        sticky="ew", padx=20, pady=(12, 16))
        dest_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dest_frame, text="مجلد الحفظ",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self._dest_var = tk.StringVar(value=str(self._ctx.backup_dir))
        ctk.CTkEntry(
            dest_frame, textvariable=self._dest_var,
            font=FONTS["body"], height=38,
            fg_color=COLORS["surface"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            dest_frame, text="📂  تصفح",
            font=FONTS["btn_sm"], height=38, width=100,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], text_color=COLORS["text"],
            command=lambda: self._browse(self._dest_var),
        ).grid(row=1, column=1)

        self._progress = ctk.CTkProgressBar(
            tab, fg_color=COLORS["surface2"],
            progress_color=COLORS["accent"], height=8, corner_radius=4,
        )
        self._progress.grid(row=1, column=0, columnspan=2,
                            sticky="ew", padx=20, pady=(0, 8))
        self._progress.set(0)

        self._backup_msg = ctk.CTkLabel(
            tab, text="جاهز للنسخ الاحتياطي",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._backup_msg.grid(row=2, column=0, sticky="w", padx=20)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e", padx=20, pady=16)

        ctk.CTkButton(
            btn_row, text="♻️  استعادة",
            font=FONTS["btn_sm"], height=42, width=130,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._restore_backup,
        ).pack(side="left", padx=(0, 10))

        self._backup_btn = ctk.CTkButton(
            btn_row, text="💾  بدء النسخ الاحتياطي",
            font=FONTS["btn_sm"], height=42, width=200,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._start_backup,
        )
        self._backup_btn.pack(side="left")

    def _browse(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory(title="اختر مجلد الحفظ")
        if path:
            var.set(path)

    def _start_backup(self) -> None:
        self._backup_btn.configure(state="disabled", text="⏳  جاري النسخ...")
        self._progress.set(0)
        self._backup_msg.configure(
            text="جاري إنشاء النسخة الاحتياطية...",
            text_color=COLORS["text_muted"],
        )
        # مهم على Windows: أغلق ملف الـ log قبل ضغط مجلد الـ Workspace
        self._ctx.workspace.close_logger()
        threading.Thread(target=self._do_backup, daemon=True).start()

    def _do_backup(self) -> None:
        try:
            ws        = self._ctx.workspace
            dest      = pathlib.Path(self._dest_var.get())
            dest.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company   = self._ctx.config.get("company_name", "MZz").replace(" ", "_")
            zip_name  = f"backup_{company}_{timestamp}.zip"
            zip_path  = dest / zip_name

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                steps = []
                if self._backup_db.get() and ws.db_path.exists():
                    steps.append(("db", ws.db_path,
                                 pathlib.Path("database") / "mzz.db"))
                if self._backup_config.get() and ws.config_path.exists():
                    steps.append(("config", ws.config_path,
                                 pathlib.Path("config") / "config.json"))
                if self._backup_uploads.get() and ws.uploads_dir.exists():
                    steps.append(("uploads", ws.uploads_dir, pathlib.Path("uploads")))

                total = len(steps) or 1
                for i, (kind, path, arc_base) in enumerate(steps):
                    self._set_progress((i / total) * 0.9)
                    if path.is_file():
                        zf.write(path, str(arc_base))
                    elif path.is_dir():
                        for f in path.rglob("*"):
                            if f.is_file():
                                zf.write(f, str(arc_base / f.relative_to(path)))

                manifest = {
                    "created_at": datetime.now().isoformat(),
                    "company":    self._ctx.config.get("company_name", ""),
                    "version":    "V2.1",
                    "workspace":  str(ws.root),
                    "includes": {
                        "database": self._backup_db.get(),
                        "uploads":  self._backup_uploads.get(),
                        "config":   self._backup_config.get(),
                    },
                }
                zf.writestr("manifest.json",
                            json.dumps(manifest, ensure_ascii=False, indent=2))

            self._set_progress(1.0)
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            self._set_msg(
                f"✅  تم الحفظ: {zip_name}  ({size_mb:.1f} MB)", COLORS["success"]
            )
            self._ctx.log(f"Backup created: {zip_name}")
            self.after(100, self._load_backups)

        except Exception as e:
            self._set_msg(f"❌  فشل النسخ الاحتياطي: {e}", COLORS["error"])
        finally:
            self.after(0, lambda: self._backup_btn.configure(
                state="normal", text="💾  بدء النسخ الاحتياطي"
            ))

    def _set_progress(self, val: float) -> None:
        self.after(0, lambda: self._progress.set(val))

    def _set_msg(self, msg: str, color: str) -> None:
        self.after(0, lambda: self._backup_msg.configure(text=msg, text_color=color))

    def _restore_backup(self) -> None:
        path = filedialog.askopenfilename(
            title="اختر ملف النسخة الاحتياطية",
            filetypes=[("ZIP Backup", "*.zip")],
            initialdir=str(self._ctx.backup_dir),
        )
        if not path:
            return
        dlg = _ConfirmDialog(
            self,
            "⚠️  تحذير!\n\nسيتم استبدال قاعدة البيانات الحالية بالنسخة المختارة.\n"
            "هل أنت متأكد؟"
        )
        self.wait_window(dlg)
        if not dlg.confirmed:
            return
        self._do_restore(pathlib.Path(path))

    def _do_restore(self, zip_path: pathlib.Path) -> None:
        ws = self._ctx.workspace
        try:
            self._backup_msg.configure(
                text="⏳  جاري الاستعادة...", text_color=COLORS["warning"]
            )
            # أغلق الـ log قبل الكتابة فوق ملفات الـ Workspace
            ws.close_logger()

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if "database/mzz.db" in names:
                    zf.extract("database/mzz.db", ws.root)
                if "config/config.json" in names:
                    zf.extract("config/config.json", ws.root)
                for name in names:
                    if name.startswith("uploads/"):
                        zf.extract(name, ws.root)

            self._ctx.log(f"Restored from backup: {zip_path.name}")
            self._backup_msg.configure(
                text="✅  تمت الاستعادة بنجاح — أعد تشغيل التطبيق",
                text_color=COLORS["success"],
            )
        except Exception as e:
            self._backup_msg.configure(
                text=f"❌  فشلت الاستعادة: {e}", text_color=COLORS["error"]
            )

    # ════════════════════════════════════════════════════════
    # TAB 2: Backup List
    # ════════════════════════════════════════════════════════

    def _build_list_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        self._list_count = ctk.CTkLabel(
            hdr, text="", font=FONTS["body_sm"],
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._list_count.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr, text="🔄  تحديث",
            font=FONTS["btn_sm"], height=34, width=100,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], text_color=COLORS["text"],
            command=self._load_backups,
        ).grid(row=0, column=1)

        self._list_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._list_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self._list_scroll.grid_columnconfigure(0, weight=1)

    def _load_backups(self) -> None:
        if not hasattr(self, "_list_scroll"):
            return
        for w in self._list_scroll.winfo_children():
            w.destroy()

        backups = sorted(
            self._ctx.backup_dir.glob("*.zip"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if hasattr(self, "_list_count"):
            self._list_count.configure(text=f"{len(backups)} نسخة احتياطية")

        if not backups:
            ctk.CTkLabel(
                self._list_scroll, text="لا توجد نسخ احتياطية بعد",
                font=FONTS["body"], text_color=COLORS["text_dim"],
            ).grid(row=0, column=0, pady=30)
            return

        for i, bak in enumerate(backups):
            _BackupRow(
                self._list_scroll, bak,
                on_restore=lambda b=bak: self._restore_specific(b),
                on_delete=lambda b=bak: self._delete_backup(b),
            ).grid(row=i, column=0, sticky="ew", pady=3)

    def _restore_specific(self, bak: pathlib.Path) -> None:
        dlg = _ConfirmDialog(
            self, f"استعادة:\n{bak.name}\n\n⚠️  سيتم استبدال البيانات الحالية!"
        )
        self.wait_window(dlg)
        if not dlg.confirmed:
            return
        try:
            self._do_restore(bak)
            _MsgDialog(self, "✅  تمت الاستعادة — أعد تشغيل التطبيق")
        except Exception as e:
            _MsgDialog(self, f"❌  فشلت الاستعادة: {e}")

    def _delete_backup(self, bak: pathlib.Path) -> None:
        dlg = _ConfirmDialog(self, f"حذف النسخة:\n{bak.name}؟")
        self.wait_window(dlg)
        if dlg.confirmed:
            bak.unlink(missing_ok=True)
            self._ctx.log(f"Backup deleted: {bak.name}")
            self._load_backups()

    # ════════════════════════════════════════════════════════
    # TAB 3: Schedule
    # ════════════════════════════════════════════════════════

    def _build_schedule_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tab, text="جدولة النسخ الاحتياطي التلقائي",
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))

        ctk.CTkLabel(
            tab,
            text="سيتم تشغيل النسخ الاحتياطي تلقائياً أثناء تشغيل التطبيق",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))

        card = ctk.CTkFrame(
            tab, fg_color=COLORS["surface2"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        card.grid(row=2, column=0, sticky="ew", padx=20)
        card.grid_columnconfigure((0, 1), weight=1)

        self._auto_enabled = tk.BooleanVar(value=False)
        ctk.CTkSwitch(
            card, text="تفعيل النسخ التلقائي", variable=self._auto_enabled,
            font=FONTS["body"], text_color=COLORS["text"],
            fg_color=COLORS["surface3"], progress_color=COLORS["accent"],
            command=self._toggle_auto,
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=16, sticky="w")

        ctk.CTkLabel(card, text="الفترة الزمنية", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=1, column=0, padx=20, pady=(0, 4), sticky="w")

        self._interval_var = tk.StringVar(value="6")
        ctk.CTkOptionMenu(
            card, variable=self._interval_var, values=["1", "3", "6", "12", "24"],
            font=FONTS["body"], height=38, width=180,
            fg_color=COLORS["surface"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"], text_color=COLORS["text"],
            corner_radius=RADIUS["md"],
        ).grid(row=2, column=0, padx=20, pady=(0, 8), sticky="w")

        ctk.CTkLabel(card, text="ساعة", font=FONTS["body_sm"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=2, column=1, padx=(0, 20), sticky="w")

        ctk.CTkLabel(card, text="الحد الأقصى للنسخ المحفوظة", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=3, column=0, padx=20, pady=(8, 4), sticky="w")

        self._max_backups = tk.StringVar(value="10")
        ctk.CTkOptionMenu(
            card, variable=self._max_backups,
            values=["5", "10", "20", "30", "unlimited"],
            font=FONTS["body"], height=38, width=180,
            fg_color=COLORS["surface"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"], text_color=COLORS["text"],
            corner_radius=RADIUS["md"],
        ).grid(row=4, column=0, padx=20, pady=(0, 20), sticky="w")

        self._auto_status = ctk.CTkLabel(
            tab, text="⏸️  النسخ التلقائي: متوقف",
            font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._auto_status.grid(row=3, column=0, sticky="w", padx=20, pady=16)

        ctk.CTkButton(
            tab, text="💾  حفظ الجدول",
            font=FONTS["btn_sm"], height=40, width=160,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._save_schedule,
        ).grid(row=4, column=0, sticky="e", padx=20)

    def _toggle_auto(self) -> None:
        if self._auto_enabled.get():
            self._auto_status.configure(
                text="✅  النسخ التلقائي: مفعّل", text_color=COLORS["success"],
            )
            self._schedule_next()
        else:
            if self._auto_job:
                self.after_cancel(self._auto_job)
                self._auto_job = None
            self._auto_status.configure(
                text="⏸️  النسخ التلقائي: متوقف", text_color=COLORS["text_muted"],
            )

    def _schedule_next(self) -> None:
        if not self._auto_enabled.get():
            return
        try:
            hours = float(self._interval_var.get())
        except ValueError:
            hours = 6
        self._auto_job = self.after(int(hours * 3600 * 1000), self._auto_backup)

    def _auto_backup(self) -> None:
        self._auto_status.configure(
            text="⏳  جاري النسخ التلقائي...", text_color=COLORS["warning"],
        )
        self._ctx.workspace.close_logger()
        threading.Thread(target=self._do_backup, daemon=True).start()
        self._cleanup_old_backups()
        self._schedule_next()

    def _cleanup_old_backups(self) -> None:
        max_val = self._max_backups.get()
        if max_val == "unlimited":
            return
        try:
            limit   = int(max_val)
            backups = sorted(
                self._ctx.backup_dir.glob("*.zip"),
                key=lambda f: f.stat().st_mtime, reverse=True,
            )
            for old in backups[limit:]:
                old.unlink(missing_ok=True)
        except Exception:
            pass

    def _save_schedule(self) -> None:
        self._auto_status.configure(
            text="✅  تم حفظ الجدول", text_color=COLORS["success"]
        )


# ── Backup Row ────────────────────────────────────────────────

class _BackupRow(ctk.CTkFrame):
    def __init__(self, parent, bak: pathlib.Path,
                 on_restore: Callable, on_delete: Callable) -> None:
        super().__init__(
            parent, fg_color=COLORS["surface"],
            corner_radius=RADIUS["md"], border_width=1, border_color=COLORS["border"],
        )
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="📦", font=(FONTS["body"][0], 24),
                     text_color=COLORS["accent"], width=50,
                     ).grid(row=0, column=0, padx=12, pady=12)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=12)

        size_mb = bak.stat().st_size / (1024 * 1024)
        mtime   = datetime.fromtimestamp(bak.stat().st_mtime).strftime("%Y-%m-%d  %H:%M")

        ctk.CTkLabel(info, text=bak.name, font=FONTS["body"],
                     text_color=COLORS["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=f"{mtime}  ·  {size_mb:.1f} MB",
                     font=FONTS["caption"], text_color=COLORS["text_dim"],
                     anchor="w").pack(anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=12, pady=12)

        ctk.CTkButton(
            btn_frame, text="♻️  استعادة", width=100, height=32,
            font=FONTS["btn_sm"], corner_radius=RADIUS["sm"],
            fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
            text_color=COLORS["accent"], command=on_restore,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="🗑", width=32, height=32,
            font=FONTS["body"], corner_radius=RADIUS["sm"],
            fg_color=COLORS["error_dim"], hover_color=COLORS["error"],
            text_color=COLORS["error"], command=on_delete,
        ).pack(side="left")

        self.bind("<Enter>", lambda _: self.configure(border_color=COLORS["accent"]))
        self.bind("<Leave>", lambda _: self.configure(border_color=COLORS["border"]))


# ── Dialogs ───────────────────────────────────────────────────

class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message: str) -> None:
        super().__init__(parent)
        self.confirmed = False
        self.title("تأكيد")
        self.geometry("400x190")
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()
        ctk.CTkLabel(self, text=message, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=340,
                     ).pack(pady=(22, 16))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        ctk.CTkButton(row, text="إلغاء", width=100, height=36,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(row, text="تأكيد", width=100, height=36,
                      fg_color=COLORS["error"], text_color=COLORS["text_inverse"],
                      command=self._ok).pack(side="left", padx=8)

    def _ok(self) -> None:
        self.confirmed = True
        self.destroy()


class _MsgDialog(ctk.CTkToplevel):
    def __init__(self, parent, msg: str) -> None:
        super().__init__(parent)
        self.title("تنبيه")
        self.geometry("380x140")
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()
        ctk.CTkLabel(self, text=msg, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=340,
                     ).pack(pady=24)
        ctk.CTkButton(self, text="حسناً", width=100, height=34,
                      fg_color=COLORS["accent"], text_color=COLORS["text_inverse"],
                      command=self.destroy).pack()