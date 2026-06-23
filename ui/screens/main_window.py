"""
ui/screens/main_window.py
=========================
Main application window — Sidebar + dynamic Content Area.
Receives the config dict from LoginScreen and stays open for the session.
"""

from __future__ import annotations

from typing import Callable, Optional
import customtkinter as ctk

from ui.theme import COLORS, FONTS, SIDEBAR_WIDTH, TOPBAR_HEIGHT, WINDOW_MIN_W, WINDOW_MIN_H, RADIUS
from ui.components.sidebar import Sidebar
from ui.screens.persons.persons_list import PersonsListScreen
from ui.screens.persons.person_form  import PersonFormScreen


class MainWindow(ctk.CTk):
    """
    Parameters
    ----------
    config     : dict   — loaded from data/config.json
    on_logout  : Callable[[], None] — called when user clicks Logout
    """

    def __init__(
        self,
        config: dict,
        on_logout: Callable[[], None],
    ) -> None:
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

    # ──────────────────────────────────────────────────────────
    # Build
    # ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Root: sidebar | right_panel
        root = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = Sidebar(
            root,
            on_navigate=self._navigate,
            on_logout=self._logout,
            company_name=self._config.get("company_name", "MZz System"),
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        # Right panel: topbar + content
        right = ctk.CTkFrame(root, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Topbar
        self._topbar = _Topbar(right, title="Dashboard",
                               username=self._config.get("admin_username", "Admin"))
        self._topbar.grid(row=0, column=0, sticky="ew")

        # Content area
        self._content = ctk.CTkFrame(right, fg_color=COLORS["bg"], corner_radius=0)
        self._content.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Load default screen
        self._navigate("dashboard")

    # ──────────────────────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────────────────────

    def _navigate(self, key: str) -> None:
        """Show the screen for *key*, creating it if needed."""
        # Hide all
        for frame in self._frames.values():
            frame.grid_forget()

        # Create if missing
        if key not in self._frames:
            self._frames[key] = self._build_screen(key)

        self._frames[key].grid(row=0, column=0, sticky="nsew")
        self._sidebar.set_active(key)

        titles = {
            "dashboard": "Dashboard",
            "persons":   "Persons",
            "employees": "Employees",
            "reports":   "Reports",
            "settings":  "Settings",
        }
        self._topbar.set_title(titles.get(key, key.capitalize()))

    def _build_screen(self, key: str) -> ctk.CTkFrame:
        """Instantiate and return the frame for *key*."""
        if key == "dashboard":
            return _DashboardPlaceholder(self._content, self._config)
        if key == "persons":
            return PersonsListScreen(
                self._content,
                on_add=self._persons_add,
                on_edit=self._persons_edit,
                on_view=self._persons_view,
            )
        if key == "employees":
            return _ComingSoon(self._content, "Employees Module")
        if key == "reports":
            return _ComingSoon(self._content, "Reports Module")
        if key == "settings":
            return _ComingSoon(self._content, "Settings Module")
        return _ComingSoon(self._content, key.capitalize())

    # ── Persons navigation helpers ────────────────────────────

    def _persons_add(self) -> None:
        """Open Add Person form."""
        self._show_person_form(person_id=None)

    def _persons_edit(self, person_id: int) -> None:
        """Open Edit Person form."""
        self._show_person_form(person_id=person_id)

    def _persons_view(self, person_id: int) -> None:
        """For now, open edit form as view (profile tabs come next)."""
        self._show_person_form(person_id=person_id)

    def _show_person_form(self, person_id) -> None:
        key = f"person_form_{person_id or 'new'}"
        # Always recreate form to get fresh data
        if key in self._frames:
            self._frames[key].grid_forget()
            self._frames[key].destroy()
            del self._frames[key]

        for frame in self._frames.values():
            frame.grid_forget()

        form = PersonFormScreen(
            self._content,
            on_save=self._after_person_save,
            on_cancel=lambda: self._navigate("persons"),
            person_id=person_id,
        )
        form.grid(row=0, column=0, sticky="nsew")
        self._frames[key] = form

        title = "Edit Person" if person_id else "Add Person"
        self._topbar.set_title(title)

    # ──────────────────────────────────────────────────────────
    # Logout
    # ──────────────────────────────────────────────────────────

    def _logout(self) -> None:
        self.destroy()
        self._on_logout()

    def _after_person_save(self, person_id: int) -> None:
        """After saving, go back to persons list and refresh."""
        # Remove cached persons list so it reloads fresh
        if "persons" in self._frames:
            self._frames["persons"].grid_forget()
            self._frames["persons"].destroy()
            del self._frames["persons"]
        self._navigate("persons")

    # ──────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── Public API ───────────────────────────────────────────

    def navigate_to(self, key: str) -> None:
        """Navigate programmatically (e.g. after saving a record)."""
        self._navigate(key)


# ── Topbar ────────────────────────────────────────────────────

class _Topbar(ctk.CTkFrame):
    def __init__(self, parent, title: str, username: str) -> None:
        super().__init__(
            parent,
            height=TOPBAR_HEIGHT,
            fg_color=COLORS["surface"],
            corner_radius=0,
        )
        self.pack_propagate(False)

        self._title_var = ctk.StringVar(value=title)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24)

        self._title_lbl = ctk.CTkLabel(
            inner, textvariable=self._title_var,
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        )
        self._title_lbl.pack(side="left")

        ctk.CTkLabel(
            inner,
            text=f"👤  {username}",
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
            anchor="e",
        ).pack(side="right")

        # Bottom border
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).pack(
            side="bottom", fill="x"
        )

    def set_title(self, title: str) -> None:
        self._title_var.set(title)


# ── Dashboard Placeholder ─────────────────────────────────────

class _DashboardPlaceholder(ctk.CTkFrame):
    def __init__(self, parent, config: dict) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure((0, 1, 2), weight=1)

        company = config.get("company_name", "")

        ctk.CTkLabel(
            self,
            text=f"Welcome to {company}",
            font=FONTS["title"],
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        ctk.CTkLabel(
            self,
            text="MZz System V1  —  Employee & Personnel Records Management",
            font=FONTS["body"],
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 32))

        # Stat cards
        stats = [
            ("👤", "Total Employees",  "—",  COLORS["accent"]),
            ("✅", "Active",           "—",  COLORS["success"]),
            ("🚗", "Vehicles",         "—",  COLORS["warning"]),
        ]
        for col, (icon, label, value, color) in enumerate(stats):
            _StatCard(self, icon, label, value, color).grid(
                row=2, column=col, sticky="ew", padx=(0, 12) if col < 2 else 0
            )


class _StatCard(ctk.CTkFrame):
    def __init__(self, parent, icon, label, value, color) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(inner, text=icon, font=(FONTS["body"][0], 28),
                     text_color=color, anchor="w").pack(anchor="w")
        ctk.CTkLabel(inner, text=label, font=FONTS["caption"],
                     text_color=COLORS["text_muted"], anchor="w").pack(anchor="w", pady=(8, 2))
        ctk.CTkLabel(inner, text=value, font=FONTS["title"],
                     text_color=COLORS["text"], anchor="w").pack(anchor="w")


# ── Coming Soon ───────────────────────────────────────────────

class _ComingSoon(ctk.CTkFrame):
    def __init__(self, parent, name: str) -> None:
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(
            self, text=f"🚧  {name}",
            font=FONTS["title"], text_color=COLORS["text_muted"],
        ).pack(expand=True)
        ctk.CTkLabel(
            self, text="Coming soon in the next phase.",
            font=FONTS["body"], text_color=COLORS["text_dim"],
        ).pack()
