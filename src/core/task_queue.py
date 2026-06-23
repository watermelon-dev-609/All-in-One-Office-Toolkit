"""Multi-threaded task queue with pause/resume/cancel support.

The central execution engine of the application. All file processing
goes through this queue, which manages worker threads and provides
progress reporting via Qt signals.

Architecture:
    TaskQueue (QObject, singleton)
    ├── _pending: deque[TaskItem]        # Waiting tasks
    ├── _active: dict[str, TaskWorker]   # Running workers
    ├── _history: deque[TaskItem]        # Completed/failed tasks
    └── _pool: QThreadPool              # Qt thread pool

Usage:
    queue = TaskQueue()
    task = TaskItem(task_type="compress_image", input_files=[...], params={...})
    queue.submit(task)
    queue.task_completed.connect(on_done)
"""

import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal, QThreadPool
from loguru import logger

from src.core.task_worker import TaskItem, TaskStatus, TaskWorker


MAX_HISTORY = 500  # Max completed tasks to retain
DEFAULT_MAX_THREADS = max(1, os.cpu_count() - 1) if os.cpu_count() else 4


class TaskQueue(QObject):
    """Central task execution queue with lifecycle management."""

    # Signals (thread-safe)
    task_submitted = Signal(str)            # task_id
    task_started = Signal(str)              # task_id
    task_progress = Signal(str, int, str)   # task_id, percent, message
    task_completed = Signal(str, list)      # task_id, output_paths
    task_failed = Signal(str, str)          # task_id, error_message
    task_cancelled = Signal(str)            # task_id
    queue_changed = Signal()                # Any change to queue state

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._pending: deque[TaskItem] = deque()
        self._active: dict[str, TaskWorker] = {}
        self._history: deque[TaskItem] = deque(maxlen=MAX_HISTORY)
        self._pool = QThreadPool.globalInstance()
        self._max_threads = DEFAULT_MAX_THREADS
        self._paused = False
        self._initialized = True

        self._pool.setMaxThreadCount(self._max_threads)
        logger.info(f"TaskQueue initialized (max threads: {self._max_threads})")

    # ---- Task Management ----

    def submit(self, task: TaskItem) -> str:
        """Submit a task to the queue. Returns task_id."""
        task.status = TaskStatus.PENDING
        self._pending.append(task)
        self.task_submitted.emit(task.task_id)
        self.queue_changed.emit()
        logger.debug(f"Task submitted: {task.task_id} ({task.task_type})")

        # Try to dispatch immediately
        self._dispatch()
        return task.task_id

    def submit_batch(self, tasks: list[TaskItem]) -> list[str]:
        """Submit multiple tasks at once."""
        ids = []
        for task in tasks:
            ids.append(self.submit(task))
        return ids

    def cancel(self, task_id: str) -> bool:
        """Cancel a task by ID. Returns True if found."""
        # Check pending queue
        for task in self._pending:
            if task.task_id == task_id:
                task.status = TaskStatus.CANCELLED
                self._pending.remove(task)
                self._history.append(task)
                self.task_cancelled.emit(task_id)
                self.queue_changed.emit()
                logger.info(f"Task cancelled (pending): {task_id}")
                return True

        # Check active tasks
        worker = self._active.get(task_id)
        if worker:
            worker.cancel()
            logger.info(f"Cancellation requested: {task_id}")
            return True

        logger.warning(f"Task not found for cancellation: {task_id}")
        return False

    def cancel_all(self) -> None:
        """Cancel all pending and active tasks."""
        # Cancel pending
        for task in list(self._pending):
            self.cancel(task.task_id)

        # Cancel active
        for task_id in list(self._active.keys()):
            self.cancel(task_id)

    def pause(self) -> None:
        """Pause all active tasks."""
        self._paused = True
        for worker in self._active.values():
            worker.pause()
        logger.info("Task queue paused")

    def resume(self) -> None:
        """Resume all paused tasks."""
        self._paused = False
        for worker in self._active.values():
            worker.resume()
        self._dispatch()
        logger.info("Task queue resumed")

    def clear_history(self) -> None:
        """Remove completed/failed tasks from history."""
        self._history.clear()
        self.queue_changed.emit()

    # ---- Query ----

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        """Find a task by ID across all collections."""
        for task in self._pending:
            if task.task_id == task_id:
                return task
        worker = self._active.get(task_id)
        if worker:
            return worker.task
        for task in self._history:
            if task.task_id == task_id:
                return task
        return None

    def get_pending_tasks(self) -> list[TaskItem]:
        return list(self._pending)

    def get_active_tasks(self) -> list[TaskItem]:
        return [w.task for w in self._active.values()]

    def get_history(self, limit: int = 50) -> list[TaskItem]:
        items = list(self._history)
        return items[-limit:]

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def max_threads(self) -> int:
        return self._max_threads

    @max_threads.setter
    def max_threads(self, value: int) -> None:
        self._max_threads = max(1, min(value, 32))
        self._pool.setMaxThreadCount(self._max_threads)

    # ---- Internal ----

    def _dispatch(self) -> None:
        """Try to start pending tasks if slots are available."""
        while self._pending and len(self._active) < self._max_threads:
            if self._paused:
                break

            task = self._pending.popleft()

            # Create worker
            worker = self._create_worker(task)
            if worker is None:
                task.status = TaskStatus.FAILED
                task.error_message = f"No worker for task type: {task.task_type}"
                self._history.append(task)
                self.task_failed.emit(task.task_id, task.error_message)
                continue

            # Connect signals
            worker.signals.started.connect(self._on_task_started)
            worker.signals.progress.connect(self._on_task_progress)
            worker.signals.completed.connect(self._on_task_completed)
            worker.signals.failed.connect(self._on_task_failed)
            worker.signals.cancelled.connect(self._on_task_cancelled)

            # Track and start
            self._active[task.task_id] = worker
            self._pool.start(worker)

    def _create_worker(self, task: TaskItem) -> Optional[TaskWorker]:
        """Factory method — maps task_type to worker class.

        Override/replace via TaskQueue.register_worker_factory().
        """
        factory = self._worker_factories.get(task.task_type)
        if factory:
            return factory(task)
        logger.error(f"No worker factory registered for '{task.task_type}'")
        return None

    _worker_factories: dict[str, Callable[[TaskItem], TaskWorker]] = {}

    @classmethod
    def register_worker(cls, task_type: str, factory: Callable[[TaskItem], TaskWorker]) -> None:
        """Register a worker factory for a task type.

        Args:
            task_type: e.g. 'compress_image', 'merge_pdf'.
            factory: A callable that takes a TaskItem and returns a TaskWorker.
        """
        cls._worker_factories[task_type] = factory
        logger.debug(f"Worker registered: {task_type}")

    # ---- Signal handlers ----

    def _on_task_started(self, task_id: str) -> None:
        logger.debug(f"Task started: {task_id}")
        self.task_started.emit(task_id)
        self.queue_changed.emit()

    def _on_task_progress(self, task_id: str, percent: int, message: str) -> None:
        self.task_progress.emit(task_id, percent, message)

    def _on_task_completed(self, task_id: str, output_paths: list) -> None:
        worker = self._active.pop(task_id, None)
        if worker:
            task = worker.task
            task.status = TaskStatus.COMPLETED
            task.result_files = [Path(p) for p in output_paths]
            self._history.append(task)
        logger.info(f"Task completed: {task_id}")
        self.task_completed.emit(task_id, output_paths)
        self.queue_changed.emit()
        self._dispatch()  # Start next pending task

    def _on_task_failed(self, task_id: str, error: str) -> None:
        worker = self._active.pop(task_id, None)
        if worker:
            task = worker.task
            task.status = TaskStatus.FAILED
            task.error_message = error
            self._history.append(task)
        logger.error(f"Task failed: {task_id} - {error}")
        self.task_failed.emit(task_id, error)
        self.queue_changed.emit()
        self._dispatch()

    def _on_task_cancelled(self, task_id: str) -> None:
        worker = self._active.pop(task_id, None)
        if worker:
            task = worker.task
            task.status = TaskStatus.CANCELLED
            self._history.append(task)
        logger.info(f"Task cancelled: {task_id}")
        self.task_cancelled.emit(task_id)
        self.queue_changed.emit()
        self._dispatch()
