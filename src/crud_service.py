"""
CRUD Service
============
The single entry-point for all database operations in MZz System V1.

Responsibilities
----------------
- Opens and manages the SQLite connection (WAL mode + FK enforcement).
- Runs SQL migrations on first use.
- Provides create / read / update / delete operations for employees.
- Provides attach / list / delete operations for employee documents.
- Delegates schema validation to SchemaLoader.
- Delegates code generation to EmployeeCodeGenerator.
- Optionally delegates file deletion to FileStore when removing records.

Usage (context manager — recommended)
--------------------------------------
    from src.crud_service import CRUDService
    from src.file_store  import FileStore

    store = FileStore()

    with CRUDService() as svc:
        svc.run_migrations()
        emp = svc.create_employee({
            "first_name":  "Ahmed",
            "last_name":   "Hassan",
            "national_id": "1234567890",
            "date_of_birth": "1990-06-15",
            "gender":      "male",
            "hire_date":   "2024-01-01",
            "department":  "Engineering",
            "position":    "Software Engineer",
        })
        print(emp["employee_code"])   # → MZZ-2024-00001

Usage (manual open/close)
--------------------------
    svc = CRUDService()
    svc.connect()
    svc.run_migrations()
    ...
    svc.close()
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import TYPE_CHECKING, Any, Optional

from .employee_code_generator import EmployeeCodeGenerator
from .file_store import FileStore
from .schema_loader import SchemaLoader

if TYPE_CHECKING:
    pass  # avoid circular imports if needed in the future


# ── Constants ────────────────────────────────────────────────
DB_PATH        = pathlib.Path(__file__).parent.parent / "data" / "mzz.db"
MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "migrations"
MAX_EMPLOYEES  = 1_000

# Fields that callers may update (excludes DB-managed / immutable fields)
_UPDATABLE_FIELDS = (
    "first_name", "last_name", "national_id", "date_of_birth",
    "gender", "phone", "email", "address", "department",
    "position", "hire_date", "employment_status", "photo_path", "notes",
)

# Fields produced by the DB that must be stripped before schema validation
_DB_FIELDS = ("id", "employee_code", "created_at", "updated_at", "uploaded_at")


# ── Custom Exceptions ────────────────────────────────────────

class EmployeeLimitError(Exception):
    """Raised when the 1,000-employee cap is reached."""


class NotFoundError(Exception):
    """Raised when a requested record does not exist in the database."""


class DuplicateError(Exception):
    """Raised when a unique constraint would be violated (e.g. national_id)."""


# ── Service ──────────────────────────────────────────────────

class CRUDService:
    """Core CRUD service.  One instance per logical session."""

    def __init__(self, db_path: pathlib.Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    # ──────────────────────────────────────────────────────────
    # Connection management
    # ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the SQLite connection with WAL journal mode and FK support."""
        self._conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")

    def close(self) -> None:
        """Close the connection if open."""
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
        """Active database connection (raises if not yet connected)."""
        if self._conn is None:
            raise RuntimeError(
                "Database is not connected. "
                "Use 'with CRUDService() as svc:' or call svc.connect() first."
            )
        return self._conn

    # ──────────────────────────────────────────────────────────
    # Migrations
    # ──────────────────────────────────────────────────────────

    def run_migrations(self) -> None:
        """Execute all *.sql files in ``migrations/`` in lexicographic order.

        Safe to call multiple times — SQL files use ``CREATE TABLE IF NOT EXISTS``.
        """
        for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = migration_file.read_text(encoding="utf-8")
            self.conn.executescript(sql)
        self.conn.commit()

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def _count_employees(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM employees").fetchone()
        return row[0]

    # ──────────────────────────────────────────────────────────
    # Employee — Create
    # ──────────────────────────────────────────────────────────

    def create_employee(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new employee record.

        Parameters
        ----------
        data : dict
            Employee fields.  Must satisfy ``schemas/employee.json``.
            Do **not** include ``id``, ``employee_code``, ``created_at``,
            or ``updated_at`` — those are managed by the system.

        Returns
        -------
        dict
            The newly created employee row (all DB columns included).

        Raises
        ------
        EmployeeLimitError
            If the 1,000-employee cap has already been reached.
        SchemaValidationError
            If *data* fails JSON Schema validation.
        DuplicateError
            If an employee with the same ``national_id`` already exists.
        """
        if self._count_employees() >= MAX_EMPLOYEES:
            raise EmployeeLimitError(
                f"The system has reached its limit of {MAX_EMPLOYEES:,} employees. "
                "MZz System V1 does not support more than this."
            )

        SchemaLoader.validate_employee(data)

        # Duplicate national_id check
        existing = self.conn.execute(
            "SELECT id FROM employees WHERE national_id = ?",
            (data["national_id"],),
        ).fetchone()
        if existing:
            raise DuplicateError(
                f"An employee with national_id '{data['national_id']}' already exists "
                f"(id={existing['id']})."
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

    # ──────────────────────────────────────────────────────────
    # Employee — Read
    # ──────────────────────────────────────────────────────────

    def get_employee(self, employee_id: int) -> dict[str, Any]:
        """Fetch a single employee by primary key.

        Raises
        ------
        NotFoundError
            If no employee with *employee_id* exists.
        """
        row = self.conn.execute(
            "SELECT * FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No employee found with id={employee_id}.")
        return self._row_to_dict(row)

    def get_employee_by_code(self, code: str) -> dict[str, Any]:
        """Fetch a single employee by their MZZ code.

        Raises
        ------
        NotFoundError
            If no employee with *code* exists.
        """
        row = self.conn.execute(
            "SELECT * FROM employees WHERE employee_code = ?", (code,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No employee found with code='{code}'.")
        return self._row_to_dict(row)

    def list_employees(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return a paginated list of all employees ordered by employee_code."""
        return self.search_employees(limit=limit, offset=offset)

    def search_employees(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        employment_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search employees with optional filters.

        Parameters
        ----------
        query : str, optional
            Free-text search across ``first_name``, ``last_name``,
            ``employee_code``, and ``national_id`` (case-insensitive LIKE).
        department : str, optional
            Exact match on ``department``.
        employment_status : str, optional
            One of ``"active"``, ``"inactive"``, ``"terminated"``.
        limit : int
            Maximum rows to return.  Defaults to 50.
        offset : int
            Row offset for pagination.  Defaults to 0.

        Returns
        -------
        list[dict]
            Matching employee rows ordered by ``employee_code``.
        """
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
            f"""
            SELECT * FROM employees
            {where}
            ORDER BY employee_code
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def count_employees(self) -> int:
        """Return the total number of employees in the database."""
        return self._count_employees()

    # ──────────────────────────────────────────────────────────
    # Employee — Update
    # ──────────────────────────────────────────────────────────

    def update_employee(
        self,
        employee_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Partially update an employee record.

        Only the keys present in *data* are updated.  The combined
        (existing + incoming) record is validated before writing.

        Parameters
        ----------
        employee_id : int
            ID of the employee to update.
        data : dict
            Fields to update.  Any subset of the employee schema fields.

        Returns
        -------
        dict
            The updated employee row.

        Raises
        ------
        NotFoundError
            If *employee_id* does not exist.
        SchemaValidationError
            If the merged record fails validation.
        """
        existing = self.get_employee(employee_id)   # raises NotFoundError

        # Build merged record for validation (strip DB-managed fields)
        merged = {
            k: v for k, v in {**existing, **data}.items()
            if k not in _DB_FIELDS
        }
        SchemaLoader.validate_employee(merged)

        set_fields = [f for f in _UPDATABLE_FIELDS if f in data]
        if not set_fields:
            return existing  # nothing to do

        set_clause = ", ".join(f"{f} = ?" for f in set_fields)
        values     = [data[f] for f in set_fields] + [employee_id]

        self.conn.execute(
            f"""
            UPDATE employees
               SET {set_clause},
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            values,
        )
        self.conn.commit()
        return self.get_employee(employee_id)

    # ──────────────────────────────────────────────────────────
    # Employee — Delete
    # ──────────────────────────────────────────────────────────

    def delete_employee(
        self,
        employee_id: int,
        file_store: Optional[FileStore] = None,
    ) -> None:
        """Delete an employee and — via ON DELETE CASCADE — all their documents.

        Parameters
        ----------
        employee_id : int
            ID of the employee to delete.
        file_store : FileStore, optional
            If provided, physical files (photo + documents) are deleted from disk
            before the DB rows are removed.

        Raises
        ------
        NotFoundError
            If *employee_id* does not exist.
        """
        employee = self.get_employee(employee_id)   # raises NotFoundError

        if file_store:
            for doc in self.list_documents(employee_id):
                file_store.delete_file(doc.get("file_path"))
            file_store.delete_file(employee.get("photo_path"))

        self.conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self.conn.commit()

    # ──────────────────────────────────────────────────────────
    # Documents — Attach / List / Delete
    # ──────────────────────────────────────────────────────────

    def attach_document(self, data: dict[str, Any]) -> dict[str, Any]:
        """Attach a document record to an employee.

        The physical file must already be saved via ``FileStore.save_document``
        before calling this method.

        Parameters
        ----------
        data : dict
            Must satisfy ``schemas/document.json``.

        Returns
        -------
        dict
            The newly created document row.

        Raises
        ------
        SchemaValidationError
            If *data* fails JSON Schema validation.
        NotFoundError
            If the referenced ``employee_id`` does not exist.
        """
        SchemaLoader.validate_document(data)
        self.get_employee(data["employee_id"])   # raises NotFoundError

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
        """Fetch a single document by primary key.

        Raises
        ------
        NotFoundError
            If no document with *document_id* exists.
        """
        row = self.conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No document found with id={document_id}.")
        return self._row_to_dict(row)

    def list_documents(self, employee_id: int) -> list[dict[str, Any]]:
        """Return all documents attached to *employee_id*, newest first."""
        rows = self.conn.execute(
            """
            SELECT * FROM documents
             WHERE employee_id = ?
             ORDER BY uploaded_at DESC
            """,
            (employee_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_document(
        self,
        document_id: int,
        file_store: Optional[FileStore] = None,
    ) -> None:
        """Delete a document record (and optionally its file).

        Parameters
        ----------
        document_id : int
            ID of the document to delete.
        file_store : FileStore, optional
            If provided, the physical file is also deleted from disk.

        Raises
        ------
        NotFoundError
            If *document_id* does not exist.
        """
        doc = self.get_document(document_id)    # raises NotFoundError
        if file_store:
            file_store.delete_file(doc.get("file_path"))
        self.conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        self.conn.commit()
