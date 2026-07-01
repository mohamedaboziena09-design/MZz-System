"""
tests/test_session.py
=======================
اختبارات Session — تسجيل الدخول، التذكر، الانتهاء، تغيير كلمة المرور.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
import pytest

from src.startup  import StartupManager
from src.context  import WorkspaceContext
from src.session  import (
    Session, SessionGuard,
    InvalidCredentials, SessionExpired,
)


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture
def ctx_with_user(tmp_path) -> WorkspaceContext:
    """Context جاهز ومعه مستخدم مسجّل (admin / Passw0rd!)."""
    ws  = StartupManager.initialize_workspace(tmp_path / "ws")
    cfg = ws.load_config()
    cfg.update({
        "company_name":   "شركة الاختبار",
        "admin_username": "admin",
        "admin_password": hashlib.sha256("Passw0rd!".encode()).hexdigest(),
        "setup_complete": True,
    })
    ws.save_config(cfg)
    ctx = WorkspaceContext(ws)
    ctx.reload_config()
    return ctx


# ════════════════════════════════════════════════════════════
# Login
# ════════════════════════════════════════════════════════════

class TestLogin:

    def test_login_success_with_correct_credentials(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        assert session.username == "admin"
        assert session.token
        assert session.is_valid()

    def test_login_fails_wrong_password(self, ctx_with_user):
        with pytest.raises(InvalidCredentials):
            Session.login(ctx_with_user, "admin", "WrongPass")

    def test_login_fails_wrong_username(self, ctx_with_user):
        with pytest.raises(InvalidCredentials):
            Session.login(ctx_with_user, "notadmin", "Passw0rd!")

    def test_login_fails_empty_credentials(self, ctx_with_user):
        with pytest.raises(InvalidCredentials):
            Session.login(ctx_with_user, "", "")

    def test_failed_login_is_logged(self, ctx_with_user):
        try:
            Session.login(ctx_with_user, "admin", "wrong")
        except InvalidCredentials:
            pass
        log_files = list(ctx_with_user.logs_dir.glob("*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "Failed login" in content

    def test_successful_login_is_logged(self, ctx_with_user):
        Session.login(ctx_with_user, "admin", "Passw0rd!")
        log_files = list(ctx_with_user.logs_dir.glob("*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "logged in successfully" in content

    def test_each_login_generates_unique_token(self, ctx_with_user):
        s1 = Session.login(ctx_with_user, "admin", "Passw0rd!")
        s2 = Session.login(ctx_with_user, "admin", "Passw0rd!")
        assert s1.token != s2.token


# ════════════════════════════════════════════════════════════
# Save / Restore (Remember Me)
# ════════════════════════════════════════════════════════════

class TestSaveRestore:

    def test_save_creates_session_file(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        session.save()
        path = ctx_with_user.config_dir / "session.json"
        assert path.exists()

    def test_restore_returns_valid_session(self, ctx_with_user):
        original = Session.login(ctx_with_user, "admin", "Passw0rd!")
        original.save()

        restored = Session.restore(ctx_with_user)
        assert restored is not None
        assert restored.username == "admin"
        assert restored.token == original.token

    def test_restore_returns_none_when_no_session(self, ctx_with_user):
        assert Session.restore(ctx_with_user) is None

    def test_restore_returns_none_for_corrupted_file(self, ctx_with_user):
        path = ctx_with_user.config_dir / "session.json"
        path.write_text("NOT VALID JSON {{{", encoding="utf-8")
        assert Session.restore(ctx_with_user) is None

    def test_restore_clears_expired_session(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        # نزرع جلسة منتهية يدوياً
        path = ctx_with_user.config_dir / "session.json"
        expired_data = {
            "username":   session.username,
            "token":      session.token,
            "created_at": (datetime.now() - timedelta(hours=20)).isoformat(),
        }
        path.write_text(json.dumps(expired_data), encoding="utf-8")

        restored = Session.restore(ctx_with_user)
        assert restored is None
        assert not path.exists()   # يجب حذفها بعد اكتشاف الانتهاء

    def test_clear_removes_session_file(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        session.save()
        session.clear()
        path = ctx_with_user.config_dir / "session.json"
        assert not path.exists()

    def test_not_saved_when_remember_false(self, ctx_with_user):
        Session.login(ctx_with_user, "admin", "Passw0rd!", remember=False)
        path = ctx_with_user.config_dir / "session.json"
        assert not path.exists()

    def test_saved_when_remember_true(self, ctx_with_user):
        Session.login(ctx_with_user, "admin", "Passw0rd!", remember=True)
        path = ctx_with_user.config_dir / "session.json"
        assert path.exists()


# ════════════════════════════════════════════════════════════
# Validity / Expiry
# ════════════════════════════════════════════════════════════

class TestValidity:

    def test_fresh_session_is_valid(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        assert session.is_valid() is True

    def test_old_session_is_invalid(self, ctx_with_user):
        session = Session(
            username="admin", token="abc",
            created_at=datetime.now() - timedelta(hours=10),
            ctx=ctx_with_user,
        )
        assert session.is_valid() is False

    def test_time_remaining_decreases(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        remaining = session.time_remaining()
        assert remaining.total_seconds() > 0
        assert remaining <= timedelta(hours=8)

    def test_time_remaining_zero_when_expired(self, ctx_with_user):
        session = Session(
            username="admin", token="abc",
            created_at=datetime.now() - timedelta(hours=20),
            ctx=ctx_with_user,
        )
        assert session.time_remaining() == timedelta(0)


# ════════════════════════════════════════════════════════════
# Logout
# ════════════════════════════════════════════════════════════

class TestLogout:

    def test_logout_clears_saved_file(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!", remember=True)
        path = ctx_with_user.config_dir / "session.json"
        assert path.exists()

        session.logout()
        assert not path.exists()

    def test_logout_is_logged(self, ctx_with_user):
        session = Session.login(ctx_with_user, "admin", "Passw0rd!")
        session.logout()
        log_files = list(ctx_with_user.logs_dir.glob("*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "logged out" in content


# ════════════════════════════════════════════════════════════
# Change Password
# ════════════════════════════════════════════════════════════

class TestChangePassword:

    def test_change_password_success(self, ctx_with_user):
        Session.change_password(ctx_with_user, "Passw0rd!", "NewPass123")
        # تأكد أن الدخول بالقديمة لم يعد يعمل
        with pytest.raises(InvalidCredentials):
            Session.login(ctx_with_user, "admin", "Passw0rd!")
        # والدخول بالجديدة يعمل
        session = Session.login(ctx_with_user, "admin", "NewPass123")
        assert session.username == "admin"

    def test_change_password_wrong_old_password(self, ctx_with_user):
        with pytest.raises(InvalidCredentials):
            Session.change_password(ctx_with_user, "WrongOld", "NewPass123")

    def test_change_password_too_short(self, ctx_with_user):
        with pytest.raises(ValueError):
            Session.change_password(ctx_with_user, "Passw0rd!", "short")

    def test_change_password_persists_to_config(self, ctx_with_user):
        Session.change_password(ctx_with_user, "Passw0rd!", "AnotherPass1")
        ctx_with_user.reload_config()
        expected_hash = hashlib.sha256("AnotherPass1".encode()).hexdigest()
        assert ctx_with_user.config["admin_password"] == expected_hash


# ════════════════════════════════════════════════════════════
# Change Username
# ════════════════════════════════════════════════════════════

class TestChangeUsername:

    def test_change_username_success(self, ctx_with_user):
        Session.change_username(ctx_with_user, "Passw0rd!", "newadmin")
        ctx_with_user.reload_config()
        assert ctx_with_user.config["admin_username"] == "newadmin"

    def test_change_username_wrong_password(self, ctx_with_user):
        with pytest.raises(InvalidCredentials):
            Session.change_username(ctx_with_user, "WrongPass", "newadmin")

    def test_change_username_empty_rejected(self, ctx_with_user):
        with pytest.raises(ValueError):
            Session.change_username(ctx_with_user, "Passw0rd!", "   ")

    def test_can_login_with_new_username(self, ctx_with_user):
        Session.change_username(ctx_with_user, "Passw0rd!", "renamed")
        ctx_with_user.reload_config()
        session = Session.login(ctx_with_user, "renamed", "Passw0rd!")
        assert session.username == "renamed"


# ════════════════════════════════════════════════════════════
# SessionGuard (Helper)
# ════════════════════════════════════════════════════════════

class TestSessionGuard:

    def test_has_saved_session_false_initially(self, ctx_with_user):
        guard = SessionGuard(ctx_with_user)
        assert guard.has_saved_session() is False

    def test_has_saved_session_true_after_login_remember(self, ctx_with_user):
        guard = SessionGuard(ctx_with_user)
        guard.login("admin", "Passw0rd!", remember=True)

        guard2 = SessionGuard(ctx_with_user)
        assert guard2.has_saved_session() is True

    def test_is_authenticated_after_login(self, ctx_with_user):
        guard = SessionGuard(ctx_with_user)
        guard.login("admin", "Passw0rd!")
        assert guard.is_authenticated() is True

    def test_is_authenticated_false_before_login(self, ctx_with_user):
        guard = SessionGuard(ctx_with_user)
        assert guard.is_authenticated() is False

    def test_logout_clears_current_session(self, ctx_with_user):
        guard = SessionGuard(ctx_with_user)
        guard.login("admin", "Passw0rd!", remember=True)
        guard.logout()
        assert guard.current is None
        assert guard.is_authenticated() is False

    def test_current_returns_active_session(self, ctx_with_user):
        guard = SessionGuard(ctx_with_user)
        session = guard.login("admin", "Passw0rd!")
        assert guard.current is session