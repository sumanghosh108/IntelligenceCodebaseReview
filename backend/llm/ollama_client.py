"""Ollama LLM client for local inference."""
import httpx
import json
import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout

    async def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.1, model: str = None) -> str:
        url = f"{self.base_url}/api/generate"
        use_model = model or self.model
        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 4096,
                "num_ctx": settings.ollama_num_ctx,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            timeout = httpx.Timeout(
                connect=10.0,
                read=float(self.timeout),
                write=30.0,
                pool=10.0,
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running?")
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Please start Ollama with: ollama serve"
            )
        except httpx.ReadTimeout:
            logger.error(f"Ollama timeout after {self.timeout}s for model '{use_model}'")
            raise TimeoutError(f"Ollama timed out after {self.timeout}s. Try increasing ICR_OLLAMA_TIMEOUT.")
        except Exception as e:
            logger.error(f"Ollama error ({type(e).__name__}): {e}")
            raise

    async def generate_with_model(self, prompt: str, model: str, system_prompt: str = None, temperature: float = 0.1) -> str:
        """Generate using an explicitly specified model."""
        return await self.generate(prompt, system_prompt=system_prompt, temperature=temperature, model=model)

    async def generate_json(self, prompt: str, system_prompt: str = None, model: str = None) -> dict:
        raw = await self.generate(prompt, system_prompt, model=model)

        # Try to extract JSON from response
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass

            # Try array
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass

            return {"raw_response": raw}

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


ollama_client = OllamaClient()
