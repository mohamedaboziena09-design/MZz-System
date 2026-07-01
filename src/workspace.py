"""
src/workspace.py
=================
Workspace Manager — V2.1
النواة الأساسية لفصل البيانات عن التطبيق.

المبدأ:
    التطبيق = binaries فقط (لا بيانات)
    البيانات = Workspace منفصل يختاره المستخدم

هيكل الـ Workspace:
    workspace/
    ├── database/
    │   └── mzz.db
    ├── uploads/
    │   ├── photos/
    │   │   ├── employees/
    │   │   └── persons/
    │   └── documents/
    │       ├── employees/
    │       └── persons/
    ├── backups/
    ├── logs/
    └── config/
        └── config.json

مسار مؤشر الـ Workspace (داخل التطبيق فقط):
    APP_DATA / workspace.ptr  ← يحتوي على مسار الـ Workspace الحالي
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import shutil
from datetime import datetime
from typing import Optional

# ── App data dir (داخل التطبيق — لا يُحذف عند التحديث) ─────
_APP_ROOT  = pathlib.Path(__file__).parent.parent
_APP_DATA  = _APP_ROOT / ".app_data"          # مخفي داخل التطبيق
_PTR_FILE  = _APP_DATA / "workspace.ptr"      # مؤشر للـ Workspace

# ── Workspace sub-folders ────────────────────────────────────
WORKSPACE_DIRS = [
    "database",
    "uploads/photos/employees",
    "uploads/photos/persons",
    "uploads/documents/employees",
    "uploads/documents/persons",
    "backups",
    "logs",
    "config",
]


# ════════════════════════════════════════════════════════════
# Workspace Class
# ════════════════════════════════════════════════════════════

class Workspace:
    """
    الواجهة الوحيدة للتعامل مع الـ Workspace.
    استخدم Workspace.load() للحصول على الـ instance الحالي.
    """

    def __init__(self, root: pathlib.Path) -> None:
        self._root = root

    # ── Properties ────────────────────────────────────────────

    @property
    def root(self) -> pathlib.Path:
        return self._root

    @property
    def database_dir(self) -> pathlib.Path:
        return self._root / "database"

    @property
    def db_path(self) -> pathlib.Path:
        return self.database_dir / "mzz.db"

    @property
    def uploads_dir(self) -> pathlib.Path:
        return self._root / "uploads"

    @property
    def backups_dir(self) -> pathlib.Path:
        return self._root / "backups"

    @property
    def logs_dir(self) -> pathlib.Path:
        return self._root / "logs"

    @property
    def config_dir(self) -> pathlib.Path:
        return self._root / "config"

    @property
    def config_path(self) -> pathlib.Path:
        return self.config_dir / "config.json"

    # ── Config ────────────────────────────────────────────────

    def load_config(self) -> dict:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_config(self, cfg: dict) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Logging ───────────────────────────────────────────────

    def get_logger(self, name: str = "mzz") -> logging.Logger:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y-%m')}.log"
        # اسم فريد لكل Workspace حتى لا يتشارك الـ logger بين مساحات عمل
        # مختلفة (مهم خصوصاً أثناء تشغيل اختبارات متعددة في نفس العملية)
        logger_name = f"{name}.{abs(hash(str(self._root)))}"
        logger = logging.getLogger(logger_name)

        # أنشئ الـ handler فقط إذا لم يكن موجوداً أو يشير لملف مختلف
        # (مثلاً تغيّر الشهر) — لتجنّب تسريب file handles بفتحه كل مرة
        current_target = str(log_file)
        needs_handler = not logger.handlers or getattr(
            logger, "_mzz_log_target", None
        ) != current_target

        if needs_handler:
            for h in list(logger.handlers):
                logger.removeHandler(h)
                h.close()
            handler = logging.FileHandler(log_file, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
            logger._mzz_log_target = current_target

        return logger

    def close_logger(self, name: str = "mzz") -> None:
        """
        إغلاق الـ file handle الخاص بالـ logger صراحة.
        ضروري على Windows قبل أي عملية تحذف أو تنقل مجلد logs/،
        لأن Windows يمنع حذف ملف مفتوح بعكس Linux/Mac.
        """
        logger_name = f"{name}.{abs(hash(str(self._root)))}"
        logger = logging.getLogger(logger_name)
        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()

    def log(self, message: str, level: str = "info") -> None:
        logger = self.get_logger()
        getattr(logger, level, logger.info)(message)

    # ── Stats ─────────────────────────────────────────────────

    def stats(self) -> dict:
        def folder_size(p: pathlib.Path) -> int:
            return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) \
                if p.exists() else 0

        def file_count(p: pathlib.Path) -> int:
            return sum(1 for f in p.rglob("*") if f.is_file()) \
                if p.exists() else 0

        db_size  = self.db_path.stat().st_size if self.db_path.exists() else 0
        upl_size = folder_size(self.uploads_dir)
        bak_size = folder_size(self.backups_dir)
        log_size = folder_size(self.logs_dir)

        return {
            "root":          str(self._root),
            "db_exists":     self.db_path.exists(),
            "db_size":       db_size,
            "uploads_size":  upl_size,
            "uploads_count": file_count(self.uploads_dir),
            "backups_count": file_count(self.backups_dir),
            "backups_size":  bak_size,
            "logs_size":     log_size,
            "total_size":    db_size + upl_size + bak_size + log_size,
        }

    # ── Ensure dirs ───────────────────────────────────────────

    def ensure_dirs(self) -> None:
        for sub in WORKSPACE_DIRS:
            (self._root / sub).mkdir(parents=True, exist_ok=True)


# ════════════════════════════════════════════════════════════
# Workspace Registry (المؤشر)
# ════════════════════════════════════════════════════════════

class WorkspaceRegistry:
    """
    يحفظ ويقرأ مسار الـ Workspace الحالي من ملف .ptr داخل التطبيق.
    هذا الملف الوحيد الذي يبقى داخل التطبيق.
    """

    @staticmethod
    def exists() -> bool:
        return _PTR_FILE.exists()

    @staticmethod
    def read() -> Optional[pathlib.Path]:
        try:
            path = pathlib.Path(_PTR_FILE.read_text(encoding="utf-8").strip())
            return path if path.exists() else None
        except Exception:
            return None

    @staticmethod
    def write(path: pathlib.Path) -> None:
        _APP_DATA.mkdir(parents=True, exist_ok=True)
        _PTR_FILE.write_text(str(path), encoding="utf-8")

    @staticmethod
    def clear() -> None:
        _PTR_FILE.unlink(missing_ok=True)


# ════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════

def workspace_selected() -> bool:
    """هل تم اختيار Workspace من قبل؟"""
    return WorkspaceRegistry.exists() and WorkspaceRegistry.read() is not None


def load_workspace() -> Optional[Workspace]:
    """تحميل الـ Workspace الحالي. يرجع None لو لم يتم اختياره."""
    path = WorkspaceRegistry.read()
    if path is None:
        return None
    ws = Workspace(path)
    ws.ensure_dirs()
    return ws


def create_workspace(root: pathlib.Path) -> Workspace:
    """
    إنشاء Workspace جديد في المسار المحدد.
    يُستدعى من شاشة الإعداد الأول أو عند نقل البيانات.
    """
    ws = Workspace(root)
    ws.ensure_dirs()
    WorkspaceRegistry.write(root)
    ws.log(f"Workspace created at: {root}")
    return ws


def migrate_workspace(
    current: Workspace,
    new_root: pathlib.Path,
    progress_cb: callable = None,
) -> tuple[bool, str]:
    """
    نقل الـ Workspace من مكانه الحالي إلى مكان جديد.

    Parameters
    ----------
    current     : الـ Workspace الحالي
    new_root    : المسار الجديد
    progress_cb : callback(float 0-1, str message)

    Returns
    -------
    (success: bool, message: str)
    """
    def _progress(val: float, msg: str) -> None:
        if progress_cb:
            progress_cb(val, msg)

    try:
        src = current.root
        dst = new_root
        dst.mkdir(parents=True, exist_ok=True)

        _progress(0.0, "جاري جمع الملفات...")

        all_files = [f for f in src.rglob("*") if f.is_file()]
        total     = len(all_files) or 1

        # ── Step 1: Copy ──────────────────────────────────────
        _progress(0.05, f"نسخ {total} ملف...")
        for i, f in enumerate(all_files):
            rel  = f.relative_to(src)
            dest = dst / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            _progress(0.05 + (i / total) * 0.80, f"نسخ: {f.name}")

        # ── Step 2: Verify ────────────────────────────────────
        _progress(0.85, "التحقق من سلامة النسخ...")
        failed = []
        for f in all_files:
            rel  = f.relative_to(src)
            dest = dst / rel
            if not dest.exists():
                failed.append(str(rel))
        if failed:
            raise RuntimeError(
                f"فشل نسخ {len(failed)} ملف:\n" + "\n".join(failed[:5])
            )

        # ── Step 3: Update pointer ────────────────────────────
        _progress(0.90, "تحديث مؤشر الـ Workspace...")
        WorkspaceRegistry.write(dst)

        # ── Step 4: Log in new workspace ─────────────────────
        new_ws = Workspace(dst)
        new_ws.ensure_dirs()
        new_ws.log(f"Workspace migrated from: {src}")

        # ── Step 5: Delete old ────────────────────────────────
        _progress(0.95, "حذف الملفات القديمة...")
        shutil.rmtree(src, ignore_errors=True)

        _progress(1.0, "✅  اكتمل النقل بنجاح!")
        return True, f"تم النقل بنجاح إلى:\n{dst}"

    except Exception as e:
        return False, f"فشل النقل: {e}"


def fmt_size(b: int) -> str:
    if b < 1024:        return f"{b} B"
    if b < 1024 ** 2:   return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:   return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"