"""Background removal engine using rembg (RMBG-1.4 ONNX model)."""

from pathlib import Path
from typing import Optional

from PIL import Image
from loguru import logger

from src.core.task_worker import TaskItem, TaskWorker


class BackgroundWorker(TaskWorker):
    """Worker for AI-powered background removal."""

    def process(self) -> list[Path]:
        output_dir = self.task.params.get("output_dir", None)
        make_white_bg = self.task.params.get("make_white_bg", False)
        alpha_matting = self.task.params.get("alpha_matting", False)

        from rembg import remove, new_session

        model_name = self.task.params.get("model", "u2net")
        self.report_progress(5, "加载去背景模型...")
        session = new_session(model_name)

        total = len(self.task.input_files)
        output_files = []

        for i, file_path in enumerate(self.task.input_files):
            self.check_pause()
            if self.is_cancelled:
                break

            src = Path(file_path)
            self.report_progress(
                int(10 + (i / total) * 85),
                f"去除背景: {src.name} ({i+1}/{total})"
            )

            try:
                img = Image.open(src)

                # Remove background
                result = remove(
                    img,
                    session=session,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=10,
                )

                if make_white_bg:
                    # Composite on white background
                    white_bg = Image.new("RGB", result.size, (255, 255, 255))
                    white_bg.paste(result, mask=result.split()[3] if result.mode == "RGBA" else None)
                    result = white_bg
                    ext = ".png"
                else:
                    ext = ".png"  # Always PNG for transparency

                # Save
                if output_dir:
                    out_dir = Path(output_dir)
                else:
                    out_dir = src.parent / "Output"
                out_dir.mkdir(parents=True, exist_ok=True)

                suffix = "_nobg" if not make_white_bg else "_whitebg"
                out_path = out_dir / f"{src.stem}{suffix}{ext}"
                counter = 1
                while out_path.exists():
                    out_path = out_dir / f"{src.stem}{suffix}_{counter}{ext}"
                    counter += 1

                result.save(out_path)
                output_files.append(out_path)
                logger.debug(f"Background removed: {src.name}")

            except Exception as e:
                logger.error(f"Background removal failed for {src.name}: {e}")

        self.report_progress(100, f"去背景完成: {len(output_files)}/{total} 个文件")
        return output_files
