-- ============================================================
-- MZz System V1 — Migration 001: Initial Schema
-- ============================================================

-- ────────────────────────────────────────
-- Table: employees
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    employee_code     TEXT     NOT NULL UNIQUE,          -- MZZ-YYYY-NNNNN
    first_name        TEXT     NOT NULL,
    last_name         TEXT     NOT NULL,
    national_id       TEXT     NOT NULL UNIQUE,
    date_of_birth     TEXT     NOT NULL,                 -- ISO 8601 (YYYY-MM-DD)
    gender            TEXT     NOT NULL
                                CHECK (gender IN ('male', 'female')),
    phone             TEXT,
    email             TEXT,
    address           TEXT,
    department        TEXT     NOT NULL,
    position          TEXT     NOT NULL,
    hire_date         TEXT     NOT NULL,                 -- ISO 8601 (YYYY-MM-DD)
    employment_status TEXT     NOT NULL DEFAULT 'active'
                                CHECK (employment_status IN ('active', 'inactive', 'terminated')),
    photo_path        TEXT,                              -- relative path, NULL if no photo
    notes             TEXT,
    created_at        TEXT     NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT     NOT NULL DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────
-- Table: documents
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER  PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER  NOT NULL,
    document_type   TEXT     NOT NULL
                              CHECK (document_type IN (
                                  'national_id_copy',
                                  'employment_contract',
                                  'certificate',
                                  'resume',
                                  'other'
                              )),
    file_name       TEXT     NOT NULL,                   -- original filename
    file_path       TEXT     NOT NULL,                   -- relative path on disk
    notes           TEXT,
    uploaded_at     TEXT     NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (employee_id) REFERENCES employees (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ────────────────────────────────────────
-- Indexes
-- ────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS uidx_employees_employee_code ON employees (employee_code);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_employees_national_id   ON employees (national_id);
CREATE        INDEX IF NOT EXISTS  idx_employees_department    ON employees (department);
CREATE        INDEX IF NOT EXISTS  idx_employees_status        ON employees (employment_status);
CREATE        INDEX IF NOT EXISTS  idx_employees_hire_date     ON employees (hire_date);
CREATE        INDEX IF NOT EXISTS  idx_documents_employee_id   ON documents (employee_id);
CREATE        INDEX IF NOT EXISTS  idx_documents_type          ON documents (document_type);
