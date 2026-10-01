import asyncio
import logging

from .alert_handler import AlertHandler
from .config import Config
from .llm_client import LLMClient
from .logger import setup_logger
from .telegram_bot import TelegramBot
from .ticket_service import StubTicketService


class Runner:
    """Собирает компоненты и запускает polling."""

    def __init__(self) -> None:
        self.config = Config()
        setup_logger(self.config.log_level)
        self.alerts = AlertHandler(self.config)
        self.bot = TelegramBot(
            self.config, LLMClient(self.config), self.alerts, StubTicketService()
        )

    def run(self) -> None:
        logging.getLogger("my_first_bot").info(
            "Bot started alerts_enabled=%s", self.alerts.enabled
        )
        asyncio.run(self.bot.run())


if __name__ == "__main__":
    try:
        runner = Runner()
    except RuntimeError as e:  # ошибка конфигурации: коротко, без traceback
        raise SystemExit(f"Ошибка конфигурации: {e}. См. .env.example")
    runner.run()
