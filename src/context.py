"""
src/context.py
===============
WorkspaceContext — V2.1
الحاوية الوحيدة التي تُمرر لكل شاشة في التطبيق.
بدل تمرير db_path لكل شاشة على حدة.

الاستخدام:
    ctx = WorkspaceContext(ws)

    # في أي شاشة:
    with ctx.db() as svc:
        svc.list_employees()

    ctx.upload_dir   → مجلد الرفع
    ctx.config       → الإعدادات
    ctx.log(msg)     → تسجيل في الـ logs
"""

from __future__ import annotations

import pathlib
from typing import Any

from src.workspace   import Workspace
from src.crud_service import CRUDService
from src.file_store   import FileStore


class WorkspaceContext:
    """
    Context موحد يُمرر لكل شاشة في التطبيق.
    يحتوي على كل ما تحتاجه الشاشة للعمل.
    """

    def __init__(self, workspace: Workspace) -> None:
        self._ws     = workspace
        self._config = workspace.load_config()

    # ── Workspace ─────────────────────────────────────────────

    @property
    def workspace(self) -> Workspace:
        return self._ws

    # ── Database ──────────────────────────────────────────────

    def db(self) -> CRUDService:
        """
        إرجاع CRUDService مضبوط على db_path الصحيح.
        استخدم دائماً مع with:

            with ctx.db() as svc:
                svc.list_employees()
        """
        return CRUDService(db_path=self._ws.db_path)

    def raw_conn(self):
        """
        اتصال مباشر بالـ SQLite للاستعلامات المخصصة.
        تذكر: أغلق الاتصال بعد الاستخدام.
        """
        import sqlite3
        conn = sqlite3.connect(self._ws.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── File Store ────────────────────────────────────────────

    @property
    def file_store(self) -> FileStore:
        return FileStore(self._ws.uploads_dir)

    # ── Paths ─────────────────────────────────────────────────

    @property
    def db_path(self) -> pathlib.Path:
        return self._ws.db_path

    @property
    def upload_dir(self) -> pathlib.Path:
        return self._ws.uploads_dir

    @property
    def backup_dir(self) -> pathlib.Path:
        return self._ws.backups_dir

    @property
    def logs_dir(self) -> pathlib.Path:
        return self._ws.logs_dir

    @property
    def config_dir(self) -> pathlib.Path:
        return self._ws.config_dir

    # ── Config ────────────────────────────────────────────────

    @property
    def config(self) -> dict:
        return self._config

    def reload_config(self) -> dict:
        self._config = self._ws.load_config()
        return self._config

    def save_config(self, cfg: dict) -> None:
        self._config = cfg
        self._ws.save_config(cfg)

    # ── Logging ───────────────────────────────────────────────

    def log(self, message: str, level: str = "info") -> None:
        self._ws.log(message, level)

    # ── Upload helpers ────────────────────────────────────────

    def photo_path(self, entity: str, entity_id: int, ext: str) -> pathlib.Path:
        """
        مسار حفظ الصورة.
        entity: 'employees' | 'persons'
        """
        dest = self._ws.uploads_dir / "photos" / entity
        dest.mkdir(parents=True, exist_ok=True)
        return dest / f"{entity_id}_photo{ext}"

    def doc_path(self, entity: str, entity_id: int, filename: str) -> pathlib.Path:
        """
        مسار حفظ المستند.
        entity: 'employees' | 'persons'
        """
        dest = self._ws.uploads_dir / "documents" / entity
        dest.mkdir(parents=True, exist_ok=True)
        return dest / f"{entity_id}_{filename}"

    def relative_path(self, full_path: pathlib.Path) -> str:
        """
        تحويل المسار الكامل إلى مسار نسبي للحفظ في DB.
        """
        try:
            return str(full_path.relative_to(self._ws.root))
        except ValueError:
            return str(full_path)

    def abs_path(self, relative: str) -> pathlib.Path:
        """
        تحويل المسار النسبي المحفوظ في DB إلى مسار كامل.
        """
        return self._ws.root / relative