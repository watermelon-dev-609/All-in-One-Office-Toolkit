"""QR code generation and decoding UI view — clean layout."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QComboBox, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QStackedWidget, QTextEdit, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.ui.components.output_path_widget import OutputPathWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class QRCodeView(QWidget):
    """View for QR code generation and decoding."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Mode switch
        mode_bar = QHBoxLayout()
        mode_bar.addWidget(QLabel("模式:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["生成二维码", "解析二维码"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_bar.addWidget(self._mode_combo)
        mode_bar.addStretch()
        layout.addLayout(mode_bar)

        # Stacked content
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_generate_page())
        self._stack.addWidget(self._create_decode_page())
        layout.addWidget(self._stack, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.setMaximumHeight(200)
        self._task_progress.connect_queue(self._queue)
        self._queue.task_completed.connect(self._on_done)
        layout.addWidget(self._task_progress)

    def _create_generate_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Left: preview placeholder
        left = QFrame()
        left.setMinimumWidth(200)
        left_layout = QVBoxLayout(left)
        left_layout.setAlignment(Qt.AlignCenter)
        hint = QLabel("二维码预览区")
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(hint)
        layout.addWidget(left)

        # Right: settings
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)

        right = QWidget()
        rlayout = QVBoxLayout(right)
        rlayout.setContentsMargins(0, 0, 0, 0)
        rlayout.setSpacing(12)

        # Content group
        content_group = QGroupBox("二维码内容")
        cform = QFormLayout(content_group)
        cform.setSpacing(8)

        self._qr_type = QComboBox()
        self._qr_type.addItems(["文本/网址", "WiFi 网络", "名片 vCard"])
        cform.addRow("类型:", self._qr_type)

        self._qr_content = QTextEdit()
        self._qr_content.setPlaceholderText("输入文本或网址...")
        self._qr_content.setMaximumHeight(80)
        cform.addRow("内容:", self._qr_content)
        rlayout.addWidget(content_group)

        # Style group
        style_group = QGroupBox("样式")
        sform = QFormLayout(style_group)
        sform.setSpacing(8)
        self._qr_box_size = QSpinBox()
        self._qr_box_size.setRange(2, 50)
        self._qr_box_size.setValue(10)
        sform.addRow("大小:", self._qr_box_size)
        rlayout.addWidget(style_group)

        rlayout.addStretch()

        self._gen_btn = QPushButton("生成二维码")
        self._gen_btn.setObjectName("primaryBtn")
        self._gen_btn.setMinimumHeight(40)
        self._gen_btn.clicked.connect(self._generate)
        rlayout.addWidget(self._gen_btn)

        right_scroll.setWidget(right)

        self._gen_output = OutputPathWidget()
        rlayout.addWidget(self._gen_output)

        layout.addWidget(right_scroll, 1)
        return page

    def _create_decode_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        decode_top = QHBoxLayout()
        decode_top.setSpacing(12)

        self._decode_drop = DropZone()
        self._decode_drop.files_dropped.connect(self._on_decode_files)
        decode_top.addWidget(self._decode_drop)

        self._decode_output = OutputPathWidget()
        layout.addWidget(self._decode_output)

        self._decode_list = FileListWidget()
        self._decode_list.setMaximumHeight(200)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._decode_btn = QPushButton("开始解析")
        self._decode_btn.setObjectName("primaryBtn")
        self._decode_btn.setMinimumHeight(40)
        self._decode_btn.clicked.connect(self._decode)
        btn_layout.addWidget(self._decode_btn)

        layout.addWidget(self._decode_list, 1)
        layout.addLayout(btn_layout)
        return page

    def _on_mode_changed(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)

    def _generate(self) -> None:
        content = self._qr_content.toPlainText().strip()
        if not content:
            return
        qr_type_map = {0: "text", 1: "wifi", 2: "vcard"}
        qr_type = qr_type_map.get(self._qr_type.currentIndex(), "text")
        output_dir = self._gen_output.output_dir or None
        task = TaskItem(
            task_type="qrcode",
            input_files=[Path.cwd() / "dummy"],
            params={
                "operation": "generate",
                "content": content,
                "qr_type": qr_type,
                "box_size": self._qr_box_size.value(),
                "output_dir": output_dir,
            },
        )
        self._queue.submit(task)
        self._task_progress.add_task(task.task_id, "qrcode", "QR码生成",
                                     output_dir=output_dir or str(Path.cwd() / "Output"))

    def _on_decode_files(self, paths: list[str]) -> None:
        self._decode_list.add_files(paths)

    def _decode(self) -> None:
        files = self._decode_list.get_files()
        if not files:
            return
        output_dir = self._decode_output.output_dir or None
        for fp in files:
            task = TaskItem(
                task_type="qrcode",
                input_files=[fp],
                params={"operation": "decode", "output_dir": output_dir},
            )
            self._queue.submit(task)
            self._task_progress.add_task(
                task.task_id, "qrcode", fp.name,
                output_dir=output_dir or str(Path(fp).parent / "Output")
            )

    def _on_done(self, task_id: str, output_paths: list) -> None:
        if output_paths:
            self._gen_output.set_latest_output(output_paths[0])
