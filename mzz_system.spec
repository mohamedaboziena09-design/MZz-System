# ============================================================
# mzz_system.spec
# PyInstaller spec file for MZz System V1
# ============================================================
# بناء التطبيق:
#   pyinstaller mzz_system.spec
# ============================================================

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Collect customtkinter assets ─────────────────────────────
ctk_datas = collect_data_files("customtkinter")

a = Analysis(
    ["run.py"],                          # نقطة الدخول
    pathex=["."],
    binaries=[],
    datas=[
        # customtkinter themes & assets
        *ctk_datas,
        # مجلد الـ migrations
        ("migrations",  "migrations"),
        # مجلد الـ schemas
        ("schemas",     "schemas"),
        # مجلد data (config.json + mzz.db)
        ("data",        "data"),
        # مجلد uploads (يُنشأ عند أول تشغيل)
        # ("uploads",  "uploads"),   # uncomment if pre-populated
    ],
    hiddenimports=[
        "customtkinter",
        "PIL",
        "PIL._tkinter_finder",
        "sqlite3",
        *collect_submodules("customtkinter"),
        *collect_submodules("PIL"),
        # src modules
        "src.crud_service",
        "src.file_store",
        "src.schema_loader",
        "src.employee_code_generator",
        # ui modules
        "ui.app",
        "ui.theme",
        "ui.components.sidebar",
        "ui.components.field",
        "ui.components.divider",
        "ui.screens.dashboard_screen",
        "ui.screens.employees.employees_list",
        "ui.screens.employees.employee_form",
        "ui.screens.employees.employee_profile",
        "ui.screens.persons.persons_list",
        "ui.screens.persons.person_form",
        "ui.screens.vehicles.vehicles_screen",
        "ui.screens.reports.reports_screen",
        "ui.screens.login_screen",
        "ui.screens.main_window",
        "ui.screens.setup_screen",
        # optional PDF
        "reportlab",
        "reportlab.platypus",
        "reportlab.lib.pagesizes",
        "reportlab.lib.styles",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MZz-System",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # لا تظهر نافذة CMD
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",  # أيقونة التطبيق
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MZz-System",
)
