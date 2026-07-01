"""
tests/test_startup.py
=======================
اختبارات StartupManager — آلية التشغيل الكاملة.
يغطي: إنشاء Workspace جديد، تحميل موجود، الإصلاح الذاتي،
       تكامل migrations، وسيناريوهات الفشل.
"""

import pathlib
import sqlite3
import pytest

from src.startup   import StartupManager, StartupResult
from src.workspace import Workspace, create_workspace


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture
def fresh_root(tmp_path) -> pathlib.Path:
    """مسار جديد لم يُنشأ فيه شيء بعد."""
    return tmp_path / "fresh-workspace"


@pytest.fixture
def ready_ws(tmp_path) -> Workspace:
    """Workspace مهيّأ بالكامل وجاهز."""
    return StartupManager.initialize_workspace(tmp_path / "ready-ws")


# ════════════════════════════════════════════════════════════
# is_workspace_ready()
# ════════════════════════════════════════════════════════════

class TestIsWorkspaceReady:

    def test_false_when_no_pointer(self, monkeypatch, tmp_path):
        import src.workspace as ws_module
        monkeypatch.setattr(
            ws_module, "_PTR_FILE", tmp_path / "nonexistent" / "workspace.ptr"
        )
        assert StartupManager.is_workspace_ready() is False

    def test_true_when_pointer_valid(self, monkeypatch, tmp_path):
        import src.workspace as ws_module
        fake_app_data = tmp_path / ".app_data"
        monkeypatch.setattr(ws_module, "_APP_DATA", fake_app_data)
        monkeypatch.setattr(ws_module, "_PTR_FILE", fake_app_data / "workspace.ptr")

        target = tmp_path / "ws"
        target.mkdir()
        ws_module.WorkspaceRegistry.write(target)

        assert StartupManager.is_workspace_ready() is True

    def test_false_when_pointer_target_deleted(self, monkeypatch, tmp_path):
        import src.workspace as ws_module
        fake_app_data = tmp_path / ".app_data"
        monkeypatch.setattr(ws_module, "_APP_DATA", fake_app_data)
        monkeypatch.setattr(ws_module, "_PTR_FILE", fake_app_data / "workspace.ptr")

        target = tmp_path / "ws-will-vanish"
        target.mkdir()
        ws_module.WorkspaceRegistry.write(target)
        target.rmdir()   # المجلد اختفى

        assert StartupManager.is_workspace_ready() is False


# ════════════════════════════════════════════════════════════
# initialize_workspace() — أول تشغيل
# ════════════════════════════════════════════════════════════

class TestInitializeWorkspace:

    def test_creates_workspace_object(self, fresh_root):
        ws = StartupManager.initialize_workspace(fresh_root)
        assert isinstance(ws, Workspace)
        assert ws.root == fresh_root

    def test_creates_all_required_dirs(self, fresh_root):
        ws = StartupManager.initialize_workspace(fresh_root)
        assert ws.database_dir.exists()
        assert ws.uploads_dir.exists()
        assert ws.backups_dir.exists()
        assert ws.logs_dir.exists()
        assert ws.config_dir.exists()

    def test_creates_database_with_tables(self, fresh_root):
        ws = StartupManager.initialize_workspace(fresh_root)
        assert ws.db_path.exists()

        conn   = sqlite3.connect(ws.db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "employees" in tables
        assert "persons"   in tables

    def test_creates_default_config(self, fresh_root):
        ws  = StartupManager.initialize_workspace(fresh_root)
        cfg = ws.load_config()
        assert cfg["setup_complete"] is False
        assert cfg["data_root"] == str(ws.root)

    def test_logs_initialization_event(self, fresh_root):
        ws = StartupManager.initialize_workspace(fresh_root)
        log_files = list(ws.logs_dir.glob("*.log"))
        assert len(log_files) >= 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "initialized" in content.lower()

    def test_idempotent_when_called_twice(self, fresh_root):
        """استدعاء initialize_workspace مرتين على نفس المسار يجب ألا يفشل."""
        ws1 = StartupManager.initialize_workspace(fresh_root)
        ws2 = StartupManager.initialize_workspace(fresh_root)
        assert ws1.root == ws2.root
        assert ws2.db_path.exists()


# ════════════════════════════════════════════════════════════
# load_and_validate() — تحميل Workspace موجود
# ════════════════════════════════════════════════════════════

class TestLoadAndValidate:

    def test_valid_workspace_passes(self, ready_ws):
        valid, msg = StartupManager.load_and_validate(ready_ws)
        assert valid is True
        assert msg == "OK"

    def test_missing_database_dir_recreated(self, ready_ws):
        import shutil
        shutil.rmtree(ready_ws.database_dir)
        valid, msg = StartupManager.load_and_validate(ready_ws)
        assert valid, msg
        assert ready_ws.database_dir.exists()
        assert ready_ws.db_path.exists()

    def test_missing_db_file_recreated_with_tables(self, ready_ws):
        ready_ws.db_path.unlink()
        valid, msg = StartupManager.load_and_validate(ready_ws)
        assert valid, msg

        conn = sqlite3.connect(ready_ws.db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "employees" in tables

    def test_missing_config_recreated(self, ready_ws):
        ready_ws.config_path.unlink()
        valid, msg = StartupManager.load_and_validate(ready_ws)
        assert valid, msg
        assert ready_ws.config_path.exists()

    def test_corrupted_database_detected(self, ready_ws):
        """ملف DB تالف يجب أن يُكتشف (أو يُعاد إنشاؤه حسب المنطق)."""
        ready_ws.db_path.write_bytes(b"NOT A VALID SQLITE FILE")
        valid, msg = StartupManager.load_and_validate(ready_ws)
        # إما يفشل بوضوح أو يصلح تلقائياً — كلاهما مقبول طالما لا يتجاهل الخطأ بصمت
        if valid:
            # تم الإصلاح — تأكد أن القاعدة الجديدة صالحة فعلاً
            conn = sqlite3.connect(ready_ws.db_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            assert result[0] == "ok"
        else:
            assert "تالفة" in msg or "خطأ" in msg


# ════════════════════════════════════════════════════════════
# ensure_migrations()
# ════════════════════════════════════════════════════════════

class TestEnsureMigrations:

    def test_safe_to_run_multiple_times(self, ready_ws):
        """تشغيل migrations عدة مرات يجب ألا يسبب أخطاء (IF NOT EXISTS)."""
        StartupManager.ensure_migrations(ready_ws)
        StartupManager.ensure_migrations(ready_ws)
        StartupManager.ensure_migrations(ready_ws)
        # لو وصلنا هنا بدون استثناء، الاختبار ناجح

    def test_existing_data_preserved_after_rerun(self, ready_ws):
        from src.crud_service import CRUDService
        with CRUDService(db_path=ready_ws.db_path) as svc:
            svc.create_person({
                "first_name": "سارة", "last_name": "علي",
            })
        StartupManager.ensure_migrations(ready_ws)
        with CRUDService(db_path=ready_ws.db_path) as svc:
            assert svc.count_persons() == 1


# ════════════════════════════════════════════════════════════
# prepare() — التكامل الكامل
# ════════════════════════════════════════════════════════════

class TestPrepare:

    def test_returns_startup_result(self, ready_ws):
        result = StartupManager.prepare(ready_ws)
        assert isinstance(result, StartupResult)

    def test_is_first_run_true_for_new_workspace(self, ready_ws):
        result = StartupManager.prepare(ready_ws)
        assert result.is_first_run is True
        assert result.setup_complete is False

    def test_is_first_run_false_after_setup(self, ready_ws):
        cfg = ready_ws.load_config()
        cfg.update({
            "company_name":   "MZz-Hub",
            "admin_username": "admin",
            "admin_password": "hashed",
            "setup_complete": True,
        })
        ready_ws.save_config(cfg)

        result = StartupManager.prepare(ready_ws)
        assert result.is_first_run is False
        assert result.setup_complete is True

    def test_raises_on_unrecoverable_error(self, ready_ws, monkeypatch):
        """إذا فشل التحقق بشكل لا يمكن إصلاحه، يجب رفع RuntimeError."""
        def fake_validate(ws):
            return False, "فشل غير قابل للإصلاح"
        monkeypatch.setattr(StartupManager, "load_and_validate",
                            staticmethod(fake_validate))

        with pytest.raises(RuntimeError):
            StartupManager.prepare(ready_ws)

    def test_config_reflects_workspace_after_prepare(self, ready_ws):
        result = StartupManager.prepare(ready_ws)
        assert result.workspace.root == ready_ws.root
        assert isinstance(result.config, dict)


# ════════════════════════════════════════════════════════════
# End-to-End Scenario
# ════════════════════════════════════════════════════════════

class TestEndToEndStartupScenario:
    """محاكاة كاملة لتجربة المستخدم من الصفر حتى الجاهزية لتسجيل الدخول."""

    def test_full_first_run_flow(self, fresh_root):
        # 1. لا يوجد Workspace بعد
        assert not fresh_root.exists()

        # 2. المستخدم يختار مجلداً → initialize
        ws = StartupManager.initialize_workspace(fresh_root)

        # 3. تجهيز كامل (كما يحدث في run.py)
        result = StartupManager.prepare(ws)
        assert result.is_first_run is True

        # 4. المستخدم يكمل SetupScreen
        cfg = result.config
        cfg.update({
            "company_name":   "شركة الاختبار",
            "admin_username": "tester",
            "admin_password": "hashedpw",
            "setup_complete": True,
        })
        ws.save_config(cfg)

        # 5. إعادة prepare يجب أن تُظهر أن الإعداد اكتمل
        result2 = StartupManager.prepare(ws)
        assert result2.is_first_run is False
        assert result2.config["company_name"] == "شركة الاختبار"

    def test_restart_after_setup_skips_setup_screen(self, ready_ws):
        """محاكاة إعادة تشغيل التطبيق بعد إعداد سابق."""
        cfg = ready_ws.load_config()
        cfg["setup_complete"] = True
        cfg["admin_username"] = "admin"
        ready_ws.save_config(cfg)

        # "إعادة تشغيل" = استدعاء prepare من جديد
        result = StartupManager.prepare(ready_ws)
        assert result.is_first_run is False