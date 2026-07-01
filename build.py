"""
build.py — V2.1
=================
سكريبت البناء الكامل لـ MZz System V2.1
يقوم بـ:
1. التحقق من المتطلبات
2. إنشاء أيقونة التطبيق
3. تنظيف بناء سابق
4. بناء التطبيق بـ PyInstaller
5. نسخ الملفات الضرورية
6. إنشاء مجلد dist جاهز للتوزيع
7. إنشاء ملف إرشادات التشغيل

التشغيل:
    python build.py
    python build.py --clean     # تنظيف فقط
    python build.py --no-icon   # بدون أيقونة مخصصة
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import json
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────
ROOT     = pathlib.Path(__file__).parent
DIST     = ROOT / "dist" / "MZz-System"
ASSETS   = ROOT / "assets"
APP_DATA = ROOT / ".app_data"

# ── Colors for terminal ───────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"   {GREEN}✅  {msg}{RESET}")
def warn(msg): print(f"   {YELLOW}⚠️   {msg}{RESET}")
def err(msg):  print(f"   {RED}❌  {msg}{RESET}")
def info(msg): print(f"   {BLUE}ℹ️   {msg}{RESET}")
def step(msg): print(f"\n{BOLD}{msg}{RESET}")


# ════════════════════════════════════════════════════════════
# Step 1: Check Requirements
# ════════════════════════════════════════════════════════════

def check_requirements() -> None:
    step("1️⃣   التحقق من المتطلبات...")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "show",
         "pyinstaller", "customtkinter", "Pillow"],
        capture_output=True, text=True,
    )
    found = {
        line.split(": ")[1].strip().lower()
        for line in result.stdout.splitlines()
        if line.startswith("Name:")
    }
    required = {
        "pyinstaller":   "pip install pyinstaller",
        "customtkinter": "pip install customtkinter",
        "pillow":        "pip install Pillow",
    }
    all_ok = True
    for pkg, install_cmd in required.items():
        if pkg in found:
            ok(pkg)
        else:
            err(f"{pkg} غير مثبت  →  {install_cmd}")
            all_ok = False

    # Optional
    opt_result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "reportlab"],
        capture_output=True, text=True,
    )
    if "Name:" in opt_result.stdout:
        ok("reportlab (PDF — اختياري)")
    else:
        warn("reportlab غير مثبت — ميزة PDF لن تعمل  →  pip install reportlab")

    if not all_ok:
        err("ثبّت المتطلبات الناقصة ثم أعد التشغيل.")
        sys.exit(1)


# ════════════════════════════════════════════════════════════
# Step 2: Create Icon
# ════════════════════════════════════════════════════════════

def create_icon(skip: bool = False) -> bool:
    step("2️⃣   إنشاء أيقونة التطبيق...")
    ASSETS.mkdir(exist_ok=True)
    icon_path = ASSETS / "icon.ico"

    if skip:
        warn("تم تخطي إنشاء الأيقونة (--no-icon)")
        return False

    if icon_path.exists():
        ok(f"الأيقونة موجودة: {icon_path}")
        return True

    try:
        from PIL import Image, ImageDraw, ImageFont
        sizes  = [16, 32, 48, 64, 128, 256]
        images = []
        for size in sizes:
            img  = Image.new("RGBA", (size, size), (15, 17, 23, 255))
            draw = ImageDraw.Draw(img)
            m    = size // 8
            draw.ellipse([m, m, size - m, size - m],
                         fill=(79, 110, 247, 255))
            fs = size // 2
            try:
                font = ImageFont.truetype("arial.ttf", fs)
            except Exception:
                font = ImageFont.load_default()
            draw.text((size // 2, size // 2), "M",
                      fill="white", font=font, anchor="mm")
            images.append(img)

        images[0].save(
            icon_path, format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=images[1:],
        )
        ok(f"تم إنشاء الأيقونة: {icon_path}")
        return True
    except Exception as e:
        warn(f"تعذر إنشاء الأيقونة: {e} — سيتم البناء بدون أيقونة مخصصة")
        return False


# ════════════════════════════════════════════════════════════
# Step 3: Clean Previous Build
# ════════════════════════════════════════════════════════════

def clean() -> None:
    step("3️⃣   تنظيف البناء السابق...")
    for folder in ["dist", "build", "__pycache__"]:
        p = ROOT / folder
        if p.exists():
            shutil.rmtree(p)
            ok(f"تم حذف: {folder}/")
    for spec in ROOT.glob("*.spec.bak"):
        spec.unlink()
    ok("مجلد البناء نظيف")


# ════════════════════════════════════════════════════════════
# Step 4: Build with PyInstaller
# ════════════════════════════════════════════════════════════

def build(has_icon: bool) -> None:
    step("4️⃣   بناء التطبيق بـ PyInstaller...")

    icon_arg = ["--icon", str(ASSETS / "icon.ico")] if has_icon else []

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",                       # لا نافذة CMD
        "--name", "MZz-System",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),

        # ── Hidden imports ──────────────────────────────────
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "sqlite3",
        "--hidden-import", "src.crud_service",
        "--hidden-import", "src.file_store",
        "--hidden-import", "src.schema_loader",
        "--hidden-import", "src.employee_code_generator",
        "--hidden-import", "src.workspace",
        "--hidden-import", "src.context",
        "--hidden-import", "src.session",
        "--hidden-import", "src.api_client",
        "--hidden-import", "ui.app",
        "--hidden-import", "ui.theme",
        "--hidden-import", "ui.components.sidebar",
        "--hidden-import", "ui.components.field",
        "--hidden-import", "ui.components.divider",
        "--hidden-import", "ui.screens.workspace_setup",
        "--hidden-import", "ui.screens.dashboard_screen",
        "--hidden-import", "ui.screens.login_screen",
        "--hidden-import", "ui.screens.main_window",
        "--hidden-import", "ui.screens.setup_screen",
        "--hidden-import", "ui.screens.employees.employees_list",
        "--hidden-import", "ui.screens.employees.employee_form",
        "--hidden-import", "ui.screens.employees.employee_profile",
        "--hidden-import", "ui.screens.persons.persons_list",
        "--hidden-import", "ui.screens.persons.person_form",
        "--hidden-import", "ui.screens.vehicles.vehicles_screen",
        "--hidden-import", "ui.screens.reports.reports_screen",
        "--hidden-import", "ui.screens.settings.settings_screen",
        "--hidden-import", "ui.screens.storage.backup_manager",
        "--hidden-import", "ui.screens.storage.data_location_manager",
        "--hidden-import", "reportlab",

        # ── Data files ──────────────────────────────────────
        "--add-data", f"{ROOT / 'migrations'}{os.pathsep}migrations",
        "--add-data", f"{ROOT / 'schemas'}{os.pathsep}schemas",

        # ── Collect customtkinter ───────────────────────────
        "--collect-all", "customtkinter",

        # ── Exclude unused ──────────────────────────────────
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "pytest",

        *icon_arg,

        # ── Entry point ─────────────────────────────────────
        str(ROOT / "run.py"),
    ]

    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        err("فشل البناء! راجع الأخطاء أعلاه.")
        sys.exit(1)
    ok("اكتمل البناء بنجاح!")


# ════════════════════════════════════════════════════════════
# Step 5: Post-build Setup
# ════════════════════════════════════════════════════════════

def post_build() -> None:
    step("5️⃣   تجهيز مجلد التوزيع...")

    if not DIST.exists():
        err(f"مجلد dist غير موجود: {DIST}")
        sys.exit(1)

    # مجلدات التطبيق الداخلية فقط (لا بيانات مستخدم)
    internal_dirs = [".app_data"]
    for d in internal_dirs:
        (DIST / d).mkdir(parents=True, exist_ok=True)
    ok("تم إنشاء .app_data/ (مؤشر Workspace)")

    # نسخ migrations
    src_mig = ROOT / "migrations"
    dst_mig = DIST / "migrations"
    if src_mig.exists():
        if dst_mig.exists():
            shutil.rmtree(dst_mig)
        shutil.copytree(src_mig, dst_mig)
        ok("تم نسخ migrations/")

    # نسخ schemas
    src_sch = ROOT / "schemas"
    dst_sch = DIST / "schemas"
    if src_sch.exists():
        if dst_sch.exists():
            shutil.rmtree(dst_sch)
        shutil.copytree(src_sch, dst_sch)
        ok("تم نسخ schemas/")

    ok(f"التطبيق جاهز في: {DIST}")


# ════════════════════════════════════════════════════════════
# Step 6: Version File
# ════════════════════════════════════════════════════════════

def write_version() -> None:
    step("6️⃣   كتابة ملف الإصدار...")
    version_info = {
        "version":    "2.1.0",
        "build_date": datetime.now().isoformat(),
        "python":     sys.version.split()[0],
    }
    (DIST / "version.json").write_text(
        json.dumps(version_info, indent=2), encoding="utf-8"
    )
    ok("version.json")


# ════════════════════════════════════════════════════════════
# Step 7: README
# ════════════════════════════════════════════════════════════

def write_readme() -> None:
    step("7️⃣   كتابة ملف إرشادات التشغيل...")

    content = """
╔══════════════════════════════════════════════════════════════╗
║              MZz System V2.1 — إرشادات التشغيل              ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀  طريقة تشغيل التطبيق
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  انقر نقراً مزدوجاً على:  MZz-System.exe

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋  خطوات أول تشغيل
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  الخطوة 1 — اختيار مساحة العمل (Workspace)
  ┌─────────────────────────────────────────────┐
  │  ستظهر شاشة تطلب منك اختيار مجلد لحفظ     │
  │  بيانات النظام.                             │
  │                                             │
  │  مثال:  D:\MZz-Workspace                   │
  │         C:\Users\Mohamed\Documents\MZz      │
  │                                             │
  │  ⚠️  اختر مكاناً ثابتاً لا تحذفه           │
  └─────────────────────────────────────────────┘

  الخطوة 2 — الإعداد الأولي
  ┌─────────────────────────────────────────────┐
  │  أدخل:                                      │
  │  • اسم الشركة                               │
  │  • اسم المستخدم                             │
  │  • كلمة المرور (8 أحرف على الأقل)           │
  └─────────────────────────────────────────────┘

  الخطوة 3 — تسجيل الدخول
  ┌─────────────────────────────────────────────┐
  │  أدخل بيانات الدخول التي اخترتها           │
  │  ✅  فعّل "تذكرني" لتجاوز الدخول           │
  │      في المرات القادمة                      │
  └─────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂  هيكل مساحة العمل (Workspace)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  MZz-Workspace/
  ├── database/          ← قاعدة البيانات (mzz.db)
  ├── uploads/           ← الصور والمستندات المرفقة
  │   ├── photos/
  │   └── documents/
  ├── backups/           ← النسخ الاحتياطية التلقائية
  ├── logs/              ← سجلات النظام الشهرية
  └── config/            ← إعدادات الشركة والحساب

  ⚠️  احتفظ بهذا المجلد دائماً
  ⚠️  لا تنقله إلا من داخل التطبيق (الإعدادات ← التخزين)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾  النسخ الاحتياطي
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • يدوي:     من الشريط الجانبي ← النسخ الاحتياطي
  • تلقائي:   يمكن جدولته كل X ساعة من نفس الشاشة
  • الاستعادة: من نفس الشاشة — اختر ملف .zip

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄  التحديث
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. قم بنسخ احتياطي أولاً
  2. احذف المجلد القديم (MZz-System/)
  3. ضع المجلد الجديد مكانه
  4. شغّل MZz-System.exe
  5. سيتعرف تلقائياً على مساحة العمل السابقة
  ✅  بياناتك لن تُمس أبداً

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚗  ميزات V2.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅  إدارة الموظفين (CRUD كامل + صور + مستندات)
  ✅  إدارة الأشخاص والعملاء
  ✅  إدارة السيارات (تعيين + حركة + تاريخ)
  ✅  التقارير والطباعة + تصدير PDF
  ✅  نسخ احتياطي تلقائي ويدوي
  ✅  فصل البيانات عن التطبيق (Workspace)
  ✅  جلسة محفوظة (تذكرني)
  ✅  إعدادات الشركة والحساب

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️  متطلبات التشغيل
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • Windows 10 / 11 (64-bit)
  • لا يحتاج Python مثبتاً
  • مساحة التطبيق: ~80 MB
  • مساحة البيانات: تعتمد على حجم الملفات

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆘  المشاكل الشائعة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ❌ "مساحة العمل غير موجودة"
     → المجلد تم نقله أو حذفه
     → اختر مجلداً جديداً من التحذير

  ❌ "بيانات الدخول غير صحيحة"
     → تحقق من اسم المستخدم وكلمة المرور
     → كلمة المرور حساسة لحالة الأحرف

  ❌ التطبيق لا يفتح
     → تأكد أن Windows Defender لا يحجبه
     → شغّل كـ Administrator

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MZz System V2.1  ·  MZz-Hub
  Build Date: {build_date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(build_date=datetime.now().strftime("%Y-%m-%d"))

    (DIST / "إرشادات_التشغيل.txt").write_text(
        content.strip(), encoding="utf-8"
    )
    ok("إرشادات_التشغيل.txt")


# ════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════

def print_summary() -> None:
    exe  = DIST / "MZz-System.exe"
    size = exe.stat().st_size / (1024 * 1024) if exe.exists() else 0

    print(f"""
{BOLD}{'═' * 56}{RESET}
{GREEN}{BOLD}   ✅  MZz System V2.1 — تم البناء بنجاح!{RESET}
{'═' * 56}

   📦  الملف:    {DIST / 'MZz-System.exe'}
   💽  الحجم:    {size:.1f} MB
   📅  التاريخ:  {datetime.now().strftime('%Y-%m-%d  %H:%M')}

   للتشغيل:
   {BLUE}cd dist\\MZz-System && MZz-System.exe{RESET}

{'═' * 56}
""")


# ════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="MZz System Build Script V2.1")
    parser.add_argument("--clean",   action="store_true", help="تنظيف فقط بدون بناء")
    parser.add_argument("--no-icon", action="store_true", help="بناء بدون أيقونة مخصصة")
    args = parser.parse_args()

    print(f"""
{BOLD}{'═' * 56}
   MZz System V2.1 — Build Script
{'═' * 56}{RESET}""")

    if args.clean:
        clean()
        ok("تم التنظيف.")
        return

    check_requirements()
    has_icon = create_icon(skip=args.no_icon)
    clean()
    build(has_icon)
    post_build()
    write_version()
    write_readme()
    print_summary()


if __name__ == "__main__":
    main()