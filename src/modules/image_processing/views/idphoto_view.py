"""ID Photo UI view — clean layout."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QFormLayout,
    QDoubleSpinBox, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class IDPhotoView(QWidget):
    """View for ID photo processing."""

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

        group = QGroupBox("证件照设置")
        form = QFormLayout(group)
        form.setSpacing(8)

        self._size_combo = QComboBox()
        self._size_combo.addItems([
            "一寸 (25x35mm)", "二寸 (35x49mm)", "小一寸 (22x32mm)",
            "大二寸 (35x53mm)", "护照 (33x48mm)"
        ])
        form.addRow("照片尺寸:", self._size_combo)

        self._bg_combo = QComboBox()
        self._bg_combo.addItems(["白色", "红色", "蓝色", "浅蓝色"])
        form.addRow("背景颜色:", self._bg_combo)

        self._brightness = QDoubleSpinBox()
        self._brightness.setRange(0.5, 2.0)
        self._brightness.setValue(1.0)
        self._brightness.setSingleStep(0.05)
        form.addRow("亮度:", self._brightness)

        self._contrast = QDoubleSpinBox()
        self._contrast.setRange(0.5, 2.0)
        self._contrast.setValue(1.0)
        self._contrast.setSingleStep(0.05)
        form.addRow("对比度:", self._contrast)
        layout.addWidget(group)

        layout.addStretch()

        self._apply_btn = QPushButton("制作证件照")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(40)
        self._apply_btn.clicked.connect(self._start)
        layout.addWidget(self._apply_btn)

        scroll.setWidget(panel)
        return scroll

    def _on_files_added(self, paths: list[str]) -> None:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        image_paths = [p for p in paths if Path(p).suffix.lower() in image_exts]
        if image_paths:
            self._file_list.add_files(image_paths)

    def _start(self) -> None:
        files = self._file_list.get_files()
        if not files:
            return

        size_map = {
            "一寸 (25x35mm)": "1inch", "二寸 (35x49mm)": "2inch",
            "小一寸 (22x32mm)": "small_1inch", "大二寸 (35x53mm)": "large_2inch",
            "护照 (33x48mm)": "passport",
        }
        bg_map = {"白色": "white", "红色": "red", "蓝色": "blue", "浅蓝色": "light_blue"}
        output_dir = self._output_path.output_dir or None

        for fp in files:
            task = TaskItem(
                task_type="id_photo",
                input_files=[fp],
                params={
                    "operation": "make",
                    "photo_size": size_map.get(self._size_combo.currentText(), "1inch"),
                    "background_color": bg_map.get(self._bg_combo.currentText(), "white"),
                    "brightness": self._brightness.value(),
                    "contrast": self._contrast.value(),
                    "output_dir": output_dir,
                },
            )
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "id_photo", fp.name,
                output_dir=output_dir or str(Path(fp).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])
