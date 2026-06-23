"""Unified export pipeline service.

Supports chaining multiple operations together for workflow automation.
"""

from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ExportStep:
    """A single step in an export pipeline."""
    name: str
    handler: Callable[[list[Path], dict], list[Path]]
    params: dict = field(default_factory=dict)


class ExportService:
    """Coordinates multi-step export pipelines.

    Example:
        pipeline = ExportService()
        pipeline.add_step("compress", compress_handler, {"quality": 85})
        pipeline.add_step("watermark", watermark_handler, {"text": "机密"})
        results = pipeline.run(input_files)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._steps = []
        return cls._instance

    def add_step(self, name: str, handler: Callable, params: dict = None) -> None:
        """Add a processing step to the pipeline."""
        self._steps.append(ExportStep(
            name=name,
            handler=handler,
            params=params or {},
        ))
        logger.debug(f"Export step added: {name}")

    def clear_steps(self) -> None:
        """Remove all steps."""
        self._steps.clear()

    def run(
        self,
        input_files: list[Path],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[Path]:
        """Execute all steps in sequence.

        Args:
            input_files: Initial list of file paths.
            progress_callback: Called with (current_step, total_steps, step_name).

        Returns:
            Final list of output file paths.
        """
        files = list(input_files)
        total = len(self._steps)

        for i, step in enumerate(self._steps):
            if progress_callback:
                progress_callback(i + 1, total, step.name)

            logger.info(f"Export step [{i+1}/{total}]: {step.name}")
            try:
                files = step.handler(files, step.params)
            except Exception as e:
                logger.error(f"Export step '{step.name}' failed: {e}")
                raise

        return files

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def get_pipeline_description(self) -> list[str]:
        """Return human-readable step names."""
        return [step.name for step in self._steps]
