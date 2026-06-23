"""Image editing engine.

Handles: format conversion, crop, rotate, flip, resize, mosaic/pixelate.
"""

from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


class EditWorker(TaskWorker):
    """Worker for batch image editing operations."""

    def process(self) -> list[Path]:
        operation = self.task.params.get("operation", "convert")
        output_dir = self.task.params.get("output_dir", None)

        total = len(self.task.input_files)
        output_files = []

        ops = {
            "convert": self._convert_format,
            "crop": self._crop,
            "rotate": self._rotate,
            "flip": self._flip,
            "resize": self._resize,
            "mosaic": self._mosaic,
        }

        handler = ops.get(operation)
        if handler is None:
            raise ValueError(f"Unknown edit operation: {operation}")

        for i, file_path in enumerate(self.task.input_files):
            self.check_pause()
            if self.is_cancelled:
                break

            src = Path(file_path)
            self.report_progress(
                int((i / total) * 100),
                f"{operation}: {src.name} ({i+1}/{total})"
            )

            try:
                output = handler(src, output_dir)
                output_files.append(output)
            except Exception as e:
                logger.error(f"Edit '{operation}' failed for {src.name}: {e}")

        self.report_progress(100, f"完成 {len(output_files)}/{total} 个文件")
        return output_files

    # ---- Operations ----

    def _convert_format(self, src: Path, output_dir: Optional[str]) -> Path:
        """Convert image to a different format."""
        target_format = self.task.params.get("target_format", "png")
        img = Image.open(src)

        out_dir = self._get_out_dir(src, output_dir)
        ext = f".{target_format.lower()}"
        out_path = out_dir / f"{src.stem}_converted{ext}"
        out_path = self._unique_path(out_path)

        if img.mode in ("RGBA", "P", "LA") and target_format.lower() in ("jpg", "jpeg"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg

        img.save(out_path)
        return out_path

    def _crop(self, src: Path, output_dir: Optional[str]) -> Path:
        """Crop image to specified box (left, top, right, bottom)."""
        crop_box = self.task.params.get("crop_box")
        if not crop_box or len(crop_box) != 4:
            raise ValueError("crop_box requires [left, top, right, bottom]")

        img = Image.open(src)
        cropped = img.crop(tuple(crop_box))

        out_dir = self._get_out_dir(src, output_dir)
        out_path = out_dir / f"{src.stem}_cropped{src.suffix}"
        out_path = self._unique_path(out_path)
        cropped.save(out_path)
        return out_path

    def _rotate(self, src: Path, output_dir: Optional[str]) -> Path:
        """Rotate image by specified angle."""
        angle = self.task.params.get("angle", 90)
        expand = self.task.params.get("expand", True)

        img = Image.open(src)
        rotated = img.rotate(angle, expand=expand, resample=Image.BICUBIC)

        out_dir = self._get_out_dir(src, output_dir)
        out_path = out_dir / f"{src.stem}_rotated{src.suffix}"
        out_path = self._unique_path(out_path)
        rotated.save(out_path)
        return out_path

    def _flip(self, src: Path, output_dir: Optional[str]) -> Path:
        """Flip image horizontally or vertically."""
        direction = self.task.params.get("direction", "horizontal")

        img = Image.open(src)
        if direction == "horizontal":
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
        elif direction == "vertical":
            flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
        else:
            raise ValueError(f"Invalid flip direction: {direction}")

        out_dir = self._get_out_dir(src, output_dir)
        out_path = out_dir / f"{src.stem}_flipped{src.suffix}"
        out_path = self._unique_path(out_path)
        flipped.save(out_path)
        return out_path

    def _resize(self, src: Path, output_dir: Optional[str]) -> Path:
        """Resize image to specific dimensions."""
        width = self.task.params.get("width", 0)
        height = self.task.params.get("height", 0)
        keep_ratio = self.task.params.get("keep_ratio", True)

        if width <= 0 and height <= 0:
            raise ValueError("width or height must be > 0")

        img = Image.open(src)
        orig_w, orig_h = img.size

        if keep_ratio:
            if width > 0 and height > 0:
                # Fit within box
                ratio = min(width / orig_w, height / orig_h)
                new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
            elif width > 0:
                ratio = width / orig_w
                new_w, new_h = width, int(orig_h * ratio)
            else:
                ratio = height / orig_h
                new_w, new_h = int(orig_w * ratio), height
        else:
            new_w = width if width > 0 else orig_w
            new_h = height if height > 0 else orig_h

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        out_dir = self._get_out_dir(src, output_dir)
        out_path = out_dir / f"{src.stem}_resized{src.suffix}"
        out_path = self._unique_path(out_path)
        resized.save(out_path)
        return out_path

    def _mosaic(self, src: Path, output_dir: Optional[str]) -> Path:
        """Apply pixelation/mosaic effect to image."""
        pixel_size = self.task.params.get("pixel_size", 10)
        region = self.task.params.get("region")  # Optional [left, top, right, bottom]

        img = Image.open(src)

        if region and len(region) == 4:
            # Mosaic only a region
            small = img.crop(tuple(region))
            small_w, small_h = small.size
            mosaic = small.resize(
                (max(1, small_w // pixel_size), max(1, small_h // pixel_size)),
                Image.NEAREST
            ).resize((small_w, small_h), Image.NEAREST)
            img_rgba = img.convert("RGBA")
            mosaic_rgba = mosaic.convert("RGBA")
            img_rgba.paste(mosaic_rgba, tuple(region))
            img = img_rgba
        else:
            # Mosaic entire image
            w, h = img.size
            img = img.resize(
                (max(1, w // pixel_size), max(1, h // pixel_size)),
                Image.NEAREST
            ).resize((w, h), Image.NEAREST)

        out_dir = self._get_out_dir(src, output_dir)
        out_path = out_dir / f"{src.stem}_mosaic{src.suffix}"
        out_path = self._unique_path(out_path)

        if src.suffix.lower() in (".jpg", ".jpeg") and img.mode == "RGBA":
            img = img.convert("RGB")

        img.save(out_path)
        return out_path

    # ---- Helpers ----

    def _get_out_dir(self, src: Path, output_dir: Optional[str]) -> Path:
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = src.parent / "Output"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        stem, ext = path.stem, path.suffix
        counter = 1
        while (new_path := path.parent / f"{stem}_{counter}{ext}").exists():
            counter += 1
        return new_path
