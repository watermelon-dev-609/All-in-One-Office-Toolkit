"""Theme/Skin management system — "Obsidian Teal" design language.

A refined dark theme with jade-green accents, inspired by polished stone
and modern Chinese office aesthetics. Clean, calm, and focused.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from loguru import logger

from src.constants import STYLES_DIR

# ── Accent Colors ──────────────────────────────────────────────
ACCENT_COLORS = {
    "teal":    "#00c9a7",   # 翡翠绿 — primary
    "blue":    "#5b9bd5",
    "purple":  "#a78bfa",
    "amber":   "#f59e0b",
    "rose":    "#f472b6",
    "cyan":    "#22d3ee",
    "lime":    "#a3e635",
    "coral":   "#fb7185",
}

FONT_SIZES = {"small": 0.88, "normal": 1.0, "large": 1.12}

# ── Dark Theme Palette ("Obsidian") ────────────────────────────
DARK_PALETTE = {
    "bg_primary":    "#0d0d16",
    "bg_secondary":  "#11111c",
    "bg_tertiary":   "#191928",
    "bg_elevated":   "#1e1e32",
    "bg_hover":      "#22223a",
    "bg_active":     "#2a2a48",
    "bg_overlay":    "#0a0a1488",

    "text_primary":   "#e8e8f0",
    "text_secondary": "#8e8ea8",
    "text_tertiary":  "#585878",

    "border_default": "#22223a",
    "border_focus":   "#00c9a7",
    "border_subtle":  "#1a1a2e",

    "accent":         "#00c9a7",
    "accent_light":   "#33dfbf",
    "accent_dark":    "#00a082",
    "accent_bg":      "#00c9a715",

    "success":  "#22c55e",
    "warning":  "#f59e0b",
    "danger":   "#ef4444",
    "info":     "#5b9bd5",

    "scrollbar_handle":       "#2e2e50",
    "scrollbar_handle_hover": "#404068",
}

# ── Light Theme Palette ("Ivory") ──────────────────────────────
LIGHT_PALETTE = {
    "bg_primary":    "#fafafc",
    "bg_secondary":  "#ffffff",
    "bg_tertiary":   "#f0f0f5",
    "bg_elevated":   "#ffffff",
    "bg_hover":      "#eaeaef",
    "bg_active":     "#e0e0ea",
    "bg_overlay":    "#00000010",

    "text_primary":   "#1a1a2e",
    "text_secondary": "#6b6b80",
    "text_tertiary":  "#a0a0b8",

    "border_default": "#e0e0ea",
    "border_focus":   "#00a082",
    "border_subtle":  "#eeeeff",

    "accent":         "#00a082",
    "accent_light":   "#00c9a7",
    "accent_dark":    "#007a60",
    "accent_bg":      "#00a08210",

    "success":  "#16a34a",
    "warning":  "#d97706",
    "danger":   "#dc2626",
    "info":     "#3b82f6",

    "scrollbar_handle":       "#d0d0dc",
    "scrollbar_handle_hover": "#b0b0c0",
}

THEME_PALETTES = {"dark": DARK_PALETTE, "light": LIGHT_PALETTE}


class ThemeConfig:
    def __init__(self, theme="dark", accent="teal", font_size="normal"):
        self.theme = theme
        self.accent = accent
        self.accent_hex = ACCENT_COLORS.get(accent, ACCENT_COLORS["teal"])
        self.font_size = font_size
        self.font_multiplier = FONT_SIZES.get(font_size, 1.0)
        self.palette = THEME_PALETTES.get(theme, DARK_PALETTE)


class ThemeManager(QObject):
    theme_changed = Signal(str)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = ThemeConfig()
        return cls._instance

    @property
    def current_config(self) -> ThemeConfig:
        return self._config

    def set_theme(self, theme="dark", accent="teal", font_size="normal"):
        config = ThemeConfig(theme=theme, accent=accent, font_size=font_size)
        self._config = config
        qss = self._compile(config)
        QApplication.instance().setStyleSheet(qss)
        logger.info(f"Theme: {theme} | accent={accent} | font={font_size}")
        self.theme_changed.emit(theme)

    def refresh(self):
        self.set_theme(self._config.theme, self._config.accent, self._config.font_size)

    def _compile(self, cfg: ThemeConfig) -> str:
        base = self._load(STYLES_DIR / "default.qss")
        if not base:
            return ""

        subs = dict(cfg.palette)
        subs["accent"] = cfg.accent_hex
        subs["accent_light"] = self._lighten(cfg.accent_hex, 0.25)
        subs["accent_dark"] = self._darken(cfg.accent_hex, 0.20)
        subs["accent_bg"] = cfg.accent_hex + "18"

        for k, v in subs.items():
            base = base.replace(f"${{{k}}}", v)

        if cfg.font_multiplier != 1.0:
            base += f"\n* {{ font-size: {int(13 * cfg.font_multiplier)}px; }}"

        override = self._load(STYLES_DIR / f"{cfg.theme}.qss")
        if override:
            for k, v in subs.items():
                override = override.replace(f"${{{k}}}", v)
            base += "\n" + override

        return base

    @staticmethod
    def _load(path: Path) -> str:
        if path.exists():
            try:
                return open(path, "r", encoding="utf-8").read()
            except Exception as e:
                logger.error(f"QSS load error {path}: {e}")
        return ""

    @staticmethod
    def _lighten(h: str, f: float) -> str:
        h = h.lstrip("#")
        r = min(255, int(int(h[0:2], 16) + (255 - int(h[0:2], 16)) * f))
        g = min(255, int(int(h[2:4], 16) + (255 - int(h[2:4], 16)) * f))
        b = min(255, int(int(h[4:6], 16) + (255 - int(h[4:6], 16)) * f))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(h: str, f: float) -> str:
        h = h.lstrip("#")
        r = max(0, int(int(h[0:2], 16) * (1 - f)))
        g = max(0, int(int(h[2:4], 16) * (1 - f)))
        b = max(0, int(int(h[4:6], 16) * (1 - f)))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def get_accent_colors() -> dict: return dict(ACCENT_COLORS)
    @staticmethod
    def get_font_sizes() -> dict:   return dict(FONT_SIZES)
    @staticmethod
    def get_themes() -> list[str]:  return list(THEME_PALETTES.keys())
