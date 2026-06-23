"""Basic Efficiency Tools Module."""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from src.modules.base_module import BaseModule


class EfficiencyToolsModule(BaseModule):
    module_id = "efficiency_tools"
    module_name = "效率工具"
    module_icon = "nav_tools"
    module_order = 50
    category = "productivity"

    def create_main_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("🔧 基础效率工具\n\n文本格式化 · 编码转换 · 单位换算\n截图 · 便签 · 密码生成 · 音视频")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("hintLabel")
        label.setStyleSheet("font-size: 15px; padding: 40px;")
        layout.addWidget(label)

        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "text_format", "name": "文本格式化"},
            {"id": "encoding", "name": "编码转换"},
            {"id": "convert", "name": "单位/日期换算"},
            {"id": "screenshot", "name": "截图工具"},
            {"id": "sticky_notes", "name": "桌面便签"},
            {"id": "password", "name": "密码生成器"},
            {"id": "media", "name": "音视频工具"},
        ]
