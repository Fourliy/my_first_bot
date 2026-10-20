import asyncio
import logging

from scripts.index_pdf import index_pdfs

from .config import Config
from .leads import init_db
from .llm_client import LLMClient
from .logger import setup_logger
from .telegram_bot import TelegramBot


class Runner:
    """Собирает компоненты и запускает polling."""

    def __init__(self) -> None:
        self.config = Config()
        setup_logger(self.config.log_level)
        init_db()
        self.llm = LLMClient(self.config)
        self.bot = TelegramBot(self.config, self.llm)

    async def _start(self) -> None:
        logger = logging.getLogger("my_first_bot")
        logger.info("event=start langsmith=%s", self.config.langsmith_enabled)
        try:
            await index_pdfs(self.llm)
        except Exception:
            logger.error("event=index_error", exc_info=True)
        await self.bot.run()

    def run(self) -> None:
        asyncio.run(self._start())


if __name__ == "__main__":
    try:
        runner = Runner()
    except RuntimeError as e:  # ошибка конфигурации: коротко, без traceback
        raise SystemExit(f"Ошибка конфигурации: {e}. См. .env.example")
    runner.run()
