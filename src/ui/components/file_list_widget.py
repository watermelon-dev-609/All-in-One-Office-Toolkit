"""File list widget for displaying and managing imported files."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from src.core.i18n_manager import tr


class FileListWidget(QWidget):
    """Displays a list of imported files with add/remove controls."""

    file_list_changed = Signal(list)  # Emits current list of file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[Path] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        self._count_label = QLabel("0 个文件")
        self._count_label.setObjectName("hintLabel")
        header.addWidget(self._count_label)
        header.addStretch()

        clear_btn = QPushButton(tr("file.clear_list"))
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # List
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        self._list.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self._list, 1)

        # Bottom bar
        bottom = QHBoxLayout()

        add_files_btn = QPushButton(tr("file.import"))
        add_files_btn.clicked.connect(self._add_files)
        bottom.addWidget(add_files_btn)

        add_folder_btn = QPushButton(tr("file.import_folder"))
        add_folder_btn.clicked.connect(self._add_folder)
        bottom.addWidget(add_folder_btn)

        remove_btn = QPushButton(tr("common.delete"))
        remove_btn.clicked.connect(self._remove_selected)
        bottom.addWidget(remove_btn)

        bottom.addStretch()
        layout.addLayout(bottom)

    def add_files(self, paths: list[str | Path]) -> None:
        """Add files to the list."""
        new_files = []
        for p in paths:
            path = Path(p)
            if path.is_file() and path not in self._files:
                self._files.append(path)
                new_files.append(path)
            elif path.is_dir():
                # Recursively add files from folder
                for f in sorted(path.rglob("*")):
                    if f.is_file() and f not in self._files:
                        self._files.append(f)
                        new_files.append(f)

        self._refresh_list()
        if new_files:
            self.file_list_changed.emit(list(self._files))

    def get_files(self) -> list[Path]:
        """Return current file list."""
        return list(self._files)

    def clear(self) -> None:
        """Remove all files."""
        self._files.clear()
        self._refresh_list()
        self.file_list_changed.emit([])

    def count(self) -> int:
        return len(self._files)

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("file.import"), "", "All Files (*.*)"
        )
        if files:
            self.add_files(files)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("file.import_folder"))
        if folder:
            self.add_files([folder])

    def _remove_selected(self) -> None:
        selected = self._list.selectedItems()
        if not selected:
            return
        for item in selected:
            path = Path(item.data(Qt.UserRole))
            if path in self._files:
                self._files.remove(path)
        self._refresh_list()
        self.file_list_changed.emit(list(self._files))

    def _refresh_list(self) -> None:
        """Rebuild the list widget."""
        self._list.clear()
        for f in self._files:
            item = QListWidgetItem(f.name)
            item.setToolTip(str(f))
            item.setData(Qt.UserRole, str(f))
            self._list.addItem(item)

        total = len(self._files)
        self._count_label.setText(f"{total} 个文件")
