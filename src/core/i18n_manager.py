"""Internationalization (i18n) manager.

Loads JSON translation files and provides a tr() function for the app.
Uses dot-notation keys and supports variable substitution.
"""

import json
from pathlib import Path
from typing import Optional

from loguru import logger

from src.constants import I18N_DIR


class I18nManager:
    """Manages translations for the application."""

    _instance = None
    _current_lang = "zh_CN"
    _translations = {}
    _fallback_lang = "zh_CN"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._load_all()
        self._loaded = True

    def _load_all(self) -> None:
        """Load all available language files from i18n directory."""
        if not I18N_DIR.exists():
            logger.warning(f"I18N directory not found: {I18N_DIR}")
            self._translations = {self._current_lang: {}}
            return

        for lang_file in I18N_DIR.glob("*.json"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self._translations[lang_code] = json.load(f)
                logger.debug(f"Loaded language: {lang_code} ({len(self._translations[lang_code])} keys)")
            except Exception as e:
                logger.error(f"Failed to load language file {lang_file}: {e}")

        if self._current_lang not in self._translations:
            # Fall back to zh_CN, then first available, then empty
            if self._fallback_lang in self._translations:
                self._current_lang = self._fallback_lang
            elif self._translations:
                self._current_lang = next(iter(self._translations.keys()))
            else:
                self._translations[self._current_lang] = {}

        logger.info(f"Current language: {self._current_lang}")

    @property
    def current_language(self) -> str:
        return self._current_lang

    @property
    def available_languages(self) -> list[str]:
        return list(self._translations.keys())

    def set_language(self, lang_code: str) -> None:
        """Switch to a different language."""
        if lang_code in self._translations:
            self._current_lang = lang_code
            logger.info(f"Language switched to: {lang_code}")
        else:
            logger.warning(f"Language '{lang_code}' not available, keeping {self._current_lang}")

    def tr(self, key: str, **kwargs) -> str:
        """Translate a key. Returns formatted string with variable substitution.

        Usage:
            _ = i18n.tr
            label.setText(_("app.name"))
            label.setText(_("task.progress", percent=75))

        Args:
            key: Dot-notation translation key.
            **kwargs: Variables for string formatting.

        Returns:
            Translated and formatted string.
        """
        # Try current language
        text = self._translations.get(self._current_lang, {}).get(key)

        # Fallback chain: current -> zh_CN -> any available -> key
        if text is None and self._current_lang != self._fallback_lang:
            text = self._translations.get(self._fallback_lang, {}).get(key)

        if text is None:
            # Try any available language
            for lang, trans in self._translations.items():
                if key in trans:
                    text = trans[key]
                    break

        if text is None:
            # Return key itself as last resort
            text = key

        # Variable substitution
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.debug(f"Format error for key '{key}': {e}")
                return text

        return text

    def has_key(self, key: str) -> bool:
        """Check if a translation key exists."""
        return key in self._translations.get(self._current_lang, {})


# Global convenience function
_i18n = I18nManager()


def tr(key: str, **kwargs) -> str:
    """Global translation function. Use: from src.core.i18n_manager import tr"""
    return _i18n.tr(key, **kwargs)
