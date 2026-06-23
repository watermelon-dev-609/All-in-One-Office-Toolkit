"""Abstract base class for all feature modules.

Every module must inherit from this and implement the required interface.
"""

from abc import ABC, abstractmethod
from typing import Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QObject


class BaseModule(ABC):
    """Abstract base for all feature modules in the application.

    Each module represents a top-level feature area (e.g., Image Processing,
    PDF Tools, AI Tools) and provides its own UI view and engines.
    """

    # ---- Module Metadata (override in subclasses) ----

    module_id: str = "base"
    module_name: str = "Base Module"
    module_icon: str = "nav_default"  # Icon key for navigation
    module_order: int = 999           # Sort order in navigation (lower = first)
    category: str = "core"            # core | productivity | ai

    def __init__(self):
        super().__init__()
        self._enabled = True
        self._main_view = None

    # ---- UI ----

    @abstractmethod
    def create_main_view(self) -> QWidget:
        """Create and return the main workspace widget for this module.

        Called when the user navigates to this module. The returned widget
        is displayed in the right panel of the main window.

        Returns:
            QWidget instance to display.
        """
        ...

    def get_sub_features(self) -> list[dict]:
        """Return sub-feature definitions for this module.

        Each sub-feature is a dict with:
            - id: str       Unique sub-feature identifier
            - name: str     Display name
            - icon: str     Icon key (optional)
            - view_class:   Callable that returns QWidget (optional)

        Returns:
            List of sub-feature dicts.
        """
        return []

    # ---- Properties ----

    @property
    def enabled(self) -> bool:
        """Whether this module is currently enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def main_view(self) -> Optional[QWidget]:
        """The module's main view widget (lazy-created)."""
        if self._main_view is None:
            self._main_view = self.create_main_view()
        return self._main_view

    # ---- Lifecycle Hooks ----

    def on_module_activated(self) -> None:
        """Called when the user switches to this module."""
        pass

    def on_module_deactivated(self) -> None:
        """Called when the user switches away from this module."""
        pass

    # ---- Config Schema ----

    def get_config_schema(self) -> dict:
        """Return a config schema for the settings dialog.

        Override to provide module-specific settings that are
        auto-rendered in the settings tree.

        Returns:
            Dict describing config keys and their UI representation.
        """
        return {}
