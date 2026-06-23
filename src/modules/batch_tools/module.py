"""Batch File Tools Module."""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from src.modules.base_module import BaseModule


class BatchToolsModule(BaseModule):
    module_id = "batch_tools"
    module_name = "批量文件"
    module_icon = "nav_batch"
    module_order = 40
    category = "productivity"

    def create_main_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("📦 批量文件工具\n\n批量重命名 · 重复文件查找 · 文件校验\n压缩解压 · 目录清单导出")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("hintLabel")
        label.setStyleSheet("font-size: 15px; padding: 40px;")
        layout.addWidget(label)

        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "rename", "name": "批量重命名"},
            {"id": "duplicate", "name": "重复文件查找"},
            {"id": "checksum", "name": "文件校验"},
            {"id": "archive", "name": "压缩解压"},
            {"id": "listing", "name": "目录清单"},
        ]
