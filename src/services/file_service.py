"""Safe file I/O service.

Ensures output files never overwrite originals. Provides file locking
and safe write operations for all modules.
"""

import shutil
import threading
from pathlib import Path
from typing import Optional, Union

from loguru import logger

from src.core.path_manager import PathManager
from src.constants import DEFAULT_OUTPUT_SUBDIR


class FileService:
    """Centralized file operations with safety guarantees."""

    _instance = None
    _lock_manager = threading.RLock()
    _locked_files: dict[str, threading.RLock] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._path_manager = PathManager()
        return cls._instance

    @property
    def path_manager(self) -> PathManager:
        return self._path_manager

    # ---- File locking ----

    def acquire_lock(self, file_path: Union[str, Path]) -> bool:
        """Acquire a processing lock for a file. Returns True if acquired."""
        path_str = str(Path(file_path).resolve())
        with self._lock_manager:
            if path_str not in self._locked_files:
                self._locked_files[path_str] = threading.RLock()
            lock = self._locked_files[path_str]

        acquired = lock.acquire(blocking=False)
        if not acquired:
            logger.warning(f"File locked by another task: {path_str}")
        return acquired

    def release_lock(self, file_path: Union[str, Path]) -> None:
        """Release a processing lock."""
        path_str = str(Path(file_path).resolve())
        with self._lock_manager:
            if path_str in self._locked_files:
                lock = self._locked_files[path_str]
                try:
                    lock.release()
                except RuntimeError:
                    pass  # Already released

    # ---- Safe file operations ----

    def safe_write(
        self,
        source_path: Union[str, Path],
        data: bytes,
        suffix: str = "",
        prefix: str = "",
        new_extension: Optional[str] = None,
    ) -> Path:
        """Write data to an output file safely (never overwrites original).

        Args:
            source_path: Original file (used to determine output directory).
            data: Binary data to write.
            suffix: Append to filename.
            prefix: Prepend to filename.
            new_extension: Replace original extension.

        Returns:
            Path to the written file.
        """
        output_path = self._path_manager.get_output_path(
            source_path, suffix=suffix, prefix=prefix, new_extension=new_extension
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
        logger.info(f"Safe write: {output_path}")
        return output_path

    def safe_copy(
        self,
        source_path: Union[str, Path],
        suffix: str = "",
        prefix: str = "",
        new_extension: Optional[str] = None,
    ) -> Path:
        """Copy a file to a safe output location.

        Args:
            source_path: Original file to copy.
            suffix, prefix, new_extension: Output filename modifiers.

        Returns:
            Path to the copied file.
        """
        source = Path(source_path)
        output_path = self._path_manager.get_output_path(
            source, suffix=suffix, prefix=prefix, new_extension=new_extension
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output_path)
        logger.info(f"Safe copy: {source} -> {output_path}")
        return output_path

    def get_output_dir(self, source_path: Union[str, Path]) -> Path:
        """Get (and create) the output directory for a source file."""
        return self._path_manager.get_output_dir(source_path)

    # ---- Utilities ----

    @staticmethod
    def get_file_size_mb(path: Union[str, Path]) -> float:
        """Get file size in megabytes."""
        return Path(path).stat().st_size / (1024 * 1024)

    @staticmethod
    def ensure_unique(path: Path) -> Path:
        """Return a unique path by appending a counter if needed."""
        if not path.exists():
            return path
        stem = path.stem
        ext = path.suffix
        parent = path.parent
        counter = 1
        while (parent / f"{stem}_{counter}{ext}").exists():
            counter += 1
        return parent / f"{stem}_{counter}{ext}"
