"""Mind Map Module."""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from src.modules.base_module import BaseModule


class MindMapModule(BaseModule):
    module_id = "mind_map"
    module_name = "思维导图"
    module_icon = "nav_mindmap"
    module_order = 70
    category = "productivity"

    def create_main_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("🗺️ 思维导图工具\n\n新建/编辑 · 文本生成导图 · 模板中心\n导出图片/PDF/大纲")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("hintLabel")
        label.setStyleSheet("font-size: 15px; padding: 40px;")
        layout.addWidget(label)

        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "editor", "name": "思维导图编辑"},
            {"id": "text2map", "name": "文本生成导图"},
            {"id": "templates", "name": "模板中心"},
        ]
