"""Image compression engine.

Supports JPG, PNG, WebP, GIF with lossless/lossy modes,
custom quality, and resolution scaling.
"""

import os
from pathlib import Path
from typing import Optional

from PIL import Image
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


class CompressWorker(TaskWorker):
    """Worker for batch image compression."""

    def process(self) -> list[Path]:
        quality = self.task.params.get("quality", 85)
        max_width = self.task.params.get("max_width", 0)  # 0 = no resize
        max_height = self.task.params.get("max_height", 0)
        output_format = self.task.params.get("output_format", "")  # Keep original
        lossless = self.task.params.get("lossless", False)
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
                f"压缩中: {src.name} ({i+1}/{total})"
            )

            try:
                output = self._compress_one(
                    src, quality, max_width, max_height,
                    output_format, lossless, output_dir
                )
                output_files.append(output)
            except Exception as e:
                logger.error(f"Compress failed for {src.name}: {e}")
                # Continue with next file

        self.report_progress(100, f"完成 {len(output_files)}/{total} 个文件")
        return output_files

    def _compress_one(
        self,
        src: Path,
        quality: int,
        max_width: int,
        max_height: int,
        output_format: str,
        lossless: bool,
        output_dir: Optional[str],
    ) -> Path:
        """Compress a single image file."""
        img = Image.open(src)
        original_size = src.stat().st_size

        # Handle transparency
        if img.mode in ("RGBA", "P", "LA"):
            if output_format.lower() in ("jpg", "jpeg"):
                # JPEG doesn't support alpha; convert to RGB
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background

        # Resize if needed
        if max_width > 0 or max_height > 0:
            w, h = img.size
            if max_width > 0 and w > max_width:
                ratio = max_width / w
                w, h = max_width, int(h * ratio)
            if max_height > 0 and h > max_height:
                ratio = max_height / h
                w, h = int(w * ratio), max_height
            if (w, h) != img.size:
                img = img.resize((w, h), Image.LANCZOS)

        # Determine output path and format
        fmt = output_format.lower().lstrip(".") if output_format else src.suffix.lstrip(".")
        if fmt in ("jpg", "jpeg"):
            fmt = "JPEG"
        elif fmt in ("webp",):
            fmt = "WEBP"
        else:
            fmt = fmt.upper()

        ext = ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"

        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = src.parent / "Output"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / f"{src.stem}_compressed{ext}"
        counter = 1
        while out_path.exists():
            out_path = out_dir / f"{src.stem}_compressed_{counter}{ext}"
            counter += 1

        # Save
        save_kwargs = {}
        if fmt == "JPEG":
            save_kwargs = {"quality": quality, "optimize": True}
        elif fmt == "PNG":
            save_kwargs = {"optimize": True}
        elif fmt == "WEBP":
            save_kwargs = {"quality": quality, "method": 6}
        elif fmt == "GIF":
            save_kwargs = {"optimize": True}

        if lossless and fmt in ("JPEG", "WEBP"):
            save_kwargs["lossless"] = True

        img.save(out_path, **save_kwargs)

        compressed_size = out_path.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        logger.debug(
            f"Compressed: {src.name} {original_size/1024:.0f}KB -> "
            f"{compressed_size/1024:.0f}KB ({ratio:.1f}% reduced)"
        )

        return out_path
