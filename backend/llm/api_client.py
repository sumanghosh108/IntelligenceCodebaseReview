"""OpenRouter LLM API client — uses stepfun/step-3.5-flash:free model.

Single provider, single model. Clean and fast.
"""
import json
import logging
import asyncio
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)

# Single model for all tasks — free tier
DEFAULT_MODEL = "stepfun/step-3.5-flash:free"


class APIClient:
    """OpenRouter API client for LLM inference."""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = DEFAULT_MODEL
        self._request_count = 0

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Generate text via OpenRouter chat completions API."""
        if not self.is_available():
            raise ConnectionError("OpenRouter API key not set. Add ICR_OPENROUTER_API_KEY to .env")

        use_model = model or self.model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://intelligence-codebase-review.local",
            "X-Title": "Intelligence Codebase Review",
        }

        url = f"{self.base_url}/chat/completions"

        try:
            timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", "3"))
                    logger.warning(f"OpenRouter rate limited, retrying in {retry_after}s")
                    await asyncio.sleep(retry_after)
                    response = await client.post(url, json=payload, headers=headers)

                response.raise_for_status()
                data = response.json()

                self._request_count += 1
                content = data["choices"][0]["message"]["content"]
                logger.debug(f"OpenRouter/{use_model}: {len(content)} chars (req #{self._request_count})")
                return content

        except httpx.ConnectError:
            raise ConnectionError(f"Cannot connect to OpenRouter API")
        except httpx.ReadTimeout:
            raise TimeoutError(f"OpenRouter timed out for model '{use_model}'")
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error {e.response.status_code}: {e.response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter error ({type(e).__name__}): {e}")
            raise

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
    ) -> dict:
        """Generate and parse JSON response."""
        # Try json_mode first
        try:
            raw = await self.generate(
                prompt, system_prompt=system_prompt, model=model, json_mode=True
            )
            return json.loads(raw)
        except (json.JSONDecodeError, httpx.HTTPStatusError):
            pass

        # Fallback: generate normally and extract JSON
        raw = await self.generate(prompt, system_prompt=system_prompt, model=model)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            for start_char, end_char in [("{", "}"), ("[", "]")]:
                start = raw.find(start_char)
                end = raw.rfind(end_char) + 1
                if start >= 0 and end > start:
                    try:
                        return json.loads(raw[start:end])
                    except json.JSONDecodeError:
                        continue
            return {"raw_response": raw}

    async def check_health(self) -> dict:
        """Check OpenRouter API health."""
        if not self.is_available():
            return {"status": "not_configured", "provider": "openrouter"}
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
                if response.status_code == 200:
                    return {"status": "healthy", "provider": "openrouter", "model": self.model}
                return {"status": "error", "provider": "openrouter", "code": response.status_code}
        except Exception as e:
            return {"status": "error", "provider": "openrouter", "error": str(e)}


api_client = APIClient()
