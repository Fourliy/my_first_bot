import logging
import time

import openai
from openai import AsyncOpenAI

from .config import Config

logger = logging.getLogger("my_first_bot")

# Ограничение ответа: экономит кредиты OpenRouter и укладывается в лимит Telegram.
MAX_TOKENS = 1000


class LLMError(Exception):
    """Ошибка LLM с безопасным текстом, который можно показать пользователю."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class LLMClient:
    """Обёртка над openai для запросов к OpenRouter."""

    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=20,
            max_retries=2,  # повтор при временных ошибках с растущей паузой
        )
        self._model = config.model_name

    async def chat(self, messages: list[dict]) -> str:
        started = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self._model, messages=messages, max_tokens=MAX_TOKENS
            )
        except openai.APITimeoutError as e:
            raise LLMError(
                "Модель отвечает слишком долго. Попробуйте ещё раз чуть позже."
            ) from e
        except openai.RateLimitError as e:
            raise LLMError("Слишком много запросов. Подождите немного и повторите.") from e
        except openai.APIConnectionError as e:
            raise LLMError("Нет связи с моделью. Попробуйте позже.") from e
        except openai.APIError as e:  # 401/402/404/5xx и прочие ошибки API
            raise LLMError("Сервис модели временно недоступен. Попробуйте позже.") from e

        latency_ms = int((time.monotonic() - started) * 1000)
        logger.info("event=llm_response model=%s latency_ms=%s", self._model, latency_ms)
        content = (response.choices[0].message.content or "") if response.choices else ""
        if not content.strip():
            raise LLMError("Модель вернула пустой ответ. Попробуйте переформулировать вопрос.")
        return content
