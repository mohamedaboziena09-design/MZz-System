"""
run.py — V2.1 النهائي
=======================
Flow:
    1. workspace_selected?  لا  → WorkspaceSetupScreen
    2. workspace_selected?  نعم → load_workspace
    3. session.restore?     نعم → MainWindow مباشرة
    4. setup_complete?      لا  → SetupScreen
    5. setup_complete?      نعم → LoginScreen → MainWindow
"""

from __future__ import annotations

import sys
import os
import pathlib


def _fix_paths() -> None:
    if getattr(sys, "frozen", False):
        base = pathlib.Path(sys.executable).parent
        os.chdir(base)
        meipass = pathlib.Path(getattr(sys, "_MEIPASS", base))
        if str(meipass) not in sys.path:
            sys.path.insert(0, str(meipass))
    else:
        root = pathlib.Path(__file__).parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))


def main() -> None:
    _fix_paths()

    import customtkinter as ctk
    from src.workspace import workspace_selected, load_workspace, Workspace
    from src.context   import WorkspaceContext
    from src.session   import Session, SessionGuard

    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.withdraw()

    # ── Step 1: Workspace ─────────────────────────────────────
    if not workspace_selected():
        _show_workspace_setup(root)
        root.mainloop()
        return

    ws = load_workspace()
    if ws is None:
        _show_missing_workspace(root)
        root.mainloop()
        return

    # ── Step 2: Run migrations ────────────────────────────────
    from src.crud_service import CRUDService
    with CRUDService(db_path=ws.db_path) as svc:
        svc.run_migrations()

    ctx = WorkspaceContext(ws)

    # ── Step 3: Try restore saved session ─────────────────────
    guard   = SessionGuard(ctx)
    session = None
    if guard.has_saved_session():
        session = guard.restore()

    if session:
        # جلسة محفوظة وصالحة — افتح التطبيق مباشرة
        _open_main(root, ctx, session, guard)
    else:
        cfg = ctx.config
        if not cfg.get("setup_complete"):
            _show_setup(root, ctx, guard)
        else:
            _show_login(root, ctx, guard)

    root.mainloop()


# ════════════════════════════════════════════════════════════
# Workspace Setup
# ════════════════════════════════════════════════════════════

def _show_workspace_setup(root) -> None:
    import customtkinter as ctk
    from src.workspace import Workspace
    from src.context   import WorkspaceContext
    from src.session   import SessionGuard
    from ui.screens.workspace_setup import WorkspaceSetupScreen

    win = ctk.CTkToplevel(root)
    win.title("MZz System — إعداد مساحة العمل")
    win.geometry("640x700")
    win.protocol("WM_DELETE_WINDOW", root.destroy)
    win.lift(); win.focus()

    def on_done(ws: Workspace) -> None:
        win.destroy()
        ctx   = WorkspaceContext(ws)
        guard = SessionGuard(ctx)
        cfg   = ctx.config
        if not cfg.get("setup_complete"):
            _show_setup(root, ctx, guard)
        else:
            _show_login(root, ctx, guard)

    WorkspaceSetupScreen(win, on_done=on_done)


# ════════════════════════════════════════════════════════════
# First-time Setup
# ════════════════════════════════════════════════════════════

def _show_setup(root, ctx, guard) -> None:
    import customtkinter as ctk
    from ui.screens.setup_screen import SetupScreen

    win = ctk.CTkToplevel(root)
    win.title("MZz System — الإعداد الأولي")
    win.geometry("800x600")
    win.protocol("WM_DELETE_WINDOW", root.destroy)
    win.lift(); win.focus()

    def on_complete() -> None:
        win.destroy()
        _show_login(root, ctx, guard)

    SetupScreen(win, on_complete=on_complete)


# ════════════════════════════════════════════════════════════
# Login
# ════════════════════════════════════════════════════════════

def _show_login(root, ctx, guard) -> None:
    import customtkinter as ctk
    from src.session import Session
    from ui.screens.login_screen import LoginScreen

    win = ctk.CTkToplevel(root)
    win.title("MZz System — تسجيل الدخول")
    win.geometry("480x560")
    win.protocol("WM_DELETE_WINDOW", root.destroy)
    win.lift(); win.focus()

    def on_login(session: Session) -> None:
        win.destroy()
        _open_main(root, ctx, session, guard)

    LoginScreen(win, ctx=ctx, on_login=on_login)


# ════════════════════════════════════════════════════════════
# Main Window
# ════════════════════════════════════════════════════════════

def _open_main(root, ctx, session, guard) -> None:
    import customtkinter as ctk
    from ui.screens.main_window import MainWindow

    win = MainWindow(
        config    = ctx.config,
        workspace = ctx.workspace,
        session   = session,
        on_logout = lambda: _on_logout(root, win, ctx, guard),
    )
    win.protocol("WM_DELETE_WINDOW", lambda: _on_close(root, win, guard))
    win.lift(); win.focus()


def _on_logout(root, win, ctx, guard) -> None:
    guard.logout()
    win.destroy()
    _show_login(root, ctx, guard)


def _on_close(root, win, guard) -> None:
    """إغلاق التطبيق — تسجيل الخروج إذا لم يكن remember me."""
    win.destroy()
    root.destroy()


# ════════════════════════════════════════════════════════════
# Missing Workspace
# ════════════════════════════════════════════════════════════

def _show_missing_workspace(root) -> None:
    import customtkinter as ctk
    from src.workspace import WorkspaceRegistry

    win = ctk.CTkToplevel(root)
    win.title("تحذير")
    win.geometry("480x260")
    win.configure(fg_color="#1A1D27")
    win.protocol("WM_DELETE_WINDOW", root.destroy)
    win.grab_set()

    ctk.CTkLabel(win, text="⚠️  مساحة العمل غير موجودة",
                 font=("Segoe UI", 18, "bold"),
                 text_color="#F39C12",
                 ).pack(pady=(32, 8))

    ctk.CTkLabel(
        win,
        text="المجلد المسجل تم نقله أو حذفه.\n"
             "اختر مساحة عمل جديدة أو استعد المجلد القديم.",
        font=("Segoe UI", 13), text_color="#E8EAF2",
        wraplength=400,
    ).pack(pady=(0, 24))

    row = ctk.CTkFrame(win, fg_color="transparent")
    row.pack()

    def choose_new() -> None:
        WorkspaceRegistry.clear()
        win.destroy()
        _show_workspace_setup(root)

    ctk.CTkButton(row, text="❌  إغلاق", width=120, height=40,
                  fg_color="#2A2E42", text_color="#8892A4",
                  command=root.destroy,
                  ).pack(side="left", padx=8)

    ctk.CTkButton(row, text="📂  اختيار جديد", width=160, height=40,
                  fg_color="#4F6EF7", text_color="white",
                  command=choose_new,
                  ).pack(side="left", padx=8)


if __name__ == "__main__":
    main()