import os

from dotenv import load_dotenv


class Config:
    """Чтение и валидация переменных окружения."""

    def __init__(self) -> None:
        load_dotenv()
        self.telegram_token = self._require("TELEGRAM_TOKEN")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Не задана переменная окружения {name}")
        return value
