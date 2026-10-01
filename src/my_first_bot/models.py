import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class DialogMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class Dialog:
    """История одного чата в памяти."""

    messages: list[DialogMessage] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_llm_messages(self, limit: int | None = None) -> list[dict]:
        """Сообщения для модели; при `limit` берутся только последние `limit` штук."""
        messages = self.messages[-limit:] if limit else self.messages
        return [{"role": m.role, "content": m.content} for m in messages]

    def trim(self, limit: int) -> None:
        """FIFO: оставляет только последние `limit` сообщений."""
        if len(self.messages) > limit:
            del self.messages[:-limit]


@dataclass
class Ticket:
    """Сервисная заявка, созданная по оповещению."""

    id: int
    title: str
    description: str
    source_chat_id: int
    source_message_id: int
    status: Literal["open", "closed"] = "open"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None
