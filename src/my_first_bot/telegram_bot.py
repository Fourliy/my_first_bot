import logging
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

from .agent import run_agent
from .config import Config
from .llm_client import LLMClient, LLMError

logger = logging.getLogger("my_first_bot")

# Сколько последних реплик чата уходит в модель.
MAX_HISTORY = 20
# Длиннее — в модель уходит усечённый текст: экономим токены и кредиты.
MAX_INPUT_CHARS = 2000
# Лимит Telegram на длину одного сообщения.
TELEGRAM_MAX_CHARS = 4096


class TelegramBot:
    """Обработчики сообщений aiogram (long polling). Ответы — через агентный цикл."""

    def __init__(self, config: Config, llm: LLMClient) -> None:
        self._llm = llm
        self._system_prompt = config.system_prompt
        self._history: dict[int, list[dict]] = {}  # chat_id → реплики user/assistant
        self.bot = Bot(token=config.telegram_token)
        self.dp = Dispatcher()
        self.dp.message.register(self._start, Command("start"))
        self.dp.message.register(self._on_text, F.text)
        self.dp.message.register(self._on_other)  # стикеры, фото, голосовые и т.д.

    async def _start(self, message: Message) -> None:
        logger.info("event=start chat_id=%s", message.chat.id)
        await message.answer(
            "Здравствуйте! Я консультант компании: расскажу про курсы, услуги и портфолио "
            "и помогу оставить заявку на консультацию. Задайте свой вопрос."
        )

    async def _on_other(self, message: Message) -> None:
        logger.info("event=message chat_id=%s content=non_text", message.chat.id)
        await message.answer("Я понимаю только текстовые сообщения. Напишите вопрос текстом.")

    async def _on_text(self, message: Message) -> None:
        chat_id = message.chat.id
        text = (message.text or "").strip()
        logger.info("event=message chat_id=%s message_len=%s", chat_id, len(text))
        if not text:
            await message.answer("Напишите вопрос текстом.")
            return
        await self.bot.send_chat_action(chat_id, ChatAction.TYPING)
        history = self._history.setdefault(chat_id, [])
        history.append({"role": "user", "content": text[:MAX_INPUT_CHARS]})
        del history[:-MAX_HISTORY]
        system = f"Сегодня {date.today().isoformat()}.\n{self._system_prompt}"
        messages = [{"role": "system", "content": system}, *history]
        try:
            reply = await run_agent(self._llm, messages, chat_id)
        except LLMError as e:
            history.pop()  # неудачный вопрос не засоряет контекст
            await message.answer(e.user_message)
            return
        except Exception:
            logger.error("event=agent_error chat_id=%s", chat_id, exc_info=True)
            history.pop()
            await message.answer("Произошла ошибка. Попробуйте ещё раз чуть позже.")
            return
        history.append({"role": "assistant", "content": reply})
        del history[:-MAX_HISTORY]
        await message.answer(reply[:TELEGRAM_MAX_CHARS])

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)
