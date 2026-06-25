"""
ui/screens/employees/employees_list.py
=======================================
Employees list screen — same pattern as PersonsListScreen.
Search + filter by department/status + view/edit/delete.
"""

from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from ui.theme import COLORS, FONTS, RADIUS
from src.crud_service import CRUDService, NotFoundError

STATUS_COLORS = {
    "active":     COLORS["success"],
    "inactive":   COLORS["warning"],
    "terminated": COLORS["error"],
}
STATUS_LABELS = {
    "active":     "نشط",
    "inactive":   "غير نشط",
    "terminated": "منتهي",
}


class EmployeesListScreen(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent    : parent widget
    on_add    : Callable — open blank employee form
    on_edit   : Callable[[int], None] — open edit form with employee_id
    on_view   : Callable[[int], None] — open profile view
    """

    def __init__(
        self,
        parent,
        on_add:  Callable,
        on_edit: Callable[[int], None],
        on_view: Callable[[int], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._on_add  = on_add
        self._on_edit = on_edit
        self._on_view = on_view

        self._all_employees: list[dict] = []
        self._filter_status = ""
        self._filter_dept   = ""

        self._build()
        self._load()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Toolbar ─────────────────────────────────────────
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        toolbar.grid_columnconfigure(0, weight=1)

        # Search
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filters())
        search = ctk.CTkEntry(
            toolbar, textvariable=self._search_var,
            placeholder_text="🔍  بحث بالاسم أو الكود أو الهوية...",
            font=FONTS["body"], height=40,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        )
        search.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        ctk.CTkButton(
            toolbar, text="+ إضافة موظف",
            font=FONTS["btn_sm"], height=40, width=140,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._on_add,
        ).grid(row=0, column=1)

        # Filters
        filter_bar = ctk.CTkFrame(toolbar, fg_color="transparent")
        filter_bar.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ctk.CTkLabel(filter_bar, text="الحالة:",
                     font=FONTS["body_sm"], text_color=COLORS["text_muted"],
                     ).pack(side="left", padx=(0, 6))

        for label, val in [("الكل", ""), ("نشط", "active"),
                           ("غير نشط", "inactive"), ("منتهي", "terminated")]:
            ctk.CTkButton(
                filter_bar, text=label,
                font=FONTS["btn_sm"], height=30, width=70,
                corner_radius=RADIUS["sm"],
                fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
                text_color=COLORS["text_muted"],
                command=lambda v=val: self._set_status_filter(v),
            ).pack(side="left", padx=3)

        # ── Count label ──────────────────────────────────────
        self._count_lbl = ctk.CTkLabel(
            self, text="",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._count_lbl.grid(row=1, column=0, sticky="w", pady=(0, 8))

        # ── Scrollable list ──────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._scroll.grid(row=2, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

    # ── Load ──────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            with CRUDService() as svc:
                self._all_employees = svc.search_employees(limit=500)
        except Exception as e:
            self._all_employees = []
        self._apply_filters()

    def refresh(self) -> None:
        self._load()

    # ── Filters ───────────────────────────────────────────────

    def _set_status_filter(self, val: str) -> None:
        self._filter_status = val
        self._apply_filters()

    def _apply_filters(self) -> None:
        q      = self._search_var.get().strip().lower()
        status = self._filter_status

        filtered = [
            e for e in self._all_employees
            if (not q or q in f"{e['first_name']} {e['last_name']} {e['employee_code']} {e.get('national_id','')}".lower())
            and (not status or e["employment_status"] == status)
        ]
        self._render(filtered)

    # ── Render ────────────────────────────────────────────────

    def _render(self, employees: list[dict]) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()

        self._count_lbl.configure(text=f"{len(employees)} موظف")

        if not employees:
            ctk.CTkLabel(
                self._scroll, text="لا يوجد موظفين مطابقين",
                font=FONTS["body"], text_color=COLORS["text_dim"],
            ).grid(row=0, column=0, pady=40)
            return

        # Header row
        _RowHeader(self._scroll).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        for i, emp in enumerate(employees):
            row = _EmployeeRow(
                self._scroll, emp,
                on_view=lambda e=emp: self._on_view(e["id"]),
                on_edit=lambda e=emp: self._on_edit(e["id"]),
                on_delete=lambda e=emp: self._confirm_delete(e),
            )
            row.grid(row=i + 1, column=0, sticky="ew", pady=2)

    # ── Delete ────────────────────────────────────────────────

    def _confirm_delete(self, emp: dict) -> None:
        name = f"{emp['first_name']} {emp['last_name']}"
        dlg  = _ConfirmDialog(self, f"حذف الموظف: {name}؟")
        self.wait_window(dlg)
        if dlg.confirmed:
            try:
                with CRUDService() as svc:
                    svc.delete_employee(emp["id"])
                self._load()
            except Exception as e:
                pass


# ── Row Header ────────────────────────────────────────────────

class _RowHeader(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(
            parent, fg_color=COLORS["surface"],
            corner_radius=RADIUS["md"],
        )
        self.grid_columnconfigure((0,1,2,3,4), weight=1)
        for col, text in enumerate(["الموظف", "الكود", "القسم", "المسمى", "الحالة"]):
            ctk.CTkLabel(
                self, text=text,
                font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
            ).grid(row=0, column=col, padx=12, pady=8, sticky="w")


# ── Employee Row ──────────────────────────────────────────────

class _EmployeeRow(ctk.CTkFrame):
    def __init__(self, parent, emp: dict,
                 on_view, on_edit, on_delete) -> None:
        super().__init__(
            parent, fg_color=COLORS["surface"],
            corner_radius=RADIUS["md"],
            border_width=1, border_color=COLORS["border"],
        )
        self.grid_columnconfigure((0,1,2,3,4), weight=1)

        # Avatar + name
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        av_letter = (emp["first_name"] or "?")[0].upper()
        av = ctk.CTkLabel(
            name_frame, text=av_letter,
            font=FONTS["btn"], text_color=COLORS["text_inverse"],
            width=34, height=34,
            fg_color=COLORS["accent"], corner_radius=17,
        )
        av.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            name_frame,
            text=f"{emp['first_name']} {emp['last_name']}",
            font=FONTS["body"], text_color=COLORS["text"], anchor="w",
        ).pack(side="left")

        # Code
        ctk.CTkLabel(
            self, text=emp.get("employee_code", "—"),
            font=FONTS["code"], text_color=COLORS["text_dim"], anchor="w",
        ).grid(row=0, column=1, padx=12, pady=10, sticky="w")

        # Department
        ctk.CTkLabel(
            self, text=emp.get("department", "—"),
            font=FONTS["body"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=2, padx=12, pady=10, sticky="w")

        # Position
        ctk.CTkLabel(
            self, text=emp.get("position", "—"),
            font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=0, column=3, padx=12, pady=10, sticky="w")

        # Status badge
        st    = emp.get("employment_status", "active")
        color = STATUS_COLORS.get(st, COLORS["text_muted"])
        ctk.CTkLabel(
            self, text=f"● {STATUS_LABELS.get(st, st)}",
            font=FONTS["body_sm"], text_color=color, anchor="w",
        ).grid(row=0, column=4, padx=12, pady=10, sticky="w")

        # Actions
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=5, padx=12, pady=8, sticky="e")

        for text, cmd, color in [
            ("👁", on_view, COLORS["surface3"]),
            ("✏️", on_edit, COLORS["accent_dim"]),
            ("🗑", on_delete, COLORS["error_dim"]),
        ]:
            ctk.CTkButton(
                btn_frame, text=text, width=34, height=34,
                font=FONTS["body"], corner_radius=RADIUS["sm"],
                fg_color=color, hover_color=COLORS["surface3"],
                text_color=COLORS["text"],
                command=cmd,
            ).pack(side="left", padx=2)

        # Hover effect
        self.bind("<Enter>", lambda _: self.configure(border_color=COLORS["accent"]))
        self.bind("<Leave>", lambda _: self.configure(border_color=COLORS["border"]))


# ── Confirm Dialog ────────────────────────────────────────────

class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message: str) -> None:
        super().__init__(parent)
        self.confirmed = False
        self.title("تأكيد")
        self.geometry("360x160")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()

        ctk.CTkLabel(
            self, text=message,
            font=FONTS["body"], text_color=COLORS["text"],
            wraplength=300,
        ).pack(pady=(24, 16))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack()

        ctk.CTkButton(
            btn_row, text="إلغاء", width=100, height=36,
            fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
            command=self.destroy,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row, text="حذف", width=100, height=36,
            fg_color=COLORS["error"], text_color=COLORS["text_inverse"],
            command=self._confirm,
        ).pack(side="left", padx=8)

    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()