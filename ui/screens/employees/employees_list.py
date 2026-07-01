"""
ui/screens/employees/employees_list.py — V2.1
يستخدم WorkspaceContext بدل CRUDService مباشرة.
"""

from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from ui.theme import COLORS, FONTS, RADIUS
from src.context import WorkspaceContext

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
    def __init__(self, parent, ctx: WorkspaceContext,
                 on_add: Callable, on_edit: Callable[[int], None],
                 on_view: Callable[[int], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._ctx     = ctx
        self._on_add  = on_add
        self._on_edit = on_edit
        self._on_view = on_view
        self._all:    list[dict] = []
        self._filter_status = ""

        self._build()
        self._load()

    def _build(self) -> None:
        import tkinter as tk

        # Toolbar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bar.grid_columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply())

        ctk.CTkEntry(
            bar, textvariable=self._search_var,
            placeholder_text="🔍  بحث بالاسم أو الكود أو الهوية...",
            font=FONTS["body"], height=40,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            bar, text="+ إضافة موظف",
            font=FONTS["btn_sm"], height=40, width=140,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._on_add,
        ).grid(row=0, column=1)

        # Filter chips
        chips = ctk.CTkFrame(bar, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ctk.CTkLabel(chips, text="الحالة:", font=FONTS["body_sm"],
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 6))
        for label, val in [("الكل",""), ("نشط","active"),
                           ("غير نشط","inactive"), ("منتهي","terminated")]:
            ctk.CTkButton(
                chips, text=label, font=FONTS["btn_sm"],
                height=28, width=80, corner_radius=RADIUS["sm"],
                fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
                text_color=COLORS["text_muted"],
                command=lambda v=val: self._set_filter(v),
            ).pack(side="left", padx=3)

        # Count
        self._count_lbl = ctk.CTkLabel(
            self, text="", font=FONTS["body_sm"],
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._count_lbl.grid(row=1, column=0, sticky="w", pady=(0, 6))

        # List
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._scroll.grid(row=2, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

    def _load(self) -> None:
        try:
            with self._ctx.db() as svc:
                self._all = svc.search_employees(limit=500)
        except Exception:
            self._all = []
        self._apply()

    def refresh(self) -> None:
        self._load()

    def _set_filter(self, val: str) -> None:
        self._filter_status = val
        self._apply()

    def _apply(self) -> None:
        q  = self._search_var.get().strip().lower()
        st = self._filter_status
        filtered = [
            e for e in self._all
            if (not q or q in f"{e['first_name']} {e['last_name']} "
                               f"{e['employee_code']} {e.get('national_id','')}".lower())
            and (not st or e["employment_status"] == st)
        ]
        self._render(filtered)

    def _render(self, employees: list[dict]) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        self._count_lbl.configure(text=f"{len(employees)} موظف")

        if not employees:
            ctk.CTkLabel(self._scroll, text="لا يوجد موظفين مطابقين",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=0, column=0, pady=40)
            return

        _RowHeader(self._scroll).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        for i, emp in enumerate(employees):
            _EmployeeRow(
                self._scroll, emp,
                on_view=lambda e=emp: self._on_view(e["id"]),
                on_edit=lambda e=emp: self._on_edit(e["id"]),
                on_delete=lambda e=emp: self._confirm_delete(e),
            ).grid(row=i + 1, column=0, sticky="ew", pady=2)

    def _confirm_delete(self, emp: dict) -> None:
        from ui.screens.employees.employees_list import _ConfirmDialog
        name = f"{emp['first_name']} {emp['last_name']}"
        dlg  = _ConfirmDialog(self, f"حذف الموظف: {name}؟")
        self.wait_window(dlg)
        if dlg.confirmed:
            try:
                with self._ctx.db() as svc:
                    svc.delete_employee(emp["id"],
                                        file_store=self._ctx.file_store)
                self._load()
            except Exception:
                pass


class _RowHeader(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["surface"],
                         corner_radius=RADIUS["md"])
        for i, text in enumerate(["الموظف","الكود","القسم","المسمى","الحالة",""]):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(self, text=text, font=FONTS["label"],
                         text_color=COLORS["text_muted"], anchor="w",
                         ).grid(row=0, column=i, padx=12, pady=8, sticky="w")


class _EmployeeRow(ctk.CTkFrame):
    def __init__(self, parent, emp: dict, on_view, on_edit, on_delete) -> None:
        super().__init__(parent, fg_color=COLORS["surface"],
                         corner_radius=RADIUS["md"],
                         border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure((0,1,2,3,4), weight=1)

        # Avatar + name
        nf = ctk.CTkFrame(self, fg_color="transparent")
        nf.grid(row=0, column=0, padx=12, pady=10, sticky="w")
        ctk.CTkLabel(nf, text=(emp["first_name"] or "?")[0].upper(),
                     font=FONTS["btn"], text_color=COLORS["text_inverse"],
                     width=32, height=32,
                     fg_color=COLORS["accent"], corner_radius=16,
                     ).pack(side="left", padx=(0,8))
        ctk.CTkLabel(nf, text=f"{emp['first_name']} {emp['last_name']}",
                     font=FONTS["body"], text_color=COLORS["text"], anchor="w",
                     ).pack(side="left")

        for col, (val, color) in enumerate([
            (emp.get("employee_code","—"), COLORS["text_dim"]),
            (emp.get("department","—"),    COLORS["text"]),
            (emp.get("position","—"),      COLORS["text_muted"]),
        ], start=1):
            ctk.CTkLabel(self, text=val, font=FONTS["body"],
                         text_color=color, anchor="w",
                         ).grid(row=0, column=col, padx=12, pady=10, sticky="w")

        st    = emp.get("employment_status","active")
        color = STATUS_COLORS.get(st, COLORS["text_muted"])
        ctk.CTkLabel(self, text=f"● {STATUS_LABELS.get(st,st)}",
                     font=FONTS["body_sm"], text_color=color, anchor="w",
                     ).grid(row=0, column=4, padx=12, pady=10, sticky="w")

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.grid(row=0, column=5, padx=12, pady=8, sticky="e")
        for txt, cmd, bg in [
            ("👁", on_view, COLORS["surface3"]),
            ("✏️", on_edit, COLORS["accent_dim"]),
            ("🗑", on_delete, COLORS["error_dim"]),
        ]:
            ctk.CTkButton(btn_f, text=txt, width=32, height=32,
                          font=FONTS["body"], corner_radius=RADIUS["sm"],
                          fg_color=bg, hover_color=COLORS["surface3"],
                          text_color=COLORS["text"], command=cmd,
                          ).pack(side="left", padx=2)

        self.bind("<Enter>", lambda _: self.configure(border_color=COLORS["accent"]))
        self.bind("<Leave>", lambda _: self.configure(border_color=COLORS["border"]))


class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message: str) -> None:
        super().__init__(parent)
        self.confirmed = False
        self.title("تأكيد")
        self.geometry("360x160")
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()
        ctk.CTkLabel(self, text=message, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=300,
                     ).pack(pady=(22, 14))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        ctk.CTkButton(row, text="إلغاء", width=100, height=34,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(row, text="حذف", width=100, height=34,
                      fg_color=COLORS["error"], text_color=COLORS["text_inverse"],
                      command=self._ok).pack(side="left", padx=8)

    def _ok(self):
        self.confirmed = True
        self.destroy()