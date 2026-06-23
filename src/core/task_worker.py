"""Base task worker for multi-threaded file processing.

Workers run in QThread and communicate progress via Qt signals.
"""

import uuid
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable
from enum import Enum

from PySide6.QtCore import QObject, Signal, QRunnable


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class TaskItem:
    """A single processing task in the queue."""
    task_type: str                          # e.g. "compress_image", "merge_pdf"
    input_files: list[Path]                 # Source files
    output_dir: Optional[Path] = None       # Override output directory
    params: dict = field(default_factory=dict)  # Engine-specific parameters
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    priority: int = 0                       # 0=normal, 1=high
    created_at: float = field(default_factory=time.time)

    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0                       # 0-100
    progress_message: str = ""
    result_files: list[Path] = field(default_factory=list)
    error_message: str = ""
    duration: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to dict for UI display."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "input_files": [str(f) for f in self.input_files],
            "status": self.status.value,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "error_message": self.error_message,
            "duration": self.duration,
        }


class TaskWorkerSignals(QObject):
    """Qt signals emitted by workers (thread-safe)."""

    started = Signal(str)                   # task_id
    progress = Signal(str, int, str)        # task_id, percent, message
    completed = Signal(str, list)           # task_id, output_paths (list[str])
    failed = Signal(str, str)               # task_id, error_message
    cancelled = Signal(str)                 # task_id


class TaskWorker(QRunnable):
    """Base class for all task workers.

    Subclasses override run() to perform the actual processing.
    Uses cooperative cancellation via threading.Event.
    """

    def __init__(self, task: TaskItem):
        super().__init__()
        self.task = task
        self.signals = TaskWorkerSignals()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially

    def run(self) -> None:
        """Execute the task. Called by QThreadPool."""
        self.task.status = TaskStatus.RUNNING
        self.signals.started.emit(self.task.task_id)

        start_time = time.time()

        try:
            result = self.process()
            self.task.status = TaskStatus.COMPLETED
            self.task.duration = time.time() - start_time
            self.task.result_files = result if isinstance(result, list) else []
            self.signals.completed.emit(
                self.task.task_id,
                [str(p) for p in self.task.result_files]
            )
        except Exception as e:
            self.task.status = TaskStatus.FAILED
            self.task.duration = time.time() - start_time
            self.task.error_message = str(e)
            self.signals.failed.emit(self.task.task_id, str(e))

    def process(self) -> Any:
        """Override in subclasses with actual processing logic.

        Returns:
            List of output file paths, or any result object.

        Raises:
            Exception: On processing failure.
        """
        raise NotImplementedError("Subclasses must implement process()")

    # ---- Cooperative control ----

    def cancel(self) -> None:
        """Request cancellation."""
        self._cancel_event.set()
        self._pause_event.set()  # Unpause so cancellation proceeds

    def pause(self) -> None:
        """Pause processing."""
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume processing."""
        self._pause_event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_event.is_set()

    def check_pause(self) -> None:
        """Block if paused. Call periodically in long-running loops."""
        self._pause_event.wait()

    def report_progress(self, percent: int, message: str = "") -> None:
        """Emit progress update."""
        self.task.progress = percent
        self.task.progress_message = message
        self.signals.progress.emit(self.task.task_id, percent, message)
