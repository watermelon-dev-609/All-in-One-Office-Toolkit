"""Watermark engine for adding text or image watermarks.

Supports text watermarks (font/size/color/opacity/position/rotation/tile)
and image watermarks (opacity/position/tile).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


class WatermarkWorker(TaskWorker):
    """Worker for batch watermark addition."""

    def process(self) -> list[Path]:
        watermark_type = self.task.params.get("watermark_type", "text")
        opacity = self.task.params.get("opacity", 0.3)
        position = self.task.params.get("position", "center")  # center, tl, tr, bl, br, tile
        rotation = self.task.params.get("rotation", 0)
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
                f"添加水印: {src.name} ({i+1}/{total})"
            )

            try:
                img = Image.open(src).convert("RGBA")

                if watermark_type == "text":
                    text = self.task.params.get("watermark_text", "Watermark")
                    font_size = self.task.params.get("font_size", 36)
                    font_color = self.task.params.get("font_color", (255, 255, 255))
                    result = self._add_text_watermark(
                        img, text, font_size, font_color, opacity, position, rotation
                    )
                else:
                    watermark_path = self.task.params.get("watermark_image", "")
                    if not watermark_path:
                        raise ValueError("No watermark image specified")
                    wm_img = Image.open(watermark_path).convert("RGBA")
                    wm_size = self.task.params.get("watermark_size", 0.2)  # Ratio of source
                    result = self._add_image_watermark(
                        img, wm_img, wm_size, opacity, position, rotation
                    )

                # Save
                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = src.parent / "Output"
                out_dir.mkdir(parents=True, exist_ok=True)

                out_path = out_dir / f"{src.stem}_watermarked{src.suffix}"
                counter = 1
                while out_path.exists():
                    out_path = out_dir / f"{src.stem}_watermarked_{counter}{src.suffix}"
                    counter += 1

                # Convert back to original mode for saving
                if src.suffix.lower() in (".jpg", ".jpeg"):
                    result = result.convert("RGB")
                result.save(out_path)
                output_files.append(out_path)

            except Exception as e:
                logger.error(f"Watermark failed for {src.name}: {e}")

        self.report_progress(100, f"完成 {len(output_files)}/{total} 个文件")
        return output_files

    def _add_text_watermark(
        self,
        img: Image.Image,
        text: str,
        font_size: int,
        font_color: tuple,
        opacity: float,
        position: str,
        rotation: int,
    ) -> Image.Image:
        """Add text watermark to image."""
        # Create watermark layer
        wm_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(wm_layer)

        # Load font
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)  # Microsoft YaHei
        except (IOError, OSError):
            try:
                font = ImageFont.truetype("simhei.ttf", font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if position == "tile":
            # Tile text across image
            spacing_x = text_w + 100
            spacing_y = text_h + 80
            for y in range(0, img.height + spacing_y, spacing_y):
                for x in range(0, img.width + spacing_x, spacing_x):
                    draw.text((x, y), text, font=font, fill=(*font_color[:3], int(255 * opacity)))
        else:
            # Position at specific corner
            pos_map = {
                "tl": (20, 20),
                "tr": (img.width - text_w - 20, 20),
                "bl": (20, img.height - text_h - 20),
                "br": (img.width - text_w - 20, img.height - text_h - 20),
                "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
            }
            x, y = pos_map.get(position, pos_map["center"])

            # Draw with rotation if needed
            if rotation != 0:
                txt_img = Image.new("RGBA", (text_w + 100, text_h + 100), (0, 0, 0, 0))
                txt_draw = ImageDraw.Draw(txt_img)
                txt_draw.text((50, 50), text, font=font, fill=(*font_color[:3], int(255 * opacity)))
                txt_img = txt_img.rotate(rotation, expand=True, resample=Image.BICUBIC)
                wm_layer.paste(txt_img, (x - 50, y - 50), txt_img)
            else:
                draw.text((x, y), text, font=font, fill=(*font_color[:3], int(255 * opacity)))

        # Composite
        return Image.alpha_composite(img, wm_layer)

    def _add_image_watermark(
        self,
        img: Image.Image,
        wm_img: Image.Image,
        wm_size: float,
        opacity: float,
        position: str,
        rotation: int,
    ) -> Image.Image:
        """Add image watermark to image."""
        # Resize watermark
        target_w = int(img.width * wm_size)
        ratio = target_w / wm_img.width
        target_h = int(wm_img.height * ratio)
        wm_img = wm_img.resize((target_w, target_h), Image.LANCZOS)

        # Apply opacity
        if opacity < 1.0:
            alpha = wm_img.split()[3] if wm_img.mode == "RGBA" else None
            if alpha:
                alpha = alpha.point(lambda p: int(p * opacity))
                wm_img.putalpha(alpha)

        # Rotate
        if rotation != 0:
            wm_img = wm_img.rotate(rotation, expand=True, resample=Image.BICUBIC)

        # Position
        pos_map = {
            "tl": (20, 20),
            "tr": (img.width - wm_img.width - 20, 20),
            "bl": (20, img.height - wm_img.height - 20),
            "br": (img.width - wm_img.width - 20, img.height - wm_img.height - 20),
            "center": ((img.width - wm_img.width) // 2, (img.height - wm_img.height) // 2),
        }
        x, y = pos_map.get(position, pos_map["center"])

        wm_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        wm_layer.paste(wm_img, (x, y), wm_img)

        return Image.alpha_composite(img, wm_layer)
