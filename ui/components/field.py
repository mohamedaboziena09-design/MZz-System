"""
ui/components/field.py
======================
Reusable labeled input field with inline error display.
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from ui.theme import COLORS, FONTS, RADIUS


class Field(ctk.CTkFrame):
    """
    Label + Entry + inline error message.

    Parameters
    ----------
    parent      : parent widget
    label       : field label text
    variable    : tk.StringVar to bind
    placeholder : grey hint text inside the entry
    show        : set to '•' for password fields
    """

    def __init__(
        self,
        parent,
        label: str,
        variable: tk.StringVar,
        placeholder: str = "",
        show: str = "",
        **kw,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kw)

        ctk.CTkLabel(
            self,
            text=label,
            font=FONTS["label"],
            text_color=COLORS["text_muted"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self._entry = ctk.CTkEntry(
            self,
            textvariable=variable,
            placeholder_text=placeholder,
            show=show,
            height=40,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["surface2"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_dim"],
            font=FONTS["body"],
        )
        self._entry.pack(fill="x")

        self._err = ctk.CTkLabel(
            self,
            text="",
            font=FONTS["caption"],
            text_color=COLORS["error"],
            anchor="w",
            height=16,
        )
        self._err.pack(fill="x", pady=(3, 0))

    def show_error(self, msg: str) -> None:
        self._err.configure(text=f"⚠  {msg}")
        self._entry.configure(border_color=COLORS["error"])

    def clear_error(self) -> None:
        self._err.configure(text="")
        self._entry.configure(border_color=COLORS["border"])

    def get(self) -> str:
        return self._entry.get()

    def focus(self) -> None:
        self._entry.focus_set()
