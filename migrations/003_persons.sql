-- ============================================================
-- MZz System V1 — Migration 003: Persons
-- ============================================================

-- ────────────────────────────────────────
-- Table: persons
-- النواة الأساسية لأي شخص في النظام
-- (عميل / مورد / شريك / أخرى)
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS persons (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    person_code       TEXT     NOT NULL UNIQUE,            -- MZZ-P-YYYY-NNNNN

    -- ── البيانات الشخصية ──────────────────
    first_name        TEXT     NOT NULL,
    last_name         TEXT     NOT NULL,
    national_id       TEXT     UNIQUE,                     -- اختياري (مش كل عميل عنده)
    date_of_birth     TEXT,                                -- ISO 8601 (YYYY-MM-DD)
    gender            TEXT     CHECK (gender IN ('male', 'female', 'unspecified')),

    -- ── بيانات التواصل ────────────────────
    phone             TEXT,
    phone_alt         TEXT,                                -- رقم احتياطي
    email             TEXT,
    address           TEXT,

    -- ── التصنيف ──────────────────────────
    person_type       TEXT     NOT NULL DEFAULT 'client'
                                CHECK (person_type IN (
                                    'client',             -- عميل
                                    'supplier',           -- مورد
                                    'partner',            -- شريك
                                    'contractor',         -- متعاقد
                                    'other'               -- أخرى
                                )),

    -- ── الحالة ───────────────────────────
    status            TEXT     NOT NULL DEFAULT 'active'
                                CHECK (status IN ('active', 'inactive')),

    -- ── اكتمال البيانات ──────────────────
    -- يُحسب تلقائياً بواسطة التطبيق
    -- مكتمل = first_name + last_name + phone + national_id + date_of_birth + gender
    profile_complete  INTEGER  NOT NULL DEFAULT 0          -- 0 = ناقص، 1 = مكتمل
                                CHECK (profile_complete IN (0, 1)),

    -- ── الصورة ───────────────────────────
    photo_path        TEXT,                                -- uploads/photos/persons/

    -- ── ملاحظات ──────────────────────────
    notes             TEXT,

    -- ── Timestamps ───────────────────────
    created_at        TEXT     NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT     NOT NULL DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────
-- Table: person_documents
-- مستندات مرتبطة بالشخص
-- (مستقلة عن employee documents)
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS person_documents (
    id              INTEGER  PRIMARY KEY AUTOINCREMENT,
    person_id       INTEGER  NOT NULL,
    document_type   TEXT     NOT NULL
                              CHECK (document_type IN (
                                  'national_id_copy',    -- صورة بطاقة
                                  'contract',            -- عقد
                                  'invoice',             -- فاتورة
                                  'certificate',         -- شهادة
                                  'resume',              -- سيرة ذاتية
                                  'other'                -- أخرى
                              )),
    file_name       TEXT     NOT NULL,                   -- اسم الملف الأصلي
    file_path       TEXT     NOT NULL,                   -- uploads/documents/persons/
    notes           TEXT,
    uploaded_at     TEXT     NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (person_id) REFERENCES persons (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ────────────────────────────────────────
-- Indexes
-- ────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS uidx_persons_code        ON persons          (person_code);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_persons_national_id ON persons          (national_id)
                                                           WHERE national_id IS NOT NULL;
CREATE        INDEX IF NOT EXISTS  idx_persons_type        ON persons          (person_type);
CREATE        INDEX IF NOT EXISTS  idx_persons_status      ON persons          (status);
CREATE        INDEX IF NOT EXISTS  idx_persons_complete    ON persons          (profile_complete);
CREATE        INDEX IF NOT EXISTS  idx_persons_name        ON persons          (last_name, first_name);

CREATE        INDEX IF NOT EXISTS  idx_pdocs_person        ON person_documents (person_id);
CREATE        INDEX IF NOT EXISTS  idx_pdocs_type          ON person_documents (document_type);
