"""
ui/screens/vehicles/vehicles_screen.py
========================================
شاشة السيارات الكاملة:
- قائمة السيارات + بحث + فلترة
- إضافة / تعديل / حذف سيارة
- تعيين سيارة لموظف
- إرجاع السيارة
- تسجيل حركة (خروج / دخول / رحلة)
- تاريخ الحركات
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, date
from typing import Callable, Any, Optional

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError(
        "customtkinter غير مثبت. شغّل: pip install customtkinter"
    )

from ui.theme import COLORS, FONTS, RADIUS
from src.crud_service import CRUDService

# ── Constants ─────────────────────────────────────────────────
VEHICLE_TYPES  = ["sedan", "suv", "van", "truck", "minibus", "other"]
VEHICLE_STATUS = ["available", "assigned", "maintenance", "retired"]
MOVEMENT_TYPES = ["exit", "entry", "trip"]

STATUS_LABELS = {
    "available":   ("✅ متاحة",        COLORS["success"]),
    "assigned":    ("👔 معينة",        COLORS["accent"]),
    "maintenance": ("🔧 صيانة",        COLORS["warning"]),
    "retired":     ("❌ خارج الخدمة", COLORS["error"]),
}
MOVE_LABELS = {
    "exit":  "خروج من المقر",
    "entry": "دخول المقر",
    "trip":  "رحلة عمل",
}


class VehiclesScreen(ctk.CTkFrame):
    def __init__(self, parent, config: dict) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._config = config
        self._all: list[dict] = []
        self._build()
        self._load()

    # ── Build ─────────────────────────────────────────────────

    def _build(self) -> None:
        # Toolbar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        bar.grid_columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply())

        ctk.CTkEntry(
            bar, textvariable=self._search_var,
            placeholder_text="🔍  بحث باللوحة أو الماركة أو الموديل...",
            font=FONTS["body"], height=40,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            bar, text="+ إضافة سيارة",
            font=FONTS["btn_sm"], height=40, width=140,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"],
            command=self._open_add_form,
        ).grid(row=0, column=1)

        # Filter chips
        chips = ctk.CTkFrame(bar, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ctk.CTkLabel(chips, text="الحالة:", font=FONTS["body_sm"],
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 6))
        for label, val in [("الكل",""), ("✅ متاحة","available"),
                            ("👔 معينة","assigned"), ("🔧 صيانة","maintenance"),
                            ("❌ خارج الخدمة","retired")]:
            ctk.CTkButton(
                chips, text=label, font=FONTS["btn_sm"], height=28, width=90,
                corner_radius=RADIUS["sm"],
                fg_color=COLORS["surface2"], hover_color=COLORS["surface3"],
                text_color=COLORS["text_muted"],
                command=lambda v=val: self._set_filter(v),
            ).pack(side="left", padx=3)

        self._filter_status = ""
        self._count_lbl = ctk.CTkLabel(
            self, text="", font=FONTS["body_sm"],
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._count_lbl.grid(row=1, column=0, sticky="nw")

        # List
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", pady=(24, 0))
        self._scroll.grid_columnconfigure(0, weight=1)

    # ── Load & Filter ─────────────────────────────────────────

    def _load(self) -> None:
        try:
            with CRUDService() as svc:
                rows = svc.conn.execute(
                    "SELECT * FROM vehicles ORDER BY created_at DESC"
                ).fetchall()
                self._all = [dict(r) for r in rows]
        except Exception:
            self._all = []
        self._apply()

    def _set_filter(self, val: str) -> None:
        self._filter_status = val
        self._apply()

    def _apply(self) -> None:
        q  = self._search_var.get().strip().lower()
        st = self._filter_status
        filtered = [
            v for v in self._all
            if (not q or q in f"{v['plate_number']} {v['make']} {v['model']}".lower())
            and (not st or v["status"] == st)
        ]
        self._render(filtered)

    # ── Render ────────────────────────────────────────────────

    def _render(self, vehicles: list[dict]) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        self._count_lbl.configure(text=f"{len(vehicles)} سيارة")

        if not vehicles:
            ctk.CTkLabel(
                self._scroll, text="لا توجد سيارات مطابقة",
                font=FONTS["body"], text_color=COLORS["text_dim"],
            ).grid(row=0, column=0, pady=40)
            return

        _VehicleHeader(self._scroll).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        for i, v in enumerate(vehicles):
            _VehicleRow(
                self._scroll, v,
                on_edit=lambda veh=v: self._open_edit_form(veh),
                on_assign=lambda veh=v: self._open_assign(veh),
                on_return=lambda veh=v: self._open_return(veh),
                on_movement=lambda veh=v: self._open_movement(veh),
                on_history=lambda veh=v: self._open_history(veh),
                on_delete=lambda veh=v: self._confirm_delete(veh),
            ).grid(row=i + 1, column=0, sticky="ew", pady=2)

    # ════════════════════════════════════════════════════════
    # Forms
    # ════════════════════════════════════════════════════════

    def _open_add_form(self) -> None:
        VehicleFormDialog(self, on_save=self._load)

    def _open_edit_form(self, v: dict) -> None:
        VehicleFormDialog(self, vehicle=v, on_save=self._load)

    def _open_assign(self, v: dict) -> None:
        AssignDialog(self, vehicle=v, on_save=self._load)

    def _open_return(self, v: dict) -> None:
        ReturnDialog(self, vehicle=v, on_save=self._load)

    def _open_movement(self, v: dict) -> None:
        MovementDialog(self, vehicle=v, on_save=self._load)

    def _open_history(self, v: dict) -> None:
        HistoryDialog(self, vehicle=v)

    def _confirm_delete(self, v: dict) -> None:
        dlg = _ConfirmDialog(self, f"حذف السيارة: {v['plate_number']}؟")
        self.wait_window(dlg)
        if dlg.confirmed:
            try:
                with CRUDService() as svc:
                    svc.conn.execute("DELETE FROM vehicles WHERE id=?", (v["id"],))
                    svc.conn.commit()
                self._load()
            except Exception as e:
                _MsgDialog(self, f"❌ خطأ: {e}")


# ── Vehicle Header ────────────────────────────────────────────

class _VehicleHeader(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["surface2"],
                         corner_radius=RADIUS["md"])
        cols = ["اللوحة", "الماركة / الموديل", "السنة", "النوع",
                "التأمين", "الرخصة", "الحالة", "إجراءات"]
        for i, c in enumerate(cols):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(self, text=c, font=FONTS["label"],
                         text_color=COLORS["text_muted"], anchor="w",
                         ).grid(row=0, column=i, padx=12, pady=8, sticky="w")


# ── Vehicle Row ───────────────────────────────────────────────

class _VehicleRow(ctk.CTkFrame):
    def __init__(self, parent, v: dict,
                 on_edit, on_assign, on_return,
                 on_movement, on_history, on_delete) -> None:
        super().__init__(parent, fg_color=COLORS["surface"],
                         corner_radius=RADIUS["md"],
                         border_width=1, border_color=COLORS["border"])

        cols = 8
        for i in range(cols):
            self.grid_columnconfigure(i, weight=1)

        st_label, st_color = STATUS_LABELS.get(
            v.get("status",""), ("—", COLORS["text_muted"])
        )

        # Plate
        ctk.CTkLabel(self, text=v.get("plate_number","—"),
                     font=FONTS["btn"], text_color=COLORS["accent"], anchor="w",
                     ).grid(row=0, column=0, padx=12, pady=10, sticky="w")
        # Make/Model
        ctk.CTkLabel(self, text=f"{v.get('make','')} {v.get('model','')}",
                     font=FONTS["body"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=1, padx=12, pady=10, sticky="w")
        # Year
        ctk.CTkLabel(self, text=str(v.get("year","—")),
                     font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=2, padx=12, pady=10, sticky="w")
        # Type
        ctk.CTkLabel(self, text=v.get("vehicle_type","—"),
                     font=FONTS["body_sm"], text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=0, column=3, padx=12, pady=10, sticky="w")
        # Insurance expiry
        ctk.CTkLabel(self, text=_expiry(v.get("insurance_expiry")),
                     font=FONTS["body_sm"], text_color=_expiry_color(v.get("insurance_expiry")),
                     anchor="w",
                     ).grid(row=0, column=4, padx=12, pady=10, sticky="w")
        # License expiry
        ctk.CTkLabel(self, text=_expiry(v.get("license_expiry")),
                     font=FONTS["body_sm"], text_color=_expiry_color(v.get("license_expiry")),
                     anchor="w",
                     ).grid(row=0, column=5, padx=12, pady=10, sticky="w")
        # Status
        ctk.CTkLabel(self, text=st_label,
                     font=FONTS["body_sm"], text_color=st_color, anchor="w",
                     ).grid(row=0, column=6, padx=12, pady=10, sticky="w")

        # Actions
        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.grid(row=0, column=7, padx=8, pady=8, sticky="e")

        for txt, cmd, color in [
            ("✏️",  on_edit,     COLORS["accent_dim"]),
            ("👔",  on_assign,   COLORS["surface3"]),
            ("↩️",  on_return,   COLORS["surface3"]),
            ("🚦",  on_movement, COLORS["success_dim"]),
            ("📋",  on_history,  COLORS["surface3"]),
            ("🗑",  on_delete,   COLORS["error_dim"]),
        ]:
            ctk.CTkButton(
                acts, text=txt, width=32, height=32,
                font=FONTS["body"], corner_radius=RADIUS["sm"],
                fg_color=color, hover_color=COLORS["surface3"],
                text_color=COLORS["text"], command=cmd,
            ).pack(side="left", padx=2)

        self.bind("<Enter>", lambda _: self.configure(border_color=COLORS["accent"]))
        self.bind("<Leave>", lambda _: self.configure(border_color=COLORS["border"]))


# ════════════════════════════════════════════════════════════
# Vehicle Form Dialog — إضافة / تعديل
# ════════════════════════════════════════════════════════════

class VehicleFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save: Callable,
                 vehicle: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._on_save = on_save
        self._v       = vehicle
        self._is_edit = vehicle is not None
        title = "تعديل سيارة" if self._is_edit else "إضافة سيارة جديدة"
        self.title(title)
        self.geometry("620x560")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self._build()
        if self._is_edit:
            self._populate()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)
        scroll.grid_columnconfigure((0,1), weight=1)

        ctk.CTkLabel(scroll, text=self.title(),
                     font=FONTS["title"], text_color=COLORS["text"],
                     anchor="w").grid(row=0, column=0, columnspan=2,
                                      sticky="w", pady=(0, 20))

        # Fields
        self._plate    = _field(scroll, "رقم اللوحة *",    1, 0)
        self._make     = _field(scroll, "الماركة *",        1, 1)
        self._model    = _field(scroll, "الموديل *",        2, 0)
        self._year     = _field(scroll, "سنة الصنع *",      2, 1)
        self._color    = _field(scroll, "اللون",            3, 0)
        self._chassis  = _field(scroll, "رقم الشاسيه",     3, 1)
        self._engine   = _field(scroll, "رقم الموتور",     4, 0)
        self._ins_exp  = _field(scroll, "انتهاء التأمين (YYYY-MM-DD)", 4, 1)
        self._lic_exp  = _field(scroll, "انتهاء الرخصة (YYYY-MM-DD)", 5, 0)

        # Type
        self._type_var = tk.StringVar(value=VEHICLE_TYPES[0])
        _dropdown(scroll, "نوع السيارة", self._type_var, VEHICLE_TYPES, 5, 1)

        # Status (edit only)
        self._status_var = tk.StringVar(value="available")
        _dropdown(scroll, "الحالة", self._status_var, VEHICLE_STATUS, 6, 0)

        # Notes
        ctk.CTkLabel(scroll, text="ملاحظات", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(12,4))
        self._notes = ctk.CTkTextbox(
            scroll, height=70,
            fg_color=COLORS["surface2"], border_color=COLORS["border"],
            border_width=1, corner_radius=RADIUS["md"],
            text_color=COLORS["text"], font=FONTS["body"],
        )
        self._notes.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0,16))

        # Error
        self._err = ctk.CTkLabel(scroll, text="", font=FONTS["body_sm"],
                                  text_color=COLORS["error"], anchor="w")
        self._err.grid(row=9, column=0, columnspan=2, sticky="w")

        # Buttons
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.grid(row=10, column=0, columnspan=2, sticky="e", pady=(8,0))
        ctk.CTkButton(btn_row, text="إلغاء", width=100, height=38,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      corner_radius=RADIUS["md"], command=self.destroy,
                      ).pack(side="left", padx=(0,10))
        lbl = "حفظ التعديلات" if self._is_edit else "إضافة السيارة"
        self._save_btn = ctk.CTkButton(
            btn_row, text=lbl, width=140, height=38,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_inverse"], corner_radius=RADIUS["md"],
            command=self._submit,
        )
        self._save_btn.pack(side="left")

    def _populate(self) -> None:
        v = self._v
        self._plate.set(v.get("plate_number",""))
        self._make.set(v.get("make",""))
        self._model.set(v.get("model",""))
        self._year.set(str(v.get("year","")))
        self._color.set(v.get("color") or "")
        self._chassis.set(v.get("chassis_number") or "")
        self._engine.set(v.get("engine_number") or "")
        self._ins_exp.set(v.get("insurance_expiry") or "")
        self._lic_exp.set(v.get("license_expiry") or "")
        self._type_var.set(v.get("vehicle_type","sedan"))
        self._status_var.set(v.get("status","available"))
        if v.get("notes"):
            self._notes.insert("1.0", v["notes"])

    def _submit(self) -> None:
        self._err.configure(text="")
        plate = self._plate.get().strip()
        make  = self._make.get().strip()
        model = self._model.get().strip()
        year  = self._year.get().strip()

        if not plate: self._err.configure(text="رقم اللوحة مطلوب"); return
        if not make:  self._err.configure(text="الماركة مطلوبة");   return
        if not model: self._err.configure(text="الموديل مطلوب");    return
        if not year.isdigit():
            self._err.configure(text="سنة الصنع يجب أن تكون رقماً"); return

        data = dict(
            plate_number=plate, make=make, model=model, year=int(year),
            color=self._color.get().strip() or None,
            vehicle_type=self._type_var.get(),
            status=self._status_var.get(),
            chassis_number=self._chassis.get().strip() or None,
            engine_number=self._engine.get().strip() or None,
            insurance_expiry=self._ins_exp.get().strip() or None,
            license_expiry=self._lic_exp.get().strip() or None,
            notes=self._notes.get("1.0","end").strip() or None,
        )
        try:
            with CRUDService() as svc:
                if self._is_edit:
                    sets = ", ".join(f"{k}=?" for k in data)
                    svc.conn.execute(
                        f"UPDATE vehicles SET {sets}, updated_at=datetime('now') WHERE id=?",
                        list(data.values()) + [self._v["id"]]
                    )
                else:
                    keys = ", ".join(data.keys())
                    qs   = ", ".join("?" * len(data))
                    svc.conn.execute(
                        f"INSERT INTO vehicles ({keys}) VALUES ({qs})",
                        list(data.values())
                    )
                svc.conn.commit()
            self._save_btn.configure(text="✓ تم", fg_color=COLORS["success"], state="disabled")
            self.after(600, lambda: (self.destroy(), self._on_save()))
        except Exception as e:
            self._err.configure(text=f"❌ {e}")


# ════════════════════════════════════════════════════════════
# Assign Dialog — تعيين سيارة لموظف
# ════════════════════════════════════════════════════════════

class AssignDialog(ctk.CTkToplevel):
    def __init__(self, parent, vehicle: dict, on_save: Callable) -> None:
        super().__init__(parent)
        self._v       = vehicle
        self._on_save = on_save
        self.title(f"تعيين سيارة: {vehicle['plate_number']}")
        self.geometry("480x340")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self._employees: list[dict] = []
        self._load_employees()
        self._build()

    def _load_employees(self) -> None:
        try:
            with CRUDService() as svc:
                self._employees = svc.search_employees(
                    employment_status="active", limit=200
                )
        except Exception:
            self._employees = []

    def _build(self) -> None:
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=24, pady=20)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text=f"تعيين: {self._v['plate_number']} — {self._v['make']} {self._v['model']}",
                     font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=0, sticky="w", pady=(0,16))

        # Employee picker
        emp_names = [f"{e['first_name']} {e['last_name']} ({e['employee_code']})"
                     for e in self._employees]
        self._emp_var = tk.StringVar(value=emp_names[0] if emp_names else "لا يوجد موظفين")
        ctk.CTkLabel(f, text="الموظف *", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=1, column=0, sticky="w", pady=(0,4))
        ctk.CTkOptionMenu(
            f, variable=self._emp_var, values=emp_names or ["—"],
            font=FONTS["body"], height=40, corner_radius=RADIUS["md"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"], text_color=COLORS["text"],
        ).grid(row=2, column=0, sticky="ew", pady=(0,12))

        self._date_var = tk.StringVar(value=date.today().isoformat())
        ctk.CTkLabel(f, text="تاريخ التعيين *", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=3, column=0, sticky="w", pady=(0,4))
        ctk.CTkEntry(f, textvariable=self._date_var, font=FONTS["body"],
                     height=40, fg_color=COLORS["surface2"],
                     border_color=COLORS["border"], border_width=1,
                     corner_radius=RADIUS["md"], text_color=COLORS["text"],
                     ).grid(row=4, column=0, sticky="ew", pady=(0,12))

        self._reason_var = tk.StringVar()
        ctk.CTkLabel(f, text="سبب التعيين", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=5, column=0, sticky="w", pady=(0,4))
        ctk.CTkEntry(f, textvariable=self._reason_var, font=FONTS["body"],
                     height=40, fg_color=COLORS["surface2"],
                     border_color=COLORS["border"], border_width=1,
                     corner_radius=RADIUS["md"], text_color=COLORS["text"],
                     placeholder_text="مثال: مهمة رسمية",
                     ).grid(row=6, column=0, sticky="ew", pady=(0,16))

        self._err = ctk.CTkLabel(f, text="", font=FONTS["body_sm"],
                                  text_color=COLORS["error"], anchor="w")
        self._err.grid(row=7, column=0, sticky="w")

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.grid(row=8, column=0, sticky="e")
        ctk.CTkButton(btn_row, text="إلغاء", width=90, height=36,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="تعيين", width=110, height=36,
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                      text_color=COLORS["text_inverse"],
                      command=self._submit).pack(side="left")

    def _submit(self) -> None:
        if not self._employees:
            self._err.configure(text="لا يوجد موظفين نشطين"); return
        idx = [f"{e['first_name']} {e['last_name']} ({e['employee_code']})"
               for e in self._employees].index(self._emp_var.get())
        emp_id = self._employees[idx]["id"]
        try:
            with CRUDService() as svc:
                # Check not already assigned
                active = svc.conn.execute(
                    "SELECT id FROM vehicle_assignments WHERE vehicle_id=? AND returned_date IS NULL",
                    (self._v["id"],)
                ).fetchone()
                if active:
                    self._err.configure(text="السيارة معينة بالفعل. أرجعها أولاً."); return
                svc.conn.execute(
                    "INSERT INTO vehicle_assignments (vehicle_id,employee_id,assigned_date,reason) VALUES (?,?,?,?)",
                    (self._v["id"], emp_id, self._date_var.get(), self._reason_var.get() or None)
                )
                svc.conn.execute(
                    "UPDATE vehicles SET status='assigned', updated_at=datetime('now') WHERE id=?",
                    (self._v["id"],)
                )
                svc.conn.commit()
            self.destroy()
            self._on_save()
        except Exception as e:
            self._err.configure(text=f"❌ {e}")


# ════════════════════════════════════════════════════════════
# Return Dialog — إرجاع السيارة
# ════════════════════════════════════════════════════════════

class ReturnDialog(ctk.CTkToplevel):
    def __init__(self, parent, vehicle: dict, on_save: Callable) -> None:
        super().__init__(parent)
        self._v       = vehicle
        self._on_save = on_save
        self.title(f"إرجاع سيارة: {vehicle['plate_number']}")
        self.geometry("420x260")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self._build()

    def _build(self) -> None:
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=24, pady=20)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text=f"إرجاع: {self._v['plate_number']} — {self._v['make']} {self._v['model']}",
                     font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=0, sticky="w", pady=(0,16))

        self._date_var = tk.StringVar(value=date.today().isoformat())
        ctk.CTkLabel(f, text="تاريخ الإرجاع *", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).grid(row=1, column=0, sticky="w", pady=(0,4))
        ctk.CTkEntry(f, textvariable=self._date_var, font=FONTS["body"],
                     height=40, fg_color=COLORS["surface2"],
                     border_color=COLORS["border"], border_width=1,
                     corner_radius=RADIUS["md"], text_color=COLORS["text"],
                     ).grid(row=2, column=0, sticky="ew", pady=(0,16))

        self._err = ctk.CTkLabel(f, text="", font=FONTS["body_sm"],
                                  text_color=COLORS["error"], anchor="w")
        self._err.grid(row=3, column=0, sticky="w")

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="e", pady=(8,0))
        ctk.CTkButton(btn_row, text="إلغاء", width=90, height=36,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="تأكيد الإرجاع", width=130, height=36,
                      fg_color=COLORS["success"], text_color=COLORS["text_inverse"],
                      command=self._submit).pack(side="left")

    def _submit(self) -> None:
        ret_date = self._date_var.get().strip()
        try:
            with CRUDService() as svc:
                assign = svc.conn.execute(
                    "SELECT id FROM vehicle_assignments WHERE vehicle_id=? AND returned_date IS NULL",
                    (self._v["id"],)
                ).fetchone()
                if not assign:
                    self._err.configure(text="لا يوجد تعيين نشط لهذه السيارة"); return
                svc.conn.execute(
                    "UPDATE vehicle_assignments SET returned_date=? WHERE id=?",
                    (ret_date, assign["id"])
                )
                svc.conn.execute(
                    "UPDATE vehicles SET status='available', updated_at=datetime('now') WHERE id=?",
                    (self._v["id"],)
                )
                svc.conn.commit()
            self.destroy()
            self._on_save()
        except Exception as e:
            self._err.configure(text=f"❌ {e}")


# ════════════════════════════════════════════════════════════
# Movement Dialog — تسجيل حركة
# ════════════════════════════════════════════════════════════

class MovementDialog(ctk.CTkToplevel):
    def __init__(self, parent, vehicle: dict, on_save: Callable) -> None:
        super().__init__(parent)
        self._v       = vehicle
        self._on_save = on_save
        self.title(f"تسجيل حركة: {vehicle['plate_number']}")
        self.geometry("580x520")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self._employees: list[dict] = []
        self._load_employees()
        self._build()

    def _load_employees(self) -> None:
        try:
            with CRUDService() as svc:
                self._employees = svc.search_employees(
                    employment_status="active", limit=200
                )
        except Exception:
            self._employees = []

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)
        scroll.grid_columnconfigure((0,1), weight=1)

        ctk.CTkLabel(scroll,
                     text=f"تسجيل حركة: {self._v['plate_number']} — {self._v['make']} {self._v['model']}",
                     font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
                     ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,16))

        # Movement type
        self._move_type = tk.StringVar(value=MOVEMENT_TYPES[0])
        _dropdown(scroll, "نوع الحركة *", self._move_type,
                  [MOVE_LABELS[t] for t in MOVEMENT_TYPES], 1, 0)

        # Driver type toggle
        self._driver_type = tk.StringVar(value="employee")
        dr_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dr_frame.grid(row=1, column=1, sticky="ew", padx=(12,0))
        ctk.CTkLabel(dr_frame, text="نوع السائق", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(anchor="w", pady=(0,4))
        for label, val in [("موظف","employee"), ("خارجي","external")]:
            ctk.CTkRadioButton(
                dr_frame, text=label, variable=self._driver_type, value=val,
                font=FONTS["body"], text_color=COLORS["text"],
                fg_color=COLORS["accent"], border_color=COLORS["border"],
                command=self._toggle_driver,
            ).pack(side="left", padx=(0,12))

        # Employee driver
        emp_names = [f"{e['first_name']} {e['last_name']} ({e['employee_code']})"
                     for e in self._employees]
        self._emp_var = tk.StringVar(value=emp_names[0] if emp_names else "—")
        self._emp_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._emp_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8,0))
        ctk.CTkLabel(self._emp_frame, text="الموظف السائق *", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(anchor="w", pady=(0,4))
        self._emp_menu = ctk.CTkOptionMenu(
            self._emp_frame, variable=self._emp_var,
            values=emp_names or ["—"],
            font=FONTS["body"], height=38, corner_radius=RADIUS["md"],
            fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
            button_hover_color=COLORS["accent"], text_color=COLORS["text"],
        )
        self._emp_menu.pack(fill="x")

        # External driver name
        self._ext_name_var = tk.StringVar()
        self._ext_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._ext_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8,0))
        ctk.CTkLabel(self._ext_frame, text="اسم السائق الخارجي *", font=FONTS["label"],
                     text_color=COLORS["text_muted"], anchor="w",
                     ).pack(anchor="w", pady=(0,4))
        ctk.CTkEntry(self._ext_frame, textvariable=self._ext_name_var,
                     font=FONTS["body"], height=38, placeholder_text="الاسم الكامل",
                     fg_color=COLORS["surface2"], border_color=COLORS["border"],
                     border_width=1, corner_radius=RADIUS["md"],
                     text_color=COLORS["text"],
                     ).pack(fill="x")
        self._ext_frame.grid_remove()

        # Times
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._dep_time = _field(scroll, "وقت المغادرة *", 4, 0, placeholder=now_str)
        self._ret_time = _field(scroll, "وقت العودة",    4, 1, placeholder="اتركه فارغاً إن لم يعد")

        # Locations
        self._dep_loc  = _field(scroll, "من (موقع المغادرة)", 5, 0, placeholder="مثال: المقر الرئيسي")
        self._dest     = _field(scroll, "إلى (الوجهة)",       5, 1, placeholder="مثال: فرع الرياض")
        self._purpose  = _field(scroll, "الغرض",              6, 0, placeholder="مثال: توصيل مواد")

        # Odometer
        self._odo_out  = _field(scroll, "عداد الخروج (كم)", 6, 1, placeholder="مثال: 45000")
        self._odo_in   = _field(scroll, "عداد الدخول (كم)", 7, 0, placeholder="مثال: 45150")

        self._err = ctk.CTkLabel(scroll, text="", font=FONTS["body_sm"],
                                  text_color=COLORS["error"], anchor="w")
        self._err.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8,0))

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.grid(row=9, column=0, columnspan=2, sticky="e", pady=(12,0))
        ctk.CTkButton(btn_row, text="إلغاء", width=90, height=36,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="تسجيل الحركة", width=140, height=36,
                      fg_color=COLORS["success"], text_color=COLORS["text_inverse"],
                      corner_radius=RADIUS["md"], command=self._submit,
                      ).pack(side="left")

    def _toggle_driver(self) -> None:
        if self._driver_type.get() == "employee":
            self._emp_frame.grid()
            self._ext_frame.grid_remove()
        else:
            self._emp_frame.grid_remove()
            self._ext_frame.grid()

    def _submit(self) -> None:
        self._err.configure(text="")
        dep_time = self._dep_time.get().strip()
        if not dep_time:
            self._err.configure(text="وقت المغادرة مطلوب"); return

        move_label = self._move_type.get()
        move_type  = MOVEMENT_TYPES[[MOVE_LABELS[t] for t in MOVEMENT_TYPES].index(move_label)]

        driver_emp_id  = None
        driver_ext_id  = None

        try:
            with CRUDService() as svc:
                if self._driver_type.get() == "employee":
                    if not self._employees:
                        self._err.configure(text="لا يوجد موظفين"); return
                    emp_names = [f"{e['first_name']} {e['last_name']} ({e['employee_code']})"
                                 for e in self._employees]
                    idx = emp_names.index(self._emp_var.get())
                    driver_emp_id = self._employees[idx]["id"]
                else:
                    ext_name = self._ext_name_var.get().strip()
                    if not ext_name:
                        self._err.configure(text="اسم السائق الخارجي مطلوب"); return
                    cur = svc.conn.execute(
                        "INSERT INTO drivers (full_name, status) VALUES (?, 'active')",
                        (ext_name,)
                    )
                    driver_ext_id = cur.lastrowid

                odo_out = self._odo_out.get().strip()
                odo_in  = self._odo_in.get().strip()

                svc.conn.execute("""
                    INSERT INTO vehicle_movements
                        (vehicle_id, driver_employee_id, driver_external_id,
                         movement_type, departure_time, return_time,
                         departure_location, destination, purpose,
                         odometer_out, odometer_in)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    self._v["id"], driver_emp_id, driver_ext_id,
                    move_type, dep_time,
                    self._ret_time.get().strip() or None,
                    self._dep_loc.get().strip() or None,
                    self._dest.get().strip() or None,
                    self._purpose.get().strip() or None,
                    int(odo_out) if odo_out.isdigit() else None,
                    int(odo_in)  if odo_in.isdigit()  else None,
                ))
                svc.conn.commit()
            self.destroy()
            self._on_save()
        except Exception as e:
            self._err.configure(text=f"❌ {e}")


# ════════════════════════════════════════════════════════════
# History Dialog — تاريخ الحركات
# ════════════════════════════════════════════════════════════

class HistoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, vehicle: dict) -> None:
        super().__init__(parent)
        self._v = vehicle
        self.title(f"تاريخ حركات: {vehicle['plate_number']}")
        self.geometry("820x500")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self,
            text=f"🚗  {self._v['plate_number']} — {self._v['make']} {self._v['model']}",
            font=FONTS["heading"], text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w", padx=20, pady=(16, 10))

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)

        try:
            with CRUDService() as svc:
                rows = svc.conn.execute("""
                    SELECT vm.*,
                           e.first_name || ' ' || e.last_name AS emp_name,
                           d.full_name AS ext_name
                    FROM vehicle_movements vm
                    LEFT JOIN employees e ON e.id = vm.driver_employee_id
                    LEFT JOIN drivers   d ON d.id = vm.driver_external_id
                    WHERE vm.vehicle_id = ?
                    ORDER BY vm.departure_time DESC
                    LIMIT 100
                """, (self._v["id"],)).fetchall()
                movements = [dict(r) for r in rows]
        except Exception:
            movements = []

        if not movements:
            ctk.CTkLabel(scroll, text="لا توجد حركات مسجلة",
                         font=FONTS["body"], text_color=COLORS["text_dim"],
                         ).grid(row=0, column=0, pady=30)
            return

        cols = ["#", "النوع", "السائق", "المغادرة", "العودة", "من", "إلى", "الغرض", "كم"]
        _TableHeader(scroll, cols).grid(row=0, column=0, sticky="ew", pady=(0,2))

        for i, m in enumerate(movements):
            driver = m.get("emp_name") or m.get("ext_name") or "—"
            km = ""
            if m.get("odometer_out") and m.get("odometer_in"):
                km = str(m["odometer_in"] - m["odometer_out"])
            values = [
                str(i+1),
                MOVE_LABELS.get(m.get("movement_type",""), "—"),
                driver,
                (m.get("departure_time") or "—")[:16],
                (m.get("return_time") or "—")[:16],
                m.get("departure_location") or "—",
                m.get("destination") or "—",
                m.get("purpose") or "—",
                km or "—",
            ]
            _TableRow(scroll, values, i).grid(row=i+1, column=0, sticky="ew", pady=1)


# ── Shared helpers ────────────────────────────────────────────

def _field(parent, label: str, row: int, col: int,
           placeholder: str = "") -> tk.StringVar:
    var = tk.StringVar()
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=col, sticky="ew",
               padx=(0,12) if col==0 else 0, pady=(0,12))
    ctk.CTkLabel(frame, text=label, font=FONTS["label"],
                 text_color=COLORS["text_muted"], anchor="w",
                 ).pack(anchor="w", pady=(0,4))
    ctk.CTkEntry(frame, textvariable=var, font=FONTS["body"],
                 height=38, placeholder_text=placeholder,
                 fg_color=COLORS["surface2"], border_color=COLORS["border"],
                 border_width=1, corner_radius=RADIUS["md"],
                 text_color=COLORS["text"],
                 ).pack(fill="x")
    return var


def _dropdown(parent, label: str, var: tk.StringVar,
              values: list, row: int, col: int) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=col, sticky="ew",
               padx=(0,12) if col==0 else 0, pady=(0,12))
    ctk.CTkLabel(frame, text=label, font=FONTS["label"],
                 text_color=COLORS["text_muted"], anchor="w",
                 ).pack(anchor="w", pady=(0,4))
    ctk.CTkOptionMenu(
        frame, variable=var, values=values,
        font=FONTS["body"], height=38, corner_radius=RADIUS["md"],
        fg_color=COLORS["surface2"], button_color=COLORS["surface3"],
        button_hover_color=COLORS["accent"], text_color=COLORS["text"],
    ).pack(fill="x")


def _expiry(val: Optional[str]) -> str:
    return val or "—"


def _expiry_color(val: Optional[str]) -> str:
    if not val:
        return COLORS["text_dim"]
    try:
        d    = datetime.strptime(val, "%Y-%m-%d").date()
        diff = (d - date.today()).days
        if diff < 0:   return COLORS["error"]
        if diff < 30:  return COLORS["warning"]
        return COLORS["success"]
    except Exception:
        return COLORS["text_muted"]


class _TableHeader(ctk.CTkFrame):
    def __init__(self, parent, cols):
        super().__init__(parent, fg_color=COLORS["surface2"], corner_radius=RADIUS["md"])
        for i, c in enumerate(cols):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(self, text=c, font=FONTS["label"],
                         text_color=COLORS["text_muted"], anchor="w",
                         ).grid(row=0, column=i, padx=10, pady=7, sticky="w")


class _TableRow(ctk.CTkFrame):
    def __init__(self, parent, values, idx):
        bg = COLORS["surface"] if idx%2==0 else COLORS["surface2"]
        super().__init__(parent, fg_color=bg, corner_radius=RADIUS["sm"])
        for i, v in enumerate(values):
            self.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(self, text=str(v), font=FONTS["body_sm"],
                         text_color=COLORS["text"], anchor="w",
                         ).grid(row=0, column=i, padx=10, pady=6, sticky="w")


class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.confirmed = False
        self.title("تأكيد")
        self.geometry("340x150")
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()
        ctk.CTkLabel(self, text=message, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=280,
                     ).pack(pady=(22,14))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        ctk.CTkButton(row, text="إلغاء", width=90, height=34,
                      fg_color=COLORS["surface3"], text_color=COLORS["text_muted"],
                      command=self.destroy).pack(side="left", padx=6)
        ctk.CTkButton(row, text="حذف", width=90, height=34,
                      fg_color=COLORS["error"], text_color=COLORS["text_inverse"],
                      command=self._ok).pack(side="left", padx=6)

    def _ok(self):
        self.confirmed = True
        self.destroy()


class _MsgDialog(ctk.CTkToplevel):
    def __init__(self, parent, msg):
        super().__init__(parent)
        self.title("تنبيه")
        self.geometry("360x140")
        self.configure(fg_color=COLORS["surface"])
        self.grab_set()
        ctk.CTkLabel(self, text=msg, font=FONTS["body"],
                     text_color=COLORS["text"], wraplength=320,
                     ).pack(pady=24)
        ctk.CTkButton(self, text="حسناً", width=100, height=34,
                      fg_color=COLORS["accent"], text_color=COLORS["text_inverse"],
                      command=self.destroy).pack()
