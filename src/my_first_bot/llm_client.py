import logging
import os
import time

import openai
from langsmith import traceable
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage

from .config import Config

logger = logging.getLogger("my_first_bot")

# Ограничение ответа: укладывается в лимит Telegram и в остаток кредитов OpenRouter.
MAX_TOKENS = 400


class LLMError(Exception):
    """Ошибка LLM с безопасным текстом, который можно показать пользователю."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class LLMClient:
    """Обёртка над openai для запросов с инструментами (локально — Ollama)."""

    def __init__(self, config: Config) -> None:
        client = AsyncOpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            timeout=20,
            max_retries=2,  # повтор при временных ошибках с растущей паузой
        )
        if config.langsmith_enabled:
            from langsmith.wrappers import wrap_openai

            os.environ.setdefault(
                "LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY", "")
            )
            os.environ.setdefault(
                "LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "")
            )
            os.environ["LANGSMITH_TRACING"] = "true"
            client = wrap_openai(client)
        self._client = client
        self._model = config.model_text
        self._embedding_model = config.embedding_model

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatCompletionMessage:
        """Один запрос к модели. Возвращает сообщение целиком: текст и/или tool_calls."""
        params: dict = {"model": self._model, "messages": messages, "max_tokens": MAX_TOKENS}
        if tools:
            params["tools"] = tools
        started = time.monotonic()
        try:
            response = await self._client.chat.completions.create(**params)
        except openai.APITimeoutError as e:
            raise LLMError(
                "Модель отвечает слишком долго. Попробуйте ещё раз чуть позже."
            ) from e
        except openai.RateLimitError as e:
            raise LLMError("Слишком много запросов. Подождите немного и повторите.") from e
        except openai.APIConnectionError as e:
            raise LLMError("Нет связи с моделью. Попробуйте позже.") from e
        except openai.APIError as e:  # 401/402/404/5xx и прочие ошибки API
            status = getattr(e, "status_code", None)
            logger.warning("event=llm_error status=%s", status)
            if status == 402:
                raise LLMError(
                    "Закончился лимит модели. Пополните кредиты OpenRouter и повторите вопрос."
                ) from e
            raise LLMError("Сервис модели временно недоступен. Попробуйте позже.") from e

        latency_ms = int((time.monotonic() - started) * 1000)
        logger.info("event=llm_response model=%s latency_ms=%s", self._model, latency_ms)
        if not response.choices:
            raise LLMError("Модель вернула пустой ответ. Попробуйте переформулировать вопрос.")
        return response.choices[0].message

    @traceable(name="embed")
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Эмбеддинги фрагментов и запроса. Тот же клиент и ключ, что у чата."""
        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model, input=texts
            )
        except openai.APITimeoutError as e:
            raise LLMError("Модель отвечает слишком долго. Попробуйте ещё раз чуть позже.") from e
        except openai.APIConnectionError as e:
            raise LLMError("Нет связи с моделью. Попробуйте позже.") from e
        except openai.APIError as e:
            raise LLMError("Сервис модели временно недоступен. Попробуйте позже.") from e
        return [item.embedding for item in response.data]
