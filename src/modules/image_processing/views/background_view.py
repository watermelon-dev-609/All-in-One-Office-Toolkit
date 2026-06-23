"""Background removal UI view with output management."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QGroupBox, QFormLayout, QSplitter,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class BackgroundView(QWidget):
    """View for AI background removal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        top = QVBoxLayout()
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_added)
        top.addWidget(self._drop_zone)
        self._output_path = OutputPathWidget()
        top.addWidget(self._output_path)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Vertical)
        self._file_list = FileListWidget()
        splitter.addWidget(self._file_list)
        controls = self._create_controls()
        splitter.addWidget(controls)
        splitter.setSizes([280, 110])
        layout.addWidget(splitter, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.connect_queue(self._queue)
        self._queue.task_completed.connect(self._on_done)
        layout.addWidget(self._task_progress)

    def _create_controls(self) -> QWidget:
        group = QGroupBox("去背景设置")
        layout = QFormLayout(group)
        self._white_bg_check = QCheckBox("输出白底图（否则输出透明 PNG）")
        self._white_bg_check.setChecked(True)
        layout.addRow("", self._white_bg_check)
        self._alpha_matting_check = QCheckBox("精细边缘处理（速度较慢）")
        layout.addRow("", self._alpha_matting_check)

        btn_layout = QHBoxLayout()
        self._apply_btn = QPushButton("开始去除背景")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(36)
        self._apply_btn.clicked.connect(self._start)
        btn_layout.addStretch()
        btn_layout.addWidget(self._apply_btn)
        layout.addRow("", btn_layout)
        return group

    def _on_files_added(self, paths: list[str]) -> None:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        image_paths = [p for p in paths if Path(p).suffix.lower() in image_exts]
        if image_paths:
            self._file_list.add_files(image_paths)

    def _start(self) -> None:
        files = self._file_list.get_files()
        if not files:
            return
        output_dir = self._output_path.output_dir or None
        for fp in files:
            task = TaskItem(
                task_type="remove_background",
                input_files=[fp],
                params={
                    "make_white_bg": self._white_bg_check.isChecked(),
                    "alpha_matting": self._alpha_matting_check.isChecked(),
                    "output_dir": output_dir,
                },
            )
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "remove_background", fp.name,
                output_dir=output_dir or str(Path(fp).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])
