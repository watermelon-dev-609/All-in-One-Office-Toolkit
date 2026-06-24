"""OCR text extraction UI view — clean layout."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QFormLayout, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class OCRView(QWidget):
    """View for OCR text extraction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_added)
        layout.addWidget(self._drop_zone)

        self._output_path = OutputPathWidget()
        layout.addWidget(self._output_path)

        middle = QHBoxLayout()
        middle.setSpacing(12)

        self._file_list = FileListWidget()
        self._file_list.setMinimumWidth(280)
        self._file_list.setMaximumWidth(400)
        middle.addWidget(self._file_list)

        settings = self._create_settings()
        middle.addWidget(settings, 1)
        layout.addLayout(middle, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.setMaximumHeight(200)
        self._task_progress.connect_queue(self._queue)
        self._queue.task_completed.connect(self._on_done)
        layout.addWidget(self._task_progress)

    def _create_settings(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        group = QGroupBox("OCR 设置")
        form = QFormLayout(group)
        form.setSpacing(8)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中英文混合", "仅中文", "仅英文"])
        form.addRow("识别语言:", self._lang_combo)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["TXT 文本", "JSON 格式"])
        form.addRow("输出格式:", self._format_combo)
        layout.addWidget(group)

        layout.addStretch()

        self._apply_btn = QPushButton("开始文字提取")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(40)
        self._apply_btn.clicked.connect(self._start)
        layout.addWidget(self._apply_btn)

        scroll.setWidget(panel)
        return scroll

    def _on_files_added(self, paths: list[str]) -> None:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
        image_paths = [p for p in paths if Path(p).suffix.lower() in image_exts]
        if image_paths:
            self._file_list.add_files(image_paths)

    def _start(self) -> None:
        files = self._file_list.get_files()
        if not files:
            return

        lang_map = {"中英文混合": ["ch_sim", "en"], "仅中文": ["ch_sim"], "仅英文": ["en"]}
        fmt_map = {"TXT 文本": "txt", "JSON 格式": "json"}
        output_dir = self._output_path.output_dir or None

        for fp in files:
            task = TaskItem(
                task_type="ocr_image",
                input_files=[fp],
                params={
                    "languages": lang_map.get(self._lang_combo.currentText(), ["ch_sim", "en"]),
                    "output_format": fmt_map.get(self._format_combo.currentText(), "txt"),
                    "output_dir": output_dir,
                },
            )
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "ocr_image", fp.name,
                output_dir=output_dir or str(Path(fp).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])
