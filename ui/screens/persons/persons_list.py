"""
ui/screens/persons/persons_list.py — V2.1
يستخدم WorkspaceContext بدل CRUDService مباشرة.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable
import customtkinter as ctk

from ui.theme    import COLORS, FONTS, RADIUS
from src.context import WorkspaceContext

TYPE_LABELS = {
    "client":     "👤 عميل",
    "supplier":   "🏭 مورد",
    "partner":    "🤝 شريك",
    "contractor": "🔧 متعاقد",
    "other":      "📎 أخرى",
}


class PersonsListScreen(ctk.CTkFrame):
    def __init__(self, parent, ctx: WorkspaceContext,
                 on_add:  Callable,
                 on_edit: Callable[[int], None],
                 on_view: Callable[[int], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._ctx          = ctx
        self._on_add       = on_add
        self._on_edit      = on_edit
        self._on_view      = on_view
        self._all:         list[dict] = []
        self._filter_type  = ""
        self._filter_status = ""

        self._build()
        self._load()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        # Toolbar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bar.grid_columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply())

        ctk.CTkEntry(
            bar, textvariable=self._search_var,
            placeholder_text="🔍  بحث بالاسم أو الكود أو الهاتف...",
            font=FONTS["body"], height=40,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            bar, text="+ إضافة شخص",
            font=FONTS["btn_sm"], height=40, width=140,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._on_add,
        ).grid(row=0, column=1)

        # Filter chips
        chips = ctk.CTkFrame(bar, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ctk.CTkLabel(chips, text="النوع:", font=FONTS["body_sm"],
                     text_color=COLORS["text_muted"],
                     ).pack(side="left", padx=(0, 6))

        for label, val in [("الكل", ""), ("👤 عميل", "client"),
                            ("🏭 مورد", "supplier"), ("🤝 شريك", "partner"),
                            ("🔧 متعاقد", "contractor")]:
            ctk.CTkButton(
                chips, text=label, font=FONTS["btn_sm"],
                height=28, width=90, corner_radius=RADIUS["sm"],
                fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
                text_color=COLORS["text_muted"],
                command=lambda v=val: self._set_type_filter(v),
            ).pack(side="left", padx=3)

        ctk.CTkLabel(chips, text="  |  الحالة:", font=FONTS["body_sm"],
                     text_color=COLORS["text_muted"],
                     ).pack(side="left", padx=(8, 6))

        for label, val in [("الكل", ""), ("نشط", "active"),
                            ("غير نشط", "inactive")]:
            ctk.CTkButton(
                chips, text=label, font=FONTS["btn_sm"],
                height=28, width=70, corner_radius=RADIUS["sm"],
                fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
                text_color=COLORS["text_muted"],
                command=lambda v=val: self._set_status_filter(v),
            ).pack(side="left", padx=3)

        # Count + complete stats
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

    # ── Load & Filter ─────────────────────────────────────────

    def _load(self) -> None:
        try:
            with self._ctx.db() as svc:
                self._all = svc.search_persons(limit=500)
        except Exception:
            self._all = []
        self._apply()

    def refresh(self) -> None:
        self._load()

    def _set_type_filter(self, val: str) -> None:
        self._filter_type = val
        self._apply()

    def _set_status_filter(self, val: str) -> None:
        self._filter_status = val
        self._apply()

    def _apply(self) -> None:
        q   = self._search_var.get().strip().lower()
        pt  = self._filter_type
        st  = self._filter_status

        filtered = [
            p for p in self._all
            if (not q or q in f"{p['first_name']} {p['last_name']} "
                              f"{p.get('person_code','')} "
                              f"{p.get('phone','') or ''} "
                              f"{p.get('national_id','') or ''}".lower())
            and (not pt  or p.get("person_type") == pt)
            and (not st  or p.get("status")      == st)
        ]
        self._render(filtered)

    # ── Render ────────────────────────────────────────────────

    def _render(self, persons: list[dict]) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()

        total    = len(persons)
        complete = sum(1 for p in persons if p.get("profile_complete"))
        self._count_lbl.configure(
            text=f"{total} شخص  ·  {complete} بيانات مكتملة  "
                 f"·  {total - complete} ناقصة"
        )

        if not persons:
            ctk.CTkLabel(self._scroll,
                         text="لا يوجد أشخاص مطابقين",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=0, column=0, pady=40)
            return

        _PersonHeader(self._scroll).grid(
            row=0, column=0, sticky="ew", pady=(0, 4)
        )
        for i, person in enumerate(persons):
            _PersonRow(
                self._scroll, person,
                on_view=lambda p=person: self._on_view(p["id"]),
                on_edit=lambda p=person: self._on_edit(p["id"]),
                on_delete=lambda p=person: self._confirm_delete(p),
            ).grid(row=i + 1, column=0, sticky="ew", pady=2)

    # ── Delete ────────────────────────────────────────────────

    def _confirm_delete(self, person: dict) -> None:
        name = f"{person['first_name']} {person['last_name']}"
        dlg  = _ConfirmDialog(self, f"حذف الشخص: {name}؟")
        self.wait_window(dlg)
        if dlg.confirmed:
            try:
                with self._ctx.db() as svc:
                    svc.delete_person(person["id"],
                                      file_store=self._ctx.file_store)
                self._load()
            except Exception:
                pass


# ── Widgets ───────────────────────────────────────────────────

class _PersonHeader(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["surface"],
                         corner_radius=RADIUS["md"])
        cols = ["الاسم", "الكود", "النوع", "الهاتف", "الحالة", "البيانات", ""]
        for i, text in enumerate(cols):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(self, text=text, font=FONTS["label"],
                         text_color=COLORS["text_muted"], anchor="w",
                         ).grid(row=0, column=i, padx=12, pady=8, sticky="w")


class _PersonRow(ctk.CTkFrame):
    def __init__(self, parent, person: dict,
                 on_view, on_edit, on_delete) -> None:
        super().__init__(parent, fg_color=COLORS["surface"],
                         corner_radius=RADIUS["md"],
                         border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure((0,1,2,3,4,5), weight=1)

        # Avatar + name
        nf = ctk.CTkFrame(self, fg_color="transparent")
        nf.grid(row=0, column=0, padx=12, pady=10, sticky="w")
        ctk.CTkLabel(
            nf,
            text=(person["first_name"] or "?")[0].upper(),
            font=FONTS["btn"], text_color=COLORS["text_inverse"],
            width=32, height=32,
            fg_color=COLORS["accent2"], corner_radius=16,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            nf,
            text=f"{person['first_name']} {person['last_name']}",
            font=FONTS["body"], text_color=COLORS["text"], anchor="w",
        ).pack(side="left")

        # Code
        ctk.CTkLabel(self, text=person.get("person_code","—"),
                     font=FONTS["code"], text_color=COLORS["text_dim"], anchor="w",
                     ).grid(row=0, column=1, padx=12, pady=10, sticky="w")

        # Type
        type_lbl = TYPE_LABELS.get(person.get("person_type",""), "—")
        ctk.CTkLabel(self, text=type_lbl, font=FONTS["body_sm"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=2, padx=12, pady=10, sticky="w")

        # Phone
        ctk.CTkLabel(self, text=person.get("phone") or "—",
                     font=FONTS["body_sm"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=3, padx=12, pady=10, sticky="w")

        # Status
        st    = person.get("status","active")
        s_clr = COLORS["success"] if st=="active" else COLORS["error"]
        s_lbl = "● نشط" if st=="active" else "● غير نشط"
        ctk.CTkLabel(self, text=s_lbl, font=FONTS["body_sm"],
                     text_color=s_clr, anchor="w",
                     ).grid(row=0, column=4, padx=12, pady=10, sticky="w")

        # Profile complete
        done  = person.get("profile_complete", 0)
        p_clr = COLORS["success"] if done else COLORS["warning"]
        p_lbl = "✅ مكتمل" if done else "⚠️ ناقص"
        ctk.CTkLabel(self, text=p_lbl, font=FONTS["body_sm"],
                     text_color=p_clr, anchor="w",
                     ).grid(row=0, column=5, padx=12, pady=10, sticky="w")

        # Actions
        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.grid(row=0, column=6, padx=12, pady=8, sticky="e")
        for txt, cmd, bg in [
            ("👁",  on_view,   COLORS["surface3"]),
            ("✏️",  on_edit,   COLORS["accent_dim"]),
            ("🗑",  on_delete, COLORS["error_dim"]),
        ]:
            ctk.CTkButton(
                btn_f, text=txt, width=32, height=32,
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
                      fg_color=COLORS["surface3"],
                      text_color=COLORS["text_muted"],
                      command=self.destroy,
                      ).pack(side="left", padx=8)
        ctk.CTkButton(row, text="حذف", width=100, height=34,
                      fg_color=COLORS["error"],
                      text_color=COLORS["text_inverse"],
                      command=self._ok,
                      ).pack(side="left", padx=8)

    def _ok(self) -> None:
        self.confirmed = True
        self.destroy()