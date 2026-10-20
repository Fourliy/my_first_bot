import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """Чтение и валидация переменных окружения."""

    def __init__(self) -> None:
        load_dotenv()
        self.telegram_token = self._require("TELEGRAM_TOKEN")
        self.openai_api_key = self._require_any("OPENROUTER_API_KEY", "OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        self.model_text = os.getenv("MODEL_TEXT", "openai/gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
        self.tavily_api_key = self._require("TAVILY_API_KEY")
        self.system_prompt_file = os.getenv("SYSTEM_PROMPT_FILE", "prompts/system.txt")
        self.system_prompt = self._read_prompt(self.system_prompt_file)
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        # Трассировка LangSmith: выключена по умолчанию, при включении нужен ключ.
        self.langsmith_enabled = os.getenv("LANGSMITH_ENABLED", "false").strip().lower() == "true"
        if self.langsmith_enabled:
            self._require_any("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY")

    @staticmethod
    def _require_any(*names: str) -> str:
        for name in names:
            value = os.getenv(name)
            if value:
                return value
        raise RuntimeError(f"Не задана переменная окружения {' или '.join(names)}")

    @staticmethod
    def _read_prompt(path: str) -> str:
        file = Path(path)
        if not file.is_file():
            raise RuntimeError(f"Не найден файл системного промпта: {path}")
        text = file.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Файл системного промпта пуст: {path}")
        return text

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Не задана переменная окружения {name}")
        return value
