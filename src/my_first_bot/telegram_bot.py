import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from .config import Config
from .llm_client import LLMClient
from .models import Dialog, DialogMessage

logger = logging.getLogger("my_first_bot")

# Сколько последних сообщений чата отправляется в модель (10 пар вопрос-ответ).
MAX_HISTORY = 20


class TelegramBot:
    """Обработчики сообщений aiogram (long polling)."""

    def __init__(self, config: Config, llm: LLMClient) -> None:
        self._llm = llm
        self._system_prompt = config.system_prompt
        self._dialogs: dict[int, Dialog] = {}  # chat_id -> история (только в памяти)
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
        dialog = self._dialogs.setdefault(message.chat.id, Dialog())
        # Сообщения одного чата обрабатываются по очереди, чтобы история не путалась.
        async with dialog.lock:
            dialog.messages.append(DialogMessage("user", message.text))
            try:
                # Новое сообщение уже в истории, поэтому окно режем до отправки.
                # Системный промпт добавляется в каждый запрос и не хранится в истории.
                messages = [
                    {"role": "system", "content": self._system_prompt},
                    *dialog.to_llm_messages(MAX_HISTORY),
                ]
                reply = await self._llm.chat(messages)
            except Exception:
                dialog.messages.pop()  # не оставляем вопрос без ответа в истории
                logger.error(
                    "event=llm_error chat_id=%s", message.chat.id, exc_info=True
                )
                await message.answer("Не удалось получить ответ, попробуйте позже.")
                return
            if reply:
                dialog.messages.append(DialogMessage("assistant", reply))
                dialog.trim(MAX_HISTORY)
            else:
                dialog.messages.pop()
            logger.info(
                "event=dialog chat_id=%s history_len=%s",
                message.chat.id,
                len(dialog.messages),
            )
        await message.answer(reply or "Модель вернула пустой ответ.")

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)
