"""Safe file output path management.

Ensures output files never overwrite originals by creating structured
output directories and handling filename collisions.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

from loguru import logger

from src.constants import DEFAULT_OUTPUT_SUBDIR


class PathManager:
    """Manages output path resolution with collision avoidance."""

    def __init__(self, output_base_dir: Optional[Path] = None):
        """Initialize path manager.

        Args:
            output_base_dir: Custom base output directory. If None,
                             outputs go to <source_dir>/Output/.
        """
        self._output_base_dir = output_base_dir

    def set_output_base_dir(self, path: Path) -> None:
        """Set a custom base output directory."""
        self._output_base_dir = path

    def get_output_dir(self, source_file: Union[str, Path]) -> Path:
        """Get the output directory for a given source file.

        If output_base_dir is set, mirrors directory structure under it.
        Otherwise, creates an Output/ subdirectory next to the source file.

        Args:
            source_file: Path to the source file.

        Returns:
            Path to the output directory (created if needed).
        """
        source = Path(source_file)
        source_dir = source.parent if source.is_file() else source

        if self._output_base_dir:
            # Mirror relative structure under custom base
            try:
                rel = source.relative_to(source.anchor)
            except ValueError:
                rel = source
            output_dir = self._output_base_dir / rel
        else:
            # Output/ subdirectory next to source
            output_dir = source_dir / DEFAULT_OUTPUT_SUBDIR

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def get_output_path(
        self,
        source_file: Union[str, Path],
        suffix: str = "",
        prefix: str = "",
        new_extension: Optional[str] = None,
        use_timestamp: bool = False,
    ) -> Path:
        """Generate a safe output file path that won't overwrite existing files.

        Args:
            source_file: Original source file path.
            suffix: Text to append before the extension.
            prefix: Text to prepend to the filename.
            new_extension: If set, replace the original extension.
            use_timestamp: If True, append a timestamp for uniqueness.

        Returns:
            A path that does not yet exist (collision-safe).
        """
        source = Path(source_file)
        output_dir = self.get_output_dir(source)

        # Build filename
        stem = source.stem
        ext = new_extension if new_extension else source.suffix

        if use_timestamp:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}{stem}{suffix}_{ts}{ext}"
        else:
            filename = f"{prefix}{stem}{suffix}{ext}"

        output_path = output_dir / filename

        # Collision avoidance: append counter until unique
        if output_path.exists() and not use_timestamp:
            counter = 1
            while output_path.exists():
                filename = f"{prefix}{stem}{suffix}_{counter}{ext}"
                output_path = output_dir / filename
                counter += 1
                if counter > 9999:
                    # Fallback to timestamp to break infinite loop
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"{prefix}{stem}{suffix}_{ts}{ext}"
                    output_path = output_dir / filename
                    break

        logger.debug(f"Output path resolved: {source} -> {output_path}")
        return output_path

    @staticmethod
    def ensure_dir(path: Path) -> Path:
        """Create directory if it doesn't exist and return it."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def is_same_file(path1: Path, path2: Path) -> bool:
        """Check if two paths point to the same file."""
        try:
            return path1.resolve() == path2.resolve()
        except (OSError, ValueError):
            return False
