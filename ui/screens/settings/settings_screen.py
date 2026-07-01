"""
ui/screens/settings/settings_screen.py
========================================
شاشة الإعدادات الكاملة — V2.1
تشمل:
- إعدادات الشركة
- إعدادات الحساب (تغيير كلمة السر)
- إعدادات التخزين والمسارات
- معلومات النظام
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
from typing import Any

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

from ui.theme import COLORS, FONTS, RADIUS

CONFIG_PATH = pathlib.Path(__file__).parent.parent.parent.parent / "data" / "config.json"
UPLOAD_DIR  = pathlib.Path(__file__).parent.parent.parent.parent / "uploads"


class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, config: dict, on_config_change: callable = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._config = dict(config)
        self._on_config_change = on_config_change
        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="⚙️  الإعدادات",
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

        tab.add("🏢  الشركة")
        tab.add("🔐  الحساب")
        tab.add("💾  التخزين")
        tab.add("ℹ️  النظام")

        self._build_company_tab(tab.tab("🏢  الشركة"))
        self._build_account_tab(tab.tab("🔐  الحساب"))
        self._build_storage_tab(tab.tab("💾  التخزين"))
        self._build_system_tab(tab.tab("ℹ️  النظام"))

    # ════════════════════════════════════════════════════════
    # TAB 1: Company
    # ════════════════════════════════════════════════════════

    def _build_company_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure((0, 1), weight=1)

        _SecLabel(tab, "بيانات الشركة").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 12)
        )

        self._company_name = tk.StringVar(value=self._config.get("company_name", ""))
        _SettingField(tab, "اسم الشركة *", self._company_name,
                      placeholder="مثال: MZz-Hub").grid(
            row=1, column=0, sticky="ew", padx=(20, 10), pady=(0, 12)
        )

        self._company_phone = tk.StringVar(value=self._config.get("company_phone", ""))
        _SettingField(tab, "هاتف الشركة", self._company_phone,
                      placeholder="مثال: +966501234567").grid(
            row=1, column=1, sticky="ew", padx=(10, 20), pady=(0, 12)
        )

        self._company_email = tk.StringVar(value=self._config.get("company_email", ""))
        _SettingField(tab, "البريد الإلكتروني", self._company_email,
                      placeholder="مثال: info@company.com").grid(
            row=2, column=0, sticky="ew", padx=(20, 10), pady=(0, 12)
        )

        self._company_address = tk.StringVar(value=self._config.get("company_address", ""))
        _SettingField(tab, "العنوان", self._company_address,
                      placeholder="مثال: الرياض، المملكة العربية السعودية").grid(
            row=2, column=1, sticky="ew", padx=(10, 20), pady=(0, 12)
        )

        # Divider
        ctk.CTkFrame(tab, height=1, fg_color=COLORS["border"]).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=16
        )

        _SecLabel(tab, "إعدادات العرض").grid(
            row=4, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12)
        )

        self._theme_var = tk.StringVar(value=self._config.get("theme", "dark"))
        _DropdownField(tab, "مظهر التطبيق", self._theme_var,
                       ["dark", "light", "system"]).grid(
            row=5, column=0, sticky="ew", padx=(20, 10), pady=(0, 12)
        )

        self._lang_var = tk.StringVar(value=self._config.get("language", "ar"))
        _DropdownField(tab, "اللغة", self._lang_var, ["ar", "en"]).grid(
            row=5, column=1, sticky="ew", padx=(10, 20), pady=(0, 12)
        )

        # Error / success
        self._company_msg = ctk.CTkLabel(
            tab, text="", font=FONTS["body_sm"], anchor="w"
        )
        self._company_msg.grid(row=6, column=0, columnspan=2, sticky="w", padx=20)

        # Save button
        ctk.CTkButton(
            tab, text="💾  حفظ إعدادات الشركة",
            font=FONTS["btn_sm"], height=40, width=200,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._save_company,
        ).grid(row=7, column=0, columnspan=2, sticky="e", padx=20, pady=16)

    def _save_company(self) -> None:
        name = self._company_name.get().strip()
        if not name:
            self._company_msg.configure(
                text="❌  اسم الشركة مطلوب", text_color=COLORS["error"]
            )
            return
        self._config.update({
            "company_name":    name,
            "company_phone":   self._company_phone.get().strip(),
            "company_email":   self._company_email.get().strip(),
            "company_address": self._company_address.get().strip(),
            "theme":           self._theme_var.get(),
            "language":        self._lang_var.get(),
        })
        self._write_config()
        self._company_msg.configure(
            text="✅  تم الحفظ بنجاح", text_color=COLORS["success"]
        )
        if self._on_config_change:
            self._on_config_change(self._config)

    # ════════════════════════════════════════════════════════
    # TAB 2: Account
    # ════════════════════════════════════════════════════════

    def _build_account_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure((0, 1), weight=1)

        _SecLabel(tab, "بيانات المستخدم").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 12)
        )

        # Username (display only)
        user_frame = ctk.CTkFrame(tab, fg_color="transparent")
        user_frame.grid(row=1, column=0, sticky="ew", padx=(20, 10), pady=(0, 12))
        ctk.CTkLabel(user_frame, text="اسم المستخدم الحالي",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            user_frame,
            text=f"  👤  {self._config.get('admin_username', '—')}",
            font=FONTS["body"], text_color=COLORS["text"],
            fg_color=COLORS["surface2"], corner_radius=RADIUS["md"],
            height=40, anchor="w",
        ).pack(fill="x")

        # New username
        self._new_username = tk.StringVar()
        _SettingField(tab, "اسم المستخدم الجديد", self._new_username,
                      placeholder="اتركه فارغاً للإبقاء على الحالي").grid(
            row=1, column=1, sticky="ew", padx=(10, 20), pady=(0, 12)
        )

        ctk.CTkFrame(tab, height=1, fg_color=COLORS["border"]).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=12
        )

        _SecLabel(tab, "تغيير كلمة المرور").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12)
        )

        self._old_pass    = tk.StringVar()
        self._new_pass    = tk.StringVar()
        self._confirm_pass = tk.StringVar()

        _SettingField(tab, "كلمة المرور الحالية *", self._old_pass,
                      show="•").grid(
            row=4, column=0, sticky="ew", padx=(20, 10), pady=(0, 12)
        )
        _SettingField(tab, "كلمة المرور الجديدة *", self._new_pass,
                      show="•", placeholder="8 أحرف على الأقل").grid(
            row=4, column=1, sticky="ew", padx=(10, 20), pady=(0, 12)
        )
        _SettingField(tab, "تأكيد كلمة المرور *", self._confirm_pass,
                      show="•").grid(
            row=5, column=0, sticky="ew", padx=(20, 10), pady=(0, 12)
        )

        # Password strength
        self._pass_strength = ctk.CTkLabel(
            tab, text="", font=FONTS["body_sm"], anchor="w"
        )
        self._pass_strength.grid(row=5, column=1, sticky="w", padx=(10, 20))
        self._new_pass.trace_add("write", lambda *_: self._check_strength())

        self._account_msg = ctk.CTkLabel(
            tab, text="", font=FONTS["body_sm"], anchor="w"
        )
        self._account_msg.grid(row=6, column=0, columnspan=2, sticky="w", padx=20)

        ctk.CTkButton(
            tab, text="🔐  حفظ بيانات الحساب",
            font=FONTS["btn_sm"], height=40, width=200,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._save_account,
        ).grid(row=7, column=0, columnspan=2, sticky="e", padx=20, pady=16)

    def _check_strength(self) -> None:
        pw = self._new_pass.get()
        if not pw:
            self._pass_strength.configure(text="")
            return
        score = sum([
            len(pw) >= 8,
            any(c.isupper() for c in pw),
            any(c.isdigit() for c in pw),
            any(c in "!@#$%^&*" for c in pw),
        ])
        levels = [
            (1, "ضعيفة جداً",  COLORS["error"]),
            (2, "ضعيفة",       COLORS["error"]),
            (3, "متوسطة",      COLORS["warning"]),
            (4, "قوية",        COLORS["success"]),
        ]
        for s, label, color in levels:
            if score <= s:
                self._pass_strength.configure(
                    text=f"قوة كلمة المرور: {label}", text_color=color
                )
                return

    def _save_account(self) -> None:
        self._account_msg.configure(text="")
        old  = self._old_pass.get()
        new  = self._new_pass.get()
        conf = self._confirm_pass.get()
        new_user = self._new_username.get().strip()

        # تحقق كلمة المرور الحالية
        old_hash = hashlib.sha256(old.encode()).hexdigest()
        if old_hash != self._config.get("admin_password", ""):
            self._account_msg.configure(
                text="❌  كلمة المرور الحالية غير صحيحة",
                text_color=COLORS["error"]
            )
            return

        if new:
            if len(new) < 8:
                self._account_msg.configure(
                    text="❌  كلمة المرور يجب أن تكون 8 أحرف على الأقل",
                    text_color=COLORS["error"]
                )
                return
            if new != conf:
                self._account_msg.configure(
                    text="❌  كلمتا المرور غير متطابقتين",
                    text_color=COLORS["error"]
                )
                return
            self._config["admin_password"] = hashlib.sha256(new.encode()).hexdigest()

        if new_user:
            self._config["admin_username"] = new_user

        self._write_config()
        self._account_msg.configure(
            text="✅  تم تحديث بيانات الحساب بنجاح",
            text_color=COLORS["success"]
        )
        self._old_pass.set("")
        self._new_pass.set("")
        self._confirm_pass.set("")
        self._new_username.set("")

    # ════════════════════════════════════════════════════════
    # TAB 3: Storage
    # ════════════════════════════════════════════════════════

    def _build_storage_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)

        _SecLabel(tab, "مسارات التخزين").grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 12)
        )

        # Upload dir
        upl_frame = ctk.CTkFrame(tab, fg_color="transparent")
        upl_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        upl_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(upl_frame, text="مجلد الرفع (Uploads)",
                     font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self._upload_path_var = tk.StringVar(
            value=self._config.get("upload_dir", str(UPLOAD_DIR))
        )
        ctk.CTkEntry(
            upl_frame, textvariable=self._upload_path_var,
            font=FONTS["body"], height=40,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            upl_frame, text="📂  تصفح",
            font=FONTS["btn_sm"], height=40, width=100,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=lambda: self._browse_dir(self._upload_path_var),
        ).grid(row=1, column=1)

        # Storage stats
        ctk.CTkFrame(tab, height=1, fg_color=COLORS["border"]).grid(
            row=2, column=0, sticky="ew", padx=20, pady=16
        )

        _SecLabel(tab, "إحصائيات التخزين").grid(
            row=3, column=0, sticky="w", padx=20, pady=(0, 12)
        )

        stats_frame = ctk.CTkFrame(
            tab, fg_color=COLORS["surface2"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        stats_frame.grid(row=4, column=0, sticky="ew", padx=20)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        stats = self._calc_storage_stats()
        for col, (icon, label, value) in enumerate(stats):
            f = ctk.CTkFrame(stats_frame, fg_color="transparent")
            f.grid(row=0, column=col, padx=16, pady=16, sticky="w")
            ctk.CTkLabel(f, text=icon, font=(FONTS["body"][0], 24),
                         text_color=COLORS["accent"]).pack(anchor="w")
            ctk.CTkLabel(f, text=label, font=FONTS["caption"],
                         text_color=COLORS["text_muted"]).pack(anchor="w", pady=(4, 0))
            ctk.CTkLabel(f, text=value, font=FONTS["heading"],
                         text_color=COLORS["text"]).pack(anchor="w")

        # Clean orphaned files
        ctk.CTkFrame(tab, height=1, fg_color=COLORS["border"]).grid(
            row=5, column=0, sticky="ew", padx=20, pady=16
        )

        self._storage_msg = ctk.CTkLabel(
            tab, text="", font=FONTS["body_sm"], anchor="w"
        )
        self._storage_msg.grid(row=6, column=0, sticky="w", padx=20)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=7, column=0, sticky="e", padx=20, pady=16)

        ctk.CTkButton(
            btn_row, text="🧹  تنظيف الملفات المجهولة",
            font=FONTS["btn_sm"], height=40, width=200,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._clean_orphaned,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="💾  حفظ مسار التخزين",
            font=FONTS["btn_sm"], height=40, width=180,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._save_storage,
        ).pack(side="left")

    def _calc_storage_stats(self) -> list:
        try:
            total_size = 0
            total_files = 0
            for root, dirs, files in os.walk(UPLOAD_DIR):
                for f in files:
                    fp = os.path.join(root, f)
                    total_size  += os.path.getsize(fp)
                    total_files += 1
            size_mb = total_size / (1024 * 1024)

            photos = sum(
                1 for root, _, files in os.walk(UPLOAD_DIR / "photos")
                for _ in files
            ) if (UPLOAD_DIR / "photos").exists() else 0

            docs = sum(
                1 for root, _, files in os.walk(UPLOAD_DIR / "documents")
                for _ in files
            ) if (UPLOAD_DIR / "documents").exists() else 0

        except Exception:
            total_files = docs = photos = 0
            size_mb = 0

        return [
            ("📦", "إجمالي الملفات",  str(total_files)),
            ("📄", "المستندات",        str(docs)),
            ("🖼️", "الصور",           str(photos)),
            ("💽", "الحجم الكلي",     f"{size_mb:.1f} MB"),
        ]

    def _browse_dir(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory(title="اختر مجلداً")
        if path:
            var.set(path)

    def _save_storage(self) -> None:
        self._config["upload_dir"] = self._upload_path_var.get().strip()
        self._write_config()
        self._storage_msg.configure(
            text="✅  تم حفظ مسار التخزين", text_color=COLORS["success"]
        )

    def _clean_orphaned(self) -> None:
        """حذف الملفات التي ليس لها سجل في قاعدة البيانات."""
        try:
            from src.crud_service import CRUDService
            with CRUDService() as svc:
                db_paths = set()
                for row in svc.conn.execute(
                    "SELECT file_path FROM documents"
                ).fetchall():
                    db_paths.add(row[0])
                for row in svc.conn.execute(
                    "SELECT file_path FROM person_documents"
                ).fetchall():
                    db_paths.add(row[0])
                for row in svc.conn.execute(
                    "SELECT photo_path FROM employees WHERE photo_path IS NOT NULL"
                ).fetchall():
                    db_paths.add(row[0])
                for row in svc.conn.execute(
                    "SELECT photo_path FROM persons WHERE photo_path IS NOT NULL"
                ).fetchall():
                    db_paths.add(row[0])

            removed = 0
            for root, _, files in os.walk(UPLOAD_DIR):
                for fname in files:
                    full = pathlib.Path(root) / fname
                    rel  = str(full)
                    if rel not in db_paths and full.suffix.lower() not in [".db", ".json"]:
                        full.unlink(missing_ok=True)
                        removed += 1

            self._storage_msg.configure(
                text=f"✅  تم حذف {removed} ملف غير مرتبط",
                text_color=COLORS["success"],
            )
        except Exception as e:
            self._storage_msg.configure(
                text=f"❌  خطأ: {e}", text_color=COLORS["error"]
            )

    # ════════════════════════════════════════════════════════
    # TAB 4: System Info
    # ════════════════════════════════════════════════════════

    def _build_system_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)

        import sys, platform

        # DB path & size
        db_path = pathlib.Path(__file__).parent.parent.parent.parent / "data" / "mzz.db"
        db_size = f"{db_path.stat().st_size / 1024:.1f} KB" if db_path.exists() else "—"

        info_items = [
            ("🖥️",  "نظام التشغيل",      platform.system() + " " + platform.release()),
            ("🐍",  "إصدار Python",       sys.version.split()[0]),
            ("📦",  "إصدار التطبيق",      "V2.1 Storage Manager"),
            ("🗄️",  "قاعدة البيانات",     "SQLite"),
            ("📂",  "مسار DB",            str(db_path)),
            ("💽",  "حجم DB",             db_size),
            ("📁",  "مجلد التطبيق",       str(pathlib.Path(__file__).parent.parent.parent.parent)),
            ("🔑",  "المستخدم",           self._config.get("admin_username", "—")),
            ("🏢",  "الشركة",             self._config.get("company_name", "—")),
        ]

        _SecLabel(tab, "معلومات النظام").grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 12)
        )

        info_card = ctk.CTkFrame(
            tab, fg_color=COLORS["surface2"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        info_card.grid(row=1, column=0, sticky="ew", padx=20)
        info_card.grid_columnconfigure(1, weight=1)

        for i, (icon, label, value) in enumerate(info_items):
            bg = COLORS["surface2"] if i % 2 == 0 else COLORS["surface"]
            row_f = ctk.CTkFrame(info_card, fg_color=bg, corner_radius=0)
            row_f.grid(row=i, column=0, columnspan=2, sticky="ew")
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row_f, text=f"  {icon}  {label}",
                         font=FONTS["body_sm"], text_color=COLORS["text_muted"],
                         anchor="w", width=200,
                         ).grid(row=0, column=0, padx=16, pady=10, sticky="w")
            ctk.CTkLabel(row_f, text=value,
                         font=FONTS["body_sm"], text_color=COLORS["text"],
                         anchor="w",
                         ).grid(row=0, column=1, padx=16, pady=10, sticky="w")

        # Reset button
        ctk.CTkFrame(tab, height=1, fg_color=COLORS["border"]).grid(
            row=2, column=0, sticky="ew", padx=20, pady=20
        )

        self._sys_msg = ctk.CTkLabel(
            tab, text="", font=FONTS["body_sm"], anchor="w"
        )
        self._sys_msg.grid(row=3, column=0, sticky="w", padx=20)

        ctk.CTkButton(
            tab, text="⚠️  إعادة تعيين الإعدادات",
            font=FONTS["btn_sm"], height=40, width=200,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["error_dim"], hover_color=COLORS["error"],
            text_color=COLORS["error"],
            command=self._confirm_reset,
        ).grid(row=4, column=0, sticky="e", padx=20, pady=(8, 20))

    def _confirm_reset(self) -> None:
        dlg = _ConfirmDialog(self, "هل تريد إعادة تعيين جميع الإعدادات؟\nلن يتم حذف البيانات.")
        self.wait_window(dlg)
        if dlg.confirmed:
            self._config = {
                "company_name":   self._config.get("company_name", ""),
                "admin_username": self._config.get("admin_username", ""),
                "admin_password": self._config.get("admin_password", ""),
                "setup_complete": True,
            }
            self._write_config()
            self._sys_msg.configure(
                text="✅  تم إعادة التعيين", text_color=COLORS["success"]
            )

    # ── Helpers ───────────────────────────────────────────────

    def _write_config(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Reusable widgets ──────────────────────────────────────────

class _SecLabel(ctk.CTkLabel):
    def __init__(self, parent, text: str) -> None:
        super().__init__(
            parent, text=text,
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        )


class _SettingField(ctk.CTkFrame):
    def __init__(self, parent, label: str, var: tk.StringVar,
                 placeholder: str = "", show: str = "") -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label, font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkEntry(
            self, textvariable=var,
            font=FONTS["body"], height=40,
            placeholder_text=placeholder, show=show,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="ew")


class _DropdownField(ctk.CTkFrame):
    def __init__(self, parent, label: str, var: tk.StringVar,
                 values: list) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label, font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkOptionMenu(
            self, variable=var, values=values,
            font=FONTS["body"], height=40, corner_radius=RADIUS["md"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"], text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="ew")


class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message: str) -> None:
        super().__init__(parent)
        self.confirmed = False
        self.title("تأكيد")
        self.geometry("380x170")
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()
        ctk.CTkLabel(self, text=message, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=320,
                     ).pack(pady=(24, 16))
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