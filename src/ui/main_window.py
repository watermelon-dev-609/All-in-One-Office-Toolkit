"""Main application window.

Provides the shell layout: left navigation panel + right workspace area.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QListWidget, QListWidgetItem, QLabel, QFrame, QStatusBar,
    QMenuBar, QMenu, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QIcon, QFont
from loguru import logger

from src.constants import APP_NAME, APP_VERSION
from src.core.i18n_manager import tr
from src.core.config_manager import ConfigManager
from src.core.event_bus import EventBus, Events
from src.core.plugin_manager import PluginManager
from src.core.theme_manager import ThemeManager, ACCENT_COLORS


NAV_ITEM_HEIGHT = 44
NAV_ICON_SIZE = 20


class MainWindow(QMainWindow):
    """Application main window with navigation sidebar and workspace."""

    module_activated = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 820)

        # Center on screen
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )

        self._modules = {}
        self._nav_items = {}  # module_id -> QListWidgetItem
        self._current_module_id = None

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._load_modules()

        logger.info("MainWindow initialized")

    # ---- UI Setup ----

    def _setup_ui(self) -> None:
        """Build the main window layout."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left: Navigation panel
        nav_panel = self._create_nav_panel()
        layout.addWidget(nav_panel)

        # Right: Workspace area
        self._workspace = QStackedWidget()
        self._workspace.setObjectName("workspaceArea")
        layout.addWidget(self._workspace, 1)

    def _create_nav_panel(self) -> QWidget:
        """Create the left navigation sidebar."""
        panel = QFrame()
        panel.setObjectName("navPanel")
        panel.setFixedWidth(220)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("navHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 12, 12)

        title = QLabel(APP_NAME)
        title.setObjectName("navTitle")
        header_layout.addWidget(title)

        subtitle = QLabel(tr("app.slogan"))
        subtitle.setObjectName("navSubtitle")
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # Module list
        self._nav_list = QListWidget()
        self._nav_list.setObjectName("navList")
        self._nav_list.setIconSize(QSize(NAV_ICON_SIZE, NAV_ICON_SIZE))
        self._nav_list.setSpacing(2)
        self._nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self._nav_list, 1)

        # Bottom spacer (for future use, e.g. version info)
        bottom = QLabel(f"v{APP_VERSION}")
        bottom.setObjectName("navSubtitle")
        bottom.setContentsMargins(16, 8, 12, 12)
        bottom.setAlignment(Qt.AlignCenter)
        layout.addWidget(bottom)

        return panel

    def _setup_menu(self) -> None:
        """Create menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu(tr("menu.file"))
        import_action = QAction(tr("menu.file.import"), self)
        import_action.triggered.connect(self._import_files)
        file_menu.addAction(import_action)
        import_folder_action = QAction(tr("menu.file.import_folder"), self)
        import_folder_action.triggered.connect(self._import_folder)
        file_menu.addAction(import_folder_action)
        file_menu.addSeparator()
        exit_action = QAction(tr("menu.file.exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu(tr("menu.view"))
        theme_menu = view_menu.addMenu(tr("menu.view.theme"))
        dark_action = QAction(tr("menu.view.theme_dark"), self)
        dark_action.triggered.connect(lambda: self._change_theme("dark"))
        theme_menu.addAction(dark_action)
        light_action = QAction(tr("menu.view.theme_light"), self)
        light_action.triggered.connect(lambda: self._change_theme("light"))
        theme_menu.addAction(light_action)

        view_menu.addSeparator()
        font_small = QAction(tr("menu.view.font_small"), self)
        font_small.triggered.connect(lambda: self._change_font_size("small"))
        view_menu.addAction(font_small)
        font_normal = QAction(tr("menu.view.font_normal"), self)
        font_normal.triggered.connect(lambda: self._change_font_size("normal"))
        view_menu.addAction(font_normal)
        font_large = QAction(tr("menu.view.font_large"), self)
        font_large.triggered.connect(lambda: self._change_font_size("large"))
        view_menu.addAction(font_large)

        # Tools menu
        tools_menu = menubar.addMenu(tr("menu.tools"))
        settings_action = QAction(tr("menu.tools.settings"), self)
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu(tr("menu.help"))
        about_action = QAction(tr("menu.help.about"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_statusbar(self) -> None:
        """Create status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage(tr("common.done"))

    # ---- Module Management ----

    def _load_modules(self) -> None:
        """Discover and load all feature modules."""
        pm = PluginManager()
        modules = pm.discover_modules()

        for module in modules:
            self._register_module(module)

        # Select first module
        if self._nav_list.count() > 0:
            self._nav_list.setCurrentRow(0)

    def _register_module(self, module) -> None:
        """Register a module in the navigation and workspace."""
        module_id = module.module_id
        self._modules[module_id] = module

        # Create nav item
        item = QListWidgetItem()
        item.setText(module.module_name)
        item.setData(Qt.UserRole, module_id)
        item.setSizeHint(QSize(0, NAV_ITEM_HEIGHT))

        # Try to set icon
        icon_path = module.module_icon
        if not icon_path.startswith("/") and not icon_path.startswith(":"):
            # Assume it's a local icon name
            from src.constants import ICONS_DIR
            icon_file = ICONS_DIR / f"{icon_path}.svg"
            if icon_file.exists():
                item.setIcon(QIcon(str(icon_file)))

        self._nav_list.addItem(item)
        self._nav_items[module_id] = item

        # Add module's main view to workspace
        view = module.main_view
        if view is not None:
            self._workspace.addWidget(view)

        logger.debug(f"Registered module: {module.module_name} ({module_id})")

    def _on_nav_changed(self, row: int) -> None:
        """Handle navigation item selection."""
        if row < 0:
            return

        item = self._nav_list.item(row)
        module_id = item.data(Qt.UserRole)

        if module_id == self._current_module_id:
            return

        # Deactivate previous
        if self._current_module_id and self._current_module_id in self._modules:
            old_module = self._modules[self._current_module_id]
            old_module.on_module_deactivated()
            EventBus().publish(Events.MODULE_DEACTIVATED, module_id=self._current_module_id)

        # Activate new
        if module_id in self._modules:
            module = self._modules[module_id]
            self._workspace.setCurrentWidget(module.main_view)
            module.on_module_activated()
            self._current_module_id = module_id
            self._statusbar.showMessage(module.module_name)
            EventBus().publish(Events.MODULE_ACTIVATED, module_id=module_id)
            self.module_activated.emit(module_id)

    # ---- Actions ----

    def _import_files(self) -> None:
        """Open file dialog to import files."""
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("file.import"), "", "All Files (*.*)"
        )
        if files:
            EventBus().publish(Events.FILE_IMPORTED, paths=files)

    def _import_folder(self) -> None:
        """Open folder dialog to import a folder."""
        folder = QFileDialog.getExistingDirectory(
            self, tr("file.import_folder"), ""
        )
        if folder:
            EventBus().publish(Events.FILE_IMPORTED, paths=[folder])

    def _change_theme(self, theme: str) -> None:
        """Switch between dark and light themes."""
        tm = ThemeManager()
        tm.set_theme(
            theme=theme,
            accent=tm.current_config.accent,
            font_size=tm.current_config.font_size,
        )
        ConfigManager().set("app.theme", theme)
        ConfigManager().save()
        EventBus().publish(Events.THEME_CHANGED, theme=theme)

    def _change_font_size(self, size: str) -> None:
        """Change font size."""
        tm = ThemeManager()
        tm.set_theme(
            theme=tm.current_config.theme,
            accent=tm.current_config.accent,
            font_size=size,
        )
        ConfigManager().set("app.font_size", size)
        ConfigManager().save()

    def _open_settings(self) -> None:
        """Open the settings dialog."""
        from src.ui.components.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    def _show_about(self) -> None:
        """Show the about dialog."""
        QMessageBox.about(
            self,
            tr("about.title"),
            f"<h3>{APP_NAME}</h3>"
            f"<p>{tr('about.version')}: {APP_VERSION}</p>"
            f"<p>{tr('about.description')}</p>"
            f"<p>{tr('about.license')}</p>",
        )

    # ---- Public API ----

    def switch_to_module(self, module_id: str) -> None:
        """Programmatically switch to a module."""
        if module_id in self._nav_items:
            item = self._nav_items[module_id]
            row = self._nav_list.row(item)
            self._nav_list.setCurrentRow(row)

    def get_current_module_id(self) -> str:
        """Return the currently active module ID."""
        return self._current_module_id
