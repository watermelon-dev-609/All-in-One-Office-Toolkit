"""OCR text extraction UI view."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QGroupBox, QFormLayout, QSplitter, QTextEdit,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class OCRView(QWidget):
    """View for OCR text extraction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()

        layout = QVBoxLayout(self)

        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_added)
        layout.addWidget(self._drop_zone)

        splitter = QSplitter(Qt.Vertical)
        self._file_list = FileListWidget()
        splitter.addWidget(self._file_list)

        controls = self._create_controls()
        splitter.addWidget(controls)
        splitter.setSizes([300, 100])
        layout.addWidget(splitter, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.connect_queue(self._queue)
        layout.addWidget(self._task_progress)

    def _create_controls(self) -> QWidget:
        group = QGroupBox("OCR 设置")
        layout = QFormLayout(group)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中英文混合", "仅中文", "仅英文"])
        layout.addRow("识别语言:", self._lang_combo)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["TXT 文本", "JSON 格式"])
        layout.addRow("输出格式:", self._format_combo)

        btn_layout = QHBoxLayout()
        self._apply_btn = QPushButton("开始文字提取")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(36)
        self._apply_btn.clicked.connect(self._start)
        btn_layout.addStretch()
        btn_layout.addWidget(self._apply_btn)
        layout.addRow("", btn_layout)

        return group

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

        for fp in files:
            task = TaskItem(
                task_type="ocr_image",
                input_files=[fp],
                params={
                    "languages": lang_map.get(self._lang_combo.currentText(), ["ch_sim", "en"]),
                    "output_format": fmt_map.get(self._format_combo.currentText(), "txt"),
                },
            )
            self._queue.submit(task)
            self._task_progress.add_task(task.task_id, "ocr_image", fp.name)
