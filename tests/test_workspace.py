"""
tests/test_workspace.py
=========================
اختبارات Workspace — إنشاء، تحقق، إصلاح ذاتي.
"""

import pathlib
import pytest

from src.startup   import StartupManager
from src.workspace import (
    Workspace, WorkspaceRegistry,
    create_workspace, fmt_size, WORKSPACE_DIRS,
)


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_ws(tmp_path) -> Workspace:
    """Workspace كامل (مجلدات + DB + config) لكل اختبار."""
    ws = StartupManager.initialize_workspace(tmp_path / "test-workspace")
    yield ws


@pytest.fixture
def empty_ws(tmp_path) -> Workspace:
    """Workspace فارغ — مجلدات فقط بدون تهيئة كاملة."""
    ws = Workspace(tmp_path / "empty-ws")
    ws.ensure_dirs()
    yield ws


# ════════════════════════════════════════════════════════════
# Directory Structure Tests
# ════════════════════════════════════════════════════════════

class TestWorkspaceStructure:

    def test_all_directories_created(self, tmp_ws):
        """يجب إنشاء كل المجلدات الخمسة الأساسية."""
        assert tmp_ws.database_dir.exists()
        assert tmp_ws.uploads_dir.exists()
        assert tmp_ws.backups_dir.exists()
        assert tmp_ws.logs_dir.exists()
        assert tmp_ws.config_dir.exists()

    def test_upload_subdirectories(self, tmp_ws):
        """المجلدات الفرعية لـ uploads يجب أن تكون موجودة."""
        for sub in [
            "photos/employees", "photos/persons",
            "documents/employees", "documents/persons",
        ]:
            assert (tmp_ws.uploads_dir / sub.split("/", 1)[1] \
                    if False else tmp_ws.root / "uploads" / sub).exists()

    def test_root_matches_chosen_path(self, tmp_path):
        chosen = tmp_path / "my-workspace"
        ws = create_workspace(chosen)
        assert ws.root == chosen

    def test_workspace_dirs_constant_matches_reality(self, tmp_ws):
        """كل مسار في WORKSPACE_DIRS يجب أن يكون موجوداً فعلياً."""
        for sub in WORKSPACE_DIRS:
            assert (tmp_ws.root / sub).exists(), f"{sub} غير موجود"


# ════════════════════════════════════════════════════════════
# Database Tests
# ════════════════════════════════════════════════════════════

class TestWorkspaceDatabase:

    def test_database_file_created(self, tmp_ws):
        assert tmp_ws.db_path.exists()
        assert tmp_ws.db_path.stat().st_size > 0

    def test_database_path_inside_workspace(self, tmp_ws):
        assert tmp_ws.database_dir in tmp_ws.db_path.parents

    def test_db_integrity_check_passes(self, tmp_ws):
        valid, msg = StartupManager.load_and_validate(tmp_ws)
        assert valid, msg

    def test_migrations_create_core_tables(self, tmp_ws):
        import sqlite3
        conn = sqlite3.connect(tmp_ws.db_path)
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        for required in ["employees", "documents", "persons",
                         "person_documents", "vehicles"]:
            assert required in tables, f"جدول {required} غير موجود"

    def test_missing_database_is_recreated(self, tmp_ws):
        """حذف الـ DB يدوياً ثم التحقق من إعادة إنشائها تلقائياً."""
        tmp_ws.db_path.unlink()
        assert not tmp_ws.db_path.exists()

        valid, msg = StartupManager.load_and_validate(tmp_ws)
        assert valid, msg
        assert tmp_ws.db_path.exists()


# ════════════════════════════════════════════════════════════
# Config Tests
# ════════════════════════════════════════════════════════════

class TestWorkspaceConfig:

    def test_config_file_created(self, tmp_ws):
        assert tmp_ws.config_path.exists()

    def test_default_config_values(self, tmp_ws):
        cfg = tmp_ws.load_config()
        assert cfg["setup_complete"] is False
        assert cfg["company_name"] == ""
        assert cfg["theme"] == "dark"
        assert cfg["language"] == "ar"

    def test_config_persists_after_save(self, tmp_ws):
        cfg = tmp_ws.load_config()
        cfg["company_name"] = "MZz-Hub"
        tmp_ws.save_config(cfg)

        reloaded = tmp_ws.load_config()
        assert reloaded["company_name"] == "MZz-Hub"

    def test_missing_config_is_recreated(self, tmp_ws):
        tmp_ws.config_path.unlink()
        assert not tmp_ws.config_path.exists()

        valid, msg = StartupManager.load_and_validate(tmp_ws)
        assert valid, msg
        assert tmp_ws.config_path.exists()
        cfg = tmp_ws.load_config()
        assert cfg["setup_complete"] is False


# ════════════════════════════════════════════════════════════
# Self-Healing Tests (إصلاح ذاتي)
# ════════════════════════════════════════════════════════════

class TestSelfHealing:

    def test_missing_uploads_dir_is_recreated(self, tmp_ws):
        import shutil
        shutil.rmtree(tmp_ws.uploads_dir)
        assert not tmp_ws.uploads_dir.exists()

        valid, msg = StartupManager.load_and_validate(tmp_ws)
        assert valid, msg
        assert tmp_ws.uploads_dir.exists()

    def test_missing_backups_dir_is_recreated(self, tmp_ws):
        import shutil
        shutil.rmtree(tmp_ws.backups_dir)

        StartupManager.load_and_validate(tmp_ws)
        assert tmp_ws.backups_dir.exists()

    def test_missing_logs_dir_is_recreated(self, tmp_ws):
        import shutil
        tmp_ws.close_logger()   # أغلق الـ file handle أولاً (مطلوب على Windows)
        shutil.rmtree(tmp_ws.logs_dir)

        StartupManager.load_and_validate(tmp_ws)
        assert tmp_ws.logs_dir.exists()


# ════════════════════════════════════════════════════════════
# Registry (Pointer File) Tests
# ════════════════════════════════════════════════════════════

class TestWorkspaceRegistry:

    def test_pointer_written_after_create(self, tmp_path, monkeypatch):
        # نوجّه الـ APP_DATA لمجلد مؤقت حتى لا نلوث بيئة الاختبار
        import src.workspace as ws_module
        fake_app_data = tmp_path / ".app_data"
        monkeypatch.setattr(ws_module, "_APP_DATA", fake_app_data)
        monkeypatch.setattr(ws_module, "_PTR_FILE", fake_app_data / "workspace.ptr")

        chosen = tmp_path / "ws1"
        ws_module.create_workspace(chosen)

        assert ws_module.WorkspaceRegistry.exists()
        assert ws_module.WorkspaceRegistry.read() == chosen

    def test_clear_removes_pointer(self, tmp_path, monkeypatch):
        import src.workspace as ws_module
        fake_app_data = tmp_path / ".app_data"
        monkeypatch.setattr(ws_module, "_APP_DATA", fake_app_data)
        monkeypatch.setattr(ws_module, "_PTR_FILE", fake_app_data / "workspace.ptr")

        ws_module.create_workspace(tmp_path / "ws2")
        ws_module.WorkspaceRegistry.clear()

        assert not ws_module.WorkspaceRegistry.exists()


# ════════════════════════════════════════════════════════════
# Stats & Helpers
# ════════════════════════════════════════════════════════════

class TestWorkspaceStats:

    def test_stats_returns_expected_keys(self, tmp_ws):
        stats = tmp_ws.stats()
        for key in ["root", "db_exists", "db_size",
                   "uploads_size", "total_size"]:
            assert key in stats

    def test_stats_db_exists_true(self, tmp_ws):
        stats = tmp_ws.stats()
        assert stats["db_exists"] is True

    def test_fmt_size_bytes(self):
        assert fmt_size(500) == "500 B"

    def test_fmt_size_kb(self):
        assert "KB" in fmt_size(2048)

    def test_fmt_size_mb(self):
        assert "MB" in fmt_size(5 * 1024 * 1024)

    def test_fmt_size_gb(self):
        assert "GB" in fmt_size(2 * 1024 ** 3)


# ════════════════════════════════════════════════════════════
# Logging Tests
# ════════════════════════════════════════════════════════════

class TestWorkspaceLogging:

    def test_log_creates_file(self, tmp_ws):
        tmp_ws.log("Test message")
        log_files = list(tmp_ws.logs_dir.glob("*.log"))
        assert len(log_files) >= 1

    def test_log_content_written(self, tmp_ws):
        tmp_ws.log("Unique test marker XYZ123")
        log_files = list(tmp_ws.logs_dir.glob("*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "XYZ123" in content