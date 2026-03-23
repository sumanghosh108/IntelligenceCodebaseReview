"""Shared memory layer for multi-agent system.

All agents read from and write to this shared state.
Replaces passing data between analysis stages through function arguments.
Thread-safe via asyncio locks.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class AgentEvent:
    """Event emitted by an agent during execution."""
    agent_name: str
    event_type: str  # "started", "progress", "completed", "failed", "retry"
    message: str
    data: Any = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "type": self.event_type,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class SharedMemory:
    """Thread-safe shared state for multi-agent coordination.

    Sections:
      - repo: cloned repo path, URL, branch
      - parsed: parsed file data from ParserAgent
      - graphs: dependency, call, knowledge graphs from GraphAgent
      - analysis: per-section analysis results (overview, security, etc.)
      - embeddings: collection name, hybrid search engine
      - meta: job metadata (job_id, timing, status)
    """

    def __init__(self):
        self._store: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._events: list[AgentEvent] = []
        self._event_callbacks: list = []
        self._agent_status: dict[str, str] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return self._store.get(key, default)

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._store[key] = value

    async def update(self, updates: dict[str, Any]):
        """Batch update multiple keys."""
        async with self._lock:
            self._store.update(updates)

    async def get_section(self, section: str) -> dict:
        """Get all keys under a section prefix (e.g., 'analysis.' returns all analysis.* keys)."""
        prefix = f"{section}."
        async with self._lock:
            return {
                k[len(prefix):]: v
                for k, v in self._store.items()
                if k.startswith(prefix)
            }

    async def set_section(self, section: str, key: str, value: Any):
        """Set a key within a section."""
        await self.set(f"{section}.{key}", value)

    async def get_all(self) -> dict:
        """Get complete snapshot of shared state."""
        async with self._lock:
            return dict(self._store)

    # ====== Agent Status Tracking ======

    async def set_agent_status(self, agent_name: str, status: str):
        async with self._lock:
            self._agent_status[agent_name] = status

    async def get_agent_statuses(self) -> dict[str, str]:
        async with self._lock:
            return dict(self._agent_status)

    # ====== Event System ======

    def on_event(self, callback):
        """Register a callback for agent events (for SSE streaming)."""
        self._event_callbacks.append(callback)

    async def emit_event(self, event: AgentEvent):
        """Emit an event from an agent."""
        async with self._lock:
            self._events.append(event)
        # Notify listeners
        for cb in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

    async def get_events(self, since: int = 0) -> list[dict]:
        """Get events since index."""
        async with self._lock:
            return [e.to_dict() for e in self._events[since:]]

    async def clear(self):
        """Reset shared memory (new analysis)."""
        async with self._lock:
            self._store.clear()
            self._events.clear()
            self._agent_status.clear()
