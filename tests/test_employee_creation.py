"""
Tests — Employee Creation & Core CRUD
======================================
Run from the project root:

    python -m unittest tests/test_employee_creation.py -v

or with pytest (if installed):

    pytest tests/ -v
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from src.crud_service import (
    CRUDService,
    DuplicateError,
    EmployeeLimitError,
    NotFoundError,
)
from src.file_store import FileStore, FileStoreError
from src.schema_loader import SchemaLoader, SchemaValidationError
from src.employee_code_generator import EmployeeCodeGenerator


# ── Fixtures ─────────────────────────────────────────────────

def _valid_employee(**overrides) -> dict:
    """Return a minimal valid employee payload, with optional overrides."""
    base = {
        "first_name":        "Ahmed",
        "last_name":         "Hassan",
        "national_id":       "1234567890",
        "date_of_birth":     "1990-01-15",
        "gender":            "male",
        "phone":             "+201234567890",
        "email":             "ahmed.hassan@example.com",
        "address":           "Cairo, Egypt",
        "department":        "Engineering",
        "position":          "Software Engineer",
        "hire_date":         "2024-01-01",
        "employment_status": "active",
    }
    return {**base, **overrides}


# ── Base test class with shared setUp/tearDown ───────────────

class BaseTestCase(unittest.TestCase):
    """Creates an isolated in-memory (temp file) database per test."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        db_path = pathlib.Path(self.tmp_dir) / "test.db"
        self.svc = CRUDService(db_path=db_path)
        self.svc.connect()
        self.svc.run_migrations()
        self.store = FileStore(base_dir=pathlib.Path(self.tmp_dir) / "uploads")

    def tearDown(self):
        self.svc.close()

    # helpers
    def _add(self, **overrides) -> dict:
        return self.svc.create_employee(_valid_employee(**overrides))


# ════════════════════════════════════════════════════════════
# 1. Schema Validation
# ════════════════════════════════════════════════════════════

class TestSchemaValidation(BaseTestCase):

    def test_valid_employee_passes(self):
        """Full valid payload should not raise."""
        SchemaLoader.validate_employee(_valid_employee())

    def test_missing_required_first_name(self):
        bad = _valid_employee()
        del bad["first_name"]
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)

    def test_missing_required_national_id(self):
        bad = _valid_employee()
        del bad["national_id"]
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)

    def test_invalid_gender_value(self):
        bad = _valid_employee(gender="unknown")
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)

    def test_invalid_employment_status(self):
        bad = _valid_employee(employment_status="retired")
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)

    def test_first_name_too_short(self):
        bad = _valid_employee(first_name="A")
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)

    def test_notes_too_long(self):
        bad = _valid_employee(notes="x" * 1001)
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)

    def test_optional_fields_may_be_omitted(self):
        """phone, email, address, notes are all optional."""
        minimal = {
            "first_name":    "Sara",
            "last_name":     "Ali",
            "national_id":   "0000000001",
            "date_of_birth": "1995-05-20",
            "gender":        "female",
            "hire_date":     "2023-03-01",
            "department":    "HR",
            "position":      "HR Manager",
        }
        SchemaLoader.validate_employee(minimal)   # must not raise

    def test_additional_properties_rejected(self):
        bad = _valid_employee(unknown_field="x")
        with self.assertRaises(SchemaValidationError):
            SchemaLoader.validate_employee(bad)


# ════════════════════════════════════════════════════════════
# 2. Employee Code Generation
# ════════════════════════════════════════════════════════════

class TestEmployeeCodeGenerator(BaseTestCase):

    def test_first_code_starts_at_00001(self):
        emp = self._add()
        parts = emp["employee_code"].split("-")
        self.assertEqual(parts[0], "MZZ")
        self.assertEqual(parts[2], "00001")

    def test_second_code_is_00002(self):
        self._add()
        emp2 = self._add(national_id="9999999999", email="b@b.com")
        self.assertEqual(emp2["employee_code"].split("-")[-1], "00002")

    def test_codes_are_sequential(self):
        codes = []
        for i in range(5):
            emp = self._add(national_id=f"100000000{i}", email=f"u{i}@x.com")
            codes.append(int(emp["employee_code"].split("-")[-1]))
        self.assertEqual(codes, [1, 2, 3, 4, 5])

    def test_parse_valid_code(self):
        result = EmployeeCodeGenerator.parse("MZZ-2024-00042")
        self.assertEqual(result["prefix"],   "MZZ")
        self.assertEqual(result["year"],     2024)
        self.assertEqual(result["sequence"], 42)

    def test_parse_invalid_code_raises(self):
        with self.assertRaises(ValueError):
            EmployeeCodeGenerator.parse("BAD-2024-00001")

    def test_parse_malformed_code_raises(self):
        with self.assertRaises(ValueError):
            EmployeeCodeGenerator.parse("MZZ2024-00001")


# ════════════════════════════════════════════════════════════
# 3. Employee CRUD
# ════════════════════════════════════════════════════════════

class TestCreateEmployee(BaseTestCase):

    def test_create_returns_dict_with_id(self):
        emp = self._add()
        self.assertIn("id", emp)
        self.assertIsInstance(emp["id"], int)

    def test_create_persists_all_fields(self):
        emp = self._add()
        self.assertEqual(emp["first_name"], "Ahmed")
        self.assertEqual(emp["department"], "Engineering")
        self.assertEqual(emp["employment_status"], "active")

    def test_create_defaults_employment_status_to_active(self):
        data = _valid_employee()
        data.pop("employment_status", None)
        emp = self.svc.create_employee(data)
        self.assertEqual(emp["employment_status"], "active")

    def test_duplicate_national_id_raises(self):
        self._add()
        with self.assertRaises(DuplicateError):
            self._add(email="other@example.com")  # same national_id

    def test_missing_required_field_raises(self):
        bad = _valid_employee()
        del bad["department"]
        with self.assertRaises(SchemaValidationError):
            self.svc.create_employee(bad)


class TestGetEmployee(BaseTestCase):

    def test_get_by_id(self):
        emp  = self._add()
        fetched = self.svc.get_employee(emp["id"])
        self.assertEqual(fetched["national_id"], emp["national_id"])

    def test_get_by_code(self):
        emp = self._add()
        fetched = self.svc.get_employee_by_code(emp["employee_code"])
        self.assertEqual(fetched["id"], emp["id"])

    def test_get_nonexistent_raises(self):
        with self.assertRaises(NotFoundError):
            self.svc.get_employee(99999)

    def test_get_nonexistent_code_raises(self):
        with self.assertRaises(NotFoundError):
            self.svc.get_employee_by_code("MZZ-2099-99999")


class TestUpdateEmployee(BaseTestCase):

    def test_update_single_field(self):
        emp     = self._add()
        updated = self.svc.update_employee(emp["id"], {"department": "HR"})
        self.assertEqual(updated["department"], "HR")

    def test_update_preserves_other_fields(self):
        emp     = self._add()
        updated = self.svc.update_employee(emp["id"], {"department": "HR"})
        self.assertEqual(updated["first_name"], "Ahmed")

    def test_update_employment_status(self):
        emp     = self._add()
        updated = self.svc.update_employee(emp["id"], {"employment_status": "inactive"})
        self.assertEqual(updated["employment_status"], "inactive")

    def test_update_with_invalid_status_raises(self):
        emp = self._add()
        with self.assertRaises(SchemaValidationError):
            self.svc.update_employee(emp["id"], {"employment_status": "fired"})

    def test_update_nonexistent_raises(self):
        with self.assertRaises(NotFoundError):
            self.svc.update_employee(99999, {"department": "HR"})

    def test_update_with_no_changes_returns_existing(self):
        emp     = self._add()
        result  = self.svc.update_employee(emp["id"], {})
        self.assertEqual(result["id"], emp["id"])


class TestDeleteEmployee(BaseTestCase):

    def test_delete_removes_employee(self):
        emp = self._add()
        self.svc.delete_employee(emp["id"])
        with self.assertRaises(NotFoundError):
            self.svc.get_employee(emp["id"])

    def test_delete_nonexistent_raises(self):
        with self.assertRaises(NotFoundError):
            self.svc.delete_employee(99999)

    def test_delete_cascades_documents(self):
        emp = self._add()
        self.svc.attach_document({
            "employee_id":   emp["id"],
            "document_type": "resume",
            "file_name":     "cv.pdf",
            "file_path":     "uploads/documents/fake.pdf",
        })
        self.svc.delete_employee(emp["id"])
        docs = self.svc.list_documents(emp["id"])
        self.assertEqual(docs, [])


# ════════════════════════════════════════════════════════════
# 4. Search & List
# ════════════════════════════════════════════════════════════

class TestSearch(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.svc.create_employee(_valid_employee(
            national_id="1000000001", email="a@x.com",
            first_name="Ahmed", department="Engineering",
        ))
        self.svc.create_employee(_valid_employee(
            national_id="1000000002", email="b@x.com",
            first_name="Sara", department="HR",
        ))
        self.svc.create_employee(_valid_employee(
            national_id="1000000003", email="c@x.com",
            first_name="Mohamed", department="Engineering",
            employment_status="inactive",
        ))

    def test_list_all(self):
        results = self.svc.list_employees(limit=100)
        self.assertEqual(len(results), 3)

    def test_search_by_first_name(self):
        results = self.svc.search_employees(query="Sara")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["first_name"], "Sara")

    def test_search_by_department(self):
        results = self.svc.search_employees(department="Engineering")
        self.assertEqual(len(results), 2)

    def test_search_by_status(self):
        results = self.svc.search_employees(employment_status="inactive")
        self.assertEqual(len(results), 1)

    def test_search_no_match_returns_empty(self):
        results = self.svc.search_employees(query="Ziad")
        self.assertEqual(results, [])

    def test_combined_filters(self):
        results = self.svc.search_employees(
            department="Engineering",
            employment_status="inactive"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["first_name"], "Mohamed")

    def test_pagination_limit(self):
        results = self.svc.list_employees(limit=2, offset=0)
        self.assertEqual(len(results), 2)

    def test_pagination_offset(self):
        page1 = self.svc.list_employees(limit=2, offset=0)
        page2 = self.svc.list_employees(limit=2, offset=2)
        self.assertEqual(len(page1), 2)
        self.assertEqual(len(page2), 1)


# ════════════════════════════════════════════════════════════
# 5. Employee Limit
# ════════════════════════════════════════════════════════════

class TestEmployeeLimit(BaseTestCase):

    def test_limit_enforced(self):
        import src.crud_service as cs
        original = cs.MAX_EMPLOYEES
        cs.MAX_EMPLOYEES = 2
        try:
            self._add(national_id="L000000001", email="l1@x.com")
            self._add(national_id="L000000002", email="l2@x.com")
            with self.assertRaises(EmployeeLimitError):
                self._add(national_id="L000000003", email="l3@x.com")
        finally:
            cs.MAX_EMPLOYEES = original

    def test_count_employees(self):
        self.assertEqual(self.svc.count_employees(), 0)
        self._add()
        self.assertEqual(self.svc.count_employees(), 1)


# ════════════════════════════════════════════════════════════
# 6. Documents
# ════════════════════════════════════════════════════════════

class TestDocuments(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.emp = self._add()

    def test_attach_document_returns_record(self):
        doc = self.svc.attach_document({
            "employee_id":   self.emp["id"],
            "document_type": "national_id_copy",
            "file_name":     "id.pdf",
            "file_path":     "uploads/documents/abc.pdf",
        })
        self.assertIn("id", doc)
        self.assertEqual(doc["document_type"], "national_id_copy")

    def test_list_documents(self):
        for dtype in ("resume", "certificate"):
            self.svc.attach_document({
                "employee_id":   self.emp["id"],
                "document_type": dtype,
                "file_name":     f"{dtype}.pdf",
                "file_path":     f"uploads/documents/{dtype}.pdf",
            })
        docs = self.svc.list_documents(self.emp["id"])
        self.assertEqual(len(docs), 2)

    def test_get_document(self):
        doc = self.svc.attach_document({
            "employee_id":   self.emp["id"],
            "document_type": "resume",
            "file_name":     "cv.pdf",
            "file_path":     "uploads/documents/cv.pdf",
        })
        fetched = self.svc.get_document(doc["id"])
        self.assertEqual(fetched["file_name"], "cv.pdf")

    def test_delete_document(self):
        doc = self.svc.attach_document({
            "employee_id":   self.emp["id"],
            "document_type": "resume",
            "file_name":     "cv.pdf",
            "file_path":     "uploads/documents/cv.pdf",
        })
        self.svc.delete_document(doc["id"])
        with self.assertRaises(NotFoundError):
            self.svc.get_document(doc["id"])

    def test_attach_document_invalid_type_raises(self):
        with self.assertRaises(SchemaValidationError):
            self.svc.attach_document({
                "employee_id":   self.emp["id"],
                "document_type": "payslip",     # not in enum
                "file_name":     "pay.pdf",
                "file_path":     "uploads/documents/pay.pdf",
            })

    def test_attach_document_unknown_employee_raises(self):
        with self.assertRaises(NotFoundError):
            self.svc.attach_document({
                "employee_id":   99999,
                "document_type": "resume",
                "file_name":     "cv.pdf",
                "file_path":     "uploads/documents/cv.pdf",
            })

    def test_list_documents_empty_after_delete(self):
        doc = self.svc.attach_document({
            "employee_id":   self.emp["id"],
            "document_type": "certificate",
            "file_name":     "cert.pdf",
            "file_path":     "uploads/documents/cert.pdf",
        })
        self.svc.delete_document(doc["id"])
        self.assertEqual(self.svc.list_documents(self.emp["id"]), [])


# ════════════════════════════════════════════════════════════
# 7. FileStore
# ════════════════════════════════════════════════════════════

class TestFileStore(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.store = FileStore(base_dir=self.tmp / "uploads")

    def test_directories_created(self):
        self.assertTrue((self.tmp / "uploads" / "photos").exists())
        self.assertTrue((self.tmp / "uploads" / "documents").exists())

    def test_save_photo_returns_relative_path(self):
        src = self.tmp / "photo.jpg"
        src.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)   # minimal JPEG header
        rel = self.store.save_photo(src, "photo.jpg")
        self.assertTrue(rel.startswith("uploads/photos/"))
        self.assertTrue(rel.endswith(".jpg"))

    def test_save_document_returns_relative_path(self):
        src = self.tmp / "doc.pdf"
        src.write_bytes(b"%PDF-1.4")
        rel = self.store.save_document(src, "doc.pdf")
        self.assertTrue(rel.startswith("uploads/documents/"))
        self.assertTrue(rel.endswith(".pdf"))

    def test_disallowed_photo_extension_raises(self):
        src = self.tmp / "virus.exe"
        src.write_bytes(b"MZ")
        with self.assertRaises(FileStoreError):
            self.store.save_photo(src, "virus.exe")

    def test_disallowed_document_extension_raises(self):
        src = self.tmp / "file.txt"
        src.write_bytes(b"hello")
        with self.assertRaises(FileStoreError):
            self.store.save_document(src, "file.txt")

    def test_delete_file_removes_file(self):
        src = self.tmp / "photo.png"
        src.write_bytes(b"\x89PNG")
        rel = self.store.save_photo(src, "photo.png")
        self.assertTrue(self.store.exists(rel))
        self.store.delete_file(rel)
        self.assertFalse(self.store.exists(rel))

    def test_delete_none_does_not_raise(self):
        self.store.delete_file(None)    # must not raise

    def test_delete_missing_file_does_not_raise(self):
        self.store.delete_file("uploads/photos/nonexistent.jpg")

    def test_get_absolute_path_returns_none_for_missing(self):
        result = self.store.get_absolute_path("uploads/photos/ghost.jpg")
        self.assertIsNone(result)

    def test_each_upload_gets_unique_name(self):
        src = self.tmp / "same.jpg"
        src.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
        rel1 = self.store.save_photo(src, "same.jpg")
        rel2 = self.store.save_photo(src, "same.jpg")
        self.assertNotEqual(rel1, rel2)


# ════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
