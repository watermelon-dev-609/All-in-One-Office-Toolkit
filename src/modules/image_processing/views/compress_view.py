"""Image compression UI view with output directory management."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QComboBox, QPushButton, QCheckBox, QGroupBox, QFormLayout,
    QSplitter,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class CompressView(QWidget):
    """View for image compression with output management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()
        self._last_output_dir = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Top bar: Drop zone + output path
        top = QVBoxLayout()
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_added)
        top.addWidget(self._drop_zone)

        self._output_path = OutputPathWidget()
        top.addWidget(self._output_path)
        layout.addLayout(top)

        # Middle: Splitter with file list + controls
        splitter = QSplitter(Qt.Vertical)
        self._file_list = FileListWidget()
        splitter.addWidget(self._file_list)

        controls = self._create_controls()
        splitter.addWidget(controls)
        splitter.setSizes([280, 160])
        layout.addWidget(splitter, 1)

        # Bottom: Task progress
        self._task_progress = TaskProgressWidget()
        self._task_progress.connect_queue(self._queue)
        self._task_progress.open_output_requested.connect(self._open_task_output)
        layout.addWidget(self._task_progress)

        # Connect queue
        self._task_progress.pause_button.clicked.connect(self._on_pause_resume)
        self._task_progress.cancel_all_button.clicked.connect(self._queue.cancel_all)
        self._task_progress.clear_button.clicked.connect(self._task_progress.clear_completed)

        # Track completions
        self._queue.task_completed.connect(self._on_task_done)

    def _create_controls(self) -> QWidget:
        group = QGroupBox("压缩设置")
        layout = QFormLayout(group)

        quality_layout = QHBoxLayout()
        self._quality_slider = QSlider(Qt.Horizontal)
        self._quality_slider.setRange(1, 100)
        self._quality_slider.setValue(85)
        quality_layout.addWidget(self._quality_slider)
        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(85)
        self._quality_spin.setSuffix("%")
        self._quality_slider.valueChanged.connect(self._quality_spin.setValue)
        self._quality_spin.valueChanged.connect(self._quality_slider.setValue)
        quality_layout.addWidget(self._quality_spin)
        layout.addRow("画质:", quality_layout)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["保持原格式", "JPG", "PNG", "WebP", "GIF"])
        layout.addRow("输出格式:", self._format_combo)

        size_layout = QHBoxLayout()
        self._width_spin = QSpinBox()
        self._width_spin.setRange(0, 10000)
        self._width_spin.setValue(0)
        self._width_spin.setSpecialValueText("不限")
        self._width_spin.setSuffix(" px")
        size_layout.addWidget(QLabel("宽:"))
        size_layout.addWidget(self._width_spin)
        self._height_spin = QSpinBox()
        self._height_spin.setRange(0, 10000)
        self._height_spin.setValue(0)
        self._height_spin.setSpecialValueText("不限")
        self._height_spin.setSuffix(" px")
        size_layout.addWidget(QLabel("高:"))
        size_layout.addWidget(self._height_spin)
        layout.addRow("最大尺寸:", size_layout)

        self._lossless_check = QCheckBox("无损压缩（文件可能更大）")
        layout.addRow("", self._lossless_check)

        btn_layout = QHBoxLayout()
        self._compress_btn = QPushButton("开始压缩")
        self._compress_btn.setObjectName("primaryBtn")
        self._compress_btn.setMinimumHeight(36)
        self._compress_btn.clicked.connect(self._start_compress)
        btn_layout.addStretch()
        btn_layout.addWidget(self._compress_btn)
        layout.addRow("", btn_layout)

        return group

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
        output_format = ""
        if fmt_text != "保持原格式":
            output_format = fmt_text.lower()

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

    def _on_task_done(self, task_id: str, output_paths: list) -> None:
        """When a task completes, update the output path widget."""
        if output_paths:
            self._output_path.set_latest_output(output_paths[0])
            self._last_output_dir = output_paths[0]
            # Mark the task row with the output path
            self._task_progress.set_output_path(task_id, output_paths)

    def _open_task_output(self, task_id: str, output_paths: list) -> None:
        """Open the output folder for a completed task."""
        if output_paths:
            p = Path(output_paths[0])
            folder = p.parent if p.is_file() else p
            if folder.exists():
                os.startfile(str(folder))

    def _on_pause_resume(self) -> None:
        if self._queue.is_paused:
            self._queue.resume()
        else:
            self._queue.pause()
