"""
src/crud_service.py  — FULL FILE (updated)
==========================================
Added in this version
---------------------
- PersonCodeGenerator  (inline, similar to EmployeeCodeGenerator)
- create_person / get_person / get_person_by_code
- list_persons / search_persons / count_persons
- update_person / delete_person
- attach_person_document / get_person_document
- list_person_documents / delete_person_document
- _compute_profile_complete  (auto-flags missing required fields)
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any, Optional

from .employee_code_generator import EmployeeCodeGenerator
from .file_store import FileStore
from .schema_loader import SchemaLoader


# ── Constants ────────────────────────────────────────────────
DB_PATH        = pathlib.Path(__file__).parent.parent / "data" / "mzz.db"
MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "migrations"
MAX_EMPLOYEES  = 1_000
MAX_PERSONS    = 10_000

# Employee updatable fields
_UPDATABLE_FIELDS = (
    "first_name", "last_name", "national_id", "date_of_birth",
    "gender", "phone", "email", "address", "department",
    "position", "hire_date", "employment_status", "photo_path", "notes",
)
_DB_FIELDS = ("id", "employee_code", "person_code",
              "created_at", "updated_at", "uploaded_at",
              "profile_complete")

# Person updatable fields
_PERSON_UPDATABLE = (
    "first_name", "last_name", "national_id", "date_of_birth",
    "gender", "phone", "phone_alt", "email", "address",
    "person_type", "status", "photo_path", "notes",
)

# Fields required for profile_complete = 1
_PERSON_REQUIRED = (
    "first_name", "last_name", "phone",
    "national_id", "date_of_birth", "gender",
)

# Person document types
PERSON_DOC_TYPES = (
    "national_id_copy", "contract", "invoice",
    "certificate", "resume", "other",
)


# ── Custom Exceptions ────────────────────────────────────────

class EmployeeLimitError(Exception):
    """Raised when the 1,000-employee cap is reached."""

class PersonLimitError(Exception):
    """Raised when the 10,000-person cap is reached."""

class NotFoundError(Exception):
    """Raised when a requested record does not exist."""

class DuplicateError(Exception):
    """Raised when a unique constraint would be violated."""


# ── Person Code Generator ────────────────────────────────────

class _PersonCodeGenerator:
    """Generates sequential codes: MZZ-P-YYYY-NNNNN."""

    @staticmethod
    def generate(conn: sqlite3.Connection) -> str:
        import datetime
        year = datetime.date.today().year
        row  = conn.execute(
            "SELECT COUNT(*) FROM persons"
        ).fetchone()
        seq = (row[0] or 0) + 1
        return f"MZZ-P-{year}-{seq:05d}"


# ── Service ──────────────────────────────────────────────────

class CRUDService:
    """Core CRUD service. One instance per logical session."""

    def __init__(self, db_path: pathlib.Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    # ── Connection ───────────────────────────────────────────

    def connect(self) -> None:
        self._conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "CRUDService":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError(
                "Database is not connected. "
                "Use 'with CRUDService() as svc:' or call svc.connect() first."
            )
        return self._conn

    # ── Migrations ───────────────────────────────────────────

    def run_migrations(self) -> None:
        """Execute all *.sql files in migrations/ in lexicographic order."""
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            self.conn.executescript(f.read_text(encoding="utf-8"))
        self.conn.commit()

    # ── Internal helpers ─────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def _count_employees(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM employees"
        ).fetchone()[0]

    def _count_persons(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM persons"
        ).fetchone()[0]

    @staticmethod
    def _compute_profile_complete(data: dict[str, Any]) -> int:
        """Return 1 if all required person fields are present and non-empty."""
        for field in _PERSON_REQUIRED:
            val = data.get(field)
            if val is None or str(val).strip() == "":
                return 0
        return 1

    # ════════════════════════════════════════════════════════
    # EMPLOYEE — Create
    # ════════════════════════════════════════════════════════

    def create_employee(self, data: dict[str, Any]) -> dict[str, Any]:
        if self._count_employees() >= MAX_EMPLOYEES:
            raise EmployeeLimitError(
                f"The system has reached its limit of {MAX_EMPLOYEES:,} employees."
            )
        SchemaLoader.validate_employee(data)
        existing = self.conn.execute(
            "SELECT id FROM employees WHERE national_id = ?",
            (data["national_id"],),
        ).fetchone()
        if existing:
            raise DuplicateError(
                f"An employee with national_id '{data['national_id']}' already exists."
            )
        employee_code = EmployeeCodeGenerator.generate(self.conn)
        cursor = self.conn.execute(
            """
            INSERT INTO employees (
                employee_code, first_name, last_name, national_id,
                date_of_birth, gender, phone, email, address,
                department, position, hire_date, employment_status,
                photo_path, notes
            ) VALUES (
                :code, :first_name, :last_name, :national_id,
                :date_of_birth, :gender, :phone, :email, :address,
                :department, :position, :hire_date, :employment_status,
                :photo_path, :notes
            )
            """,
            {
                "code":              employee_code,
                "first_name":        data["first_name"],
                "last_name":         data["last_name"],
                "national_id":       data["national_id"],
                "date_of_birth":     data["date_of_birth"],
                "gender":            data["gender"],
                "phone":             data.get("phone"),
                "email":             data.get("email"),
                "address":           data.get("address"),
                "department":        data["department"],
                "position":          data["position"],
                "hire_date":         data["hire_date"],
                "employment_status": data.get("employment_status", "active"),
                "photo_path":        data.get("photo_path"),
                "notes":             data.get("notes"),
            },
        )
        self.conn.commit()
        return self.get_employee(cursor.lastrowid)

    # ── EMPLOYEE — Read ──────────────────────────────────────

    def get_employee(self, employee_id: int) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No employee found with id={employee_id}.")
        return self._row_to_dict(row)

    def get_employee_by_code(self, code: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM employees WHERE employee_code = ?", (code,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No employee found with code='{code}'.")
        return self._row_to_dict(row)

    def list_employees(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        return self.search_employees(limit=limit, offset=offset)

    def search_employees(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        employment_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params:     list[Any] = []
        if query:
            like = f"%{query}%"
            conditions.append(
                "(first_name LIKE ? OR last_name LIKE ? "
                "OR employee_code LIKE ? OR national_id LIKE ?)"
            )
            params.extend([like, like, like, like])
        if department:
            conditions.append("department = ?")
            params.append(department)
        if employment_status:
            conditions.append("employment_status = ?")
            params.append(employment_status)
        where  = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params += [limit, offset]
        rows = self.conn.execute(
            f"SELECT * FROM employees {where} ORDER BY employee_code LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count_employees(self) -> int:
        return self._count_employees()

    # ── EMPLOYEE — Update ────────────────────────────────────

    def update_employee(self, employee_id: int, data: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_employee(employee_id)
        merged = {
            k: v for k, v in {**existing, **data}.items()
            if k not in _DB_FIELDS
        }
        SchemaLoader.validate_employee(merged)
        set_fields = [f for f in _UPDATABLE_FIELDS if f in data]
        if not set_fields:
            return existing
        set_clause = ", ".join(f"{f} = ?" for f in set_fields)
        values     = [data[f] for f in set_fields] + [employee_id]
        self.conn.execute(
            f"UPDATE employees SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self.conn.commit()
        return self.get_employee(employee_id)

    # ── EMPLOYEE — Delete ────────────────────────────────────

    def delete_employee(
        self, employee_id: int, file_store: Optional[FileStore] = None
    ) -> None:
        employee = self.get_employee(employee_id)
        if file_store:
            for doc in self.list_documents(employee_id):
                file_store.delete_file(doc.get("file_path"))
            file_store.delete_file(employee.get("photo_path"))
        self.conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self.conn.commit()

    # ── EMPLOYEE DOCUMENTS ───────────────────────────────────

    def attach_document(self, data: dict[str, Any]) -> dict[str, Any]:
        SchemaLoader.validate_document(data)
        self.get_employee(data["employee_id"])
        cursor = self.conn.execute(
            """
            INSERT INTO documents (employee_id, document_type, file_name, file_path, notes)
            VALUES (:employee_id, :document_type, :file_name, :file_path, :notes)
            """,
            {
                "employee_id":   data["employee_id"],
                "document_type": data["document_type"],
                "file_name":     data["file_name"],
                "file_path":     data["file_path"],
                "notes":         data.get("notes"),
            },
        )
        self.conn.commit()
        return self.get_document(cursor.lastrowid)

    def get_document(self, document_id: int) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No document found with id={document_id}.")
        return self._row_to_dict(row)

    def list_documents(self, employee_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM documents WHERE employee_id = ? ORDER BY uploaded_at DESC",
            (employee_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_document(
        self, document_id: int, file_store: Optional[FileStore] = None
    ) -> None:
        doc = self.get_document(document_id)
        if file_store:
            file_store.delete_file(doc.get("file_path"))
        self.conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        self.conn.commit()

    # ════════════════════════════════════════════════════════
    # PERSONS — Create
    # ════════════════════════════════════════════════════════

    def create_person(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new person record.

        Parameters
        ----------
        data : dict
            Required : first_name, last_name
            Optional : national_id, date_of_birth, gender,
                       phone, phone_alt, email, address,
                       person_type, status, photo_path, notes

        Returns
        -------
        dict  — the newly created person row.

        Raises
        ------
        PersonLimitError   — cap of 10,000 reached.
        DuplicateError     — national_id already exists.
        ValueError         — first_name or last_name missing.
        """
        if self._count_persons() >= MAX_PERSONS:
            raise PersonLimitError(
                f"The system has reached its limit of {MAX_PERSONS:,} persons."
            )

        # Minimal validation
        if not data.get("first_name", "").strip():
            raise ValueError("first_name is required.")
        if not data.get("last_name", "").strip():
            raise ValueError("last_name is required.")

        # Duplicate national_id check (only if provided)
        nat_id = data.get("national_id")
        if nat_id:
            existing = self.conn.execute(
                "SELECT id FROM persons WHERE national_id = ?", (nat_id,)
            ).fetchone()
            if existing:
                raise DuplicateError(
                    f"A person with national_id '{nat_id}' already exists "
                    f"(id={existing['id']})."
                )

        person_code      = _PersonCodeGenerator.generate(self.conn)
        profile_complete = self._compute_profile_complete(data)

        cursor = self.conn.execute(
            """
            INSERT INTO persons (
                person_code, first_name, last_name, national_id,
                date_of_birth, gender, phone, phone_alt, email, address,
                person_type, status, profile_complete, photo_path, notes
            ) VALUES (
                :person_code, :first_name, :last_name, :national_id,
                :date_of_birth, :gender, :phone, :phone_alt, :email, :address,
                :person_type, :status, :profile_complete, :photo_path, :notes
            )
            """,
            {
                "person_code":       person_code,
                "first_name":        data["first_name"].strip(),
                "last_name":         data["last_name"].strip(),
                "national_id":       data.get("national_id"),
                "date_of_birth":     data.get("date_of_birth"),
                "gender":            data.get("gender"),
                "phone":             data.get("phone"),
                "phone_alt":         data.get("phone_alt"),
                "email":             data.get("email"),
                "address":           data.get("address"),
                "person_type":       data.get("person_type", "client"),
                "status":            data.get("status", "active"),
                "profile_complete":  profile_complete,
                "photo_path":        data.get("photo_path"),
                "notes":             data.get("notes"),
            },
        )
        self.conn.commit()
        return self.get_person(cursor.lastrowid)

    # ── PERSONS — Read ───────────────────────────────────────

    def get_person(self, person_id: int) -> dict[str, Any]:
        """Fetch a single person by primary key."""
        row = self.conn.execute(
            "SELECT * FROM persons WHERE id = ?", (person_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No person found with id={person_id}.")
        return self._row_to_dict(row)

    def get_person_by_code(self, code: str) -> dict[str, Any]:
        """Fetch a single person by their MZZ-P code."""
        row = self.conn.execute(
            "SELECT * FROM persons WHERE person_code = ?", (code,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No person found with code='{code}'.")
        return self._row_to_dict(row)

    def list_persons(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Return a paginated list of all persons ordered by person_code."""
        return self.search_persons(limit=limit, offset=offset)

    def search_persons(
        self,
        query:            Optional[str] = None,
        person_type:      Optional[str] = None,
        status:           Optional[str] = None,
        profile_complete: Optional[int] = None,
        limit:            int = 50,
        offset:           int = 0,
    ) -> list[dict[str, Any]]:
        """
        Search persons with optional filters.

        Parameters
        ----------
        query            : free-text across name / code / national_id / phone / email
        person_type      : client | supplier | partner | contractor | other
        status           : active | inactive
        profile_complete : 1 = complete only, 0 = incomplete only
        limit / offset   : pagination
        """
        conditions: list[str] = []
        params:     list[Any] = []

        if query:
            like = f"%{query}%"
            conditions.append(
                "(first_name LIKE ? OR last_name LIKE ? "
                "OR person_code LIKE ? OR national_id LIKE ? "
                "OR phone LIKE ? OR email LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])

        if person_type:
            conditions.append("person_type = ?")
            params.append(person_type)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if profile_complete is not None:
            conditions.append("profile_complete = ?")
            params.append(profile_complete)

        where  = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params += [limit, offset]

        rows = self.conn.execute(
            f"""
            SELECT * FROM persons
            {where}
            ORDER BY person_code
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count_persons(
        self,
        person_type:      Optional[str] = None,
        status:           Optional[str] = None,
        profile_complete: Optional[int] = None,
    ) -> int:
        """Return count of persons matching optional filters."""
        conditions: list[str] = []
        params:     list[Any] = []
        if person_type:
            conditions.append("person_type = ?")
            params.append(person_type)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if profile_complete is not None:
            conditions.append("profile_complete = ?")
            params.append(profile_complete)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.conn.execute(
            f"SELECT COUNT(*) FROM persons {where}", params
        ).fetchone()[0]

    # ── PERSONS — Update ─────────────────────────────────────

    def update_person(
        self, person_id: int, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Partially update a person record.
        Recomputes profile_complete automatically after every update.

        Raises
        ------
        NotFoundError  — person_id does not exist.
        DuplicateError — new national_id conflicts with another record.
        """
        existing = self.get_person(person_id)   # raises NotFoundError

        # Duplicate national_id check (only if changing it)
        new_nat_id = data.get("national_id")
        if new_nat_id and new_nat_id != existing.get("national_id"):
            conflict = self.conn.execute(
                "SELECT id FROM persons WHERE national_id = ? AND id != ?",
                (new_nat_id, person_id),
            ).fetchone()
            if conflict:
                raise DuplicateError(
                    f"national_id '{new_nat_id}' is already used by person id={conflict['id']}."
                )

        set_fields = [f for f in _PERSON_UPDATABLE if f in data]
        if not set_fields:
            return existing

        # Merge for profile_complete computation
        merged = {**existing, **data}
        profile_complete = self._compute_profile_complete(merged)

        set_clause = ", ".join(f"{f} = ?" for f in set_fields)
        values     = [data[f] for f in set_fields]
        values    += [profile_complete, person_id]

        self.conn.execute(
            f"""
            UPDATE persons
               SET {set_clause},
                   profile_complete = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            values,
        )
        self.conn.commit()
        return self.get_person(person_id)

    # ── PERSONS — Delete ─────────────────────────────────────

    def delete_person(
        self, person_id: int, file_store: Optional[FileStore] = None
    ) -> None:
        """
        Delete a person and — via ON DELETE CASCADE — all their documents.

        Raises
        ------
        NotFoundError — person_id does not exist.
        """
        person = self.get_person(person_id)   # raises NotFoundError
        if file_store:
            for doc in self.list_person_documents(person_id):
                file_store.delete_file(doc.get("file_path"))
            file_store.delete_file(person.get("photo_path"))
        self.conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        self.conn.commit()

    # ════════════════════════════════════════════════════════
    # PERSON DOCUMENTS — Attach / List / Delete
    # ════════════════════════════════════════════════════════

    def attach_person_document(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Attach a document to a person.

        data keys
        ---------
        person_id, document_type, file_name, file_path, notes (optional)

        Raises
        ------
        NotFoundError — person_id does not exist.
        ValueError    — document_type not in allowed list.
        """
        self.get_person(data["person_id"])   # raises NotFoundError

        if data.get("document_type") not in PERSON_DOC_TYPES:
            raise ValueError(
                f"document_type must be one of {PERSON_DOC_TYPES}. "
                f"Got: '{data.get('document_type')}'"
            )
        if not data.get("file_name"):
            raise ValueError("file_name is required.")
        if not data.get("file_path"):
            raise ValueError("file_path is required.")

        cursor = self.conn.execute(
            """
            INSERT INTO person_documents
                (person_id, document_type, file_name, file_path, notes)
            VALUES
                (:person_id, :document_type, :file_name, :file_path, :notes)
            """,
            {
                "person_id":     data["person_id"],
                "document_type": data["document_type"],
                "file_name":     data["file_name"],
                "file_path":     data["file_path"],
                "notes":         data.get("notes"),
            },
        )
        self.conn.commit()
        return self.get_person_document(cursor.lastrowid)

    def get_person_document(self, document_id: int) -> dict[str, Any]:
        """Fetch a single person document by primary key."""
        row = self.conn.execute(
            "SELECT * FROM person_documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No person document found with id={document_id}.")
        return self._row_to_dict(row)

    def list_person_documents(self, person_id: int) -> list[dict[str, Any]]:
        """Return all documents attached to person_id, newest first."""
        rows = self.conn.execute(
            """
            SELECT * FROM person_documents
             WHERE person_id = ?
             ORDER BY uploaded_at DESC
            """,
            (person_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_person_document(
        self, document_id: int, file_store: Optional[FileStore] = None
    ) -> None:
        """
        Delete a person document (and optionally its file).

        Raises
        ------
        NotFoundError — document_id does not exist.
        """
        doc = self.get_person_document(document_id)   # raises NotFoundError
        if file_store:
            file_store.delete_file(doc.get("file_path"))
        self.conn.execute(
            "DELETE FROM person_documents WHERE id = ?", (document_id,)
        )
        self.conn.commit()
