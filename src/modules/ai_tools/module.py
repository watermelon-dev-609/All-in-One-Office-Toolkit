"""AI Smart Tools Module."""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from src.modules.base_module import BaseModule


class AIToolsModule(BaseModule):
    module_id = "ai_tools"
    module_name = "AI 智能"
    module_icon = "nav_ai"
    module_order = 60
    category = "ai"

    def create_main_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("🧠 AI 智能工具\n\nAI 文案写作 · AI 图片处理\n语音转文字 · 翻译 · 简历优化")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("hintLabel")
        label.setStyleSheet("font-size: 15px; padding: 40px;")
        layout.addWidget(label)

        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "text_ai", "name": "AI 文案写作"},
            {"id": "image_ai", "name": "AI 图片处理"},
            {"id": "assistant", "name": "AI 多功能辅助"},
        ]
