"""PDF Tools Module.

Handles: merge, split, page operations, compress, encrypt/decrypt,
watermark, text/image extraction, signature, format conversion.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from src.modules.base_module import BaseModule


class PDFToolsModule(BaseModule):
    module_id = "pdf_tools"
    module_name = "PDF 工具"
    module_icon = "nav_pdf"
    module_order = 20
    category = "core"

    def create_main_view(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("📄 PDF 全能工具\n\n合并 · 拆分 · 页面操作 · 压缩\n加密 · 水印 · 提取 · 签名 · 格式转换")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("hintLabel")
        label.setStyleSheet("font-size: 15px; padding: 40px;")
        layout.addWidget(label)

        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "merge", "name": "PDF 合并"},
            {"id": "split", "name": "PDF 拆分"},
            {"id": "page_ops", "name": "页面操作"},
            {"id": "compress", "name": "PDF 压缩"},
            {"id": "security", "name": "加密解密"},
            {"id": "watermark", "name": "PDF 水印"},
            {"id": "extract", "name": "内容提取"},
            {"id": "signature", "name": "PDF 签名"},
            {"id": "convert", "name": "格式转换"},
        ]
