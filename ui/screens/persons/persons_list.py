"""
ui/screens/persons/persons_list.py
===================================
Persons List Screen — Full CRUD entry point.

Layout
------
┌─ Topbar ──────────────────────────────────────────┐
│  Persons                          [+ Add Person]  │
├─ Toolbar ─────────────────────────────────────────┤
│  [🔍 Search...]  [Type ▾]  [Status ▾]  [⚠ Only]  │
├─ Table ───────────────────────────────────────────┤
│  Code │ Name │ Type │ Phone │ Status │ Profile │  │
│  ...  │ ...  │ ...  │ ...   │ ...    │ ...     │  │
├─ Footer ──────────────────────────────────────────┤
│  Showing X of Y        [< Prev]  Page N  [Next >] │
└───────────────────────────────────────────────────┘
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, Any

import customtkinter as ctk

from ui.theme import COLORS, FONTS, RADIUS
from src.crud_service import CRUDService, NotFoundError

# Pagination
PAGE_SIZE = 20

# Table columns: (key, header, width, anchor)
COLUMNS = [
    ("person_code",      "Code",       130, "w"),
    ("full_name",        "Name",       180, "w"),
    ("person_type",      "Type",       110, "center"),
    ("phone",            "Phone",      130, "w"),
    ("email",            "Email",      180, "w"),
    ("status",           "Status",      90, "center"),
    ("profile_complete", "Profile",     90, "center"),
]

TYPE_LABELS = {
    "client":     "Client",
    "supplier":   "Supplier",
    "partner":    "Partner",
    "contractor": "Contractor",
    "other":      "Other",
}

TYPE_OPTIONS  = ["All Types"] + list(TYPE_LABELS.values())
STATUS_OPTIONS = ["All Status", "Active", "Inactive"]


class PersonsListScreen(ctk.CTkFrame):
    """
    Parameters
    ----------
    parent      : parent widget (content area of MainWindow)
    on_add      : Callable — open Add Person form
    on_edit     : Callable[[int], None] — open Edit form for person_id
    on_view     : Callable[[int], None] — open Profile view for person_id
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
        self.grid_rowconfigure(2, weight=1)

        self._on_add  = on_add
        self._on_edit = on_edit
        self._on_view = on_view

        self._page        = 0
        self._total       = 0
        self._rows: list[dict[str, Any]] = []
        self._selected_id: Optional[int] = None

        # Filter state
        self._query_var  = tk.StringVar()
        self._type_var   = tk.StringVar(value="All Types")
        self._status_var = tk.StringVar(value="All Status")
        self._incomplete_only = tk.BooleanVar(value=False)

        self._build()
        self.refresh()

    # ──────────────────────────────────────────────────────────
    # Build UI
    # ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Header ──────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Persons",
            font=FONTS["title"], text_color=COLORS["text"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="＋  Add Person",
            font=FONTS["btn_sm"], height=36,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._on_add,
        ).grid(row=0, column=1, sticky="e")

        # ── Toolbar ──────────────────────────────────────────
        toolbar = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                corner_radius=RADIUS["md"],
                                border_width=1, border_color=COLORS["border"])
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)
        inner.grid_columnconfigure(0, weight=1)

        # Search
        search_frame = ctk.CTkFrame(inner, fg_color=COLORS["surface2"],
                                     corner_radius=RADIUS["md"],
                                     border_width=1, border_color=COLORS["border"])
        search_frame.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        ctk.CTkLabel(search_frame, text="🔍", font=FONTS["body"],
                     text_color=COLORS["text_muted"],
                     width=32).pack(side="left", padx=(10, 0))

        search_entry = ctk.CTkEntry(
            search_frame, textvariable=self._query_var,
            placeholder_text="Search by name, code, phone, email...",
            border_width=0, fg_color="transparent",
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_dim"],
            font=FONTS["body"], height=36,
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=8)
        self._query_var.trace_add("write", lambda *_: self._on_filter_change())

        # Type filter
        ctk.CTkOptionMenu(
            inner, variable=self._type_var,
            values=TYPE_OPTIONS,
            font=FONTS["body_sm"], dropdown_font=FONTS["body_sm"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            width=140, height=36, corner_radius=RADIUS["md"],
            command=lambda _: self._on_filter_change(),
        ).grid(row=0, column=1, padx=(0, 8))

        # Status filter
        ctk.CTkOptionMenu(
            inner, variable=self._status_var,
            values=STATUS_OPTIONS,
            font=FONTS["body_sm"], dropdown_font=FONTS["body_sm"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            width=130, height=36, corner_radius=RADIUS["md"],
            command=lambda _: self._on_filter_change(),
        ).grid(row=0, column=2, padx=(0, 8))

        # Incomplete only toggle
        ctk.CTkCheckBox(
            inner, text="⚠  Incomplete only",
            variable=self._incomplete_only,
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color=COLORS["text_inverse"],
            command=self._on_filter_change,
        ).grid(row=0, column=3)

        # ── Table ────────────────────────────────────────────
        table_card = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                   corner_radius=RADIUS["md"],
                                   border_width=1, border_color=COLORS["border"])
        table_card.grid(row=2, column=0, sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)

        # Table header
        self._table_header = _TableHeader(table_card)
        self._table_header.grid(row=0, column=0, sticky="ew")

        # Table body (scrollable)
        self._table_body = ctk.CTkScrollableFrame(
            table_card, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._table_body.grid(row=1, column=0, sticky="nsew")
        self._table_body.grid_columnconfigure(0, weight=1)

        # Empty state
        self._empty_label = ctk.CTkLabel(
            self._table_body,
            text="No persons found.",
            font=FONTS["body"], text_color=COLORS["text_dim"],
        )

        # ── Footer ───────────────────────────────────────────
        self._footer = _Footer(
            self,
            on_prev=self._prev_page,
            on_next=self._next_page,
        )
        self._footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    # ──────────────────────────────────────────────────────────
    # Data
    # ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload data from DB and re-render the table."""
        filters = self._get_filters()

        with CRUDService() as svc:
            svc.run_migrations()
            self._rows  = svc.search_persons(**filters, limit=PAGE_SIZE, offset=self._page * PAGE_SIZE)
            self._total = svc.count_persons(
                person_type=filters.get("person_type"),
                status=filters.get("status"),
                profile_complete=filters.get("profile_complete"),
            )

        self._render_table()
        self._footer.update_info(
            shown=len(self._rows),
            total=self._total,
            page=self._page,
            page_size=PAGE_SIZE,
        )

    def _get_filters(self) -> dict:
        f: dict = {}

        q = self._query_var.get().strip()
        if q:
            f["query"] = q

        t = self._type_var.get()
        if t != "All Types":
            # reverse lookup label → key
            rev = {v: k for k, v in TYPE_LABELS.items()}
            f["person_type"] = rev.get(t, t.lower())

        s = self._status_var.get()
        if s != "All Status":
            f["status"] = s.lower()

        if self._incomplete_only.get():
            f["profile_complete"] = 0

        return f

    def _on_filter_change(self) -> None:
        self._page = 0
        self.refresh()

    # ──────────────────────────────────────────────────────────
    # Render
    # ──────────────────────────────────────────────────────────

    def _render_table(self) -> None:
        for w in self._table_body.winfo_children():
            w.destroy()

        if not self._rows:
            self._empty_label = ctk.CTkLabel(
                self._table_body,
                text="No persons found.",
                font=FONTS["body"], text_color=COLORS["text_dim"],
            )
            self._empty_label.pack(pady=40)
            return

        for i, row in enumerate(self._rows):
            bg = COLORS["surface"] if i % 2 == 0 else COLORS["surface2"]
            _TableRow(
                self._table_body,
                data=row,
                bg=bg,
                on_edit=self._on_edit,
                on_view=self._on_view,
                on_delete=self._confirm_delete,
            ).grid(row=i, column=0, sticky="ew", pady=1)

    # ──────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────

    def _confirm_delete(self, person_id: int, name: str) -> None:
        dialog = _ConfirmDialog(
            self,
            title="Delete Person",
            message=f"Are you sure you want to delete\n\"{name}\"?\n\nThis action cannot be undone.",
            on_confirm=lambda: self._do_delete(person_id),
        )
        dialog.grab_set()

    def _do_delete(self, person_id: int) -> None:
        with CRUDService() as svc:
            svc.delete_person(person_id)
        self.refresh()

    # ──────────────────────────────────────────────────────────
    # Pagination
    # ──────────────────────────────────────────────────────────

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self) -> None:
        if (self._page + 1) * PAGE_SIZE < self._total:
            self._page += 1
            self.refresh()


# ── Table Header ──────────────────────────────────────────────

class _TableHeader(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["surface3"],
                         corner_radius=0, height=40)
        self.pack_propagate(False)
        self.grid_columnconfigure(len(COLUMNS), weight=1)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16)

        for i, (_, header, width, anchor) in enumerate(COLUMNS):
            ctk.CTkLabel(
                row, text=header,
                font=FONTS["label"], text_color=COLORS["text_muted"],
                width=width, anchor=anchor,
            ).pack(side="left", padx=(0, 8))

        # Actions column
        ctk.CTkLabel(
            row, text="Actions",
            font=FONTS["label"], text_color=COLORS["text_muted"],
            width=120, anchor="center",
        ).pack(side="right")


# ── Table Row ─────────────────────────────────────────────────

class _TableRow(ctk.CTkFrame):
    def __init__(
        self, parent,
        data: dict[str, Any],
        bg: str,
        on_edit:   Callable[[int], None],
        on_view:   Callable[[int], None],
        on_delete: Callable[[int, str], None],
    ) -> None:
        super().__init__(parent, fg_color=bg, corner_radius=0, height=44)
        self.pack_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        pid  = data["id"]
        name = f"{data['first_name']} {data['last_name']}"

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=16)

        # Data cells
        values = {
            "person_code":      data.get("person_code", ""),
            "full_name":        name,
            "person_type":      TYPE_LABELS.get(data.get("person_type", ""), "—"),
            "phone":            data.get("phone") or "—",
            "email":            data.get("email") or "—",
            "status":           (data.get("status") or "").capitalize(),
            "profile_complete": "✅ Complete" if data.get("profile_complete") else "⚠ Incomplete",
        }

        for key, _, width, anchor in COLUMNS:
            val = values.get(key, "—")
            color = COLORS["text"]
            if key == "status":
                color = COLORS["success"] if val == "Active" else COLORS["text_muted"]
            elif key == "profile_complete":
                color = COLORS["success"] if "Complete" in val else COLORS["warning"]

            ctk.CTkLabel(
                row, text=val,
                font=FONTS["body_sm"], text_color=color,
                width=width, anchor=anchor,
            ).pack(side="left", padx=(0, 8))

        # Action buttons
        actions = ctk.CTkFrame(row, fg_color="transparent", width=120)
        actions.pack(side="right")
        actions.pack_propagate(False)

        ctk.CTkButton(
            actions, text="View",
            font=FONTS["caption"], width=38, height=26,
            corner_radius=RADIUS["sm"],
            fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
            text_color=COLORS["accent"],
            command=lambda: on_view(pid),
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            actions, text="Edit",
            font=FONTS["caption"], width=38, height=26,
            corner_radius=RADIUS["sm"],
            fg_color=COLORS["surface3"], hover_color=COLORS["accent"],
            text_color=COLORS["text_muted"],
            command=lambda: on_edit(pid),
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            actions, text="✕",
            font=FONTS["caption"], width=26, height=26,
            corner_radius=RADIUS["sm"],
            fg_color=COLORS["error_dim"], hover_color=COLORS["error"],
            text_color=COLORS["error"],
            command=lambda: on_delete(pid, name),
        ).pack(side="left")


# ── Footer ────────────────────────────────────────────────────

class _Footer(ctk.CTkFrame):
    def __init__(self, parent, on_prev: Callable, on_next: Callable) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)

        self._info_var = tk.StringVar(value="")

        ctk.CTkLabel(
            self, textvariable=self._info_var,
            font=FONTS["caption"], text_color=COLORS["text_dim"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=2, sticky="e")

        self._prev_btn = ctk.CTkButton(
            nav, text="← Prev",
            font=FONTS["caption"], width=70, height=30,
            corner_radius=RADIUS["sm"],
            fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
            text_color=COLORS["text_muted"],
            command=on_prev,
        )
        self._prev_btn.pack(side="left", padx=(0, 8))

        self._page_label = ctk.CTkLabel(
            nav, text="Page 1",
            font=FONTS["caption"], text_color=COLORS["text_muted"],
        )
        self._page_label.pack(side="left", padx=(0, 8))

        self._next_btn = ctk.CTkButton(
            nav, text="Next →",
            font=FONTS["caption"], width=70, height=30,
            corner_radius=RADIUS["sm"],
            fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
            text_color=COLORS["text_muted"],
            command=on_next,
        )
        self._next_btn.pack(side="left")

    def update_info(self, shown: int, total: int, page: int, page_size: int) -> None:
        start = page * page_size + 1 if total > 0 else 0
        end   = start + shown - 1
        self._info_var.set(f"Showing {start}–{end} of {total} persons")
        self._page_label.configure(text=f"Page {page + 1}")
        self._prev_btn.configure(state="normal" if page > 0 else "disabled")
        self._next_btn.configure(
            state="normal" if (page + 1) * page_size < total else "disabled"
        )


# ── Confirm Delete Dialog ─────────────────────────────────────

class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, message: str,
                 on_confirm: Callable) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("380x220")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["surface"])
        self._on_confirm = on_confirm

        # Center over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"380x220+{px - 190}+{py - 110}")

        ctk.CTkLabel(
            self, text=title,
            font=FONTS["heading"], text_color=COLORS["text"],
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            self, text=message,
            font=FONTS["body_sm"], text_color=COLORS["text_muted"],
            justify="center", wraplength=320,
        ).pack(pady=(0, 24))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack()

        ctk.CTkButton(
            btns, text="Cancel",
            font=FONTS["btn_sm"], width=100, height=36,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface3"], hover_color=COLORS["surface2"],
            text_color=COLORS["text_muted"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            btns, text="Delete",
            font=FONTS["btn_sm"], width=100, height=36,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["error"], hover_color="#C0392B",
            text_color=COLORS["text_inverse"],
            command=self._confirm,
        ).pack(side="left")

    def _confirm(self) -> None:
        self.destroy()
        self._on_confirm()
