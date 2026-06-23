"""Plugin discovery and module management.

Scans src/modules/ for BaseModule subclasses and manages their lifecycle.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Optional

from loguru import logger

from src.constants import MODULES_DIR
from src.modules.base_module import BaseModule


class PluginManager:
    """Discovers and manages feature modules."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._modules = {}
            cls._instance._module_order = []
            cls._instance._discovered = False
        return cls._instance

    def discover_modules(self) -> list[BaseModule]:
        """Scan and load all available modules.

        Returns:
            List of module instances sorted by module_order.
        """
        if self._discovered:
            return list(self._modules.values())

        if not MODULES_DIR.exists():
            logger.error(f"Modules directory not found: {MODULES_DIR}")
            return []

        # Walk through module directories
        for item in sorted(MODULES_DIR.iterdir()):
            if item.is_dir() and (item / "module.py").exists():
                self._load_module(item.name)

        self._discovered = True
        logger.info(f"Discovered {len(self._modules)} modules: {list(self._modules.keys())}")
        return self.get_modules()

    def _load_module(self, module_name: str) -> Optional[BaseModule]:
        """Load a single module by directory name.

        Args:
            module_name: Name of the module directory.

        Returns:
            Module instance or None if failed.
        """
        try:
            package = f"src.modules.{module_name}.module"
            mod = importlib.import_module(package)

            # Find BaseModule subclass
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseModule)
                    and attr is not BaseModule
                ):
                    instance = attr()
                    self._register(instance)
                    logger.info(f"Loaded module: {instance.module_name} ({instance.module_id})")
                    return instance

            logger.warning(f"No BaseModule subclass found in {module_name}.module")
            return None

        except Exception as e:
            logger.error(f"Failed to load module '{module_name}': {e}")
            return None

    def _register(self, module: BaseModule) -> None:
        """Register a module instance."""
        self._modules[module.module_id] = module
        self._module_order.append(module.module_id)
        # Sort by order whenever a new module is added
        self._module_order.sort(
            key=lambda mid: self._modules[mid].module_order
        )

    def get_module(self, module_id: str) -> Optional[BaseModule]:
        """Get a module by its ID."""
        return self._modules.get(module_id)

    def get_modules(self) -> list[BaseModule]:
        """Get all modules sorted by order."""
        return [self._modules[mid] for mid in self._module_order if mid in self._modules]

    def get_modules_by_category(self, category: str) -> list[BaseModule]:
        """Get modules filtered by category."""
        return [
            m for m in self.get_modules()
            if getattr(m, 'category', '') == category
        ]

    @property
    def module_count(self) -> int:
        return len(self._modules)

    def is_module_enabled(self, module_id: str) -> bool:
        """Check if a module is currently enabled."""
        module = self._modules.get(module_id)
        return module is not None and module.enabled
