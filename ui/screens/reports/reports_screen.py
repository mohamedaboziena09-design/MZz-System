"""
ui/screens/reports/reports_screen.py
======================================
شاشة التقارير — عرض + طباعة + تصدير PDF
يشمل: تقرير الموظفين، الأشخاص، السيارات
"""

from __future__ import annotations

import os
import pathlib
import tkinter as tk
from datetime import datetime
from typing import Any

import customtkinter as ctk

from ui.theme import COLORS, FONTS, RADIUS
from src.crud_service import CRUDService

REPORTS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "uploads" / "reports"


class ReportsScreen(ctk.CTkFrame):
    def __init__(self, parent, config: dict) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._config = config
        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        # Title
        ctk.CTkLabel(
            self, text="📊  التقارير",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Tabs
        self._tab = ctk.CTkTabview(
            self,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface2"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["surface2"],
            segmented_button_unselected_hover_color=COLORS["surface3"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=RADIUS["lg"],
        )
        self._tab.grid(row=1, column=0, sticky="nsew")

        self._tab.add("👔  الموظفين")
        self._tab.add("👥  الأشخاص")
        self._tab.add("🚗  السيارات")
        self._tab.add("📈  الملخص")

        self._build_employees_tab(self._tab.tab("👔  الموظفين"))
        self._build_persons_tab(self._tab.tab("👥  الأشخاص"))
        self._build_vehicles_tab(self._tab.tab("🚗  السيارات"))
        self._build_summary_tab(self._tab.tab("📈  الملخص"))

    # ════════════════════════════════════════════════════════
    # TAB: Employees
    # ════════════════════════════════════════════════════════

    def _build_employees_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Filter bar
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        bar.grid_columnconfigure(0, weight=1)

        self._emp_search = tk.StringVar()
        self._emp_search.trace_add("write", lambda *_: self._load_employees())

        ctk.CTkEntry(
            bar, textvariable=self._emp_search,
            placeholder_text="🔍  بحث...",
            font=FONTS["body"], height=36,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self._emp_status_var = tk.StringVar(value="الكل")
        ctk.CTkOptionMenu(
            bar, variable=self._emp_status_var,
            values=["الكل", "active", "inactive", "terminated"],
            font=FONTS["body"], height=36, width=140,
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            corner_radius=RADIUS["md"],
            command=lambda _: self._load_employees(),
        ).grid(row=0, column=1, padx=(0, 10))

        ctk.CTkButton(
            bar, text="🖨️  طباعة",
            font=FONTS["btn_sm"], height=36, width=110,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._print_employees,
        ).grid(row=0, column=2, padx=(0, 6))

        ctk.CTkButton(
            bar, text="💾  PDF",
            font=FONTS["btn_sm"], height=36, width=90,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._export_employees_pdf,
        ).grid(row=0, column=3)

        # Count
        self._emp_count = ctk.CTkLabel(
            tab, text="",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._emp_count.grid(row=1, column=0, sticky="w", padx=16)

        # Table
        self._emp_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._emp_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 16))
        self._emp_scroll.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        self._emp_data: list[dict] = []
        self._load_employees()

    def _load_employees(self) -> None:
        q  = self._emp_search.get().strip() if hasattr(self, "_emp_search") else ""
        st = self._emp_status_var.get() if hasattr(self, "_emp_status_var") else "الكل"
        try:
            with CRUDService() as svc:
                self._emp_data = svc.search_employees(
                    query=q or None,
                    employment_status=None if st == "الكل" else st,
                    limit=500,
                )
        except Exception:
            self._emp_data = []
        self._render_employees()

    def _render_employees(self) -> None:
        for w in self._emp_scroll.winfo_children():
            w.destroy()
        data = self._emp_data
        self._emp_count.configure(text=f"{len(data)} موظف")

        cols = ["#", "الاسم", "الكود", "القسم", "المسمى", "الهاتف", "تاريخ التعيين", "الحالة"]
        _TableHeader(self._emp_scroll, cols).grid(row=0, column=0, sticky="ew", pady=(0, 2))

        if not data:
            ctk.CTkLabel(self._emp_scroll, text="لا يوجد موظفين",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=1, column=0, pady=30)
            return

        for i, e in enumerate(data):
            values = [
                str(i + 1),
                f"{e['first_name']} {e['last_name']}",
                e.get("employee_code", "—"),
                e.get("department", "—"),
                e.get("position", "—"),
                e.get("phone") or "—",
                e.get("hire_date", "—"),
                e.get("employment_status", "—"),
            ]
            _TableRow(self._emp_scroll, values, i).grid(
                row=i + 1, column=0, sticky="ew", pady=1
            )

    def _print_employees(self) -> None:
        self._open_print_window(
            title="تقرير الموظفين",
            headers=["#", "الاسم", "الكود", "القسم", "المسمى", "الهاتف", "تاريخ التعيين", "الحالة"],
            rows=[
                [str(i+1), f"{e['first_name']} {e['last_name']}",
                 e.get("employee_code",""), e.get("department",""),
                 e.get("position",""), e.get("phone") or "",
                 e.get("hire_date",""), e.get("employment_status","")]
                for i, e in enumerate(self._emp_data)
            ],
        )

    def _export_employees_pdf(self) -> None:
        self._export_pdf(
            title="تقرير الموظفين",
            headers=["#", "الاسم", "الكود", "القسم", "المسمى", "الحالة"],
            rows=[
                [str(i+1), f"{e['first_name']} {e['last_name']}",
                 e.get("employee_code",""), e.get("department",""),
                 e.get("position",""), e.get("employment_status","")]
                for i, e in enumerate(self._emp_data)
            ],
            filename=f"employees_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        )

    # ════════════════════════════════════════════════════════
    # TAB: Persons
    # ════════════════════════════════════════════════════════

    def _build_persons_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        bar.grid_columnconfigure(0, weight=1)

        self._per_search = tk.StringVar()
        self._per_search.trace_add("write", lambda *_: self._load_persons())

        ctk.CTkEntry(
            bar, textvariable=self._per_search,
            placeholder_text="🔍  بحث...",
            font=FONTS["body"], height=36,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self._per_type_var = tk.StringVar(value="الكل")
        ctk.CTkOptionMenu(
            bar, variable=self._per_type_var,
            values=["الكل", "client", "supplier", "partner", "contractor", "other"],
            font=FONTS["body"], height=36, width=150,
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"], corner_radius=RADIUS["md"],
            command=lambda _: self._load_persons(),
        ).grid(row=0, column=1, padx=(0, 10))

        ctk.CTkButton(
            bar, text="🖨️  طباعة",
            font=FONTS["btn_sm"], height=36, width=110,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._print_persons,
        ).grid(row=0, column=2, padx=(0, 6))

        ctk.CTkButton(
            bar, text="💾  PDF",
            font=FONTS["btn_sm"], height=36, width=90,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text"],
            command=self._export_persons_pdf,
        ).grid(row=0, column=3)

        self._per_count = ctk.CTkLabel(
            tab, text="",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._per_count.grid(row=1, column=0, sticky="w", padx=16)

        self._per_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._per_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 16))
        self._per_scroll.grid_columnconfigure(0, weight=1)

        self._per_data: list[dict] = []
        self._load_persons()

    def _load_persons(self) -> None:
        q  = self._per_search.get().strip() if hasattr(self, "_per_search") else ""
        pt = self._per_type_var.get() if hasattr(self, "_per_type_var") else "الكل"
        try:
            with CRUDService() as svc:
                self._per_data = svc.search_persons(
                    query=q or None,
                    person_type=None if pt == "الكل" else pt,
                    limit=500,
                )
        except Exception:
            self._per_data = []
        self._render_persons()

    def _render_persons(self) -> None:
        for w in self._per_scroll.winfo_children():
            w.destroy()
        data = self._per_data
        self._per_count.configure(text=f"{len(data)} شخص")

        cols = ["#", "الاسم", "الكود", "النوع", "الهاتف", "البريد", "الحالة", "البيانات"]
        _TableHeader(self._per_scroll, cols).grid(row=0, column=0, sticky="ew", pady=(0, 2))

        if not data:
            ctk.CTkLabel(self._per_scroll, text="لا يوجد أشخاص",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=1, column=0, pady=30)
            return

        for i, p in enumerate(data):
            values = [
                str(i + 1),
                f"{p['first_name']} {p['last_name']}",
                p.get("person_code", "—"),
                p.get("person_type", "—"),
                p.get("phone") or "—",
                p.get("email") or "—",
                p.get("status", "—"),
                "✅ مكتمل" if p.get("profile_complete") else "⚠️ ناقص",
            ]
            _TableRow(self._per_scroll, values, i).grid(
                row=i + 1, column=0, sticky="ew", pady=1
            )

    def _print_persons(self) -> None:
        self._open_print_window(
            title="تقرير الأشخاص",
            headers=["#", "الاسم", "الكود", "النوع", "الهاتف", "الحالة"],
            rows=[
                [str(i+1), f"{p['first_name']} {p['last_name']}",
                 p.get("person_code",""), p.get("person_type",""),
                 p.get("phone") or "", p.get("status","")]
                for i, p in enumerate(self._per_data)
            ],
        )

    def _export_persons_pdf(self) -> None:
        self._export_pdf(
            title="تقرير الأشخاص",
            headers=["#", "الاسم", "الكود", "النوع", "الهاتف", "الحالة"],
            rows=[
                [str(i+1), f"{p['first_name']} {p['last_name']}",
                 p.get("person_code",""), p.get("person_type",""),
                 p.get("phone") or "", p.get("status","")]
                for i, p in enumerate(self._per_data)
            ],
            filename=f"persons_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        )

    # ════════════════════════════════════════════════════════
    # TAB: Vehicles
    # ════════════════════════════════════════════════════════

    def _build_vehicles_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        bar.grid_columnconfigure(0, weight=1)

        self._veh_search = tk.StringVar()
        self._veh_search.trace_add("write", lambda *_: self._load_vehicles())
        ctk.CTkEntry(
            bar, textvariable=self._veh_search,
            placeholder_text="🔍  بحث باللوحة أو الماركة...",
            font=FONTS["body"], height=36,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self._veh_status_var = tk.StringVar(value="الكل")
        ctk.CTkOptionMenu(
            bar, variable=self._veh_status_var,
            values=["الكل", "available", "assigned", "maintenance", "retired"],
            font=FONTS["body"], height=36, width=150,
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"], corner_radius=RADIUS["md"],
            command=lambda _: self._load_vehicles(),
        ).grid(row=0, column=1, padx=(0, 10))

        ctk.CTkButton(
            bar, text="🖨️  طباعة",
            font=FONTS["btn_sm"], height=36, width=110,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._print_vehicles,
        ).grid(row=0, column=2)

        self._veh_count = ctk.CTkLabel(
            tab, text="",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        )
        self._veh_count.grid(row=1, column=0, sticky="w", padx=16)

        self._veh_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._veh_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 16))
        self._veh_scroll.grid_columnconfigure(0, weight=1)

        self._veh_data: list[dict] = []
        self._load_vehicles()

    def _load_vehicles(self) -> None:
        q  = self._veh_search.get().strip() if hasattr(self, "_veh_search") else ""
        st = self._veh_status_var.get() if hasattr(self, "_veh_status_var") else "الكل"
        try:
            with CRUDService() as svc:
                db = svc.conn
                conds, params = [], []
                if q:
                    conds.append("(plate_number LIKE ? OR make LIKE ? OR model LIKE ?)")
                    kw = f"%{q}%"; params += [kw, kw, kw]
                if st != "الكل":
                    conds.append("status = ?"); params.append(st)
                where = f"WHERE {' AND '.join(conds)}" if conds else ""
                rows = db.execute(
                    f"SELECT * FROM vehicles {where} ORDER BY created_at DESC LIMIT 500",
                    params
                ).fetchall()
                self._veh_data = [dict(r) for r in rows]
        except Exception:
            self._veh_data = []
        self._render_vehicles()

    def _render_vehicles(self) -> None:
        for w in self._veh_scroll.winfo_children():
            w.destroy()
        data = self._veh_data
        self._veh_count.configure(text=f"{len(data)} سيارة")

        cols = ["#", "اللوحة", "الماركة", "الموديل", "السنة", "النوع", "التأمين", "الرخصة", "الحالة"]
        _TableHeader(self._veh_scroll, cols).grid(row=0, column=0, sticky="ew", pady=(0, 2))

        if not data:
            ctk.CTkLabel(self._veh_scroll, text="لا توجد سيارات",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=1, column=0, pady=30)
            return

        for i, v in enumerate(data):
            values = [
                str(i + 1),
                v.get("plate_number", "—"),
                v.get("make", "—"),
                v.get("model", "—"),
                str(v.get("year", "—")),
                v.get("vehicle_type", "—"),
                v.get("insurance_expiry") or "—",
                v.get("license_expiry") or "—",
                v.get("status", "—"),
            ]
            _TableRow(self._veh_scroll, values, i).grid(
                row=i + 1, column=0, sticky="ew", pady=1
            )

    def _print_vehicles(self) -> None:
        self._open_print_window(
            title="تقرير السيارات",
            headers=["#", "اللوحة", "الماركة", "الموديل", "السنة", "الحالة"],
            rows=[
                [str(i+1), v.get("plate_number",""), v.get("make",""),
                 v.get("model",""), str(v.get("year","")), v.get("status","")]
                for i, v in enumerate(self._veh_data)
            ],
        )

    # ════════════════════════════════════════════════════════
    # TAB: Summary
    # ════════════════════════════════════════════════════════

    def _build_summary_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure((0, 1), weight=1)

        try:
            with CRUDService() as svc:
                emp_total    = svc.count_employees()
                emp_active   = len(svc.search_employees(employment_status="active"))
                emp_inactive = len(svc.search_employees(employment_status="inactive"))
                emp_term     = len(svc.search_employees(employment_status="terminated"))
                per_total    = svc.count_persons()
                per_active   = svc.count_persons(status="active")
                per_complete = svc.count_persons(profile_complete=1)
                try:
                    veh_total = svc.conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
                    veh_avail = svc.conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='available'").fetchone()[0]
                    veh_asgn  = svc.conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='assigned'").fetchone()[0]
                    veh_maint = svc.conn.execute("SELECT COUNT(*) FROM vehicles WHERE status='maintenance'").fetchone()[0]
                except Exception:
                    veh_total = veh_avail = veh_asgn = veh_maint = 0
        except Exception:
            emp_total = emp_active = emp_inactive = emp_term = 0
            per_total = per_active = per_complete = 0
            veh_total = veh_avail = veh_asgn = veh_maint = 0

        company  = self._config.get("company_name", "")
        now_str  = datetime.now().strftime("%Y-%m-%d  %H:%M")

        ctk.CTkLabel(
            tab, text=f"تقرير شامل — {company}",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 2))

        ctk.CTkLabel(
            tab, text=f"تاريخ التقرير: {now_str}",
            font=FONTS["caption"], text_color=COLORS["text_dim"], anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 20))

        sections = [
            ("👔  الموظفين", [
                ("الإجمالي",    str(emp_total)),
                ("النشطين",     str(emp_active)),
                ("غير النشطين", str(emp_inactive)),
                ("المنتهية خدمتهم", str(emp_term)),
            ]),
            ("👥  الأشخاص", [
                ("الإجمالي",       str(per_total)),
                ("النشطين",        str(per_active)),
                ("بيانات مكتملة",  str(per_complete)),
                ("بيانات ناقصة",   str(per_total - per_complete)),
            ]),
            ("🚗  السيارات", [
                ("الإجمالي",   str(veh_total)),
                ("المتاحة",    str(veh_avail)),
                ("المعينة",    str(veh_asgn)),
                ("الصيانة",    str(veh_maint)),
            ]),
        ]

        for col, (title, rows) in enumerate(sections):
            card = ctk.CTkFrame(
                tab, fg_color=COLORS["surface"],
                corner_radius=RADIUS["lg"],
                border_width=1, border_color=COLORS["border"],
            )
            card.grid(row=2, column=col % 2, sticky="nsew",
                      padx=(16 if col%2==0 else 8, 8 if col%2==0 else 16),
                      pady=6)
            card.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                card, text=title,
                font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
            ).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 10), sticky="w")

            for r, (label, value) in enumerate(rows):
                ctk.CTkLabel(
                    card, text=label,
                    font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
                ).grid(row=r+1, column=0, padx=16, pady=4, sticky="w")
                ctk.CTkLabel(
                    card, text=value,
                    font=FONTS["heading"], text_color=COLORS["accent"], anchor="e",
                ).grid(row=r+1, column=1, padx=16, pady=4, sticky="e")

        # Print summary button
        ctk.CTkButton(
            tab, text="🖨️  طباعة الملخص الكامل",
            font=FONTS["btn"], height=44, corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=lambda: self._open_print_window(
                title=f"ملخص شامل — {company}  ({now_str})",
                headers=["البيان", "القيمة"],
                rows=[
                    ["إجمالي الموظفين", str(emp_total)],
                    ["الموظفين النشطين", str(emp_active)],
                    ["إجمالي الأشخاص", str(per_total)],
                    ["الأشخاص النشطين", str(per_active)],
                    ["إجمالي السيارات", str(veh_total)],
                    ["السيارات المتاحة", str(veh_avail)],
                ],
            ),
        ).grid(row=4, column=0, columnspan=2, padx=16, pady=20, sticky="ew")

    # ════════════════════════════════════════════════════════
    # Print Window
    # ════════════════════════════════════════════════════════

    def _open_print_window(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
    ) -> None:
        win = ctk.CTkToplevel(self)
        win.title(f"طباعة — {title}")
        win.geometry("900x620")
        win.configure(fg_color=COLORS["bg"])
        win.grab_set()

        # Header bar
        top = ctk.CTkFrame(win, fg_color=COLORS["surface"], corner_radius=0)
        top.pack(fill="x")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text=title,
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, padx=20, pady=12, sticky="w")

        ctk.CTkLabel(
            top,
            text=f"التاريخ: {datetime.now().strftime('%Y-%m-%d')}   |   "
                 f"عدد السجلات: {len(rows)}",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, padx=20, pady=(0, 12), sticky="w")

        ctk.CTkButton(
            top, text="🖨️  طباعة",
            font=FONTS["btn_sm"], width=110, height=36,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=lambda: self._do_print(win, title, headers, rows),
        ).grid(row=0, column=1, rowspan=2, padx=20)

        # Table
        scroll = ctk.CTkScrollableFrame(
            win, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        _TableHeader(scroll, headers).grid(row=0, column=0, sticky="ew", pady=(0, 2))
        for i, row in enumerate(rows):
            _TableRow(scroll, row, i).grid(row=i+1, column=0, sticky="ew", pady=1)

    def _do_print(self, win, title, headers, rows) -> None:
        """طباعة عبر نافذة HTML مؤقتة"""
        import tempfile, webbrowser
        html = self._build_html(title, headers, rows)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as f:
            f.write(html)
            path = f.name
        webbrowser.open(f"file://{path}")

    # ════════════════════════════════════════════════════════
    # PDF Export
    # ════════════════════════════════════════════════════════

    def _export_pdf(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
        filename: str,
    ) -> None:
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors as rl_colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            out = REPORTS_DIR / filename

            doc = SimpleDocTemplate(str(out), pagesize=landscape(A4))
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph(title, styles["Title"]))
            elements.append(Paragraph(
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Records: {len(rows)}",
                styles["Normal"],
            ))
            elements.append(Spacer(1, 12))

            data = [headers] + rows
            t = Table(data, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), rl_colors.HexColor("#4F6EF7")),
                ("TEXTCOLOR",   (0,0), (-1,0), rl_colors.white),
                ("FONTSIZE",    (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),
                 [rl_colors.HexColor("#1A1D27"), rl_colors.HexColor("#222535")]),
                ("TEXTCOLOR",   (0,1), (-1,-1), rl_colors.HexColor("#E8EAF2")),
                ("GRID",        (0,0), (-1,-1), 0.25, rl_colors.HexColor("#2E3248")),
                ("ALIGN",       (0,0), (-1,-1), "CENTER"),
                ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                ("TOPPADDING",  (0,0), (-1,-1), 6),
                ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ]))
            elements.append(t)
            doc.build(elements)
            self._show_success(f"✅  تم الحفظ:\n{out}")

        except ImportError:
            self._show_success(
                "⚠️  مكتبة reportlab غير مثبتة.\n"
                "شغّل:  pip install reportlab"
            )
        except Exception as e:
            self._show_success(f"❌  خطأ: {e}")

    # ════════════════════════════════════════════════════════
    # HTML for print
    # ════════════════════════════════════════════════════════

    def _build_html(self, title, headers, rows) -> str:
        th = "".join(f"<th>{h}</th>" for h in headers)
        tr = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            for row in rows
        )
        company = self._config.get("company_name", "MZz System")
        now     = datetime.now().strftime("%Y-%m-%d  %H:%M")
        return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin:30px; color:#111; }}
  h1   {{ font-size:20px; margin-bottom:4px; }}
  p    {{ font-size:12px; color:#555; margin-bottom:16px; }}
  table{{ border-collapse:collapse; width:100%; font-size:12px; }}
  th   {{ background:#4F6EF7; color:#fff; padding:9px 12px; text-align:right; }}
  td   {{ padding:8px 12px; text-align:right; border-bottom:1px solid #ddd; }}
  tr:nth-child(even) td {{ background:#f5f6fb; }}
  @media print {{ body {{ margin:10px; }} }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>{company}  —  {now}  |  عدد السجلات: {len(rows)}</p>
<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>
<script>window.onload=()=>window.print();</script>
</body></html>"""

    def _show_success(self, msg: str) -> None:
        dlg = ctk.CTkToplevel(self)
        dlg.title("تنبيه")
        dlg.geometry("400x160")
        dlg.configure(fg_color=COLORS["surface"])
        dlg.grab_set()
        ctk.CTkLabel(dlg, text=msg, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=360).pack(pady=24)
        ctk.CTkButton(dlg, text="حسناً", width=100, height=36,
                      fg_color=COLORS["accent"], text_color=COLORS["text_inverse"],
                      command=dlg.destroy).pack()


# ── Shared Table Widgets ──────────────────────────────────────

class _TableHeader(ctk.CTkFrame):
    def __init__(self, parent, cols: list[str]) -> None:
        super().__init__(parent, fg_color=COLORS["surface2"],
                         corner_radius=RADIUS["md"])
        for i, c in enumerate(cols):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(
                self, text=c,
                font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
            ).grid(row=0, column=i, padx=12, pady=8, sticky="w")


class _TableRow(ctk.CTkFrame):
    def __init__(self, parent, values: list[str], idx: int) -> None:
        bg = COLORS["surface"] if idx % 2 == 0 else COLORS["surface2"]
        super().__init__(parent, fg_color=bg, corner_radius=RADIUS["sm"])
        for i, v in enumerate(values):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(
                self, text=str(v),
                font=FONTS["body_sm"], text_color=COLORS["text"], anchor="w",
            ).grid(row=0, column=i, padx=12, pady=7, sticky="w")
        self.bind("<Enter>", lambda _: self.configure(fg_color=COLORS["surface3"]))
        self.bind("<Leave>", lambda _: self.configure(fg_color=bg))