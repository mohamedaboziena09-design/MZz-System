"""
ui/screens/persons/person_form.py — V2.1
يستخدم WorkspaceContext بدل CRUDService مباشرة.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, Any
import customtkinter as ctk

from ui.theme    import COLORS, FONTS, RADIUS
from ui.components.field   import Field
from ui.components.divider import Divider
from src.context      import WorkspaceContext
from src.crud_service import DuplicateError

PERSON_TYPES   = ["client", "supplier", "partner", "contractor", "other"]
GENDER_OPTIONS = ["male", "female", "unspecified"]
STATUS_OPTIONS = ["active", "inactive"]


class PersonFormScreen(ctk.CTkFrame):
    def __init__(self, parent, ctx: WorkspaceContext,
                 on_save:   Callable[[int], None],
                 on_cancel: Callable,
                 person_id: Optional[int] = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._ctx       = ctx
        self._on_save   = on_save
        self._on_cancel = on_cancel
        self._person_id = person_id
        self._is_edit   = person_id is not None
        self._existing: dict[str, Any] = {}

        if self._is_edit:
            self._load_existing()

        self._build()
        if self._is_edit:
            self._populate()

    # ── Load ──────────────────────────────────────────────────

    def _load_existing(self) -> None:
        with self._ctx.db() as svc:
            self._existing = svc.get_person(self._person_id)

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        title_text = "Edit Person" if self._is_edit else "Add New Person"

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=title_text,
                     font=FONTS["title"], text_color=COLORS["text"],
                     anchor="w").grid(row=0, column=0, sticky="w")

        if self._is_edit and self._existing:
            ctk.CTkLabel(
                header,
                text=self._existing.get("person_code", ""),
                font=FONTS["code"], text_color=COLORS["text_dim"],
                anchor="w",
            ).grid(row=1, column=0, sticky="w")

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        # Warning banner (edit mode — incomplete profile)
        self._warning = ctk.CTkFrame(
            scroll, fg_color=COLORS["error_dim"],
            corner_radius=RADIUS["md"],
            border_width=1, border_color=COLORS["error"],
        )
        ctk.CTkLabel(
            self._warning,
            text="⚠  البيانات غير مكتملة — يرجى ملء الحقول المطلوبة.",
            font=FONTS["body_sm"], text_color=COLORS["error"],
        ).pack(padx=16, pady=10)

        if self._is_edit and self._existing.get("profile_complete") == 0:
            self._warning.grid(row=0, column=0, columnspan=2,
                               sticky="ew", pady=(0, 16))

        # ── Personal Info ────────────────────────────────────
        _SectionLabel(scroll, "Personal Information").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._first_name = tk.StringVar()
        self._last_name  = tk.StringVar()
        self._nat_id     = tk.StringVar()
        self._dob        = tk.StringVar()
        self._gender_var = tk.StringVar(value=GENDER_OPTIONS[0])

        self._f_first = Field(scroll, "First Name *", self._first_name,
                               placeholder="e.g. Ahmed")
        self._f_first.grid(row=2, column=0, sticky="ew",
                           padx=(0, 12), pady=(0, 12))

        self._f_last = Field(scroll, "Last Name *", self._last_name,
                              placeholder="e.g. Hassan")
        self._f_last.grid(row=2, column=1, sticky="ew", pady=(0, 12))

        self._f_nat_id = Field(scroll, "National ID", self._nat_id,
                                placeholder="e.g. 12345678901234")
        self._f_nat_id.grid(row=3, column=0, sticky="ew",
                            padx=(0, 12), pady=(0, 12))

        self._f_dob = Field(scroll, "Date of Birth", self._dob,
                             placeholder="YYYY-MM-DD")
        self._f_dob.grid(row=3, column=1, sticky="ew", pady=(0, 12))

        # Gender
        gf = ctk.CTkFrame(scroll, fg_color="transparent")
        gf.grid(row=4, column=0, sticky="ew", padx=(0, 12), pady=(0, 16))
        ctk.CTkLabel(gf, text="Gender", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(fill="x", pady=(0, 4))
        ctk.CTkOptionMenu(
            gf, variable=self._gender_var, values=GENDER_OPTIONS,
            font=FONTS["body"], dropdown_font=FONTS["body"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"], height=40,
            corner_radius=RADIUS["md"],
        ).pack(fill="x")

        Divider(scroll).grid(row=5, column=0, columnspan=2,
                             sticky="ew", pady=(0, 16))

        # ── Contact ──────────────────────────────────────────
        _SectionLabel(scroll, "Contact Information").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._phone     = tk.StringVar()
        self._phone_alt = tk.StringVar()
        self._email     = tk.StringVar()
        self._address   = tk.StringVar()

        self._f_phone = Field(scroll, "Phone *", self._phone,
                               placeholder="e.g. 01012345678")
        self._f_phone.grid(row=7, column=0, sticky="ew",
                           padx=(0, 12), pady=(0, 12))

        Field(scroll, "Alt Phone", self._phone_alt,
              placeholder="e.g. 01098765432",
              ).grid(row=7, column=1, sticky="ew", pady=(0, 12))

        Field(scroll, "Email", self._email,
              placeholder="e.g. ahmed@example.com",
              ).grid(row=8, column=0, sticky="ew",
                     padx=(0, 12), pady=(0, 12))

        Field(scroll, "Address", self._address,
              placeholder="e.g. Cairo, Egypt",
              ).grid(row=8, column=1, sticky="ew", pady=(0, 12))

        Divider(scroll).grid(row=9, column=0, columnspan=2,
                             sticky="ew", pady=(0, 16))

        # ── Classification ───────────────────────────────────
        _SectionLabel(scroll, "Classification").grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._type_var   = tk.StringVar(value=PERSON_TYPES[0])
        self._status_var = tk.StringVar(value=STATUS_OPTIONS[0])

        tf = ctk.CTkFrame(scroll, fg_color="transparent")
        tf.grid(row=11, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))
        ctk.CTkLabel(tf, text="Person Type", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(fill="x", pady=(0, 4))
        ctk.CTkOptionMenu(
            tf, variable=self._type_var, values=PERSON_TYPES,
            font=FONTS["body"], dropdown_font=FONTS["body"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"], height=40,
            corner_radius=RADIUS["md"],
        ).pack(fill="x")

        sf = ctk.CTkFrame(scroll, fg_color="transparent")
        sf.grid(row=11, column=1, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(sf, text="Status", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(fill="x", pady=(0, 4))
        ctk.CTkOptionMenu(
            sf, variable=self._status_var, values=STATUS_OPTIONS,
            font=FONTS["body"], dropdown_font=FONTS["body"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"], height=40,
            corner_radius=RADIUS["md"],
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
        btn_row.grid(row=15, column=0, columnspan=2,
                     sticky="e", pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="Cancel",
            font=FONTS["btn_sm"], width=100, height=40,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text_muted"],
            command=self._on_cancel,
        ).pack(side="left", padx=(0, 12))

        self._save_btn = ctk.CTkButton(
            btn_row,
            text="Save Changes" if self._is_edit else "Add Person",
            font=FONTS["btn_sm"], width=130, height=40,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._submit,
        )
        self._save_btn.pack(side="left")

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
        self._phone_alt.set(d.get("phone_alt") or "")
        self._email.set(d.get("email") or "")
        self._address.set(d.get("address") or "")
        self._type_var.set(d.get("person_type") or PERSON_TYPES[0])
        self._status_var.set(d.get("status") or STATUS_OPTIONS[0])
        if d.get("notes"):
            self._notes_box.insert("1.0", d["notes"])

    # ── Submit ────────────────────────────────────────────────

    def _submit(self) -> None:
        for f in [self._f_first, self._f_last,
                  self._f_nat_id, self._f_dob, self._f_phone]:
            f.clear_error()
        self._err_banner.grid_forget()

        first = self._first_name.get().strip()
        last  = self._last_name.get().strip()
        dob   = self._dob.get().strip()

        ok = True
        if not first:
            self._f_first.show_error("First name is required.")
            ok = False
        if not last:
            self._f_last.show_error("Last name is required.")
            ok = False

        parsed_dob = None
        if dob:
            parsed_dob = _parse_date(dob)
            if parsed_dob is None:
                self._f_dob.show_error(
                    "Cannot parse date. Try: 2002-12-02 or 2/12/2002"
                )
                ok = False

        if not ok:
            return

        data = {
            "first_name":    first,
            "last_name":     last,
            "national_id":   self._nat_id.get().strip() or None,
            "date_of_birth": parsed_dob,
            "gender":        self._gender_var.get(),
            "phone":         self._phone.get().strip() or None,
            "phone_alt":     self._phone_alt.get().strip() or None,
            "email":         self._email.get().strip() or None,
            "address":       self._address.get().strip() or None,
            "person_type":   self._type_var.get(),
            "status":        self._status_var.get(),
            "notes":         self._notes_box.get("1.0", "end").strip() or None,
        }

        try:
            with self._ctx.db() as svc:
                if self._is_edit:
                    person = svc.update_person(self._person_id, data)
                else:
                    person = svc.create_person(data)

            self._ctx.log(
                f"Person {'updated' if self._is_edit else 'created'}: "
                f"{first} {last} (id={person['id']})"
            )
            self._save_btn.configure(
                text="✓  Saved",
                fg_color=COLORS["success"],
                state="disabled",
            )
            self.after(600, lambda: self._on_save(person["id"]))

        except DuplicateError:
            self._f_nat_id.show_error("This National ID already exists.")
        except ValueError as e:
            self._show_banner(str(e))
        except Exception as e:
            self._show_banner(f"Error: {e}")

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