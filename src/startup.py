"""
src/startup.py
===============
آلية التشغيل الكاملة — V2.1

Flow:
    run.py
      ↓
    StartupManager.run()
      ↓
    [1] هل workspace.ptr موجود وصالح؟
          لا  → WorkspaceSetupScreen → إنشاء Workspace
          نعم → تحميل Workspace
      ↓
    [2] هل قاعدة البيانات موجودة؟
          لا  → إنشاء + تشغيل migrations تلقائياً
          نعم → التحقق من سلامتها
      ↓
    [3] هل config.json موجود؟
          لا  → إنشاء config فارغ
          نعم → تحميله
      ↓
    [4] هل setup_complete = True؟
          لا  → SetupScreen (اسم الشركة + كلمة السر)
          نعم → LoginScreen
      ↓
    [5] تسجيل الدخول → MainWindow
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
from typing import Optional

from src.workspace import (
    Workspace, WorkspaceRegistry,
    create_workspace, load_workspace,
    workspace_selected, WORKSPACE_DIRS,
)


# ════════════════════════════════════════════════════════════
# Startup Result
# ════════════════════════════════════════════════════════════

class StartupResult:
    """نتيجة عملية التشغيل."""

    def __init__(self, workspace: Workspace, config: dict,
                 is_first_run: bool = False) -> None:
        self.workspace     = workspace
        self.config        = config
        self.is_first_run  = is_first_run   # True = يحتاج SetupScreen

    @property
    def setup_complete(self) -> bool:
        return self.config.get("setup_complete", False)


# ════════════════════════════════════════════════════════════
# Startup Manager
# ════════════════════════════════════════════════════════════

class StartupManager:
    """
    يدير كل عمليات التشغيل الأولي.
    يُستخدم من run.py فقط.
    """

    # ── Step A: Validate Workspace ────────────────────────────

    @staticmethod
    def is_workspace_ready() -> bool:
        """هل الـ Workspace موجود وصالح؟"""
        if not WorkspaceRegistry.exists():
            return False
        path = WorkspaceRegistry.read()
        if path is None:
            return False
        # تحقق أن المجلد الأساسي موجود
        return path.exists()

    # ── Step B: Initialize Workspace ─────────────────────────

    @staticmethod
    def initialize_workspace(root: pathlib.Path) -> Workspace:
        """
        إنشاء Workspace جديد كامل:
        - إنشاء المجلدات
        - إنشاء قاعدة البيانات
        - تشغيل الـ migrations
        - إنشاء config.json
        - حفظ المسار في workspace.ptr
        """
        # 1. إنشاء المجلدات
        ws = create_workspace(root)

        # 2. إنشاء قاعدة البيانات وتشغيل migrations
        StartupManager._init_database(ws)

        # 3. إنشاء config.json فارغ
        StartupManager._init_config(ws)

        # 4. تسجيل في logs
        ws.log("Workspace initialized successfully.")
        ws.log(f"Database created at: {ws.db_path}")
        ws.log(f"Config created at: {ws.config_path}")

        return ws

    @staticmethod
    def _init_database(ws: Workspace) -> None:
        """إنشاء قاعدة البيانات وتشغيل كل الـ migrations."""
        from src.crud_service import CRUDService
        ws.database_dir.mkdir(parents=True, exist_ok=True)
        with CRUDService(db_path=ws.db_path) as svc:
            svc.run_migrations()

    @staticmethod
    def _init_config(ws: Workspace) -> None:
        """إنشاء config.json فارغ إذا لم يكن موجوداً."""
        if ws.config_path.exists():
            return
        ws.config_dir.mkdir(parents=True, exist_ok=True)
        default_config = {
            "company_name":    "",
            "admin_username":  "",
            "admin_password":  "",
            "setup_complete":  False,
            "theme":           "dark",
            "language":        "ar",
            "api_url":         "http://127.0.0.1:8000",
            "api_timeout":     10,
            "data_root":       str(ws.root),
            "data_location_history": [],
        }
        ws.save_config(default_config)

    # ── Step C: Load & Validate Existing Workspace ───────────

    @staticmethod
    def load_and_validate(ws: Workspace) -> tuple[bool, str]:
        """
        التحقق من سلامة Workspace موجود مسبقاً.

        Returns: (is_valid, error_message)
        """
        checks = [
            (ws.database_dir, "مجلد database"),
            (ws.uploads_dir,  "مجلد uploads"),
            (ws.config_dir,   "مجلد config"),
            (ws.backups_dir,  "مجلد backups"),
            (ws.logs_dir,     "مجلد logs"),
        ]
        # تأكد من وجود المجلدات (أنشئها إذا ناقصة)
        for path, name in checks:
            path.mkdir(parents=True, exist_ok=True)

        # تحقق من قاعدة البيانات
        if not ws.db_path.exists():
            # قاعدة البيانات مفقودة — أنشئها
            try:
                StartupManager._init_database(ws)
                ws.log("Database was missing — recreated.", level="warning")
            except Exception as e:
                return False, f"فشل إنشاء قاعدة البيانات: {e}"

        # تحقق من سلامة قاعدة البيانات
        ok, msg = StartupManager._check_db_integrity(ws)
        if not ok:
            return False, msg

        # تحقق من config
        if not ws.config_path.exists():
            StartupManager._init_config(ws)
            ws.log("Config was missing — recreated.", level="warning")

        return True, "OK"

    @staticmethod
    def _check_db_integrity(ws: Workspace) -> tuple[bool, str]:
        """التحقق من سلامة قاعدة البيانات."""
        try:
            conn = sqlite3.connect(ws.db_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if result and result[0] == "ok":
                return True, "OK"
            return False, f"قاعدة البيانات تالفة: {result}"
        except Exception as e:
            return False, f"خطأ في قاعدة البيانات: {e}"

    # ── Step D: Run Migrations (if needed) ───────────────────

    @staticmethod
    def ensure_migrations(ws: Workspace) -> None:
        """
        تشغيل الـ migrations إذا كانت هناك جداول جديدة.
        آمن للتشغيل في كل مرة (IF NOT EXISTS).
        """
        from src.crud_service import CRUDService
        with CRUDService(db_path=ws.db_path) as svc:
            svc.run_migrations()

    # ── Main Entry ────────────────────────────────────────────

    @classmethod
    def prepare(cls, ws: Workspace) -> StartupResult:
        """
        تجهيز Workspace موجود للتشغيل.
        يُستدعى بعد تحميل workspace ناجح.
        """
        # تحقق من السلامة وإصلاح ما يمكن إصلاحه
        valid, msg = cls.load_and_validate(ws)
        if not valid:
            raise RuntimeError(msg)

        # تشغيل migrations
        cls.ensure_migrations(ws)

        # تحميل config
        config       = ws.load_config()
        is_first_run = not config.get("setup_complete", False)

        return StartupResult(
            workspace    = ws,
            config       = config,
            is_first_run = is_first_run,
        )