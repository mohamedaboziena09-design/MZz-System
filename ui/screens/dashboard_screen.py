"""
ui/screens/dashboard_screen.py
================================
Dashboard — إحصائيات حقيقية من قاعدة البيانات.
"""

from __future__ import annotations
import customtkinter as ctk
from ui.theme import COLORS, FONTS, RADIUS
from src.crud_service import CRUDService


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, parent, config: dict) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._config = config
        self._build()

    def _build(self) -> None:
        company = self._config.get("company_name", "MZz System")

        ctk.CTkLabel(
            self, text=f"مرحباً بك في {company}",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            self,
            text="MZz System V1  —  إدارة الموظفين والأشخاص والمركبات",
            font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 28))

        # Load stats
        stats = self._load_stats()

        cards = [
            ("👔", "الموظفين",        str(stats["employees"]),  COLORS["accent"]),
            ("✅", "الموظفين النشطين", str(stats["active_emp"]), COLORS["success"]),
            ("👥", "الأشخاص",         str(stats["persons"]),    COLORS["warning"]),
            ("🚗", "السيارات",         str(stats["vehicles"]),   COLORS["error"]),
        ]

        for col, (icon, label, value, color) in enumerate(cards):
            _StatCard(self, icon, label, value, color).grid(
                row=2, column=col, sticky="ew",
                padx=(0, 12) if col < 3 else 0,
            )

        # Recent employees table
        ctk.CTkLabel(
            self, text="آخر الموظفين المضافين",
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(28, 10))

        table = ctk.CTkFrame(
            self, fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        table.grid(row=4, column=0, columnspan=4, sticky="ew")
        table.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Header
        for col, text in enumerate(["الاسم", "الكود", "القسم", "الحالة"]):
            ctk.CTkLabel(
                table, text=text,
                font=FONTS["label"], text_color=COLORS["text_muted"], anchor="w",
            ).grid(row=0, column=col, padx=16, pady=10, sticky="w")

        # Rows
        for i, emp in enumerate(stats["recent_emps"]):
            bg = COLORS["surface"] if i % 2 == 0 else COLORS["surface2"]
            st_color = {
                "active": COLORS["success"],
                "inactive": COLORS["warning"],
                "terminated": COLORS["error"],
            }.get(emp.get("employment_status", ""), COLORS["text_muted"])

            for col, val in enumerate([
                f"{emp['first_name']} {emp['last_name']}",
                emp.get("employee_code", "—"),
                emp.get("department", "—"),
                emp.get("employment_status", "—"),
            ]):
                color = st_color if col == 3 else COLORS["text"]
                ctk.CTkLabel(
                    table, text=val,
                    font=FONTS["body_sm"], text_color=color, anchor="w",
                    fg_color=bg,
                ).grid(row=i + 1, column=col, padx=16, pady=8, sticky="ew")

        if not stats["recent_emps"]:
            ctk.CTkLabel(
                table, text="لا يوجد موظفين بعد",
                font=FONTS["body"], text_color=COLORS["text_dim"],
            ).grid(row=1, column=0, columnspan=4, pady=20)

    def _load_stats(self) -> dict:
        try:
            with CRUDService() as svc:
                svc.run_migrations()
                employees   = svc.count_employees()
                active_emp  = len(svc.search_employees(employment_status="active"))
                persons     = svc.count_persons()
                recent_emps = svc.search_employees(limit=5)
                # vehicles count — direct query
                try:
                    vehicles = svc.conn.execute(
                        "SELECT COUNT(*) FROM vehicles"
                    ).fetchone()[0]
                except Exception:
                    vehicles = 0
            return {
                "employees":   employees,
                "active_emp":  active_emp,
                "persons":     persons,
                "vehicles":    vehicles,
                "recent_emps": recent_emps,
            }
        except Exception:
            return {
                "employees": 0, "active_emp": 0,
                "persons": 0,   "vehicles": 0,
                "recent_emps": [],
            }


class _StatCard(ctk.CTkFrame):
    def __init__(self, parent, icon, label, value, color) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"],
            border_width=1, border_color=COLORS["border"],
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            inner, text=icon,
            font=(FONTS["body"][0], 28),
            text_color=color, anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner, text=label,
            font=FONTS["caption"], text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(8, 2))

        ctk.CTkLabel(
            inner, text=value,
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")