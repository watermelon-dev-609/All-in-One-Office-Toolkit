"""Image editing UI view — clean horizontal layout."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QComboBox, QPushButton, QGroupBox, QFormLayout,
    QFrame, QScrollArea,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class EditView(QWidget):
    """View for basic image editing: rotate, flip, resize, format convert, mosaic."""

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

        group = QGroupBox("编辑操作")
        form = QFormLayout(group)
        form.setSpacing(8)

        self._op_combo = QComboBox()
        self._op_combo.addItems([
            "格式转换", "旋转", "水平翻转", "垂直翻转", "调整大小", "马赛克/打码"
        ])
        form.addRow("操作:", self._op_combo)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG", "JPG", "WebP", "GIF", "BMP"])
        form.addRow("目标格式:", self._format_combo)

        sz = QHBoxLayout()
        self._resize_w = QSpinBox()
        self._resize_w.setRange(1, 99999)
        self._resize_w.setValue(800)
        sz.addWidget(QLabel("宽:"))
        sz.addWidget(self._resize_w)
        self._resize_h = QSpinBox()
        self._resize_h.setRange(1, 99999)
        self._resize_h.setValue(600)
        sz.addWidget(QLabel("高:"))
        sz.addWidget(self._resize_h)
        form.addRow("尺寸:", sz)

        self._angle_spin = QSpinBox()
        self._angle_spin.setRange(0, 360)
        self._angle_spin.setValue(90)
        self._angle_spin.setSuffix("°")
        form.addRow("旋转角度:", self._angle_spin)

        self._mosaic_size = QSpinBox()
        self._mosaic_size.setRange(2, 100)
        self._mosaic_size.setValue(10)
        self._mosaic_size.setSuffix(" px")
        form.addRow("马赛克大小:", self._mosaic_size)
        layout.addWidget(group)

        layout.addStretch()

        self._apply_btn = QPushButton("开始处理")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(40)
        self._apply_btn.clicked.connect(self._start)
        layout.addWidget(self._apply_btn)

        scroll.setWidget(panel)
        return scroll

    def _on_files_added(self, paths: list[str]) -> None:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        image_paths = [p for p in paths if Path(p).suffix.lower() in image_exts]
        if image_paths:
            self._file_list.add_files(image_paths)

    def _start(self) -> None:
        files = self._file_list.get_files()
        if not files:
            return

        op_map = {
            "格式转换": "convert", "旋转": "rotate",
            "水平翻转": "flip", "垂直翻转": "flip",
            "调整大小": "resize", "马赛克/打码": "mosaic",
        }
        op = op_map.get(self._op_combo.currentText(), "convert")
        output_dir = self._output_path.output_dir or None

        params = {"operation": op, "output_dir": output_dir}
        if op == "convert":
            params["target_format"] = self._format_combo.currentText().lower()
        elif op == "rotate":
            params["angle"] = self._angle_spin.value()
        elif op == "flip":
            params["direction"] = "horizontal" if self._op_combo.currentText() == "水平翻转" else "vertical"
        elif op == "resize":
            params["width"] = self._resize_w.value()
            params["height"] = self._resize_h.value()
            params["keep_ratio"] = True
        elif op == "mosaic":
            params["pixel_size"] = self._mosaic_size.value()

        for fp in files:
            task = TaskItem(task_type="edit_image", input_files=[fp], params=params)
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "edit_image", fp.name,
                output_dir=output_dir or str(Path(fp).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])
