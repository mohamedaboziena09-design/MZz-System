"""
ui/screens/employees/employee_profile.py — V2.1
يستخدم WorkspaceContext لكل العمليات.
"""

from __future__ import annotations

import shutil
import pathlib
import tkinter as tk
from tkinter import filedialog
from typing import Callable, Any

import customtkinter as ctk
from PIL import Image

from ui.theme import COLORS, FONTS, RADIUS
from src.context import WorkspaceContext

DOC_TYPE_LABELS = {
    "national_id_copy":    "🪪  صورة الهوية",
    "employment_contract": "📄  عقد العمل",
    "certificate":         "🎓  شهادة علمية",
    "resume":              "📝  السيرة الذاتية",
    "other":               "📎  أخرى",
}
DOC_TYPES = list(DOC_TYPE_LABELS.keys())

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


class EmployeeProfileScreen(ctk.CTkFrame):
    def __init__(self, parent, ctx: WorkspaceContext,
                 employee_id: int,
                 on_back: Callable,
                 on_edit: Callable[[int], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._ctx     = ctx
        self._emp_id  = employee_id
        self._on_back = on_back
        self._on_edit = on_edit
        self._emp:  dict[str, Any] = {}
        self._docs: list[dict]     = []

        self._load()
        self._build()

    def _load(self) -> None:
        with self._ctx.db() as svc:
            self._emp  = svc.get_employee(self._emp_id)
            self._docs = svc.list_documents(self._emp_id)

    def _build(self) -> None:
        emp = self._emp

        # Action bar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(bar, text="← رجوع",
                      font=FONTS["btn_sm"], width=100, height=36,
                      corner_radius=RADIUS["md"],
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self._on_back,
                      ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(bar, text="✏️  تعديل البيانات",
                      font=FONTS["btn_sm"], width=150, height=36,
                      corner_radius=RADIUS["md"],
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      text_color=COLORS["text_inverse"],
                      command=lambda: self._on_edit(self._emp_id),
                      ).grid(row=0, column=2, sticky="e")

        # Scroll
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=COLORS["border"])
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Profile card
        card = ctk.CTkFrame(scroll, fg_color=COLORS["surface"],
                            corner_radius=RADIUS["xl"],
                            border_width=1, border_color=COLORS["border"])
        card.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        card.grid_columnconfigure(1, weight=1)

        # Photo
        pf = ctk.CTkFrame(card, fg_color="transparent")
        pf.grid(row=0, column=0, padx=24, pady=24, sticky="n")

        self._photo_lbl = ctk.CTkLabel(pf, text="", width=110, height=110)
        self._photo_lbl.pack()
        self._render_photo()

        ctk.CTkButton(pf, text="📷 تغيير",
                      font=FONTS["caption"], width=110, height=28,
                      corner_radius=RADIUS["sm"],
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self._upload_photo,
                      ).pack(pady=(8, 0))

        # Info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, padx=(0, 24), pady=24, sticky="nsew")
        info.grid_columnconfigure((0, 1), weight=1)

        name = f"{emp['first_name']} {emp['last_name']}"
        st   = emp.get("employment_status", "active")

        ctk.CTkLabel(info, text=name, font=FONTS["title"],
                     text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        ctk.CTkLabel(info, text=emp.get("position","—"), font=FONTS["subtitle"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        badges = ctk.CTkFrame(info, fg_color="transparent")
        badges.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 16))
        for text, bg, fg in [
            (emp.get("employee_code",""),  COLORS["accent_dim"],   COLORS["accent"]),
            (emp.get("department",""),     COLORS["surface3"],     COLORS["text"]),
            (STATUS_LABELS.get(st, st),
             COLORS["success_dim"] if st == "active" else COLORS["error_dim"],
             STATUS_COLORS.get(st, COLORS["text_muted"])),
        ]:
            ctk.CTkLabel(badges, text=f"  {text}  ", font=FONTS["body_sm"],
                         text_color=fg, fg_color=bg, corner_radius=RADIUS["sm"],
                         height=26).pack(side="left", padx=(0, 8))

        fields = [
            ("رقم الهوية",    emp.get("national_id","—")),
            ("تاريخ الميلاد", emp.get("date_of_birth","—")),
            ("الجنس",         "ذكر" if emp.get("gender")=="male" else "أنثى"),
            ("الهاتف",        emp.get("phone") or "—"),
            ("البريد",        emp.get("email") or "—"),
            ("العنوان",       emp.get("address") or "—"),
            ("تاريخ التعيين", emp.get("hire_date","—")),
            ("ملاحظات",       emp.get("notes") or "—"),
        ]
        for i, (label, value) in enumerate(fields):
            col = i % 2
            row = (i // 2) + 3
            _InfoCell(info, label, value).grid(
                row=row, column=col, sticky="ew",
                padx=(0, 12) if col == 0 else 0, pady=4,
            )

        # Documents section
        _SectionLabel(scroll, "📁  المستندات المرفقة").grid(
            row=1, column=0, sticky="w", pady=(0, 12))

        # Upload bar
        ubar = ctk.CTkFrame(scroll, fg_color="transparent")
        ubar.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ubar.grid_columnconfigure(0, weight=1)

        self._doc_type_var = tk.StringVar(value=DOC_TYPES[0])
        ctk.CTkOptionMenu(
            ubar, variable=self._doc_type_var, values=DOC_TYPES,
            font=FONTS["body"], fg_color=COLORS["surface2"],
            button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text"], height=38,
            corner_radius=RADIUS["md"], width=220,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(ubar, text="📎  رفع مستند",
                      font=FONTS["btn_sm"], height=38, width=130,
                      corner_radius=RADIUS["md"],
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      text_color=COLORS["text_inverse"],
                      command=self._upload_document,
                      ).grid(row=0, column=1, padx=(12, 0))

        # Docs list
        self._docs_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._docs_frame.grid(row=3, column=0, sticky="ew")
        self._docs_frame.grid_columnconfigure(0, weight=1)
        self._render_docs()

    # ── Photo ─────────────────────────────────────────────────

    def _render_photo(self) -> None:
        rel = self._emp.get("photo_path")
        try:
            if rel:
                full = self._ctx.abs_path(rel)
                if full.exists():
                    img    = Image.open(full).resize((110, 110))
                    ctk_img = ctk.CTkImage(img, size=(110, 110))
                    self._photo_lbl.configure(
                        image=ctk_img, text="", fg_color="transparent")
                    self._photo_lbl._image = ctk_img
                    return
        except Exception:
            pass
        letter = (self._emp.get("first_name") or "?")[0].upper()
        self._photo_lbl.configure(
            text=letter, font=FONTS["logo"],
            text_color=COLORS["text_inverse"],
            fg_color=COLORS["accent"],
            corner_radius=55, width=110, height=110,
        )

    def _upload_photo(self) -> None:
        src = filedialog.askopenfilename(
            title="اختر صورة",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")],
        )
        if not src:
            return
        ext  = pathlib.Path(src).suffix
        dest = self._ctx.photo_path("employees", self._emp_id, ext)
        shutil.copy2(src, dest)
        rel  = self._ctx.relative_path(dest)
        with self._ctx.db() as svc:
            svc.update_employee(self._emp_id, {"photo_path": rel})
        self._emp["photo_path"] = rel
        self._render_photo()
        self._ctx.log(f"Photo updated for employee {self._emp_id}")

    # ── Documents ─────────────────────────────────────────────

    def _render_docs(self) -> None:
        for w in self._docs_frame.winfo_children():
            w.destroy()
        if not self._docs:
            ctk.CTkLabel(self._docs_frame,
                         text="لا توجد مستندات مرفقة بعد.",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=0, column=0, pady=16)
            return
        for i, doc in enumerate(self._docs):
            _DocRow(self._docs_frame, doc,
                    on_open=lambda d=doc: self._open_doc(d),
                    on_delete=lambda d=doc: self._delete_doc(d),
                    ).grid(row=i, column=0, sticky="ew", pady=3)

    def _upload_document(self) -> None:
        src = filedialog.askopenfilename(
            title="اختر مستنداً",
            filetypes=[("All files","*.*"), ("PDF","*.pdf"),
                       ("Images","*.png *.jpg"), ("Word","*.docx")],
        )
        if not src:
            return
        fname = pathlib.Path(src).name
        dest  = self._ctx.doc_path("employees", self._emp_id, fname)
        shutil.copy2(src, dest)
        rel = self._ctx.relative_path(dest)
        with self._ctx.db() as svc:
            svc.attach_document({
                "employee_id":   self._emp_id,
                "document_type": self._doc_type_var.get(),
                "file_name":     fname,
                "file_path":     rel,
                "notes":         None,
            })
            self._docs = svc.list_documents(self._emp_id)
        self._render_docs()
        self._ctx.log(f"Document uploaded for employee {self._emp_id}: {fname}")

    def _open_doc(self, doc: dict) -> None:
        import os
        full = self._ctx.abs_path(doc["file_path"])
        try:
            os.startfile(str(full))
        except Exception:
            pass

    def _delete_doc(self, doc: dict) -> None:
        with self._ctx.db() as svc:
            svc.delete_document(doc["id"],
                                file_store=self._ctx.file_store)
            self._docs = svc.list_documents(self._emp_id)
        self._render_docs()
        self._ctx.log(f"Document deleted: {doc.get('file_name')}")


# ── Widgets ───────────────────────────────────────────────────

class _DocRow(ctk.CTkFrame):
    def __init__(self, parent, doc: dict,
                 on_open: Callable, on_delete: Callable) -> None:
        super().__init__(parent, fg_color=COLORS["surface"],
                         corner_radius=RADIUS["md"],
                         border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(1, weight=1)

        icon = DOC_TYPE_LABELS.get(doc.get("document_type",""), "📎")
        ctk.CTkLabel(self, text=icon, font=FONTS["body"],
                     text_color=COLORS["text"], width=160,
                     ).grid(row=0, column=0, padx=14, pady=10, sticky="w")
        ctk.CTkLabel(self, text=doc.get("file_name","—"),
                     font=FONTS["body"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=1, padx=8, pady=10, sticky="w")
        ctk.CTkLabel(self, text=doc.get("uploaded_at","")[:10],
                     font=FONTS["caption"], text_color=COLORS["text_dim"],
                     ).grid(row=0, column=2, padx=12)

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.grid(row=0, column=3, padx=12)
        ctk.CTkButton(btn_f, text="📂", width=32, height=32,
                      font=FONTS["body"], corner_radius=RADIUS["sm"],
                      fg_color=COLORS["accent_dim"], text_color=COLORS["accent"],
                      command=on_open).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_f, text="🗑", width=32, height=32,
                      font=FONTS["body"], corner_radius=RADIUS["sm"],
                      fg_color=COLORS["error_dim"], text_color=COLORS["error"],
                      command=on_delete).pack(side="left")


class _InfoCell(ctk.CTkFrame):
    def __init__(self, parent, label: str, value: str) -> None:
        super().__init__(parent, fg_color=COLORS["surface2"],
                         corner_radius=RADIUS["md"])
        ctk.CTkLabel(self, text=label, font=FONTS["caption"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(self, text=str(value), font=FONTS["body"],
                     text_color=COLORS["text"], anchor="w", wraplength=280,
                     ).pack(fill="x", padx=12, pady=(2, 8))


class _SectionLabel(ctk.CTkLabel):
    def __init__(self, parent, text: str) -> None:
        super().__init__(parent, text=text, font=FONTS["heading"],
                         text_color=COLORS["text"], anchor="w")