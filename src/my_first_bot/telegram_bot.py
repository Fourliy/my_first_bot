import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from .config import Config

logger = logging.getLogger("my_first_bot")


class TelegramBot:
    """Обработчики сообщений aiogram (long polling)."""

    def __init__(self, config: Config) -> None:
        self.bot = Bot(token=config.telegram_token)
        self.dp = Dispatcher()
        self.dp.message.register(self._start, Command("start"))

    async def _start(self, message: Message) -> None:
        logger.info("event=start chat_id=%s", message.chat.id)
        await message.answer(
            "Привет! Я бот-ассистент и я на связи. Скоро научусь отвечать на вопросы."
        )

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)
