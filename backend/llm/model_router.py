"""Model router — maps analysis tasks to the best available model."""
import logging
from config.settings import settings
from backend.llm.ollama_client import ollama_client

logger = logging.getLogger(__name__)

# Task → model mapping
TASK_MODEL_MAP = {
    # Fast tasks — use lightweight model
    "tech_stack": "fast",
    "cost": "fast",
    "quick_stats": "fast",
    "modules": "fast",

    # Agent reasoning — use fast model for speed
    "agent": "fast",

    # Code reasoning — use code-specialized model
    "file_analysis": "code",
    "function_analysis": "code",
    "security": "code",
    "dependencies": "code",
    "call_graph": "code",
    "code_quality": "code",

    # Deep reasoning — use powerful model
    "overview": "deep",
    "system_flow": "deep",
    "production": "deep",
    "interview": "deep",
    "views": "deep",
    "recommendations": "deep",
    "synthesis": "deep",
    "impact": "deep",
    "query": "deep",
}


class ModelRouter:
    """Routes analysis tasks to the best available model."""

    def __init__(self):
        self._available_models: list[str] | None = None

    async def _ensure_models_checked(self):
        """Check which models are actually available in Ollama."""
        if self._available_models is None:
            self._available_models = await ollama_client.list_models()
            logger.info(f"Available models: {self._available_models}")

    def _resolve_model(self, tier: str) -> str:
        """Resolve a tier (fast/code/deep) to an actual model name."""
        model_map = {
            "fast": settings.model_fast,
            "code": settings.model_code,
            "deep": settings.model_deep,
        }
        desired = model_map.get(tier, settings.ollama_model)

        # Check if desired model is available, fallback to default
        if self._available_models and desired not in self._available_models:
            # Try matching by prefix (e.g., "llama3" matches "llama3:latest")
            for avail in self._available_models:
                if avail.startswith(desired) or desired.startswith(avail.split(":")[0]):
                    return avail
            logger.warning(f"Model {desired} not available, falling back to {settings.ollama_model}")
            # Try fallback
            for avail in self._available_models:
                if avail.startswith(settings.ollama_model) or settings.ollama_model.startswith(avail.split(":")[0]):
                    return avail
            # Use whatever is available
            if self._available_models:
                return self._available_models[0]
            return settings.ollama_model
        return desired

    async def get_model_for_task(self, task: str) -> str:
        """Get the best model for a given analysis task."""
        await self._ensure_models_checked()
        tier = TASK_MODEL_MAP.get(task, "deep")
        model = self._resolve_model(tier)
        return model

    async def generate(self, task: str, prompt: str, system_prompt: str = None, temperature: float = 0.1) -> str:
        """Generate using the best model for the task."""
        model = await self.get_model_for_task(task)
        logger.info(f"Task '{task}' → model '{model}'")
        return await ollama_client.generate(prompt, system_prompt=system_prompt, temperature=temperature, model=model)

    async def generate_json(self, task: str, prompt: str, system_prompt: str = None) -> dict:
        """Generate JSON using the best model for the task."""
        model = await self.get_model_for_task(task)
        logger.info(f"Task '{task}' → model '{model}' (JSON)")
        return await ollama_client.generate_json(prompt, system_prompt=system_prompt, model=model)


model_router = ModelRouter()
