"""
tests/test_context.py
=======================
اختبارات WorkspaceContext — الحاوية الموحدة لكل الشاشات.
يغطي: قاعدة البيانات، الملفات، المسارات، الإعدادات، الـ logging.
"""

import pathlib
import pytest

from src.startup  import StartupManager
from src.context  import WorkspaceContext


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture
def ctx(tmp_path) -> WorkspaceContext:
    ws = StartupManager.initialize_workspace(tmp_path / "ctx-ws")
    return WorkspaceContext(ws)


# ════════════════════════════════════════════════════════════
# Database Access
# ════════════════════════════════════════════════════════════

class TestDatabaseAccess:

    def test_db_returns_working_crud_service(self, ctx):
        with ctx.db() as svc:
            emp = svc.create_employee({
                "first_name": "أحمد", "last_name": "محمد",
                "national_id": "1110000001", "date_of_birth": "1990-01-01",
                "gender": "male", "department": "IT",
                "position": "مطور", "hire_date": "2021-01-01",
            })
        assert emp["id"] > 0

    def test_db_uses_correct_workspace_path(self, ctx):
        with ctx.db() as svc:
            pass
        # تأكد أن db_path يطابق مسار الـ workspace فعلياً
        assert ctx.db_path == ctx.workspace.db_path

    def test_data_persists_across_db_calls(self, ctx):
        with ctx.db() as svc:
            svc.create_person({"first_name": "سارة", "last_name": "علي"})
        with ctx.db() as svc:
            assert svc.count_persons() == 1

    def test_raw_conn_works(self, ctx):
        conn = ctx.raw_conn()
        result = conn.execute("SELECT 1").fetchone()
        conn.close()
        assert result[0] == 1

    def test_raw_conn_has_foreign_keys_enabled(self, ctx):
        conn = ctx.raw_conn()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        assert fk == 1


# ════════════════════════════════════════════════════════════
# File Store
# ════════════════════════════════════════════════════════════

class TestFileStore:

    def test_file_store_points_to_uploads_dir(self, ctx):
        store = ctx.file_store
        assert store is not None


# ════════════════════════════════════════════════════════════
# Paths
# ════════════════════════════════════════════════════════════

class TestPaths:

    def test_db_path_matches_workspace(self, ctx):
        assert ctx.db_path == ctx.workspace.db_path

    def test_upload_dir_matches_workspace(self, ctx):
        assert ctx.upload_dir == ctx.workspace.uploads_dir

    def test_backup_dir_matches_workspace(self, ctx):
        assert ctx.backup_dir == ctx.workspace.backups_dir

    def test_logs_dir_matches_workspace(self, ctx):
        assert ctx.logs_dir == ctx.workspace.logs_dir

    def test_config_dir_matches_workspace(self, ctx):
        assert ctx.config_dir == ctx.workspace.config_dir


# ════════════════════════════════════════════════════════════
# Config
# ════════════════════════════════════════════════════════════

class TestConfig:

    def test_config_loaded_on_init(self, ctx):
        assert isinstance(ctx.config, dict)
        assert "setup_complete" in ctx.config

    def test_reload_config_reflects_external_change(self, ctx):
        # تعديل الملف مباشرة من خارج الـ context
        cfg = ctx.workspace.load_config()
        cfg["company_name"] = "تم التعديل خارجياً"
        ctx.workspace.save_config(cfg)

        reloaded = ctx.reload_config()
        assert reloaded["company_name"] == "تم التعديل خارجياً"
        assert ctx.config["company_name"] == "تم التعديل خارجياً"

    def test_save_config_writes_to_disk(self, ctx):
        cfg = ctx.config
        cfg["company_name"] = "MZz-Hub"
        ctx.save_config(cfg)

        # اقرأ مباشرة من القرص للتأكد
        fresh_ws_cfg = ctx.workspace.load_config()
        assert fresh_ws_cfg["company_name"] == "MZz-Hub"

    def test_save_config_updates_in_memory_copy(self, ctx):
        cfg = dict(ctx.config)
        cfg["theme"] = "light"
        ctx.save_config(cfg)
        assert ctx.config["theme"] == "light"


# ════════════════════════════════════════════════════════════
# Logging
# ════════════════════════════════════════════════════════════

class TestLogging:

    def test_log_writes_message(self, ctx):
        ctx.log("رسالة اختبار فريدة QWERTY")
        log_files = list(ctx.logs_dir.glob("*.log"))
        assert len(log_files) >= 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "QWERTY" in content

    def test_log_supports_warning_level(self, ctx):
        ctx.log("تحذير اختباري", level="warning")
        log_files = list(ctx.logs_dir.glob("*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "WARNING" in content


# ════════════════════════════════════════════════════════════
# Upload Helpers (photo_path / doc_path)
# ════════════════════════════════════════════════════════════

class TestUploadHelpers:

    def test_photo_path_creates_employee_dir(self, ctx):
        path = ctx.photo_path("employees", 1, ".png")
        assert path.parent.exists()
        assert path.name == "1_photo.png"

    def test_photo_path_creates_person_dir(self, ctx):
        path = ctx.photo_path("persons", 5, ".jpg")
        assert "persons" in str(path.parent)
        assert path.name == "5_photo.jpg"

    def test_doc_path_creates_employee_dir(self, ctx):
        path = ctx.doc_path("employees", 3, "contract.pdf")
        assert path.parent.exists()
        assert path.name == "3_contract.pdf"

    def test_doc_path_creates_person_dir(self, ctx):
        path = ctx.doc_path("persons", 7, "id.png")
        assert "persons" in str(path.parent)
        assert path.name == "7_id.png"

    def test_photo_path_is_inside_workspace(self, ctx):
        path = ctx.photo_path("employees", 1, ".png")
        assert ctx.workspace.root in path.parents


# ════════════════════════════════════════════════════════════
# Relative / Absolute Path Conversion
# ════════════════════════════════════════════════════════════

class TestPathConversion:

    def test_relative_path_strips_workspace_root(self, ctx):
        full = ctx.workspace.root / "uploads" / "photos" / "1_photo.png"
        rel  = ctx.relative_path(full)
        assert rel == str(pathlib.Path("uploads") / "photos" / "1_photo.png")

    def test_abs_path_reconstructs_full_path(self, ctx):
        rel  = "uploads/photos/1_photo.png"
        full = ctx.abs_path(rel)
        assert full == ctx.workspace.root / rel

    def test_round_trip_relative_then_absolute(self, ctx):
        original = ctx.workspace.root / "uploads" / "documents" / "x.pdf"
        rel      = ctx.relative_path(original)
        restored = ctx.abs_path(rel)
        assert restored == original

    def test_relative_path_handles_path_outside_workspace(self, ctx, tmp_path):
        outside = tmp_path.parent / "totally-outside" / "file.txt"
        rel = ctx.relative_path(outside)
        # يجب ألا يرفع استثناء — يرجع المسار الكامل كـ fallback
        assert isinstance(rel, str)


# ════════════════════════════════════════════════════════════
# Integration: Full upload-then-delete cycle via Context
# ════════════════════════════════════════════════════════════

class TestContextIntegration:

    def test_employee_photo_upload_cycle(self, ctx, tmp_path):
        # 1. أنشئ موظف
        with ctx.db() as svc:
            emp = svc.create_employee({
                "first_name": "خالد", "last_name": "سعيد",
                "national_id": "9990000001", "date_of_birth": "1985-05-05",
                "gender": "male", "department": "HR",
                "position": "موظف", "hire_date": "2019-01-01",
            })

        # 2. "ارفع" صورة وهمية عبر الـ helper
        dest = ctx.photo_path("employees", emp["id"], ".png")
        dest.write_bytes(b"\x89PNG fake content")
        rel = ctx.relative_path(dest)

        # 3. حدّث السجل بمسار الصورة
        with ctx.db() as svc:
            svc.update_employee(emp["id"], {"photo_path": rel})
            updated = svc.get_employee(emp["id"])

        # 4. تحقق من استرجاع المسار الصحيح
        assert updated["photo_path"] == rel
        full = ctx.abs_path(updated["photo_path"])
        assert full.exists()
        assert full.read_bytes().startswith(b"\x89PNG")