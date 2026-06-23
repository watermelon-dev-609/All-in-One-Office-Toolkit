"""Application lifecycle manager.

QApplication subclass that orchestrates startup and shutdown.
"""

import sys
import signal
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from loguru import logger

from src.constants import APP_NAME, APP_VERSION, DATA_DIR, LOG_DIR, MODELS_DIR
from src.core.config_manager import ConfigManager
from src.core.log_manager import LogManager
from src.core.i18n_manager import I18nManager, tr
from src.core.theme_manager import ThemeManager
from src.core.event_bus import EventBus, Events
from src.core.path_manager import PathManager


class App(QApplication):
    """Main application class managing the full lifecycle."""

    def __init__(self, argv: list[str]):
        super().__init__(argv)

        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setOrganizationName("OmniOffice")
        self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        self.setAttribute(Qt.AA_EnableHighDpiScaling, True)

        self._main_window = None
        self._shutting_down = False

        # Initialize in order
        self._init_dirs()
        self._init_logging()
        self._init_config()
        self._init_i18n()
        self._init_theme()
        self._init_path_manager()

        logger.info(f"{APP_NAME} v{APP_VERSION} starting...")

    def _init_dirs(self) -> None:
        """Ensure data directories exist."""
        for d in [DATA_DIR, LOG_DIR, MODELS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def _init_logging(self) -> None:
        """Configure logging."""
        LogManager.setup(level="DEBUG" if self._is_dev() else "INFO")

    def _init_config(self) -> None:
        """Load or create configuration."""
        self.config = ConfigManager()

    def _init_i18n(self) -> None:
        """Initialize internationalization."""
        self.i18n = I18nManager()
        # Apply saved language preference
        saved_lang = self.config.get("app.language", "zh_CN")
        self.i18n.set_language(saved_lang)

    def _init_theme(self) -> None:
        """Initialize theme manager."""
        self.theme_manager = ThemeManager()

    def _init_path_manager(self) -> None:
        """Initialize path manager."""
        self.path_manager = PathManager()
        base_dir = self.config.get("output.base_dir", "")
        if base_dir:
            self.path_manager.set_output_base_dir(Path(base_dir))

    def run(self) -> int:
        """Start the application event loop.

        Returns:
            Exit code (0 = success).
        """
        # Defer window creation to let Qt fully initialize
        QTimer.singleShot(0, self._create_main_window)
        return self.exec()

    def _create_main_window(self) -> None:
        """Create and show the main application window."""
        from src.ui.main_window import MainWindow

        self._main_window = MainWindow()
        self._main_window.show()

        # Apply initial theme
        theme = self.config.get("app.theme", "dark")
        accent = self.config.get("app.accent_color", "teal")
        font_size = self.config.get("app.font_size", "normal")
        self.theme_manager.set_theme(theme, accent, font_size)

        # Mark first run
        if self.config.get("app.first_run", True):
            self.config.set("app.first_run", False)
            self.config.save()
            logger.info("First run completed")

        logger.info("Main window created and shown")

    @property
    def main_window(self):
        """Get the main window instance."""
        return self._main_window

    def _is_dev(self) -> bool:
        """Check if running in development mode."""
        return not getattr(sys, 'frozen', False)

    # ---- Shutdown ----

    def aboutToQuit(self) -> None:
        """Handle application shutdown."""
        if self._shutting_down:
            return
        self._shutting_down = True

        logger.info(f"{APP_NAME} shutting down...")

        # Save config
        try:
            self.config.save()
        except Exception as e:
            logger.error(f"Failed to save config on shutdown: {e}")

        # Cleanup
        logger.info("Shutdown complete")
