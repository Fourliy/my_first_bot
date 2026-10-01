import re

from aiogram.types import Message

from .config import Config


class AlertHandler:
    """Распознаёт сообщение-оповещение по правилу из окружения (ALERT_*)."""

    def __init__(self, config: Config) -> None:
        self._chat_id = config.alert_chat_id
        self._sender_id = config.alert_sender_id
        try:
            self._pattern = (
                re.compile(config.alert_pattern, re.IGNORECASE) if config.alert_pattern else None
            )
        except re.error as e:
            raise RuntimeError(f"Некорректный ALERT_PATTERN: {e}") from e

    @property
    def enabled(self) -> bool:
        return any(v is not None for v in (self._chat_id, self._sender_id, self._pattern))

    def is_alert(self, message: Message) -> bool:
        """Сообщение — оповещение, если совпали все заданные условия."""
        if not self.enabled:
            return False
        if self._chat_id is not None and message.chat.id != self._chat_id:
            return False
        if self._sender_id is not None and _sender_id(message) != self._sender_id:
            return False
        if self._pattern is not None and not self._pattern.search(message.text or ""):
            return False
        return True


def _sender_id(message: Message) -> int | None:
    # В каналах автора-пользователя нет, отправитель — сам канал.
    if message.from_user:
        return message.from_user.id
    if message.sender_chat:
        return message.sender_chat.id
    return None
