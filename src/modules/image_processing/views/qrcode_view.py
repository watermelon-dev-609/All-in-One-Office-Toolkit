"""QR code generation and decoding UI view."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QComboBox, QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QSplitter, QStackedWidget, QTextEdit,
)
from PySide6.QtCore import Qt

from src.ui.components.drop_zone import DropZone
from src.ui.components.file_list_widget import FileListWidget
from src.ui.components.task_progress_widget import TaskProgressWidget
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem


class QRCodeView(QWidget):
    """View for QR code generation and decoding."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = TaskQueue()

        layout = QVBoxLayout(self)

        # Mode switch
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["生成二维码", "解析二维码"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Stacked content
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_generate_page())
        self._stack.addWidget(self._create_decode_page())
        layout.addWidget(self._stack, 1)

        self._task_progress = TaskProgressWidget()
        self._task_progress.connect_queue(self._queue)
        layout.addWidget(self._task_progress)

    def _create_generate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("二维码内容")
        form = QFormLayout(group)

        self._qr_type = QComboBox()
        self._qr_type.addItems(["文本/网址", "WiFi 网络", "名片 vCard"])
        self._qr_type.currentIndexChanged.connect(self._on_qr_type_changed)
        form.addRow("类型:", self._qr_type)

        self._qr_content = QTextEdit()
        self._qr_content.setPlaceholderText("输入文本或网址...")
        self._qr_content.setMaximumHeight(80)
        form.addRow("内容:", self._qr_content)

        layout.addWidget(group)

        settings = QGroupBox("样式设置")
        sform = QFormLayout(settings)
        self._qr_box_size = QSpinBox()
        self._qr_box_size.setRange(2, 50)
        self._qr_box_size.setValue(10)
        sform.addRow("大小:", self._qr_box_size)
        layout.addWidget(settings)

        btn = QPushButton("生成二维码")
        btn.setObjectName("primaryBtn")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._generate)
        layout.addWidget(btn)
        layout.addStretch()

        return page

    def _create_decode_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._decode_drop = DropZone()
        self._decode_drop.files_dropped.connect(self._on_decode_files)
        layout.addWidget(self._decode_drop)

        self._decode_list = FileListWidget()
        layout.addWidget(self._decode_list, 1)

        btn = QPushButton("开始解析")
        btn.setObjectName("primaryBtn")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._decode)
        layout.addWidget(btn)

        return page

    def _on_mode_changed(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)

    def _on_qr_type_changed(self, idx: int) -> None:
        if idx == 1:  # WiFi
            self._qr_content.setPlaceholderText("SSID:MyWiFi\nPassword:12345678")
        elif idx == 2:  # vCard
            self._qr_content.setPlaceholderText("Name:张三\nPhone:13800138000")

    def _generate(self) -> None:
        content = self._qr_content.toPlainText().strip()
        if not content:
            return

        qr_type_map = {0: "text", 1: "wifi", 2: "vcard"}
        qr_type = qr_type_map.get(self._qr_type.currentIndex(), "text")

        task = TaskItem(
            task_type="qrcode",
            input_files=[Path("dummy")],  # Not file-based for generation
            params={
                "operation": "generate",
                "content": content,
                "qr_type": qr_type,
                "box_size": self._qr_box_size.value(),
            },
        )
        self._queue.submit(task)
        self._task_progress.add_task(task.task_id, "qrcode", "QR码生成")

    def _on_decode_files(self, paths: list[str]) -> None:
        self._decode_list.add_files(paths)

    def _decode(self) -> None:
        files = self._decode_list.get_files()
        if not files:
            return
        for fp in files:
            task = TaskItem(
                task_type="qrcode",
                input_files=[fp],
                params={"operation": "decode"},
            )
            self._queue.submit(task)
            self._task_progress.add_task(task.task_id, "qrcode", fp.name)
