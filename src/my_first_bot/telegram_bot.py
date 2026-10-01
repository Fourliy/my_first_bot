import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from .alert_handler import AlertHandler
from .config import Config
from .llm_client import LLMClient, LLMError
from .models import Dialog, DialogMessage, Ticket
from .ticket_service import TicketService

logger = logging.getLogger("my_first_bot")

# Сколько последних сообщений чата отправляется в модель (10 пар вопрос-ответ).
MAX_HISTORY = 20
# Длиннее — отказываем: экономим токены и кредиты.
MAX_INPUT_CHARS = 2000
# Лимит Telegram на длину одного сообщения.
TELEGRAM_MAX_CHARS = 4096
MAX_TITLE_CHARS = 80


class TelegramBot:
    """Обработчики сообщений aiogram (long polling)."""

    def __init__(
        self, config: Config, llm: LLMClient, alerts: AlertHandler, tickets: TicketService
    ) -> None:
        self._llm = llm
        self._alerts = alerts
        self._tickets = tickets
        self._system_prompt = config.system_prompt
        self._ticket_prompt = config.ticket_prompt
        self._notify_chat_id = config.notify_chat_id
        self._dialogs: dict[int, Dialog] = {}  # chat_id -> история (только в памяти)
        self.bot = Bot(token=config.telegram_token)
        self.dp = Dispatcher()
        self.dp.message.register(self._start, Command("start"))
        self.dp.message.register(self._on_text, F.text)
        self.dp.message.register(self._on_other)  # стикеры, фото, голосовые и т.д.
        # В группах Telegram не доставляет сообщения других ботов, а в канале, где бот —
        # администратор, приходят посты любых авторов. В каналах диалога нет, только оповещения.
        self.dp.channel_post.register(self._on_channel_post, F.text)

    async def _start(self, message: Message) -> None:
        logger.info("event=start chat_id=%s", message.chat.id)
        await message.answer(
            "Привет! Я бот технической поддержки. Опишите проблему, и я помогу разобраться. "
            "На оповещения о сбоях я создаю сервисную заявку и сообщаю о ней в чат."
        )

    async def _on_other(self, message: Message) -> None:
        logger.info("event=unsupported chat_id=%s", message.chat.id)
        await message.answer("Я понимаю только текстовые сообщения. Напишите вопрос словами.")

    async def _on_channel_post(self, message: Message) -> None:
        if self._alerts.is_alert(message):
            await self._on_alert(message)

    async def _on_text(self, message: Message) -> None:
        chat_id = message.chat.id
        text = message.text
        logger.info("event=message chat_id=%s message_len=%s", chat_id, len(text))
        if not text.strip():
            await message.answer("Сообщение пустое. Напишите вопрос словами.")
            return
        if self._alerts.is_alert(message):
            await self._on_alert(message)
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

    async def _on_alert(self, message: Message) -> None:
        chat_id, message_id = message.chat.id, message.message_id
        logger.info("event=alert_detected chat_id=%s message_id=%s", chat_id, message_id)
        if await self._tickets.get_by_source(chat_id, message_id):
            logger.info("event=alert_duplicate chat_id=%s message_id=%s", chat_id, message_id)
            return
        title, description = await self._describe_alert(message.text)
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
                    {"role": "system", "content": self._ticket_prompt},
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
        return text.splitlines()[0][:MAX_TITLE_CHARS], text

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
