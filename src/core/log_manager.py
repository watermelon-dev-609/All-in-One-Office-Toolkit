"""Centralized logging configuration using loguru."""

import sys
from pathlib import Path
from loguru import logger

from src.constants import LOG_DIR, APP_NAME


class LogManager:
    """Configures and manages application logging."""

    _initialized = False

    @classmethod
    def setup(cls, level: str = "INFO") -> None:
        """Initialize logging with console and file sinks.

        Args:
            level: Minimum log level for console output.
        """
        if cls._initialized:
            return

        # Remove default handler
        logger.remove()

        # Console sink - colored
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=level,
            colorize=True,
        )

        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # File sink - all logs, daily rotation
        logger.add(
            LOG_DIR / "{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation="00:00",
            retention="30 days",
            encoding="utf-8",
            enqueue=True,  # Thread-safe
        )

        # Error file sink - errors only, longer retention
        logger.add(
            LOG_DIR / "errors.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation="10 MB",
            retention="90 days",
            encoding="utf-8",
            enqueue=True,
        )

        cls._initialized = True
        logger.info(f"{APP_NAME} logging initialized (level={level})")

    @classmethod
    def set_level(cls, level: str) -> None:
        """Change console log level at runtime."""
        # Remove old console sink and add new one
        for handler_id, handler_config in list(logger._core.handlers.items()):
            if hasattr(handler_config, "_sink") and handler_config._sink is sys.stderr:
                logger.remove(handler_id)
                break
        logger.add(sys.stderr, level=level, colorize=True)
        logger.debug(f"Log level changed to {level}")

    @classmethod
    def get_logger(cls, name: str = None):
        """Get a logger instance with an optional module name."""
        if name:
            return logger.bind(name=name)
        return logger
