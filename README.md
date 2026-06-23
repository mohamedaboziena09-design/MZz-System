# MZz System V1

Employee File Management System — lightweight, offline-first, schema-validated.

---

## Overview

MZz System V1 is a local employee file management system built on **Python + SQLite**.
It handles up to **1,000 employees**, with support for profile photos and attached
documents, validated on every write against strict JSON Schemas.

The system is intentionally minimal: no web server, no ORM, no migrations framework —
just a clean Python package you can import or wrap with any interface you like.

---

## Features

| Capability | Supported |
|---|---|
| Add employee | ✅ |
| Edit employee | ✅ |
| Delete employee | ✅ |
| View employee | ✅ |
| Search employees | ✅ |
| Profile photos | ✅ |
| Attach documents | ✅ |
| Up to 1,000 employees | ✅ |
| Attendance / leave | ❌ |
| Payroll | ❌ |
| Role-based access | ❌ |
| Multi-user | ❌ |
| Reports | ❌ |

---

## Requirements

- Python 3.10 or higher
- `jsonschema` (see `requirements.txt`)

---

## Installation

```bash
git clone https://github.com/your-username/mzz-system.git
cd mzz-system
pip install -r requirements.txt
```

---

## Project Structure

```
mzz-system/
│
├─ schemas/
│  ├─ employee.json          # JSON Schema (Draft 7) for employee records
│  └─ document.json          # JSON Schema (Draft 7) for document records
│
├─ migrations/
│  └─ 001_init.sql           # Creates employees + documents tables and indexes
│
├─ src/
│  ├─ __init__.py
│  ├─ schema_loader.py       # Loads and caches schemas; validates dicts
│  ├─ employee_code_generator.py  # Generates MZZ-YYYY-NNNNN codes
│  ├─ crud_service.py        # All DB operations (context manager)
│  └─ file_store.py          # Saves / deletes photos and documents on disk
│
├─ tests/
│  └─ test_employee_creation.py   # 40+ unit tests covering all layers
│
├─ uploads/
│  ├─ photos/                # Profile photos land here
│  └─ documents/             # Employee documents land here
│
├─ data/
│  └─ mzz.db                 # SQLite database (created on first run)
│
├─ requirements.txt
├─ .gitignore
└─ README.md
```

---

## Usage

### Initialize the database

```python
from src.crud_service import CRUDService

with CRUDService() as svc:
    svc.run_migrations()
```

### Create an employee

```python
from src.crud_service import CRUDService

with CRUDService() as svc:
    svc.run_migrations()

    emp = svc.create_employee({
        "first_name":    "Ahmed",
        "last_name":     "Hassan",
        "national_id":   "1234567890",
        "date_of_birth": "1990-06-15",
        "gender":        "male",
        "phone":         "+201234567890",
        "email":         "ahmed@example.com",
        "department":    "Engineering",
        "position":      "Software Engineer",
        "hire_date":     "2024-01-01",
    })

    print(emp["employee_code"])   # MZZ-2024-00001
    print(emp["id"])              # 1
```

### Read / search employees

```python
with CRUDService() as svc:
    # by ID
    emp = svc.get_employee(1)

    # by code
    emp = svc.get_employee_by_code("MZZ-2024-00001")

    # search (name / code / national_id)
    results = svc.search_employees(query="Ahmed")

    # filter by department + status
    results = svc.search_employees(
        department="Engineering",
        employment_status="active",
    )

    # paginated list
    page1 = svc.list_employees(limit=20, offset=0)
    page2 = svc.list_employees(limit=20, offset=20)
```

### Update an employee

```python
with CRUDService() as svc:
    updated = svc.update_employee(1, {
        "department":        "HR",
        "employment_status": "inactive",
    })
```

### Attach a photo

```python
import pathlib
from src.crud_service import CRUDService
from src.file_store   import FileStore

store = FileStore()

with CRUDService() as svc:
    # 1. Save the file to disk
    rel_path = store.save_photo(
        src=pathlib.Path("/tmp/ahmed_photo.jpg"),
        original_filename="ahmed_photo.jpg",
    )

    # 2. Store the path in the employee record
    svc.update_employee(1, {"photo_path": rel_path})
```

### Attach a document

```python
import pathlib
from src.crud_service import CRUDService
from src.file_store   import FileStore

store = FileStore()

with CRUDService() as svc:
    # 1. Save the file to disk
    rel_path = store.save_document(
        src=pathlib.Path("/tmp/ahmed_contract.pdf"),
        original_filename="ahmed_contract.pdf",
    )

    # 2. Create the document record
    doc = svc.attach_document({
        "employee_id":   1,
        "document_type": "employment_contract",
        "file_name":     "ahmed_contract.pdf",
        "file_path":     rel_path,
        "notes":         "Signed copy",
    })

    # 3. List all documents for the employee
    docs = svc.list_documents(1)
```

### Delete an employee (with files)

```python
from src.crud_service import CRUDService
from src.file_store   import FileStore

store = FileStore()

with CRUDService() as svc:
    # Pass file_store to also remove photos and documents from disk
    svc.delete_employee(1, file_store=store)
```

---

## Employee Code Format

Every employee gets a unique, human-readable code generated at creation time:

```
MZZ-YYYY-NNNNN
 │    │     └─ 5-digit sequence, resets each calendar year
 │    └─────── year of registration
 └──────────── system prefix
```

Examples: `MZZ-2024-00001`, `MZZ-2024-00042`, `MZZ-2025-00001`

---

## Document Types

| Value | Description |
|---|---|
| `national_id_copy` | Copy of the national ID or passport |
| `employment_contract` | Signed employment contract |
| `certificate` | Academic or professional certificate |
| `resume` | CV / résumé |
| `other` | Any other document |

---

## Allowed File Types

| Category | Extensions | Max size |
|---|---|---|
| Photo | `.jpg` `.jpeg` `.png` `.webp` | 5 MB |
| Document | `.pdf` `.doc` `.docx` `.png` `.jpg` `.jpeg` | 20 MB |

---

## Running Tests

```bash
# with unittest (no extra install)
python -m unittest tests/test_employee_creation.py -v

# or with pytest
pip install pytest
pytest tests/ -v
```

The test suite covers:

- Schema validation (all required fields, enums, length constraints)
- Employee code generation and parsing
- Full CRUD lifecycle (create, read, update, delete)
- Search and pagination
- The 1,000-employee limit
- Document attach / list / delete / cascade
- FileStore (type validation, size check, unique names, delete)

---

## Architecture

```
employee.json  ──┐
document.json  ──┤
                 ▼
           SchemaLoader
                 │
                 ▼
          CRUDService  ◄── EmployeeCodeGenerator
                 │
                 ▼
              SQLite
           (data/mzz.db)

FileStore (independent)
  uploads/photos/
  uploads/documents/
```

`CRUDService` is the only component that touches the database.
`FileStore` is fully independent — it only handles the filesystem.
Both are wired together only inside `delete_employee` / `delete_document`,
where an optional `FileStore` argument enables physical file cleanup.

---

## Design Decisions

**Why SQLite?**
No server process, no configuration, single file. Perfect for a local
system with up to 1,000 records. WAL mode is enabled for better
concurrent read performance.

**Why JSON Schema instead of Pydantic?**
The schema files in `schemas/` are the single source of truth — readable
by humans, usable by any future frontend, and independent of Python.
Pydantic would embed the schema logic inside the Python classes, making
it harder to inspect or share.

**Why sequential codes instead of UUIDs?**
`MZZ-2024-00001` is meaningful to a person glancing at a printout.
UUIDs are not.

**Why no ORM?**
The query surface is small and well-defined. Raw SQL with named bindings
is easier to audit and has zero magic.

---

## Limitations (V1)

This is V1. The following are explicitly out of scope:

- Attendance, leave, and payroll
- Role-based access control
- Multi-user / networked access
- Reporting and analytics
- Import / export (CSV, Excel)

---

## License

MIT

#MZz Hub

created by Mohamed Ziena