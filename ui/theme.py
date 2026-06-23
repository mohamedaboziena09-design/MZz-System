"""
ui/theme.py
===========
Single source of truth for every visual token in MZz System V1.
Import this module anywhere in the UI layer — never hard-code colors or fonts.
"""

# ── Palette ──────────────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg":           "#0F1117",   # window background
    "surface":      "#1A1D27",   # card / panel
    "surface2":     "#222535",   # input background
    "surface3":     "#2A2E42",   # hover state / subtle highlight

    # Borders
    "border":       "#2E3248",
    "border_focus": "#4F6EF7",

    # Accent (primary action)
    "accent":       "#4F6EF7",
    "accent_hover": "#3B57E0",
    "accent_dim":   "#1E2D6B",   # subtle accent background

    # Semantic
    "success":      "#2ECC71",
    "success_dim":  "#1A5C38",
    "warning":      "#F39C12",
    "error":        "#E74C3C",
    "error_dim":    "#5C1A1A",

    # Sidebar
    "sidebar_bg":   "#13151F",
    "sidebar_item": "#1E2130",
    "sidebar_active":"#4F6EF7",

    # Text
    "text":         "#E8EAF2",
    "text_muted":   "#7880A0",
    "text_dim":     "#4A5070",
    "text_inverse": "#FFFFFF",
}

# ── Typography ───────────────────────────────────────────────
FONT = "Segoe UI"

FONTS = {
    "logo":      (FONT, 48, "bold"),
    "title":     (FONT, 22, "bold"),
    "subtitle":  (FONT, 16),
    "heading":   (FONT, 15, "bold"),
    "label":     (FONT, 12, "bold"),
    "body":      (FONT, 13),
    "body_sm":   (FONT, 12),
    "caption":   (FONT, 11),
    "btn":       (FONT, 14, "bold"),
    "btn_sm":    (FONT, 12, "bold"),
    "code":      ("Consolas", 12),
}

# ── Sizing ───────────────────────────────────────────────────
RADIUS = {
    "sm":  6,
    "md":  8,
    "lg":  12,
    "xl":  16,
}

SIDEBAR_WIDTH  = 200
TOPBAR_HEIGHT  = 56
WINDOW_MIN_W   = 1024
WINDOW_MIN_H   = 640
