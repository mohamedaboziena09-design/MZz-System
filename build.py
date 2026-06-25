"""
build.py
=========
سكريبت البناء الكامل لـ MZz System V1
يقوم بـ:
1. التحقق من المتطلبات
2. إنشاء أيقونة التطبيق
3. بناء التطبيق بـ PyInstaller
4. نسخ الملفات الضرورية
5. إنشاء مجلد dist جاهز للتوزيع

التشغيل:
    python build.py
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import pathlib

# ── Paths ─────────────────────────────────────────────────────
ROOT     = pathlib.Path(__file__).parent
DIST     = ROOT / "dist" / "MZz-System"
ASSETS   = ROOT / "assets"
DATA_DIR = ROOT / "data"


def check_requirements() -> None:
    print("⚙️  التحقق من المتطلبات...")
    # تحقق بـ pip list بدل __import__ لتجنب مشاكل الـ import
    import subprocess as sp
    result = sp.run(
        [sys.executable, "-m", "pip", "show",
         "pyinstaller", "customtkinter", "Pillow"],
        capture_output=True, text=True,
    )
    found = {
        line.split(": ")[1].lower()
        for line in result.stdout.splitlines()
        if line.startswith("Name:")
    }
    required = {"pyinstaller": "pyinstaller",
                "customtkinter": "customtkinter",
                "pillow": "Pillow"}
    all_ok = True
    for key, install_name in required.items():
        if key in found:
            print(f"   ✅  {install_name}")
        else:
            print(f"   ❌  {install_name} غير مثبت — شغّل: pip install {install_name}")
            all_ok = False
    if not all_ok:
        sys.exit(1)


def create_icon() -> None:
    """إنشاء أيقونة بسيطة لو مش موجودة."""
    ASSETS.mkdir(exist_ok=True)
    icon_path = ASSETS / "icon.ico"
    if icon_path.exists():
        print("✅  الأيقونة موجودة")
        return
    print("🎨  إنشاء أيقونة افتراضية...")
    try:
        from PIL import Image, ImageDraw, ImageFont
        sizes = [16, 32, 48, 64, 128, 256]
        images = []
        for size in sizes:
            img  = Image.new("RGBA", (size, size), (15, 17, 23, 255))
            draw = ImageDraw.Draw(img)
            # Circle background
            margin = size // 8
            draw.ellipse(
                [margin, margin, size - margin, size - margin],
                fill=(79, 110, 247, 255),
            )
            # Text "M"
            font_size = size // 2
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            draw.text(
                (size // 2, size // 2),
                "M", fill="white", font=font, anchor="mm",
            )
            images.append(img)
        images[0].save(
            icon_path, format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=images[1:],
        )
        print(f"   ✅  أيقونة تم إنشاؤها: {icon_path}")
    except Exception as e:
        print(f"   ⚠️  تعذر إنشاء الأيقونة: {e}")
        print("   سيتم البناء بدون أيقونة مخصصة.")
        # Patch spec to remove icon
        spec = ROOT / "mzz_system.spec"
        if spec.exists():
            content = spec.read_text(encoding="utf-8")
            content = content.replace('icon="assets/icon.ico",', "")
            spec.write_text(content, encoding="utf-8")


def ensure_data_dir() -> None:
    """تأكد أن مجلد data موجود مع config.json فارغ لو مش موجود."""
    DATA_DIR.mkdir(exist_ok=True)
    config = DATA_DIR / "config.json"
    if not config.exists():
        import json
        config.write_text(
            json.dumps({
                "company_name":   "",
                "admin_username": "",
                "admin_password": "",
                "setup_complete": False,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("   ✅  config.json تم إنشاؤه (فارغ — سيظهر إعداد أول تشغيل)")


def build() -> None:
    print("\n🔨  بناء التطبيق بـ PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller",
         "--clean",
         "mzz_system.spec"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("\n❌  فشل البناء! راجع الأخطاء أعلاه.")
        sys.exit(1)
    print("✅  البناء اكتمل!")


def post_build() -> None:
    """نسخ ملفات ضرورية لمجلد dist."""
    print("\n📦  تجهيز مجلد التوزيع...")

    if not DIST.exists():
        print(f"❌  مجلد dist غير موجود: {DIST}")
        return

    # إنشاء مجلدات ضرورية
    for folder in ["uploads/photos/employees",
                   "uploads/photos/persons",
                   "uploads/documents/employees",
                   "uploads/documents/persons",
                   "uploads/reports",
                   "data"]:
        (DIST / folder).mkdir(parents=True, exist_ok=True)

    # نسخ config.json لو موجود (بدون كلمة السر)
    src_config = DATA_DIR / "config.json"
    dst_config = DIST / "data" / "config.json"
    if src_config.exists() and not dst_config.exists():
        shutil.copy2(src_config, dst_config)
        print("   ✅  config.json تم نسخه")

    # نسخ migrations
    src_mig = ROOT / "migrations"
    dst_mig = DIST / "migrations"
    if src_mig.exists():
        if dst_mig.exists():
            shutil.rmtree(dst_mig)
        shutil.copytree(src_mig, dst_mig)
        print("   ✅  migrations تم نسخها")

    # إنشاء README للمستخدم
    readme = DIST / "تعليمات_التشغيل.txt"
    readme.write_text(
        "MZz System V1\n"
        "==============\n\n"
        "طريقة التشغيل:\n"
        "  انقر نقراً مزدوجاً على MZz-System.exe\n\n"
        "أول تشغيل:\n"
        "  سيظهر نافذة الإعداد — أدخل اسم الشركة واسم المستخدم وكلمة المرور\n\n"
        "ملاحظات:\n"
        "  - قاعدة البيانات تُحفظ في مجلد data/mzz.db\n"
        "  - الصور والمستندات تُحفظ في مجلد uploads/\n"
        "  - احتفظ بنسخة احتياطية من مجلد data/ بانتظام\n\n"
        "الدعم الفني: MZz-Hub\n",
        encoding="utf-8",
    )
    print("   ✅  تعليمات التشغيل تم إنشاؤها")

    print(f"\n🎉  التطبيق جاهز في: {DIST}")
    print(f"     شغّل: {DIST / 'MZz-System.exe'}")


def main() -> None:
    print("=" * 50)
    print("   MZz System V1 — Build Script")
    print("=" * 50)
    check_requirements()
    create_icon()
    ensure_data_dir()
    build()
    post_build()
    print("\n✅  العملية اكتملت بنجاح!")


if __name__ == "__main__":
    main()
