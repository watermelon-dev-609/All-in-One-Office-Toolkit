"""Task progress widget with output file tracking and quick-access."""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QProgressBar, QLabel, QHeaderView, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor

from src.core.i18n_manager import tr
from src.core.task_worker import TaskStatus


class TaskProgressWidget(QWidget):
    """Displays the task queue with progress bars and output access."""

    open_output_requested = Signal(str, list)  # task_id, output_paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: dict[str, QTreeWidgetItem] = {}
        self._progress_bars: dict[str, QProgressBar] = {}
        self._output_dirs: dict[str, str] = {}
        self._output_paths: dict[str, list] = {}
        self._is_paused = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        self._title_label = QLabel(tr("task.empty"))
        self._title_label.setObjectName("sectionTitle")
        header.addWidget(self._title_label)
        header.addStretch()

        self._pause_btn = QPushButton(tr("task.pause"))
        self._pause_btn.setFixedHeight(28)
        header.addWidget(self._pause_btn)

        self._cancel_all_btn = QPushButton(tr("task.cancel"))
        self._cancel_all_btn.setFixedHeight(28)
        header.addWidget(self._cancel_all_btn)

        self._clear_btn = QPushButton(tr("task.clear"))
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.clicked.connect(self.clear_completed)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)

        # Task tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["文件名 / 输出", "状态", "进度", "操作"])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        h = self._tree.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Fixed)
        h.resizeSection(1, 72)
        h.setSectionResizeMode(2, QHeaderView.Fixed)
        h.resizeSection(2, 140)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        h.resizeSection(3, 60)

        layout.addWidget(self._tree, 1)

    # ── Public API ────────────────────────────────────────────

    def add_task(self, task_id: str, task_type: str, filename: str,
                 output_dir: str = "") -> None:
        """Add a task row. output_dir is shown for context."""
        if task_id in self._rows:
            return

        item = QTreeWidgetItem()
        item.setText(0, filename)
        # Show output hint in column 0 tooltip
        if output_dir:
            item.setToolTip(0, f"输出目录: {output_dir}")
        self._output_dirs[task_id] = output_dir

        item.setText(1, tr("task.status.pending"))
        item.setText(3, "—")

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setFixedHeight(18)
        progress.setFormat("")

        self._tree.addTopLevelItem(item)
        self._tree.setItemWidget(item, 2, progress)

        self._rows[task_id] = item
        self._progress_bars[task_id] = progress
        self._update_title()

    def update_progress(self, task_id: str, percent: int, message: str = "") -> None:
        item = self._rows.get(task_id)
        progress = self._progress_bars.get(task_id)
        if item and progress:
            progress.setValue(percent)
            item.setText(1, tr("task.status.running"))
            if message:
                item.setToolTip(0, message)

    def set_output_path(self, task_id: str, output_paths: list) -> None:
        """Store output paths and update the row display."""
        self._output_paths[task_id] = output_paths
        item = self._rows.get(task_id)
        if item and output_paths:
            first = Path(output_paths[0])
            item.setText(0, f"✓ {first.name}")
            item.setToolTip(0, str(first))
            item.setText(3, "打开 ▶")
            # Style: make it look clickable
            item.setForeground(3, Qt.GlobalColor(0))  # will inherit accent from QSS :selected

    def mark_completed(self, task_id: str) -> None:
        item = self._rows.get(task_id)
        progress = self._progress_bars.get(task_id)
        if item and progress:
            progress.setValue(100)
            item.setText(1, tr("task.status.completed"))

    def mark_failed(self, task_id: str, error: str = "") -> None:
        item = self._rows.get(task_id)
        if item:
            item.setText(1, tr("task.status.failed"))
            if error:
                item.setToolTip(0, error)

    def mark_cancelled(self, task_id: str) -> None:
        item = self._rows.get(task_id)
        if item:
            item.setText(1, tr("task.status.cancelled"))

    def clear_completed(self) -> None:
        to_remove = []
        for task_id, item in self._rows.items():
            st = item.text(1)
            if st in (tr("task.status.completed"), tr("task.status.failed"),
                      tr("task.status.cancelled")):
                to_remove.append(task_id)
        for tid in to_remove:
            self._remove_row(tid)
        self._update_title()

    def clear_all(self) -> None:
        self._tree.clear()
        self._rows.clear()
        self._progress_bars.clear()
        self._output_dirs.clear()
        self._output_paths.clear()
        self._update_title()

    def connect_queue(self, queue) -> None:
        queue.task_progress.connect(self.update_progress)
        queue.task_completed.connect(self._on_queue_completed)
        queue.task_failed.connect(self._on_queue_failed)
        queue.task_cancelled.connect(self._on_queue_cancelled)

    # ── Signal handlers ───────────────────────────────────────

    def _on_queue_completed(self, task_id: str, output_paths: list) -> None:
        self.mark_completed(task_id)
        self.set_output_path(task_id, output_paths)

    def _on_queue_failed(self, task_id: str, error: str) -> None:
        self.mark_failed(task_id, error)

    def _on_queue_cancelled(self, task_id: str) -> None:
        self.mark_cancelled(task_id)

    # ── Context menu & double-click ───────────────────────────

    def _show_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if not item:
            return
        # Find task_id from the item
        for tid, it in self._rows.items():
            if it is item:
                paths = self._output_paths.get(tid, [])
                if paths:
                    menu = QMenu(self)
                    open_action = QAction("打开输出文件", self)
                    open_action.triggered.connect(lambda: self._open_paths(paths))
                    menu.addAction(open_action)
                    folder_action = QAction("打开所在目录", self)
                    folder_action.triggered.connect(lambda: self._open_folder(paths))
                    menu.addAction(folder_action)
                    menu.exec(QCursor.pos())
                break

    def _on_item_double_clicked(self, item, column) -> None:
        for tid, it in self._rows.items():
            if it is item:
                paths = self._output_paths.get(tid, [])
                if paths:
                    self._open_paths(paths)
                    self.open_output_requested.emit(tid, paths)
                elif it.text(1) == tr("task.status.completed"):
                    # Try to open based on output_dir
                    out_dir = self._output_dirs.get(tid)
                    if out_dir and Path(out_dir).exists():
                        os.startfile(out_dir)
                break

    # ── Helpers ───────────────────────────────────────────────

    def _open_paths(self, paths: list) -> None:
        """Open the first output file."""
        if paths:
            p = Path(paths[0])
            if p.exists():
                os.startfile(str(p))

    def _open_folder(self, paths: list) -> None:
        """Open the folder containing the output."""
        if paths:
            p = Path(paths[0])
            folder = p.parent if p.is_file() else p
            if folder.exists():
                os.startfile(str(folder))

    def _remove_row(self, task_id: str) -> None:
        item = self._rows.pop(task_id, None)
        self._progress_bars.pop(task_id, None)
        self._output_paths.pop(task_id, None)
        self._output_dirs.pop(task_id, None)
        if item:
            idx = self._tree.indexOfTopLevelItem(item)
            if idx >= 0:
                self._tree.takeTopLevelItem(idx)

    def _update_title(self) -> None:
        count = len(self._rows)
        self._title_label.setText(
            tr("task.empty") if count == 0 else f"任务队列 ({count})"
        )

    @property
    def pause_button(self) -> QPushButton:
        return self._pause_btn

    @property
    def cancel_all_button(self) -> QPushButton:
        return self._cancel_all_btn

    @property
    def clear_button(self) -> QPushButton:
        return self._clear_btn
