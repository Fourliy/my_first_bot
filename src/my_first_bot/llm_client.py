import logging
import time

from openai import AsyncOpenAI

from .config import Config

logger = logging.getLogger("my_first_bot")

# Ограничение ответа: экономит кредиты OpenRouter и укладывается в лимит Telegram.
MAX_TOKENS = 1000


class LLMClient:
    """Обёртка над openai для запросов к OpenRouter."""

    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=30,
        )
        self._model = config.model_name

    async def chat(self, messages: list[dict]) -> str:
        started = time.monotonic()
        response = await self._client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=MAX_TOKENS
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        logger.info("event=llm_response model=%s latency_ms=%s", self._model, latency_ms)
        return response.choices[0].message.content or ""
