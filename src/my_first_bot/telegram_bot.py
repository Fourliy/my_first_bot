import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from .alert_handler import AlertHandler
from .config import Config
from .llm_client import LLMClient
from .models import Ticket
from .ticket_service import TicketService

logger = logging.getLogger("my_first_bot")

# Длиннее — в заявку уходит усечённый текст: экономим токены и кредиты.
MAX_INPUT_CHARS = 2000
# Лимит Telegram на длину одного сообщения.
TELEGRAM_MAX_CHARS = 4096
MAX_TITLE_CHARS = 80


class TelegramBot:
    """Обработчики сообщений aiogram (long polling). Бот — оповещатель, диалога нет."""

    def __init__(
        self, config: Config, llm: LLMClient, alerts: AlertHandler, tickets: TicketService
    ) -> None:
        self._llm = llm
        self._alerts = alerts
        self._tickets = tickets
        self._system_prompt = config.system_prompt
        self._ticket_prompt = config.ticket_prompt
        self._notify_chat_id = config.notify_chat_id
        self.bot = Bot(token=config.telegram_token)
        self.dp = Dispatcher()
        self.dp.message.register(self._start, Command("start"))
        self.dp.message.register(self._on_text, F.text)
        self.dp.message.register(self._on_other)  # стикеры, фото, голосовые и т.д.
        # В группах Telegram не доставляет сообщения других ботов, а в канале, где бот —
        # администратор, приходят посты любых авторов.
        self.dp.channel_post.register(self._on_channel_post, F.text)

    async def _start(self, message: Message) -> None:
        logger.info("event=start chat_id=%s", message.chat.id)
        await message.answer(
            "Я бот-оповещатель технической поддержки. На оповещения Zabbix создаю заявку "
            "и сообщаю о ней в чат. В диалог не вступаю."
        )

    async def _on_other(self, message: Message) -> None:
        logger.info("event=message chat_id=%s content=non_text", message.chat.id)

    async def _on_channel_post(self, message: Message) -> None:
        if self._alerts.is_alert(message):
            await self._on_alert(message)
            return
        logger.info(
            "event=message chat_id=%s message_len=%s", message.chat.id, len(message.text or "")
        )

    async def _on_text(self, message: Message) -> None:
        text = message.text or ""
        logger.info("event=message chat_id=%s message_len=%s", message.chat.id, len(text))
        if text.strip() and self._alerts.is_alert(message):
            await self._on_alert(message)

    async def _on_alert(self, message: Message) -> None:
        chat_id, message_id = message.chat.id, message.message_id
        logger.info("event=alert_detected chat_id=%s message_id=%s", chat_id, message_id)
        if await self._tickets.get_by_source(chat_id, message_id):
            logger.info("event=alert_duplicate chat_id=%s message_id=%s", chat_id, message_id)
            return
        title, description = await self._describe_alert(message.text or "")
        try:
            ticket = await self._tickets.create(title, description, chat_id, message_id)
        except Exception:
            logger.error("event=ticket_error chat_id=%s", chat_id, exc_info=True)
            await self.bot.send_message(
                self._notify_chat_id or chat_id, "Не удалось создать заявку по оповещению."
            )
            return
        await self._notify(
            ticket, f"Заявка №{ticket.id} создана: {ticket.title}\n\n{ticket.description}"
        )

    async def _describe_alert(self, text: str) -> tuple[str, str]:
        """Тема и описание заявки от LLM; при сбое — исходный текст оповещения."""
        text = text.strip()
        try:
            reply = await self._llm.chat(
                [
                    {
                        "role": "system",
                        "content": f"{self._system_prompt}\n\n{self._ticket_prompt}",
                    },
                    {"role": "user", "content": text[:MAX_INPUT_CHARS]},
                ]
            )
            reply = reply.strip()
            title, sep, description = reply.partition("\n")
            if not sep:  # модель иногда пишет тему и описание одной строкой
                title, sep, description = reply.partition(". ")
            if title.strip():
                return title.strip()[:MAX_TITLE_CHARS], description.strip() or text
        except Exception:
            logger.error("event=llm_error alert=true", exc_info=True)
        return (text.splitlines() or [""])[0][:MAX_TITLE_CHARS], text

    async def close_ticket(self, ticket_id: int) -> None:
        """Закрывает заявку и сообщает об этом. Вызов появится вместе с реальной системой заявок."""
        ticket = await self._tickets.close(ticket_id)
        await self._notify(ticket, f"Заявка №{ticket.id} закрыта: {ticket.title}")

    async def _notify(self, ticket: Ticket, text: str) -> None:
        await self.bot.send_message(
            self._notify_chat_id or ticket.source_chat_id, text[:TELEGRAM_MAX_CHARS]
        )

    async def run(self) -> None:
        await self.dp.start_polling(self.bot)
