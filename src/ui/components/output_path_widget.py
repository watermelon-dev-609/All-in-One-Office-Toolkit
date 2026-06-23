"""Output directory selector widget with open-folder action."""

import os
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFileDialog,
)
from PySide6.QtCore import Signal


class OutputPathWidget(QWidget):
    """Shows the output directory path with browse and open buttons."""

    path_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("输出:")
        label.setStyleSheet("font-weight: 600; font-size: 12px;")
        layout.addWidget(label)

        self._path_label = QLabel("自动（原文件旁 Output/）")
        self._path_label.setObjectName("hintLabel")
        self._path_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._path_label, 1)

        browse_btn = QPushButton("选择目录")
        browse_btn.setFixedHeight(26)
        browse_btn.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn)

        self._open_btn = QPushButton("打开目录")
        self._open_btn.setFixedHeight(26)
        self._open_btn.setObjectName("primaryBtn")
        self._open_btn.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self._open_btn.clicked.connect(self._open_folder)
        layout.addWidget(self._open_btn)

        self._output_dir = None

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self._output_dir = Path(folder)
            self._path_label.setText(str(folder))
            self.path_changed.emit(folder)

    def _open_folder(self) -> None:
        """Open the output directory in Windows Explorer."""
        target = self._output_dir
        if target is None:
            # Default: show a hint
            return
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        # Open in Explorer
        try:
            os.startfile(str(target))
        except Exception:
            subprocess.Popen(["explorer", str(target)])

    @property
    def output_dir(self) -> str:
        """Get current output directory (empty string = auto)."""
        return str(self._output_dir) if self._output_dir else ""

    def set_latest_output(self, path: str) -> None:
        """Update to show the latest output directory from a completed task."""
        p = Path(path)
        if p.is_file():
            p = p.parent
        if p.exists():
            self._output_dir = p
            self._path_label.setText(str(p))
