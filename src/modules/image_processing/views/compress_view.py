"""Image compression UI view — clean horizontal layout."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QComboBox, QPushButton, QCheckBox, QGroupBox, QFormLayout,
    QFrame, QScrollArea,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class CompressView(QWidget):
    """View for image compression."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top bar
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_added)
        layout.addWidget(self._drop_zone)

        self._output_path = OutputPathWidget()
        layout.addWidget(self._output_path)

        # Middle: file list + settings
        middle = QHBoxLayout()
        middle.setSpacing(12)

        self._file_list = FileListWidget()
        self._file_list.setMinimumWidth(280)
        self._file_list.setMaximumWidth(400)
        middle.addWidget(self._file_list)

        settings = self._create_settings()
        middle.addWidget(settings, 1)

        layout.addLayout(middle, 1)

        # Bottom: task progress
        self._task_progress = TaskProgressWidget()
        self._task_progress.setMaximumHeight(200)
        self._task_progress.connect_queue(self._queue)
        self._queue.task_completed.connect(self._on_done)
        layout.addWidget(self._task_progress)

        self._task_progress.pause_button.clicked.connect(self._on_pause_resume)
        self._task_progress.cancel_all_button.clicked.connect(self._queue.cancel_all)
        self._task_progress.clear_button.clicked.connect(self._task_progress.clear_completed)

    def _create_settings(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Compression settings
        comp_group = QGroupBox("压缩参数")
        form = QFormLayout(comp_group)
        form.setSpacing(8)

        qly = QHBoxLayout()
        self._quality_slider = QSlider(Qt.Horizontal)
        self._quality_slider.setRange(1, 100)
        self._quality_slider.setValue(85)
        qly.addWidget(self._quality_slider)
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(85)
        self._quality_spin.setSuffix("%")
        self._quality_spin.setFixedWidth(70)
        self._quality_slider.valueChanged.connect(self._quality_spin.setValue)
        self._quality_spin.valueChanged.connect(self._quality_slider.setValue)
        qly.addWidget(self._quality_spin)
        form.addRow("画质:", qly)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["保持原格式", "JPG", "PNG", "WebP", "GIF"])
        form.addRow("输出格式:", self._format_combo)

        sz = QHBoxLayout()
        self._width_spin = QSpinBox()
        self._width_spin.setRange(0, 10000)
        self._width_spin.setValue(0)
        self._width_spin.setSpecialValueText("不限")
        self._width_spin.setSuffix(" px")
        sz.addWidget(QLabel("宽:"))
        sz.addWidget(self._width_spin)
        self._height_spin = QSpinBox()
        self._height_spin.setRange(0, 10000)
        self._height_spin.setValue(0)
        self._height_spin.setSpecialValueText("不限")
        self._height_spin.setSuffix(" px")
        sz.addWidget(QLabel("高:"))
        sz.addWidget(self._height_spin)
        form.addRow("最大尺寸:", sz)

        self._lossless_check = QCheckBox("无损压缩（文件可能更大）")
        form.addRow("", self._lossless_check)
        layout.addWidget(comp_group)

        layout.addStretch()

        self._compress_btn = QPushButton("开始压缩")
        self._compress_btn.setObjectName("primaryBtn")
        self._compress_btn.setMinimumHeight(40)
        self._compress_btn.clicked.connect(self._start_compress)
        layout.addWidget(self._compress_btn)

        scroll.setWidget(panel)
        return scroll

    def _on_files_added(self, paths: list[str]) -> None:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
        image_paths = [p for p in paths if Path(p).suffix.lower() in image_exts]
        if image_paths:
            self._file_list.add_files(image_paths)

    def _start_compress(self) -> None:
        files = self._file_list.get_files()
        if not files:
            return

        quality = self._quality_slider.value()
        fmt_text = self._format_combo.currentText()
        output_format = "" if fmt_text == "保持原格式" else fmt_text.lower()
        output_dir = self._output_path.output_dir or None

        for file_path in files:
            task = TaskItem(
                task_type="compress_image",
                input_files=[file_path],
                params={
                    "quality": quality,
                    "max_width": self._width_spin.value(),
                    "max_height": self._height_spin.value(),
                    "output_format": output_format,
                    "lossless": self._lossless_check.isChecked(),
                    "output_dir": output_dir,
                },
            )
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "compress_image", file_path.name,
                output_dir=output_dir or str(Path(file_path).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])

    def _on_pause_resume(self) -> None:
        if self._queue.is_paused:
            self._queue.resume()
        else:
            self._queue.pause()
