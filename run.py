"""
run.py
=======
نقطة الدخول الرئيسية لـ MZz System.
يعمل سواء من المصدر أو بعد البناء بـ PyInstaller.
"""

from __future__ import annotations

import sys
import os
import pathlib


def _fix_paths() -> None:
    """
    عند التشغيل من PyInstaller (frozen):
    - _MEIPASS هو المجلد المؤقت للملفات المضمنة
    - نضيف المجلد الحالي للـ path عشان نلاقي data/ و migrations/
    """
    if getattr(sys, "frozen", False):
        # التطبيق مبني بـ PyInstaller
        base = pathlib.Path(sys.executable).parent
        os.chdir(base)
        # أضف المجلد المؤقت للـ path
        meipass = pathlib.Path(getattr(sys, "_MEIPASS", base))
        if str(meipass) not in sys.path:
            sys.path.insert(0, str(meipass))
    else:
        # التشغيل من المصدر مباشرة
        root = pathlib.Path(__file__).parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))


def _ensure_dirs() -> None:
    """إنشاء المجلدات الضرورية عند أول تشغيل."""
    folders = [
        "data",
        "uploads/photos/employees",
        "uploads/photos/persons",
        "uploads/documents/employees",
        "uploads/documents/persons",
        "uploads/reports",
    ]
    for folder in folders:
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)


def main() -> None:
    _fix_paths()
    _ensure_dirs()

    # استيراد بعد إصلاح الـ paths
    from ui.app import launch
    launch()


if __name__ == "__main__":
    main()