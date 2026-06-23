"""
ui/components/divider.py
========================
Thin horizontal divider line.
"""

import customtkinter as ctk
from ui.theme import COLORS


class Divider(ctk.CTkFrame):
    def __init__(self, parent, color: str = COLORS["border"], **kw):
        super().__init__(parent, height=1, fg_color=color, **kw)
