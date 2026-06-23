"""Office Document Tools Module."""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from src.modules.base_module import BaseModule


class OfficeToolsModule(BaseModule):
    module_id = "office_tools"
    module_name = "Office 文档"
    module_icon = "nav_office"
    module_order = 30
    category = "core"

    def create_main_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("📊 Office 文档工具\n\nWord · Excel · PPT\n批量处理 · 格式转换 · 合并拆分")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("hintLabel")
        label.setStyleSheet("font-size: 15px; padding: 40px;")
        layout.addWidget(label)

        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "word", "name": "Word 工具"},
            {"id": "excel", "name": "Excel 工具"},
            {"id": "ppt", "name": "PPT 工具"},
        ]
