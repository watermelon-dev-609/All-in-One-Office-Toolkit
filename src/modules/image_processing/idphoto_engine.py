"""ID Photo engine.

Handles: face detection, standard size crop, background color replacement,
brightness/contrast adjustment.
"""

from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


# Standard Chinese ID photo sizes (mm)
ID_PHOTO_SIZES = {
    "1inch": (25, 35),       # 一寸
    "2inch": (35, 49),       # 二寸
    "small_1inch": (22, 32),  # 小一寸
    "large_2inch": (35, 53),  # 大二寸
    "passport": (33, 48),     # 护照
    "visa_us": (51, 51),      # 美国签证
}


class IDPhotoWorker(TaskWorker):
    """Worker for ID photo processing."""

    def process(self) -> list[Path]:
        operation = self.task.params.get("operation", "make")
        output_dir = self.task.params.get("output_dir", None)

        total = len(self.task.input_files)
        output_files = []

        for i, file_path in enumerate(self.task.input_files):
            self.check_pause()
            if self.is_cancelled:
                break

            src = Path(file_path)
            self.report_progress(
                int((i / total) * 100),
                f"证件照处理: {src.name} ({i+1}/{total})"
            )

            try:
                img = Image.open(src).convert("RGB")
                opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                if operation == "make":
                    result = self._make_id_photo(img, opencv_img)
                elif operation == "change_bg":
                    result = self._change_background(img, opencv_img)
                elif operation == "adjust":
                    result = self._adjust(img)
                else:
                    raise ValueError(f"Unknown operation: {operation}")

                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = src.parent / "Output"
                out_dir.mkdir(parents=True, exist_ok=True)

                out_path = out_dir / f"{src.stem}_idphoto.png"
                counter = 1
                while out_path.exists():
                    out_path = out_dir / f"{src.stem}_idphoto_{counter}.png"
                    counter += 1

                result.save(out_path)
                output_files.append(out_path)

            except Exception as e:
                logger.error(f"ID photo processing failed for {src.name}: {e}")

        self.report_progress(100, f"完成 {len(output_files)}/{total} 个文件")
        return output_files

    def _make_id_photo(self, img: Image.Image, cv_img: np.ndarray) -> Image.Image:
        """Detect face, crop to standard size, replace background."""
        size_key = self.task.params.get("photo_size", "1inch")
        bg_color = self.task.params.get("background_color", "white")
        bg_colors = {
            "white": (255, 255, 255),
            "red": (219, 60, 68),
            "blue": (67, 142, 219),
            "light_blue": (135, 206, 250),
        }
        bg_rgb = bg_colors.get(bg_color, (255, 255, 255))

        photo_mm = ID_PHOTO_SIZES.get(size_key, (25, 35))
        # Convert mm to pixels at 300 DPI
        dpi = 300
        mm_to_px = dpi / 25.4
        target_w = int(photo_mm[0] * mm_to_px)
        target_h = int(photo_mm[1] * mm_to_px)

        # Face detection
        face = self._detect_face(cv_img)
        if face is None:
            logger.warning("No face detected, using center crop")
            # Centered crop fallback
            result = self._center_crop(img, target_w, target_h)
        else:
            fx, fy, fw, fh = face
            # Expand region to include shoulders
            expand = 1.8
            center_x, center_y = fx + fw // 2, fy + fh // 2

            # The face area should be ~2/3 of the photo height
            crop_h = int(fh * 2.5)
            crop_w = int(crop_h * (target_w / target_h))

            crop_x1 = max(0, center_x - crop_w // 2)
            crop_y1 = max(0, center_y - int(crop_h * 0.4))  # 40% above face center
            crop_x2 = min(img.width, crop_x1 + crop_w)
            crop_y2 = min(img.height, crop_y1 + crop_h)

            # Adjust if out of bounds
            if crop_x2 - crop_x1 < crop_w:
                crop_x1 = max(0, crop_x2 - crop_w)
            if crop_y2 - crop_y1 < crop_h:
                crop_y1 = max(0, crop_y2 - crop_h)

            cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            result = cropped.resize((target_w, target_h), Image.LANCZOS)

        # Replace background (simple implementation: fill with color)
        bg_layer = Image.new("RGB", (target_w, target_h), bg_rgb)

        # Try to mask the person from the background
        result = self._simple_bg_replace(result, bg_rgb)

        return result

    def _change_background(self, img: Image.Image, cv_img: np.ndarray) -> Image.Image:
        """Change the background color of an existing ID photo."""
        bg_color = self.task.params.get("background_color", "white")
        bg_colors = {
            "white": (255, 255, 255),
            "red": (219, 60, 68),
            "blue": (67, 142, 219),
            "light_blue": (135, 206, 250),
        }
        bg_rgb = bg_colors.get(bg_color, (255, 255, 255))
        return self._simple_bg_replace(img, bg_rgb)

    def _adjust(self, img: Image.Image) -> Image.Image:
        """Adjust brightness, contrast, color of ID photo."""
        brightness = self.task.params.get("brightness", 1.0)
        contrast = self.task.params.get("contrast", 1.0)
        saturation = self.task.params.get("saturation", 1.0)

        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation)

        return img

    def _detect_face(self, cv_img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Detect the largest face in the image.

        Returns (x, y, w, h) or None.
        """
        # Try OpenCV DNN face detector first
        try:
            # Use Haar cascade as a simple default
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)

            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )

            if len(faces) > 0:
                # Return the largest face
                largest = max(faces, key=lambda f: f[2] * f[3])
                return tuple(largest)
        except Exception as e:
            logger.debug(f"Haar cascade failed: {e}")

        return None

    def _center_crop(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Crop from center with target aspect ratio."""
        ratio = target_w / target_h
        w, h = img.size

        if w / h > ratio:
            new_w = int(h * ratio)
            new_h = h
            x = (w - new_w) // 2
            y = 0
        else:
            new_w = w
            new_h = int(w / ratio)
            x = 0
            y = (h - new_h) // 2

        cropped = img.crop((x, y, x + new_w, y + new_h))
        return cropped.resize((target_w, target_h), Image.LANCZOS)

    def _simple_bg_replace(self, img: Image.Image, bg_color: Tuple[int, int, int]) -> Image.Image:
        """Simple background replacement using edge-based approach."""
        cv_img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

        # GrabCut-based segmentation
        mask = np.zeros(cv_img.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        h, w = cv_img.shape[:2]
        margin = int(min(w, h) * 0.05)
        rect = (margin, margin, w - 2 * margin, h - 2 * margin)

        try:
            cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

            # Smooth mask edges
            mask2 = cv2.GaussianBlur(mask2, (5, 5), 0)

            # Apply new background
            result = cv_img.copy()
            bg = np.full_like(cv_img, bg_color[::-1], dtype=np.uint8)  # BGR
            for c in range(3):
                result[:, :, c] = cv_img[:, :, c] * mask2 + bg[:, :, c] * (1 - mask2)

            return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

        except cv2.error as e:
            logger.debug(f"GrabCut failed, returning original: {e}")
            return img
