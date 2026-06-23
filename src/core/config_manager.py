"""Application configuration manager with YAML persistence.

Thread-safe singleton that manages app settings with dot-notation access.
"""

import os
import threading
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

from src.constants import CONFIG_FILE, DATA_DIR, DEFAULT_MAX_THREADS, DEFAULT_MAX_MEMORY_MB


# Default configuration
DEFAULT_CONFIG = {
    "app": {
        "language": "zh_CN",
        "theme": "dark",
        "accent_color": "teal",
        "font_size": "normal",
        "first_run": True,
        "check_updates": True,
    },
    "output": {
        "base_dir": "",  # Empty = auto (Output/ subdir)
        "preserve_structure": True,
        "overwrite_policy": "rename",  # rename | skip | ask
    },
    "performance": {
        "max_threads": DEFAULT_MAX_THREADS,
        "max_memory_mb": DEFAULT_MAX_MEMORY_MB,
    },
    "modules": {},
    "shortcuts": {},
}


class ConfigManager:
    """Thread-safe configuration singleton backed by YAML file."""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls, config_path: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None):
        if self._initialized:
            return
        self._config_path = config_path or CONFIG_FILE
        self._data = {}
        self._dirty = False
        self.load()
        self._initialized = True

    def load(self) -> None:
        """Load configuration from disk or create defaults."""
        with self._lock:
            if self._config_path.exists():
                try:
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f) or {}
                    # Merge with defaults to ensure all keys exist
                    self._data = self._deep_merge(DEFAULT_CONFIG, loaded)
                    logger.info(f"Config loaded from {self._config_path}")
                except Exception as e:
                    logger.error(f"Failed to load config: {e}, using defaults")
                    self._data = self._deep_copy(DEFAULT_CONFIG)
            else:
                self._data = self._deep_copy(DEFAULT_CONFIG)
                self.save()
                logger.info("Default config created")

    def save(self) -> None:
        """Persist configuration to disk."""
        with self._lock:
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                with open(self._config_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(self._data, f, allow_unicode=True, default_flow_style=False)
                self._dirty = False
                logger.debug("Config saved")
            except Exception as e:
                logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-notation key (e.g., 'app.theme')."""
        with self._lock:
            keys = key.split(".")
            value = self._data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    def set(self, key: str, value: Any) -> None:
        """Set a config value by dot-notation key and mark dirty."""
        with self._lock:
            keys = key.split(".")
            target = self._data
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value
            self._dirty = True

    def reset_to_defaults(self) -> None:
        """Reset all configuration to defaults."""
        with self._lock:
            self._data = self._deep_copy(DEFAULT_CONFIG)
            self._dirty = True
            self.save()
            logger.info("Config reset to defaults")

    def get_module_config(self, module_id: str) -> dict:
        """Get the configuration section for a specific module."""
        with self._lock:
            if module_id not in self._data.get("modules", {}):
                if "modules" not in self._data:
                    self._data["modules"] = {}
                self._data["modules"][module_id] = {}
            return dict(self._data["modules"][module_id])

    def set_module_config(self, module_id: str, key: str, value: Any) -> None:
        """Set a module-specific config value."""
        self.set(f"modules.{module_id}.{key}", value)

    @property
    def all_data(self) -> dict:
        """Return a deep copy of all config data (read-only)."""
        with self._lock:
            return self._deep_copy(self._data)

    @staticmethod
    def _deep_copy(d: dict) -> dict:
        """Deep copy a dictionary."""
        import copy
        return copy.deepcopy(d)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge override into base, preserving base keys."""
        import copy
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
