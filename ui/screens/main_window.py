"""
ui/screens/main_window.py
=========================
Main application window — Sidebar + dynamic Content Area.
Updated to include Employees, Vehicles, Reports screens.
"""

from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from ui.theme import (
    COLORS, FONTS, RADIUS,
    SIDEBAR_WIDTH, TOPBAR_HEIGHT,
    WINDOW_MIN_W, WINDOW_MIN_H,
)
from ui.components.sidebar import Sidebar

# Screens
from ui.screens.persons.persons_list   import PersonsListScreen
from ui.screens.persons.person_form    import PersonFormScreen
from ui.screens.employees.employees_list    import EmployeesListScreen
from ui.screens.employees.employee_form    import EmployeeFormScreen
from ui.screens.employees.employee_profile import EmployeeProfileScreen
from ui.screens.reports.reports_screen     import ReportsScreen
from ui.screens.vehicles.vehicles_screen   import VehiclesScreen
from ui.screens.dashboard_screen           import DashboardScreen


class MainWindow(ctk.CTk):
    def __init__(self, config: dict, on_logout: Callable) -> None:
        super().__init__()
        self._config    = config
        self._on_logout = on_logout
        self._frames: dict[str, ctk.CTkFrame] = {}

        ctk.set_appearance_mode("dark")
        self.title(f"MZz System V1  —  {config.get('company_name', '')}")
        self.geometry(f"{WINDOW_MIN_W}x{WINDOW_MIN_H}")
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.configure(fg_color=COLORS["bg"])
        self._center(WINDOW_MIN_W, WINDOW_MIN_H)
        self._build()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        root = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        self._sidebar = Sidebar(
            root,
            on_navigate=self._navigate,
            on_logout=self._logout,
            company_name=self._config.get("company_name", "MZz System"),
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        right = ctk.CTkFrame(root, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._topbar = _Topbar(
            right, title="Dashboard",
            username=self._config.get("admin_username", "Admin"),
        )
        self._topbar.grid(row=0, column=0, sticky="ew")

        self._content = ctk.CTkFrame(right, fg_color=COLORS["bg"], corner_radius=0)
        self._content.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._navigate("dashboard")

    # ── Navigation ────────────────────────────────────────────

    def _navigate(self, key: str) -> None:
        for frame in self._frames.values():
            frame.grid_forget()
        if key not in self._frames:
            self._frames[key] = self._build_screen(key)
        self._frames[key].grid(row=0, column=0, sticky="nsew")
        self._sidebar.set_active(key)
        titles = {
            "dashboard": "Dashboard",
            "persons":   "الأشخاص والعملاء",
            "employees": "الموظفين",
            "vehicles":  "السيارات",
            "reports":   "التقارير",
            "settings":  "الإعدادات",
        }
        self._topbar.set_title(titles.get(key, key.capitalize()))

    def _build_screen(self, key: str) -> ctk.CTkFrame:
        if key == "dashboard":
            return DashboardScreen(self._content, self._config)
        if key == "persons":
            return PersonsListScreen(
                self._content,
                on_add=self._persons_add,
                on_edit=self._persons_edit,
                on_view=self._persons_view,
            )
        if key == "employees":
            return EmployeesListScreen(
                self._content,
                on_add=self._employees_add,
                on_edit=self._employees_edit,
                on_view=self._employees_view,
            )
        if key == "vehicles":
            return VehiclesScreen(self._content, self._config)
        if key == "reports":
            return ReportsScreen(self._content, self._config)
        if key == "settings":
            return _ComingSoon(self._content, "⚙️ الإعدادات")
        return _ComingSoon(self._content, key)

    # ── Persons ───────────────────────────────────────────────

    def _persons_add(self)              -> None: self._show_person_form(None)
    def _persons_edit(self, pid: int)   -> None: self._show_person_form(pid)
    def _persons_view(self, pid: int)   -> None: self._show_person_form(pid)

    def _show_person_form(self, person_id) -> None:
        key = f"person_form_{person_id or 'new'}"
        self._destroy_frame(key)
        self._hide_all()
        form = PersonFormScreen(
            self._content,
            on_save=self._after_person_save,
            on_cancel=lambda: self._navigate("persons"),
            person_id=person_id,
        )
        form.grid(row=0, column=0, sticky="nsew")
        self._frames[key] = form
        self._topbar.set_title("تعديل شخص" if person_id else "إضافة شخص")

    def _after_person_save(self, pid: int) -> None:
        self._destroy_frame("persons")
        self._navigate("persons")

    # ── Employees ─────────────────────────────────────────────

    def _employees_add(self)             -> None: self._show_employee_form(None)
    def _employees_edit(self, eid: int)  -> None: self._show_employee_form(eid)
    def _employees_view(self, eid: int)  -> None: self._show_employee_profile(eid)

    def _show_employee_profile(self, employee_id: int) -> None:
        key = f"emp_profile_{employee_id}"
        self._destroy_frame(key)
        self._hide_all()
        profile = EmployeeProfileScreen(
            self._content,
            employee_id=employee_id,
            on_back=lambda: self._navigate("employees"),
            on_edit=self._show_employee_form,
        )
        profile.grid(row=0, column=0, sticky="nsew")
        self._frames[key] = profile
        self._topbar.set_title("بطاقة الموظف")

    def _show_employee_form(self, employee_id) -> None:
        key = f"emp_form_{employee_id or 'new'}"
        self._destroy_frame(key)
        self._hide_all()
        form = EmployeeFormScreen(
            self._content,
            on_save=self._after_employee_save,
            on_cancel=lambda: self._navigate("employees"),
            employee_id=employee_id,
        )
        form.grid(row=0, column=0, sticky="nsew")
        self._frames[key] = form
        self._topbar.set_title("تعديل موظف" if employee_id else "إضافة موظف")

    def _after_employee_save(self, eid: int) -> None:
        self._destroy_frame("employees")
        self._navigate("employees")

    # ── Helpers ───────────────────────────────────────────────

    def _hide_all(self) -> None:
        for f in self._frames.values():
            f.grid_forget()

    def _destroy_frame(self, key: str) -> None:
        if key in self._frames:
            self._frames[key].grid_forget()
            self._frames[key].destroy()
            del self._frames[key]

    def _logout(self) -> None:
        self.destroy()
        self._on_logout()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


# ── Topbar ────────────────────────────────────────────────────

class _Topbar(ctk.CTkFrame):
    def __init__(self, parent, title: str, username: str) -> None:
        super().__init__(
            parent, height=TOPBAR_HEIGHT,
            fg_color=COLORS["surface"], corner_radius=0,
        )
        self.pack_propagate(False)
        self._title_var = ctk.StringVar(value=title)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24)

        ctk.CTkLabel(
            inner, textvariable=self._title_var,
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            inner, text=f"👤  {username}",
            font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="e",
        ).pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).pack(
            side="bottom", fill="x"
        )

    def set_title(self, title: str) -> None:
        self._title_var.set(title)


# ── Coming Soon ───────────────────────────────────────────────

class _ComingSoon(ctk.CTkFrame):
    def __init__(self, parent, name: str) -> None:
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(
            self, text=name,
            font=FONTS["title"], text_color=COLORS["text_muted"],
        ).pack(expand=True)
        ctk.CTkLabel(
            self, text="قريباً في الإصدار القادم.",
            font=FONTS["body"], text_color=COLORS["text_dim"],
        ).pack()