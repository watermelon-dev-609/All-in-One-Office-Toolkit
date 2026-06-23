"""Image Processing Module.

Handles: compression, watermark, crop/rotate/format, OCR, QR code,
background removal, ID photo, mosaic/filter.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal

from src.modules.base_module import BaseModule
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskItem

# Import workers
from src.modules.image_processing.compress_engine import CompressWorker
from src.modules.image_processing.watermark_engine import WatermarkWorker
from src.modules.image_processing.edit_engine import EditWorker
from src.modules.image_processing.ocr_engine import OCRWorker
from src.modules.image_processing.qrcode_engine import QRCodeWorker
from src.modules.image_processing.background_engine import BackgroundWorker
from src.modules.image_processing.idphoto_engine import IDPhotoWorker

# Register workers with TaskQueue
TaskQueue.register_worker("compress_image", CompressWorker)
TaskQueue.register_worker("add_watermark", WatermarkWorker)
TaskQueue.register_worker("edit_image", EditWorker)
TaskQueue.register_worker("ocr_image", OCRWorker)
TaskQueue.register_worker("qrcode", QRCodeWorker)
TaskQueue.register_worker("remove_background", BackgroundWorker)
TaskQueue.register_worker("id_photo", IDPhotoWorker)


class ImageProcessingModule(BaseModule):
    module_id = "image_processing"
    module_name = "图片处理"
    module_icon = "nav_image"
    module_order = 10
    category = "core"

    def create_main_view(self) -> QWidget:
        from src.modules.image_processing.views.compress_view import CompressView
        from src.modules.image_processing.views.watermark_view import WatermarkView
        from src.modules.image_processing.views.edit_view import EditView
        from src.modules.image_processing.views.ocr_view import OCRView
        from src.modules.image_processing.views.qrcode_view import QRCodeView
        from src.modules.image_processing.views.background_view import BackgroundView
        from src.modules.image_processing.views.idphoto_view import IDPhotoView

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget for sub-features
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)

        self._tabs.addTab(CompressView(), "📦 图片压缩")
        self._tabs.addTab(WatermarkView(), "💧 水印工具")
        self._tabs.addTab(EditView(), "✂️ 基础编辑")
        self._tabs.addTab(OCRView(), "📝 OCR 提取")
        self._tabs.addTab(QRCodeView(), "📱 二维码")
        self._tabs.addTab(BackgroundView(), "🎭 去背景")
        self._tabs.addTab(IDPhotoView(), "📷 证件照")

        layout.addWidget(self._tabs)
        return widget

    def get_sub_features(self) -> list[dict]:
        return [
            {"id": "compress", "name": "图片压缩"},
            {"id": "watermark", "name": "水印工具"},
            {"id": "edit", "name": "基础编辑"},
            {"id": "ocr", "name": "OCR 文字提取"},
            {"id": "qrcode", "name": "二维码工具"},
            {"id": "background", "name": "去背景"},
            {"id": "idphoto", "name": "证件照制作"},
        ]
