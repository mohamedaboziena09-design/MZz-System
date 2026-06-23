-- ============================================================
-- MZz System V1 — Migration 002: Vehicle Management
-- ============================================================

-- ────────────────────────────────────────
-- Table: vehicles
-- بيانات السيارة الثابتة (ملك الشركة)
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicles (
    id                  INTEGER  PRIMARY KEY AUTOINCREMENT,
    plate_number        TEXT     NOT NULL UNIQUE,           -- رقم اللوحة
    make                TEXT     NOT NULL,                  -- الماركة (Toyota, Hyundai...)
    model               TEXT     NOT NULL,                  -- الموديل (Corolla, Elantra...)
    year                INTEGER  NOT NULL,                  -- سنة الصنع
    color               TEXT,
    vehicle_type        TEXT     NOT NULL DEFAULT 'sedan'
                                  CHECK (vehicle_type IN (
                                      'sedan', 'suv', 'van',
                                      'truck', 'minibus', 'other'
                                  )),
    status              TEXT     NOT NULL DEFAULT 'available'
                                  CHECK (status IN (
                                      'available',          -- متاحة
                                      'assigned',           -- معينة لموظف
                                      'maintenance',        -- في الصيانة
                                      'retired'             -- خارج الخدمة
                                  )),
    chassis_number      TEXT     UNIQUE,                   -- رقم الشاسيه
    engine_number       TEXT,                              -- رقم الموتور
    insurance_expiry    TEXT,                              -- انتهاء التأمين (YYYY-MM-DD)
    license_expiry      TEXT,                              -- انتهاء الرخصة (YYYY-MM-DD)
    notes               TEXT,
    created_at          TEXT     NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT     NOT NULL DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────
-- Table: vehicle_assignments
-- تاريخ تعيين السيارات للموظفين
-- السيارة لموظف واحد في كل مرة، بس بتتغير كتير
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicle_assignments (
    id              INTEGER  PRIMARY KEY AUTOINCREMENT,
    vehicle_id      INTEGER  NOT NULL,
    employee_id     INTEGER  NOT NULL,
    assigned_date   TEXT     NOT NULL,                     -- تاريخ بداية التعيين
    returned_date   TEXT,                                  -- تاريخ الإرجاع (NULL = لسه معاه)
    reason          TEXT,                                  -- سبب التعيين
    notes           TEXT,
    created_at      TEXT     NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (vehicle_id)  REFERENCES vehicles  (id) ON DELETE RESTRICT,
    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE RESTRICT,

    -- ضمان: نفس السيارة مش هتتعين لاتنين في نفس الوقت
    CHECK (returned_date IS NULL OR returned_date >= assigned_date)
);

-- ────────────────────────────────────────
-- Table: drivers
-- سائقين خارجيين (مش موظفين في النظام)
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drivers (
    id              INTEGER  PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT     NOT NULL,
    national_id     TEXT     UNIQUE,
    phone           TEXT,
    license_number  TEXT     UNIQUE,                       -- رقم رخصة القيادة
    license_expiry  TEXT,                                  -- انتهاء الرخصة (YYYY-MM-DD)
    license_type    TEXT,                                  -- نوع الرخصة (A, B, C...)
    status          TEXT     NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'inactive')),
    notes           TEXT,
    created_at      TEXT     NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT     NOT NULL DEFAULT (datetime('now'))
);

-- ────────────────────────────────────────
-- Table: vehicle_movements
-- تسجيل حركة السيارات
-- يشمل: دخول/خروج المقر + رحلات العمل
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicle_movements (
    id                  INTEGER  PRIMARY KEY AUTOINCREMENT,
    vehicle_id          INTEGER  NOT NULL,

    -- السائق: موظف أو خارجي (واحد منهم بس)
    driver_employee_id  INTEGER,                           -- لو الموظف هو السائق
    driver_external_id  INTEGER,                           -- لو سائق خارجي

    movement_type       TEXT     NOT NULL
                                  CHECK (movement_type IN (
                                      'entry',             -- دخول المقر
                                      'exit',              -- خروج من المقر
                                      'trip'               -- رحلة عمل
                                  )),

    -- بيانات الحركة
    departure_time      TEXT     NOT NULL,                 -- وقت المغادرة
    return_time         TEXT,                              -- وقت العودة (NULL لو لسه برا)
    departure_location  TEXT,                              -- من
    destination         TEXT,                              -- إلى
    purpose             TEXT,                              -- الغرض من الرحلة/الخروج

    -- عداد الكيلومترات
    odometer_out        INTEGER,                           -- عداد عند الخروج
    odometer_in         INTEGER,                           -- عداد عند العودة

    -- موافقة/إذن
    authorized_by       INTEGER,                           -- employee_id للشخص اللي وافق
    notes               TEXT,
    created_at          TEXT     NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (vehicle_id)         REFERENCES vehicles  (id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_employee_id) REFERENCES employees (id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_external_id) REFERENCES drivers   (id) ON DELETE RESTRICT,
    FOREIGN KEY (authorized_by)      REFERENCES employees (id) ON DELETE RESTRICT,

    -- ضمان: لازم يكون في سائق واحد على الأقل
    CHECK (
        driver_employee_id IS NOT NULL OR
        driver_external_id IS NOT NULL
    ),
    -- ضمان: مش هيكون الاتنين في نفس الوقت
    CHECK (
        NOT (driver_employee_id IS NOT NULL AND driver_external_id IS NOT NULL)
    ),
    -- ضمان: وقت العودة بعد المغادرة
    CHECK (return_time IS NULL OR return_time >= departure_time),
    -- ضمان: عداد الدخول أكبر من الخروج
    CHECK (odometer_in IS NULL OR odometer_in >= odometer_out)
);

-- ────────────────────────────────────────
-- Indexes
-- ────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS uidx_vehicles_plate         ON vehicles           (plate_number);
CREATE        INDEX IF NOT EXISTS  idx_vehicles_status        ON vehicles           (status);

CREATE        INDEX IF NOT EXISTS  idx_vassign_vehicle        ON vehicle_assignments (vehicle_id);
CREATE        INDEX IF NOT EXISTS  idx_vassign_employee       ON vehicle_assignments (employee_id);
CREATE        INDEX IF NOT EXISTS  idx_vassign_active         ON vehicle_assignments (vehicle_id)
                                                               WHERE returned_date IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_drivers_national_id   ON drivers            (national_id);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_drivers_license       ON drivers            (license_number);

CREATE        INDEX IF NOT EXISTS  idx_vmov_vehicle           ON vehicle_movements  (vehicle_id);
CREATE        INDEX IF NOT EXISTS  idx_vmov_emp_driver        ON vehicle_movements  (driver_employee_id);
CREATE        INDEX IF NOT EXISTS  idx_vmov_ext_driver        ON vehicle_movements  (driver_external_id);
CREATE        INDEX IF NOT EXISTS  idx_vmov_type              ON vehicle_movements  (movement_type);
CREATE        INDEX IF NOT EXISTS  idx_vmov_departure         ON vehicle_movements  (departure_time);
CREATE        INDEX IF NOT EXISTS  idx_vmov_open              ON vehicle_movements  (vehicle_id)
                                                               WHERE return_time IS NULL;
