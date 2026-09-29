import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from .config import Config
from .llm_client import LLMClient

logger = logging.getLogger("my_first_bot")


class TelegramBot:
    """Обработчики сообщений aiogram (long polling)."""

    def __init__(self, config: Config, llm: LLMClient) -> None:
        self._llm = llm
        self.bot = Bot(token=config.telegram_token)
        self.dp = Dispatcher()
        self.dp.message.register(self._start, Command("start"))
        self.dp.message.register(self._on_text, F.text)

    async def _start(self, message: Message) -> None:
        logger.info("event=start chat_id=%s", message.chat.id)
        await message.answer(
            "Привет! Я бот-ассистент и я на связи. Напиши мне вопрос, и я отвечу."
        )

    async def _on_text(self, message: Message) -> None:
        logger.info(
            "event=message chat_id=%s message_len=%s", message.chat.id, len(message.text)
        )
        try:
            reply = await self._llm.chat([{"role": "user", "content": message.text}])
        except Exception:
            logger.error("event=llm_error chat_id=%s", message.chat.id, exc_info=True)
            await message.answer("Не удалось получить ответ, попробуйте позже.")
            return
        await message.answer(reply or "Модель вернула пустой ответ.")

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)
