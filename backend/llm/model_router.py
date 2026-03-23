"""Model router — all tasks go through OpenRouter API.

Single model (stepfun/step-3.5-flash:free) for all tasks.
No Ollama, no Groq — clean and simple.
"""
import logging
from backend.llm.api_client import api_client

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes all LLM tasks through OpenRouter."""

    async def generate(self, task: str, prompt: str, system_prompt: str = None, temperature: float = 0.1) -> str:
        """Generate text for a task."""
        logger.info(f"Task '{task}' → openrouter/{api_client.model}")
        return await api_client.generate(prompt, system_prompt=system_prompt, temperature=temperature)

    async def generate_json(self, task: str, prompt: str, system_prompt: str = None) -> dict:
        """Generate JSON for a task."""
        logger.info(f"Task '{task}' → openrouter/{api_client.model} (JSON)")
        return await api_client.generate_json(prompt, system_prompt=system_prompt)

    async def get_model_for_task(self, task: str) -> str:
        """Get model name (always the same)."""
        return api_client.model


model_router = ModelRouter()
