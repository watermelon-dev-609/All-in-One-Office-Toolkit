"""Settings dialog with tree-based navigation."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QWidget, QLabel, QComboBox, QCheckBox, QSpinBox,
    QPushButton, QDialogButtonBox, QFileDialog, QLineEdit, QFrame,
    QFormLayout, QScrollArea, QGroupBox,
)
from PySide6.QtCore import Qt, Signal
from loguru import logger

from src.core.i18n_manager import tr
from src.core.config_manager import ConfigManager
from src.core.theme_manager import ThemeManager, ACCENT_COLORS

TREE_WIDTH = 180


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumSize(700, 480)
        self.resize(750, 520)

        self._config = ConfigManager()
        self._theme_manager = ThemeManager()

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self) -> None:
        """Build the settings dialog layout."""
        layout = QHBoxLayout(self)

        # Left: Category tree
        self._tree = QTreeWidget()
        self._tree.setFixedWidth(TREE_WIDTH)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)
        self._tree.currentItemChanged.connect(self._on_category_changed)

        # Create categories
        self._cat_general = QTreeWidgetItem(self._tree, [tr("settings.general")])
        self._cat_general.setData(0, Qt.UserRole, "general")
        self._cat_appearance = QTreeWidgetItem(self._tree, [tr("settings.appearance")])
        self._cat_appearance.setData(0, Qt.UserRole, "appearance")
        self._cat_output = QTreeWidgetItem(self._tree, [tr("settings.output")])
        self._cat_output.setData(0, Qt.UserRole, "output")
        self._cat_performance = QTreeWidgetItem(self._tree, [tr("settings.performance")])
        self._cat_performance.setData(0, Qt.UserRole, "performance")

        self._tree.expandAll()
        layout.addWidget(self._tree)

        # Right: Stack of settings pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_general_page())
        self._stack.addWidget(self._create_appearance_page())
        self._stack.addWidget(self._create_output_page())
        self._stack.addWidget(self._create_performance_page())
        layout.addWidget(self._stack, 1)

        # Select first category
        self._tree.setCurrentItem(self._cat_general)

    # ---- Pages ----

    def _wrap_page(self, title: str, inner: QWidget) -> QWidget:
        """Wrap a settings page in a scroll area with a title."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        return page

    def _create_general_page(self) -> QWidget:
        inner = QWidget()
        layout = QFormLayout(inner)
        layout.setSpacing(12)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem(tr("settings.language_zh"), "zh_CN")
        layout.addRow(tr("settings.language"), self._lang_combo)

        self._check_updates = QCheckBox(tr("settings.check_updates"))
        layout.addRow("", self._check_updates)

        return self._wrap_page(tr("settings.general"), inner)

    def _create_appearance_page(self) -> QWidget:
        inner = QWidget()
        layout = QFormLayout(inner)
        layout.setSpacing(12)

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItem(tr("settings.theme_dark"), "dark")
        self._theme_combo.addItem(tr("settings.theme_light"), "light")
        layout.addRow(tr("settings.theme"), self._theme_combo)

        # Accent color
        self._accent_combo = QComboBox()
        for name, hex_val in ACCENT_COLORS.items():
            self._accent_combo.addItem(f"  ■  {name}", name)
        layout.addRow(tr("settings.accent_color"), self._accent_combo)

        # Font size
        self._font_combo = QComboBox()
        self._font_combo.addItem(tr("settings.font_small"), "small")
        self._font_combo.addItem(tr("settings.font_normal"), "normal")
        self._font_combo.addItem(tr("settings.font_large"), "large")
        layout.addRow(tr("settings.font_size"), self._font_combo)

        return self._wrap_page(tr("settings.appearance"), inner)

    def _create_output_page(self) -> QWidget:
        inner = QWidget()
        layout = QFormLayout(inner)
        layout.setSpacing(12)

        # Output directory
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText(tr("settings.output_dir_auto"))
        dir_layout.addWidget(self._output_dir_edit)
        browse_btn = QPushButton(tr("common.browse"))
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(browse_btn)
        layout.addRow(tr("settings.output_dir"), dir_widget)

        return self._wrap_page(tr("settings.output"), inner)

    def _create_performance_page(self) -> QWidget:
        inner = QWidget()
        layout = QFormLayout(inner)
        layout.setSpacing(12)

        self._max_threads = QSpinBox()
        self._max_threads.setRange(0, 32)
        self._max_threads.setSpecialValueText(tr("settings.max_threads_auto"))
        layout.addRow(tr("settings.max_threads"), self._max_threads)

        return self._wrap_page(tr("settings.performance"), inner)

    # ---- Navigation ----

    def _on_category_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem) -> None:
        if current is None:
            return
        category = current.data(0, Qt.UserRole)
        index_map = {"general": 0, "appearance": 1, "output": 2, "performance": 3}
        self._stack.setCurrentIndex(index_map.get(category, 0))

    # ---- Load / Save ----

    def _load_current_values(self) -> None:
        """Populate UI from current config."""
        # General
        lang = self._config.get("app.language", "zh_CN")
        idx = self._lang_combo.findData(lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)

        self._check_updates.setChecked(self._config.get("app.check_updates", True))

        # Appearance
        theme = self._config.get("app.theme", "dark")
        idx = self._theme_combo.findData(theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

        accent = self._config.get("app.accent_color", "blue")
        idx = self._accent_combo.findData(accent)
        if idx >= 0:
            self._accent_combo.setCurrentIndex(idx)

        font_size = self._config.get("app.font_size", "normal")
        idx = self._font_combo.findData(font_size)
        if idx >= 0:
            self._font_combo.setCurrentIndex(idx)

        # Output
        base_dir = self._config.get("output.base_dir", "")
        self._output_dir_edit.setText(base_dir)

        # Performance
        self._max_threads.setValue(self._config.get("performance.max_threads", 0))

    def _save_and_close(self) -> None:
        """Save all settings and close dialog."""
        # General
        self._config.set("app.language", self._lang_combo.currentData())
        self._config.set("app.check_updates", self._check_updates.isChecked())

        # Appearance
        theme_changed = self._config.get("app.theme") != self._theme_combo.currentData()
        self._config.set("app.theme", self._theme_combo.currentData())
        self._config.set("app.accent_color", self._accent_combo.currentData())
        self._config.set("app.font_size", self._font_combo.currentData())

        # Output
        output_dir = self._output_dir_edit.text().strip()
        self._config.set("output.base_dir", output_dir)

        # Performance
        self._config.set("performance.max_threads", self._max_threads.value())

        self._config.save()

        # Apply theme immediately if changed
        if theme_changed:
            self._theme_manager.refresh()

        logger.info("Settings saved")
        self.accept()

    def _browse_output_dir(self) -> None:
        """Browse for custom output directory."""
        folder = QFileDialog.getExistingDirectory(self, tr("settings.output_dir"))
        if folder:
            self._output_dir_edit.setText(folder)
