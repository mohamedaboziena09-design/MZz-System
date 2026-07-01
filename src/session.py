"""
src/session.py
===============
Session Manager — V2.1
يدير جلسة المستخدم الحالية.

المهام:
    - التحقق من بيانات الدخول (محلياً أو عبر API)
    - حفظ الجلسة واستعادتها (remember me)
    - تسجيل الخروج وتنظيف الجلسة
    - تسجيل أحداث الدخول/الخروج في الـ logs

الاستخدام:
    session = Session.login(ctx, username, password)
    session.is_valid()
    session.logout()
    Session.restore(ctx)   # استعادة جلسة سابقة
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import secrets
from datetime import datetime, timedelta
from typing   import Optional

from src.context import WorkspaceContext


# ── Session file (داخل config dir) ──────────────────────────
_SESSION_FILE = "session.json"
_TOKEN_BYTES  = 32
_SESSION_TTL  = timedelta(hours=8)   # مدة صلاحية الجلسة


class SessionError(Exception):
    pass

class InvalidCredentials(SessionError):
    pass

class SessionExpired(SessionError):
    pass


class Session:
    """
    جلسة مستخدم واحدة.
    """

    def __init__(self, username: str, token: str,
                 created_at: datetime, ctx: WorkspaceContext) -> None:
        self._username   = username
        self._token      = token
        self._created_at = created_at
        self._ctx        = ctx

    # ── Properties ────────────────────────────────────────────

    @property
    def username(self) -> str:
        return self._username

    @property
    def token(self) -> str:
        return self._token

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def is_valid(self) -> bool:
        """هل الجلسة لا تزال صالحة؟"""
        return datetime.now() - self._created_at < _SESSION_TTL

    def time_remaining(self) -> timedelta:
        """الوقت المتبقي للجلسة."""
        elapsed = datetime.now() - self._created_at
        return max(_SESSION_TTL - elapsed, timedelta(0))

    # ── Save / Restore ────────────────────────────────────────

    def save(self) -> None:
        """حفظ الجلسة على الـ disk (remember me)."""
        data = {
            "username":   self._username,
            "token":      self._token,
            "created_at": self._created_at.isoformat(),
        }
        path = self._ctx.config_dir / _SESSION_FILE
        path.write_text(json.dumps(data), encoding="utf-8")

    def clear(self) -> None:
        """حذف ملف الجلسة من الـ disk."""
        path = self._ctx.config_dir / _SESSION_FILE
        path.unlink(missing_ok=True)

    # ── Logout ────────────────────────────────────────────────

    def logout(self) -> None:
        self.clear()
        self._ctx.log(f"User '{self._username}' logged out.")

    # ════════════════════════════════════════════════════════
    # Class methods
    # ════════════════════════════════════════════════════════

    @classmethod
    def login(cls, ctx: WorkspaceContext,
              username: str, password: str,
              remember: bool = False) -> "Session":
        """
        تسجيل الدخول — يتحقق من الـ config.json محلياً.

        Raises
        ------
        InvalidCredentials — إذا كانت البيانات خاطئة
        """
        cfg      = ctx.config
        expected_user = cfg.get("admin_username", "")
        expected_hash = cfg.get("admin_password", "")
        pw_hash  = hashlib.sha256(password.encode()).hexdigest()

        ok_user = secrets.compare_digest(username, expected_user)
        ok_pass = secrets.compare_digest(pw_hash,  expected_hash)

        if not (ok_user and ok_pass):
            ctx.log(
                f"Failed login attempt for user '{username}'",
                level="warning",
            )
            raise InvalidCredentials(401, "اسم المستخدم أو كلمة المرور غير صحيحة")

        token   = secrets.token_hex(_TOKEN_BYTES)
        session = cls(
            username   = username,
            token      = token,
            created_at = datetime.now(),
            ctx        = ctx,
        )
        if remember:
            session.save()

        ctx.log(f"User '{username}' logged in successfully.")
        return session

    @classmethod
    def restore(cls, ctx: WorkspaceContext) -> Optional["Session"]:
        """
        استعادة جلسة محفوظة إذا كانت لا تزال صالحة.
        يُستدعى عند تشغيل التطبيق (remember me).

        Returns None إذا لم توجد جلسة أو انتهت صلاحيتها.
        """
        path = ctx.config_dir / _SESSION_FILE
        if not path.exists():
            return None
        try:
            data       = json.loads(path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(data["created_at"])
            session    = cls(
                username   = data["username"],
                token      = data["token"],
                created_at = created_at,
                ctx        = ctx,
            )
            if not session.is_valid():
                session.clear()
                ctx.log("Saved session expired — cleared.")
                return None
            ctx.log(f"Session restored for user '{session.username}'.")
            return session
        except Exception as e:
            path.unlink(missing_ok=True)
            ctx.log(f"Failed to restore session: {e}", level="warning")
            return None

    @classmethod
    def change_password(cls, ctx: WorkspaceContext,
                        old_password: str,
                        new_password: str) -> None:
        """
        تغيير كلمة المرور.

        Raises
        ------
        InvalidCredentials — إذا كانت كلمة المرور القديمة خاطئة
        ValueError         — إذا كانت كلمة المرور الجديدة ضعيفة
        """
        if len(new_password) < 8:
            raise ValueError("كلمة المرور يجب أن تكون 8 أحرف على الأقل")

        cfg      = ctx.config
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        if not secrets.compare_digest(old_hash, cfg.get("admin_password","")):
            raise InvalidCredentials(401, "كلمة المرور الحالية غير صحيحة")

        cfg["admin_password"] = hashlib.sha256(new_password.encode()).hexdigest()
        ctx.save_config(cfg)
        ctx.log("Password changed successfully.")

    @classmethod
    def change_username(cls, ctx: WorkspaceContext,
                        password: str,
                        new_username: str) -> None:
        """
        تغيير اسم المستخدم.
        يتطلب التحقق بكلمة المرور.
        """
        if not new_username.strip():
            raise ValueError("اسم المستخدم لا يمكن أن يكون فارغاً")

        cfg      = ctx.config
        pw_hash  = hashlib.sha256(password.encode()).hexdigest()
        if not secrets.compare_digest(pw_hash, cfg.get("admin_password","")):
            raise InvalidCredentials(401, "كلمة المرور غير صحيحة")

        old_username            = cfg.get("admin_username","")
        cfg["admin_username"]   = new_username.strip()
        ctx.save_config(cfg)
        ctx.log(f"Username changed from '{old_username}' to '{new_username}'.")


# ════════════════════════════════════════════════════════════
# Session-aware Login Screen helper
# ════════════════════════════════════════════════════════════

class SessionGuard:
    """
    يُستخدم في login_screen.py لإدارة منطق الجلسة.

    مثال:
        guard = SessionGuard(ctx)

        # تحقق من جلسة محفوظة
        if guard.has_saved_session():
            session = guard.restore()
            on_login(session)
        else:
            session = guard.login(username, password, remember=True)
            on_login(session)
    """

    def __init__(self, ctx: WorkspaceContext) -> None:
        self._ctx     = ctx
        self._session: Optional[Session] = None

    def has_saved_session(self) -> bool:
        saved = Session.restore(self._ctx)
        if saved:
            self._session = saved
            return True
        return False

    def restore(self) -> Optional[Session]:
        return self._session

    def login(self, username: str, password: str,
              remember: bool = False) -> Session:
        session       = Session.login(self._ctx, username, password, remember)
        self._session = session
        return session

    def logout(self) -> None:
        if self._session:
            self._session.logout()
            self._session = None

    @property
    def current(self) -> Optional[Session]:
        return self._session

    def is_authenticated(self) -> bool:
        return (self._session is not None and
                self._session.is_valid())