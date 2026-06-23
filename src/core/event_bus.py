"""Event bus for decoupled inter-module communication.

Uses a simple publish/subscribe pattern within a single process.
Modules should communicate through events rather than direct imports.
"""

from typing import Callable, Any
from collections import defaultdict
from loguru import logger


class EventBus:
    """Simple in-process publish/subscribe event system."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = defaultdict(list)
            cls._instance._history = []  # Store recent events for debugging
            cls._instance._max_history = 200
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: Event name (e.g., 'task:completed', 'theme:changed').
            callback: Function to call when event is published.
        """
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to '{event_type}': {callback.__name__}")

    def unsubscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Remove a callback registration."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from '{event_type}': {callback.__name__}")

    def publish(self, event_type: str, **kwargs) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Event name.
            **kwargs: Event data passed to subscribers.
        """
        # Store in history
        self._history.append({"type": event_type, "data": kwargs})
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Notify subscribers
        subscribers = self._subscribers.get(event_type, [])
        if not subscribers:
            return

        for callback in subscribers:
            try:
                callback(**kwargs)
            except Exception as e:
                logger.error(f"Error in event handler '{callback.__name__}' for '{event_type}': {e}")

    def get_history(self, event_type: str = None, limit: int = 50) -> list:
        """Get recent event history, optionally filtered by type."""
        if event_type:
            return [e for e in self._history if e["type"] == event_type][-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Common event type constants
class Events:
    """Well-known event type strings."""

    # Task events
    TASK_STARTED = "task:started"
    TASK_PROGRESS = "task:progress"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"
    TASK_CANCELLED = "task:cancelled"
    TASK_PAUSED = "task:paused"
    TASK_RESUMED = "task:resumed"

    # File events
    FILE_OUTPUT_READY = "file:output_ready"
    FILE_IMPORTED = "file:imported"

    # App events
    SETTINGS_CHANGED = "settings:changed"
    THEME_CHANGED = "theme:changed"
    LANGUAGE_CHANGED = "language:changed"
    MODULE_ACTIVATED = "module:activated"
    MODULE_DEACTIVATED = "module:deactivated"

    # AI events
    AI_MODEL_DOWNLOAD_PROGRESS = "ai:model_download_progress"
    AI_MODEL_DOWNLOAD_COMPLETE = "ai:model_download_complete"
    AI_MODEL_DOWNLOAD_FAILED = "ai:model_download_failed"
    AI_GENERATION_TOKEN = "ai:generation_token"
    AI_GENERATION_COMPLETE = "ai:generation_complete"
