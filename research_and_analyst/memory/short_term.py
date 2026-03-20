"""
Short-Term Memory — in-memory store for intermediate outputs within a single task session.

Stores agent outputs, intermediate results, and task context.
Scoped to a single decision workflow execution.
"""

import time
from typing import Any, Dict, List, Optional

from research_and_analyst.logger import GLOBAL_LOGGER as log


class MemoryEntry:
    """A single memory entry with metadata."""

    __slots__ = ("key", "value", "timestamp", "source", "entry_type")

    def __init__(self, key: str, value: Any, source: str = "", entry_type: str = "general"):
        self.key = key
        self.value = value
        self.timestamp = time.time()
        self.source = source
        self.entry_type = entry_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "type": self.entry_type,
        }


class ShortTermMemory:
    """
    In-memory store for a single workflow execution.

    Features:
    - Key-value storage with metadata
    - Type-based retrieval (agent_output, intermediate, context)
    - Ordered history tracking
    - Size-bounded with automatic eviction of oldest entries
    """

    def __init__(self, max_entries: int = 100):
        self._store: Dict[str, MemoryEntry] = {}
        self._history: List[str] = []
        self.max_entries = max_entries

    def store(self, key: str, value: Any, source: str = "", entry_type: str = "general") -> None:
        """Store a value with metadata."""
        if len(self._store) >= self.max_entries:
            self._evict_oldest()

        entry = MemoryEntry(key=key, value=value, source=source, entry_type=entry_type)
        self._store[key] = entry
        self._history.append(key)
        log.debug("Short-term memory stored", key=key, type=entry_type)

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve a value by key."""
        entry = self._store.get(key)
        return entry.value if entry else None

    def recall_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """Retrieve all entries of a given type."""
        return [
            entry.to_dict()
            for entry in self._store.values()
            if entry.entry_type == entry_type
        ]

    def recall_all(self) -> Dict[str, Any]:
        """Return all stored key-value pairs."""
        return {key: entry.value for key, entry in self._store.items()}

    def get_context_summary(self) -> str:
        """Get a text summary of all stored items for LLM context injection."""
        lines = []
        for key in self._history:
            entry = self._store.get(key)
            if entry:
                val_preview = str(entry.value)[:200]
                lines.append(f"[{entry.entry_type}] {key}: {val_preview}")
        return "\n".join(lines)

    def has(self, key: str) -> bool:
        return key in self._store

    def clear(self) -> None:
        """Clear all memory."""
        self._store.clear()
        self._history.clear()

    def size(self) -> int:
        return len(self._store)

    def _evict_oldest(self) -> None:
        """Remove the oldest entry to make room."""
        if self._history:
            oldest_key = self._history.pop(0)
            self._store.pop(oldest_key, None)
            log.debug("Short-term memory evicted", key=oldest_key)
