# MZz System V2.1 — دليل التطوير الاحترافي

---

## 1️⃣ إعداد البيئة من الصفر

### الخطوة 1 — تحقق من Python
```bash
python --version
# يجب أن يكون 3.11 أو 3.12
# إذا كان أقل: حمّله من python.org
```

### الخطوة 2 — أنشئ بيئة افتراضية معزولة
```bash
# داخل مجلد المشروع (mzz-system/)
python -m venv .venv

# تفعيلها (Windows)
.venv\Scripts\activate

# ستظهر (.venv) في بداية السطر — هذا صحيح
```

### الخطوة 3 — ثبّت المتطلبات بالطريقة الصحيحة
```bash
# أولاً: حدّث pip نفسه
python -m pip install --upgrade pip

# ثانياً: ثبّت المتطلبات
pip install -r requirements.txt

# إذا فشل متطلب معين — ثبّته منفرداً:
pip install customtkinter==5.2.2
pip install Pillow>=11.2.1
```

### الخطوة 4 — تحقق من التثبيت
```bash
python -c "import customtkinter; print('CTK OK')"
python -c "import fastapi; print('FastAPI OK')"
python -c "import PIL; print('Pillow OK')"
python -c "import sqlite3; print('SQLite OK')"
```

---

## 2️⃣ التشغيل الصحيح للاختبار

### تشغيل التطبيق (Desktop)
```bash
# تأكد أن البيئة الافتراضية مفعّلة أولاً
.venv\Scripts\activate

# شغّل التطبيق
python run.py
```

### تشغيل الـ API (FastAPI)
```bash
# في terminal منفصل
.venv\Scripts\activate
cd mzz-system
uvicorn main:app --reload --port 8000

# افتح في المتصفح:
# http://127.0.0.1:8000/docs
```

### تشغيل الاثنين معاً (للتطوير)
```bash
# Terminal 1 — API
uvicorn main:app --reload --port 8000

# Terminal 2 — Desktop App
python run.py
```

---

## 3️⃣ الاختبار الاحترافي

### أولاً — اختبار يدوي مرتّب (Smoke Test)

افعل هذا بالترتيب في كل مرة قبل البناء:

```
✅ 1. شغّل python run.py
✅ 2. هل ظهرت شاشة اختيار Workspace؟
✅ 3. اختر مجلداً جديداً (مثل Desktop\Test-WS)
✅ 4. هل أُنشئت المجلدات تلقائياً؟
      Test-WS/database/mzz.db  ← موجود؟
      Test-WS/config/config.json ← موجود؟
✅ 5. هل ظهرت شاشة الإعداد؟
✅ 6. أدخل اسم الشركة + مستخدم + كلمة مرور
✅ 7. هل انتقلت لشاشة Login؟
✅ 8. سجّل الدخول
✅ 9. هل فتح الـ Dashboard؟
✅ 10. جرّب إضافة موظف
✅ 11. جرّب رفع صورة
✅ 12. جرّب النسخ الاحتياطي
✅ 13. أغلق وأعد الفتح — هل تذكّرك؟
```

### ثانياً — اختبار تلقائي بـ pytest

**أنشئ ملف `tests/test_workspace.py`:**
```python
import pathlib
import tempfile
import pytest
from src.startup   import StartupManager
from src.workspace import Workspace, WorkspaceRegistry

@pytest.fixture
def tmp_ws(tmp_path):
    """Workspace مؤقت لكل اختبار."""
    ws = StartupManager.initialize_workspace(tmp_path / "test-ws")
    yield ws
    # تنظيف تلقائي بعد الاختبار

def test_workspace_dirs_created(tmp_ws):
    """التحقق أن كل المجلدات أُنشئت."""
    assert tmp_ws.database_dir.exists()
    assert tmp_ws.uploads_dir.exists()
    assert tmp_ws.backups_dir.exists()
    assert tmp_ws.logs_dir.exists()
    assert tmp_ws.config_dir.exists()

def test_database_created(tmp_ws):
    """التحقق أن قاعدة البيانات أُنشئت."""
    assert tmp_ws.db_path.exists()
    assert tmp_ws.db_path.stat().st_size > 0

def test_db_integrity(tmp_ws):
    """التحقق من سلامة قاعدة البيانات."""
    valid, msg = StartupManager.load_and_validate(tmp_ws)
    assert valid, msg

def test_config_created(tmp_ws):
    """التحقق أن config.json أُنشئ."""
    assert tmp_ws.config_path.exists()
    cfg = tmp_ws.load_config()
    assert "setup_complete" in cfg
    assert cfg["setup_complete"] == False
```

**أنشئ `tests/test_crud.py`:**
```python
import pathlib
import pytest
from src.startup      import StartupManager
from src.crud_service import CRUDService, DuplicateError, NotFoundError

@pytest.fixture
def svc(tmp_path):
    ws = StartupManager.initialize_workspace(tmp_path / "ws")
    with CRUDService(db_path=ws.db_path) as s:
        yield s

SAMPLE_EMP = {
    "first_name":    "أحمد",
    "last_name":     "محمد",
    "national_id":   "1234567890",
    "date_of_birth": "1990-01-01",
    "gender":        "male",
    "department":    "الإدارة",
    "position":      "مدير",
    "hire_date":     "2020-01-01",
}

def test_create_employee(svc):
    emp = svc.create_employee(SAMPLE_EMP)
    assert emp["id"] > 0
    assert emp["first_name"] == "أحمد"
    assert emp["employee_code"].startswith("MZZ-")

def test_get_employee(svc):
    created = svc.create_employee(SAMPLE_EMP)
    found   = svc.get_employee(created["id"])
    assert found["national_id"] == "1234567890"

def test_duplicate_national_id(svc):
    svc.create_employee(SAMPLE_EMP)
    with pytest.raises(DuplicateError):
        svc.create_employee(SAMPLE_EMP)

def test_not_found(svc):
    with pytest.raises(NotFoundError):
        svc.get_employee(9999)

def test_update_employee(svc):
    emp = svc.create_employee(SAMPLE_EMP)
    updated = svc.update_employee(emp["id"], {"position": "نائب مدير"})
    assert updated["position"] == "نائب مدير"

def test_delete_employee(svc):
    emp = svc.create_employee(SAMPLE_EMP)
    svc.delete_employee(emp["id"])
    with pytest.raises(NotFoundError):
        svc.get_employee(emp["id"])
```

**شغّل الاختبارات:**
```bash
# كل الاختبارات
pytest tests/ -v

# اختبار واحد
pytest tests/test_workspace.py -v

# مع تقرير مفصّل
pytest tests/ -v --tb=short

# نتائج متوقعة:
# tests/test_workspace.py::test_workspace_dirs_created PASSED
# tests/test_workspace.py::test_database_created       PASSED
# tests/test_crud.py::test_create_employee             PASSED
# ...
```

---

## 4️⃣ التعامل مع الأخطاء الشائعة

### 🔴 خطأ: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'customtkinter'
```
**الحل:**
```bash
# تأكد أن البيئة الافتراضية مفعّلة
.venv\Scripts\activate

# ثم ثبّت
pip install customtkinter==5.2.2
```

---

### 🔴 خطأ: PIL version conflict

```
ImportError: cannot import name 'xxx' from 'PIL'
```
**الحل:**
```bash
pip uninstall Pillow -y
pip install Pillow>=11.2.1
```

---

### 🔴 خطأ: DLL load failed (Windows)

```
ImportError: DLL load failed while importing _tkinter
```
**الحل:**
```bash
# أعد تثبيت Python مع اختيار "tcl/tk and IDLE"
# أو:
pip install python-tk
```

---

### 🔴 خطأ: database is locked

```
sqlite3.OperationalError: database is locked
```
**الحل:**
```python
# في CRUDService — تأكد من استخدام with:
with CRUDService(db_path=ws.db_path) as svc:
    # كل العمليات هنا
    pass
# الاتصال يُغلق تلقائياً
```

---

### 🔴 خطأ: PyInstaller - missing module

```
ModuleNotFoundError: No module named 'src.workspace'
```
**الحل في `build.py`:**
```bash
# أضف للـ hidden-imports:
"--hidden-import", "src.workspace",
"--hidden-import", "src.context",
"--hidden-import", "src.startup",
```

---

### 🔴 خطأ: customtkinter assets missing (بعد البناء)

```
FileNotFoundError: themes/dark-blue.json
```
**الحل:**
```bash
# في build.py — تأكد من وجود:
"--collect-all", "customtkinter",
```

---

### 🔴 خطأ: Permission denied (uploads)

```
PermissionError: [Errno 13] Permission denied: 'uploads/...'
```
**الحل:**
```python
# تأكد أن المجلد أُنشئ قبل الكتابة:
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dest)
```

---

### 🔴 خطأ: Workspace ptr points to deleted folder

```
⚠️  مساحة العمل غير موجودة
```
**الحل للمستخدم:**
- اضغط "اختيار مجلد جديد"
- أو استعد المجلد القديم ثم أعد التشغيل

**الحل للمطور:**
```python
from src.workspace import WorkspaceRegistry
WorkspaceRegistry.clear()   # امسح المؤشر
# عند التشغيل سيطلب مجلداً جديداً
```

---

## 5️⃣ سير العمل اليومي (Workflow)

```bash
# 1. افتح VS Code
code .

# 2. فعّل البيئة الافتراضية
.venv\Scripts\activate

# 3. شغّل الاختبارات أولاً
pytest tests/ -v --tb=short

# 4. شغّل التطبيق للتطوير
python run.py

# 5. عدّل الكود

# 6. أعد الاختبارات
pytest tests/ -v

# 7. إذا كل شيء OK — ابنِ التطبيق
python build.py

# 8. جرّب الـ .exe
dist\MZz-System\MZz-System.exe
```

---

## 6️⃣ requirements.txt المنقّح والصحيح

```txt
# ── Core UI ──────────────────────────────
customtkinter==5.2.2
Pillow>=11.2.1

# ── API ──────────────────────────────────
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
aiofiles==23.2.1
pydantic==2.7.1

# ── PDF (اختياري) ────────────────────────
reportlab==4.1.0

# ── Build ─────────────────────────────────
pyinstaller==6.6.0

# ── Testing ───────────────────────────────
pytest==8.2.0
pytest-cov==5.0.0
```

> ملاحظة: باقي المكتبات في ملفك (uvicorn, starlette...)
> تُثبَّت تلقائياً كـ dependencies — لا تضفها يدوياً

---

## 7️⃣ أوامر مفيدة

```bash
# عرض كل المكتبات المثبتة
pip list

# تجميد الإصدارات الحالية
pip freeze > requirements.lock

# تنظيف cache
pip cache purge

# إزالة بيئة افتراضية والبدء من جديد
deactivate
rmdir /s /q .venv
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# تشغيل اختبار واحد بالاسم
pytest tests/ -v -k "test_create_employee"

# تشغيل مع coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 8️⃣ checklist قبل كل build

```
□ pytest tests/ -v          ← كل الاختبارات تمر
□ python run.py             ← التطبيق يفتح بدون أخطاء
□ smoke test يدوي (الـ 13 نقطة)
□ python build.py           ← يكتمل بدون أخطاء
□ تشغيل dist\MZz-System\MZz-System.exe
□ smoke test على الـ .exe
□ git commit
```