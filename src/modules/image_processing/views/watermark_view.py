"""Watermark UI view with output management."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QComboBox, QPushButton, QCheckBox, QGroupBox, QFormLayout,
    QLineEdit, QSplitter,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class WatermarkView(QWidget):
    """View for adding watermarks."""

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
        splitter.setSizes([280, 220])
        layout.addWidget(splitter, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.connect_queue(self._queue)
        self._queue.task_completed.connect(self._on_done)
        layout.addWidget(self._task_progress)

    def _create_controls(self) -> QWidget:
        group = QGroupBox("水印设置")
        layout = QFormLayout(group)

        self._type_combo = QComboBox()
        self._type_combo.addItems(["文字水印", "图片水印"])
        layout.addRow("水印类型:", self._type_combo)

        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("输入水印文字...")
        self._text_edit.setText("机密文件")
        layout.addRow("水印文字:", self._text_edit)

        self._pos_combo = QComboBox()
        self._pos_combo.addItems(["居中", "左上角", "右上角", "左下角", "右下角", "平铺"])
        layout.addRow("位置:", self._pos_combo)

        opacity_layout = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(5, 100)
        self._opacity_slider.setValue(30)
        opacity_layout.addWidget(self._opacity_slider)
        self._opacity_spin = QSpinBox()
        self._opacity_spin.setRange(5, 100)
        self._opacity_spin.setValue(30)
        self._opacity_spin.setSuffix("%")
        self._opacity_slider.valueChanged.connect(self._opacity_spin.setValue)
        self._opacity_spin.valueChanged.connect(self._opacity_slider.setValue)
        layout.addRow("透明度:", opacity_layout)

        self._rotation_spin = QSpinBox()
        self._rotation_spin.setRange(0, 360)
        self._rotation_spin.setValue(0)
        self._rotation_spin.setSuffix("°")
        layout.addRow("旋转角度:", self._rotation_spin)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 200)
        self._font_size_spin.setValue(36)
        layout.addRow("字体大小:", self._font_size_spin)

        btn_layout = QHBoxLayout()
        self._apply_btn = QPushButton("开始添加水印")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(36)
        self._apply_btn.clicked.connect(self._start)
        btn_layout.addStretch()
        btn_layout.addWidget(self._apply_btn)
        layout.addRow("", btn_layout)

        return group

    def _on_files_added(self, paths: list[str]) -> None:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        image_paths = [p for p in paths if Path(p).suffix.lower() in image_exts]
        if image_paths:
            self._file_list.add_files(image_paths)

    def _start(self) -> None:
        files = self._file_list.get_files()
        if not files:
            return

        pos_map = {"居中": "center", "左上角": "tl", "右上角": "tr",
                    "左下角": "bl", "右下角": "br", "平铺": "tile"}
        output_dir = self._output_path.output_dir or None

        for fp in files:
            task = TaskItem(
                task_type="add_watermark",
                input_files=[fp],
                params={
                    "watermark_type": "text" if self._type_combo.currentIndex() == 0 else "image",
                    "watermark_text": self._text_edit.text(),
                    "opacity": self._opacity_slider.value() / 100.0,
                    "position": pos_map.get(self._pos_combo.currentText(), "center"),
                    "rotation": self._rotation_spin.value(),
                    "font_size": self._font_size_spin.value(),
                    "output_dir": output_dir,
                },
            )
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "add_watermark", fp.name,
                output_dir=output_dir or str(Path(fp).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])
