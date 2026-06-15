"""
Employee Code Generator
=======================
Generates unique employee codes in the format:

    MZZ-YYYY-NNNNN

Where:
    MZZ    → system prefix (fixed)
    YYYY   → 4-digit year the code was generated
    NNNNN  → 5-digit zero-padded sequence, resets each calendar year

Examples
--------
    MZZ-2024-00001   ← first employee added in 2024
    MZZ-2024-00042   ← forty-second employee added in 2024
    MZZ-2025-00001   ← first employee added in 2025 (sequence resets)
"""

from __future__ import annotations

import sqlite3
from datetime import date


class EmployeeCodeGenerator:
    """Generates and parses MZZ employee codes.

    All methods are static — no instantiation required.
    """

    PREFIX = "MZZ"
    SEQ_DIGITS = 5  # zero-padded width of the sequence number

    @classmethod
    def generate(cls, conn: sqlite3.Connection) -> str:
        """Return the next available employee code for the current year.

        This method reads the highest existing sequence for the current
        calendar year from the database and increments it by one.
        The query and INSERT happen inside the caller's transaction, so
        there is no race condition when called from within CRUDService.

        Parameters
        ----------
        conn : sqlite3.Connection
            An open database connection (WAL mode recommended).

        Returns
        -------
        str
            Next available code, e.g. ``"MZZ-2024-00007"``.
        """
        year   = date.today().year
        prefix = f"{cls.PREFIX}-{year}-"

        row = conn.execute(
            """
            SELECT employee_code
              FROM employees
             WHERE employee_code LIKE ?
             ORDER BY employee_code DESC
             LIMIT 1
            """,
            (f"{prefix}%",),
        ).fetchone()

        next_seq = int(row[0].split("-")[-1]) + 1 if row else 1
        return f"{prefix}{next_seq:0{cls.SEQ_DIGITS}d}"

    @classmethod
    def parse(cls, code: str) -> dict[str, int | str]:
        """Decompose a code string into its components.

        Parameters
        ----------
        code : str
            A valid employee code, e.g. ``"MZZ-2024-00001"``.

        Returns
        -------
        dict
            ``{"prefix": "MZZ", "year": 2024, "sequence": 1}``

        Raises
        ------
        ValueError
            If *code* does not conform to the expected format.
        """
        parts = code.split("-")
        if len(parts) != 3 or parts[0] != cls.PREFIX:
            raise ValueError(
                f"Invalid employee code '{code}'. "
                f"Expected format: {cls.PREFIX}-YYYY-NNNNN"
            )
        try:
            year     = int(parts[1])
            sequence = int(parts[2])
        except ValueError as exc:
            raise ValueError(f"Invalid employee code '{code}': {exc}") from exc

        return {"prefix": parts[0], "year": year, "sequence": sequence}
