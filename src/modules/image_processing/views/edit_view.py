"""Image editing UI view (crop, rotate, flip, format convert, mosaic)."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QComboBox, QPushButton, QGroupBox, QFormLayout, QSplitter, QDoubleSpinBox,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class EditView(QWidget):
    """View for basic image editing operations."""

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
        splitter.setSizes([300, 180])
        layout.addWidget(splitter, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.connect_queue(self._queue)
        layout.addWidget(self._task_progress)

    def _create_controls(self) -> QWidget:
        group = QGroupBox("编辑设置")
        layout = QFormLayout(group)

        self._op_combo = QComboBox()
        self._op_combo.addItems([
            "格式转换", "旋转", "水平翻转", "垂直翻转", "调整大小", "马赛克/打码"
        ])
        self._op_combo.currentTextChanged.connect(self._on_op_changed)
        layout.addRow("操作:", self._op_combo)

        # Format conversion
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG", "JPG", "WebP", "GIF", "BMP"])

        # Rotation angle
        self._angle_spin = QSpinBox()
        self._angle_spin.setRange(0, 360)
        self._angle_spin.setValue(90)
        self._angle_spin.setSuffix("°")

        # Resize
        size_layout = QHBoxLayout()
        self._resize_w = QSpinBox()
        self._resize_w.setRange(1, 99999)
        self._resize_w.setValue(800)
        size_layout.addWidget(QLabel("宽:"))
        size_layout.addWidget(self._resize_w)
        self._resize_h = QSpinBox()
        self._resize_h.setRange(1, 99999)
        self._resize_h.setValue(600)
        size_layout.addWidget(QLabel("高:"))
        size_layout.addWidget(self._resize_h)

        # Mosaic pixel size
        self._mosaic_size = QSpinBox()
        self._mosaic_size.setRange(2, 100)
        self._mosaic_size.setValue(10)
        self._mosaic_size.setSuffix(" px")

        # Stack for different controls
        self._fmt_widget = self._format_combo
        self._angle_widget = self._angle_spin
        self._size_widget = QWidget()
        self._size_widget.setLayout(size_layout)
        self._mosaic_widget = self._mosaic_size

        self._fmt_row = layout.rowCount()
        layout.addRow("目标格式:", self._format_combo)

        btn_layout = QHBoxLayout()
        self._apply_btn = QPushButton("开始处理")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setMinimumHeight(36)
        self._apply_btn.clicked.connect(self._start)
        btn_layout.addStretch()
        btn_layout.addWidget(self._apply_btn)
        layout.addRow("", btn_layout)

        return group

    def _on_op_changed(self, text: str) -> None:
        """Update visible controls based on operation."""
        pass  # Simplified — always show all controls

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
            "格式转换": "convert",
            "旋转": "rotate",
            "水平翻转": "flip",
            "垂直翻转": "flip",
            "调整大小": "resize",
            "马赛克/打码": "mosaic",
        }
        op = op_map.get(self._op_combo.currentText(), "convert")

        params = {"operation": op}
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
            self._task_progress.add_task(task.task_id, "edit_image", fp.name)
