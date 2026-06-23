"""OCR (Optical Character Recognition) engine using EasyOCR.

Supports Chinese and English text extraction from images.
"""

from pathlib import Path
from typing import Optional

from PIL import Image
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


class OCRWorker(TaskWorker):
    """Worker for OCR text extraction from images."""

    def process(self) -> list[Path]:
        languages = self.task.params.get("languages", ["ch_sim", "en"])
        output_dir = self.task.params.get("output_dir", None)
        output_format = self.task.params.get("output_format", "txt")  # txt or json

        # Lazy-load EasyOCR (heavy import)
        import easyocr
        self.report_progress(5, "加载 OCR 模型...")
        reader = easyocr.Reader(languages, gpu=False)

        total = len(self.task.input_files)
        output_files = []

        for i, file_path in enumerate(self.task.input_files):
            self.check_pause()
            if self.is_cancelled:
                break

            src = Path(file_path)
            self.report_progress(
                int(10 + (i / total) * 85),
                f"OCR 识别: {src.name} ({i+1}/{total})"
            )

            try:
                # Run OCR
                results = reader.readtext(str(src), detail=1)

                if output_format == "json":
                    import json
                    data = [
                        {
                            "text": text,
                            "confidence": round(conf, 3),
                            "box": [[int(x), int(y)] for x, y in box],
                        }
                        for box, text, conf in results
                    ]
                    content = json.dumps(data, ensure_ascii=False, indent=2)
                    ext = ".json"
                else:
                    # Plain text
                    lines = [text for _, text, _ in results]
                    content = "\n".join(lines)
                    ext = ".txt"

                # Write output
                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = src.parent / "Output"
                out_dir.mkdir(parents=True, exist_ok=True)

                out_path = out_dir / f"{src.stem}_ocr{ext}"
                counter = 1
                while out_path.exists():
                    out_path = out_dir / f"{src.stem}_ocr_{counter}{ext}"
                    counter += 1

                out_path.write_text(content, encoding="utf-8")
                output_files.append(out_path)
                logger.debug(f"OCR: {src.name} -> {len(results)} text regions")

            except Exception as e:
                logger.error(f"OCR failed for {src.name}: {e}")

        self.report_progress(100, f"OCR 完成: {len(output_files)}/{total} 个文件")
        return output_files
