"""
ui/screens/employees/employee_form.py
======================================
Add / Edit Employee Form.
Same pattern as PersonFormScreen — built on CRUDService directly.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, Any

import customtkinter as ctk

from ui.theme import COLORS, FONTS, RADIUS
from ui.components.field import Field
from ui.components.divider import Divider
from src.crud_service import CRUDService, DuplicateError, NotFoundError

GENDER_OPTIONS = ["male", "female"]
STATUS_OPTIONS = ["active", "inactive", "terminated"]

DEPARTMENTS = [
    "الإدارة العليا",
    "الموارد البشرية",
    "المالية والمحاسبة",
    "المبيعات",
    "العمليات",
    "تقنية المعلومات",
    "أخرى",
]


class EmployeeFormScreen(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent      : parent widget
    on_save     : Callable[[int], None] — called with employee_id after save
    on_cancel   : Callable — called when user cancels
    employee_id : int, optional — if provided, loads existing employee for editing
    """

    def __init__(
        self,
        parent,
        on_save:     Callable[[int], None],
        on_cancel:   Callable,
        employee_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._on_save      = on_save
        self._on_cancel    = on_cancel
        self._employee_id  = employee_id
        self._is_edit      = employee_id is not None
        self._existing: dict[str, Any] = {}

        if self._is_edit:
            self._load_existing()

        self._build()

        if self._is_edit:
            self._populate()

    # ── Load ─────────────────────────────────────────────────

    def _load_existing(self) -> None:
        with CRUDService() as svc:
            self._existing = svc.get_employee(self._employee_id)

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        title_text = "Edit Employee" if self._is_edit else "Add New Employee"

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text=title_text,
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        if self._is_edit and self._existing:
            ctk.CTkLabel(
                header,
                text=self._existing.get("employee_code", ""),
                font=FONTS["code"], text_color=COLORS["text_dim"], anchor="w",
            ).grid(row=1, column=0, sticky="w")

        # Scrollable body
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        # ── Section: Personal Info ───────────────────────────
        _SectionLabel(scroll, "Personal Information").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._first_name = tk.StringVar()
        self._last_name  = tk.StringVar()
        self._nat_id     = tk.StringVar()
        self._dob        = tk.StringVar()
        self._gender_var = tk.StringVar(value=GENDER_OPTIONS[0])

        self._f_first = Field(scroll, "الاسم الأول *", self._first_name,
                              placeholder="مثال: أحمد")
        self._f_first.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

        self._f_last = Field(scroll, "الاسم الأخير *", self._last_name,
                             placeholder="مثال: محمد")
        self._f_last.grid(row=1, column=1, sticky="ew", pady=(0, 12))

        self._f_nat_id = Field(scroll, "رقم الهوية *", self._nat_id,
                               placeholder="مثال: 1098765432")
        self._f_nat_id.grid(row=2, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

        self._f_dob = Field(scroll, "تاريخ الميلاد *", self._dob,
                            placeholder="YYYY-MM-DD")
        self._f_dob.grid(row=2, column=1, sticky="ew", pady=(0, 12))

        # Gender
        gender_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        gender_frame.grid(row=3, column=0, sticky="ew", padx=(0, 12), pady=(0, 16))
        ctk.CTkLabel(gender_frame, text="الجنس",
                     font=FONTS["label"], text_color=COLORS["text_muted"],
                     anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkOptionMenu(
            gender_frame, variable=self._gender_var,
            values=GENDER_OPTIONS,
            font=FONTS["body"], dropdown_font=FONTS["body"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            height=40, corner_radius=RADIUS["md"],
        ).pack(fill="x")

        Divider(scroll).grid(row=4, column=0, columnspan=2,
                             sticky="ew", pady=(0, 16))

        # ── Section: Contact ─────────────────────────────────
        _SectionLabel(scroll, "Contact Information").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._phone   = tk.StringVar()
        self._email   = tk.StringVar()
        self._address = tk.StringVar()

        self._f_phone = Field(scroll, "الهاتف", self._phone,
                              placeholder="مثال: 0501234567")
        self._f_phone.grid(row=6, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

        Field(scroll, "البريد الإلكتروني", self._email,
              placeholder="مثال: ahmed@company.com",
              ).grid(row=6, column=1, sticky="ew", pady=(0, 12))

        Field(scroll, "العنوان", self._address,
              placeholder="مثال: الرياض، حي النزهة",
              ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        Divider(scroll).grid(row=8, column=0, columnspan=2,
                             sticky="ew", pady=(0, 16))

        # ── Section: Job Info ────────────────────────────────
        _SectionLabel(scroll, "Job Information").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._dept_var    = tk.StringVar(value=DEPARTMENTS[0])
        self._position    = tk.StringVar()
        self._hire_date   = tk.StringVar()
        self._status_var  = tk.StringVar(value=STATUS_OPTIONS[0])

        # Department
        dept_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dept_frame.grid(row=10, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))
        ctk.CTkLabel(dept_frame, text="القسم *",
                     font=FONTS["label"], text_color=COLORS["text_muted"],
                     anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkOptionMenu(
            dept_frame, variable=self._dept_var,
            values=DEPARTMENTS,
            font=FONTS["body"], dropdown_font=FONTS["body"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            height=40, corner_radius=RADIUS["md"],
        ).pack(fill="x")

        self._f_position = Field(scroll, "المسمى الوظيفي *", self._position,
                                 placeholder="مثال: مدير عام")
        self._f_position.grid(row=10, column=1, sticky="ew", pady=(0, 12))

        self._f_hire = Field(scroll, "تاريخ التعيين *", self._hire_date,
                             placeholder="YYYY-MM-DD")
        self._f_hire.grid(row=11, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))

        # Status
        status_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        status_frame.grid(row=11, column=1, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(status_frame, text="الحالة الوظيفية",
                     font=FONTS["label"], text_color=COLORS["text_muted"],
                     anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkOptionMenu(
            status_frame, variable=self._status_var,
            values=STATUS_OPTIONS,
            font=FONTS["body"], dropdown_font=FONTS["body"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            height=40, corner_radius=RADIUS["md"],
        ).pack(fill="x")

        Divider(scroll).grid(row=12, column=0, columnspan=2,
                             sticky="ew", pady=(0, 16))

        # ── Notes ────────────────────────────────────────────
        _SectionLabel(scroll, "Notes").grid(
            row=13, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self._notes_box = ctk.CTkTextbox(
            scroll, height=80,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"], font=FONTS["body"],
        )
        self._notes_box.grid(row=14, column=0, columnspan=2,
                             sticky="ew", pady=(0, 24))

        # ── Buttons ──────────────────────────────────────────
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.grid(row=15, column=0, columnspan=2, sticky="e", pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="Cancel",
            font=FONTS["btn_sm"], width=100, height=40,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text_muted"],
            command=self._on_cancel,
        ).pack(side="left", padx=(0, 12))

        label = "Save Changes" if self._is_edit else "Add Employee"
        self._save_btn = ctk.CTkButton(
            btn_row, text=label,
            font=FONTS["btn_sm"], width=140, height=40,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._submit,
        )
        self._save_btn.pack(side="left")

        # Error banner
        self._err_banner = ctk.CTkLabel(
            scroll, text="",
            font=FONTS["body_sm"], text_color=COLORS["error"],
            fg_color=COLORS["error_dim"], corner_radius=RADIUS["md"],
            height=36,
        )

    # ── Populate ──────────────────────────────────────────────

    def _populate(self) -> None:
        d = self._existing
        self._first_name.set(d.get("first_name", ""))
        self._last_name.set(d.get("last_name", ""))
        self._nat_id.set(d.get("national_id") or "")
        self._dob.set(d.get("date_of_birth") or "")
        self._gender_var.set(d.get("gender") or GENDER_OPTIONS[0])
        self._phone.set(d.get("phone") or "")
        self._email.set(d.get("email") or "")
        self._address.set(d.get("address") or "")
        self._dept_var.set(d.get("department") or DEPARTMENTS[0])
        self._position.set(d.get("position") or "")
        self._hire_date.set(d.get("hire_date") or "")
        self._status_var.set(d.get("employment_status") or STATUS_OPTIONS[0])
        if d.get("notes"):
            self._notes_box.insert("1.0", d["notes"])

    # ── Submit ────────────────────────────────────────────────

    def _submit(self) -> None:
        # Clear errors
        for f in [self._f_first, self._f_last, self._f_nat_id,
                  self._f_dob, self._f_phone, self._f_position, self._f_hire]:
            f.clear_error()
        self._err_banner.grid_forget()

        first    = self._first_name.get().strip()
        last     = self._last_name.get().strip()
        nat_id   = self._nat_id.get().strip()
        dob      = self._dob.get().strip()
        position = self._position.get().strip()
        hire     = self._hire_date.get().strip()

        ok = True
        if not first:
            self._f_first.show_error("الاسم الأول مطلوب.")
            ok = False
        if not last:
            self._f_last.show_error("الاسم الأخير مطلوب.")
            ok = False
        if not nat_id:
            self._f_nat_id.show_error("رقم الهوية مطلوب.")
            ok = False
        if not position:
            self._f_position.show_error("المسمى الوظيفي مطلوب.")
            ok = False

        parsed_dob = None
        if dob:
            parsed_dob = _parse_date(dob)
            if parsed_dob is None:
                self._f_dob.show_error("صيغة التاريخ غير صحيحة. مثال: 1990-05-20")
                ok = False
        else:
            self._f_dob.show_error("تاريخ الميلاد مطلوب.")
            ok = False

        parsed_hire = None
        if hire:
            parsed_hire = _parse_date(hire)
            if parsed_hire is None:
                self._f_hire.show_error("صيغة التاريخ غير صحيحة. مثال: 2020-01-01")
                ok = False
        else:
            self._f_hire.show_error("تاريخ التعيين مطلوب.")
            ok = False

        if not ok:
            return

        data = {
            "first_name":        first,
            "last_name":         last,
            "national_id":       nat_id,
            "date_of_birth":     parsed_dob,
            "gender":            self._gender_var.get(),
            "phone":             self._phone.get().strip() or None,
            "email":             self._email.get().strip() or None,
            "address":           self._address.get().strip() or None,
            "department":        self._dept_var.get(),
            "position":          position,
            "hire_date":         parsed_hire,
            "employment_status": self._status_var.get(),
            "notes":             self._notes_box.get("1.0", "end").strip() or None,
        }

        try:
            with CRUDService() as svc:
                if self._is_edit:
                    emp = svc.update_employee(self._employee_id, data)
                else:
                    emp = svc.create_employee(data)

            self._save_btn.configure(
                text="✓  Saved",
                fg_color=COLORS["success"],
                state="disabled",
            )
            self.after(600, lambda: self._on_save(emp["id"]))

        except DuplicateError:
            self._f_nat_id.show_error("رقم الهوية مسجل مسبقاً.")
        except ValueError as e:
            self._show_banner(str(e))
        except Exception as e:
            self._show_banner(f"خطأ: {e}")

    def _show_banner(self, msg: str) -> None:
        self._err_banner.configure(text=f"  ✗  {msg}")
        self._err_banner.grid(row=16, column=0, columnspan=2,
                              sticky="ew", pady=(0, 8))


# ── Helpers ───────────────────────────────────────────────────

def _parse_date(s: str) -> Optional[str]:
    import re
    s = s.strip()
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if m:
        y, mo, d = m.groups()
        try:
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        except Exception:
            pass
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", s)
    if m:
        d, mo, y = m.groups()
        try:
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        except Exception:
            pass
    return None


class _SectionLabel(ctk.CTkLabel):
    def __init__(self, parent, text: str) -> None:
        super().__init__(
            parent, text=text,
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        )