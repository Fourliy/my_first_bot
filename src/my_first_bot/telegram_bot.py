import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from .config import Config
from .llm_client import LLMClient, LLMError
from .models import Dialog, DialogMessage

logger = logging.getLogger("my_first_bot")

# Сколько последних сообщений чата отправляется в модель (10 пар вопрос-ответ).
MAX_HISTORY = 20
# Длиннее — отказываем: экономим токены и кредиты.
MAX_INPUT_CHARS = 2000
# Лимит Telegram на длину одного сообщения.
TELEGRAM_MAX_CHARS = 4096


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
        self.dp.message.register(self._on_other)  # стикеры, фото, голосовые и т.д.

    async def _start(self, message: Message) -> None:
        logger.info("event=start chat_id=%s", message.chat.id)
        await message.answer(
            "Привет! Я бот-ассистент и я на связи. Напиши мне вопрос, и я отвечу."
        )

    async def _on_other(self, message: Message) -> None:
        logger.info("event=unsupported chat_id=%s", message.chat.id)
        await message.answer("Я понимаю только текстовые сообщения. Напишите вопрос словами.")

    async def _on_text(self, message: Message) -> None:
        chat_id = message.chat.id
        text = message.text
        logger.info("event=message chat_id=%s message_len=%s", chat_id, len(text))
        if not text.strip():
            await message.answer("Сообщение пустое. Напишите вопрос словами.")
            return
        if len(text) > MAX_INPUT_CHARS:
            logger.info("event=too_long chat_id=%s message_len=%s", chat_id, len(text))
            await message.answer(
                f"Сообщение слишком длинное ({len(text)} символов). "
                f"Пожалуйста, сократите его до {MAX_INPUT_CHARS}."
            )
            return

        dialog = self._dialogs.setdefault(chat_id, Dialog())
        # Сообщения одного чата обрабатываются по очереди, чтобы история не путалась.
        async with dialog.lock:
            dialog.messages.append(DialogMessage("user", text))
            try:
                # Новое сообщение уже в истории, поэтому окно режем до отправки.
                # Системный промпт добавляется в каждый запрос и не хранится в истории.
                messages = [
                    {"role": "system", "content": self._system_prompt},
                    *dialog.to_llm_messages(MAX_HISTORY),
                ]
                reply = await self._llm.chat(messages)
            except Exception as e:
                dialog.messages.pop()  # не оставляем вопрос без ответа в истории
                logger.error("event=llm_error chat_id=%s", chat_id, exc_info=True)
                user_message = (
                    e.user_message
                    if isinstance(e, LLMError)
                    else "Не удалось получить ответ, попробуйте позже."
                )
                await message.answer(user_message)
                return
            dialog.messages.append(DialogMessage("assistant", reply))
            dialog.trim(MAX_HISTORY)
            logger.info(
                "event=dialog chat_id=%s history_len=%s", chat_id, len(dialog.messages)
            )
        await message.answer(reply[:TELEGRAM_MAX_CHARS])

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)
