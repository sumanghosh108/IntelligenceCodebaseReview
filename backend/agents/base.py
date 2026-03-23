"""Base agent class for the multi-agent system.

Every specialized agent inherits from BaseAgent, which provides:
  - Structured execution with retry logic
  - Automatic event emission (started, progress, completed, failed)
  - Access to shared memory for reading inputs and writing outputs
  - Timeout enforcement
"""
import asyncio
import logging
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any

from config.settings import settings
from backend.agents.shared_memory import SharedMemory, AgentEvent

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    name: str = "base"
    description: str = "Base agent"
    # Per-agent timeout override (seconds). None = use settings default.
    default_timeout: int | None = None

    def __init__(self, memory: SharedMemory):
        self.memory = memory
        self.max_retries = settings.agent_max_retries
        self.timeout = self.default_timeout or settings.agent_task_timeout

    @abstractmethod
    async def execute(self) -> dict[str, Any]:
        """Core agent logic. Read from self.memory, return results dict.

        Returns a dict of key→value pairs that will be stored in shared memory
        under the section for this agent (e.g., analysis.security_analysis).
        """
        ...

    async def run(self) -> dict[str, Any]:
        """Execute with retry, timeout, and event emission."""
        await self.memory.set_agent_status(self.name, "running")
        await self.memory.emit_event(AgentEvent(
            agent_name=self.name,
            event_type="started",
            message=f"{self.description} started",
        ))

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                t0 = time.monotonic()

                # Run with timeout
                result = await asyncio.wait_for(
                    self.execute(),
                    timeout=self.timeout,
                )

                elapsed_ms = int((time.monotonic() - t0) * 1000)

                await self.memory.set_agent_status(self.name, "completed")
                await self.memory.emit_event(AgentEvent(
                    agent_name=self.name,
                    event_type="completed",
                    message=f"{self.description} completed in {elapsed_ms}ms",
                    data={"duration_ms": elapsed_ms, "attempt": attempt},
                ))

                logger.info(f"Agent '{self.name}' completed in {elapsed_ms}ms (attempt {attempt})")
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout}s"
                logger.warning(f"Agent '{self.name}' timed out (attempt {attempt}/{self.max_retries})")
                await self.memory.emit_event(AgentEvent(
                    agent_name=self.name,
                    event_type="retry",
                    message=f"{self.description} timed out, retrying ({attempt}/{self.max_retries})",
                ))

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Agent '{self.name}' failed (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    await self.memory.emit_event(AgentEvent(
                        agent_name=self.name,
                        event_type="retry",
                        message=f"{self.description} failed: {e}, retrying ({attempt}/{self.max_retries})",
                    ))
                    await asyncio.sleep(1)  # Brief pause before retry

        # All retries exhausted
        await self.memory.set_agent_status(self.name, "failed")
        await self.memory.emit_event(AgentEvent(
            agent_name=self.name,
            event_type="failed",
            message=f"{self.description} failed after {self.max_retries} attempts: {last_error}",
        ))
        logger.error(f"Agent '{self.name}' failed permanently: {last_error}")
        return {"error": last_error}

    async def emit_progress(self, message: str, data: Any = None):
        """Emit a progress event during execution."""
        await self.memory.emit_event(AgentEvent(
            agent_name=self.name,
            event_type="progress",
            message=message,
            data=data,
        ))
