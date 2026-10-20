from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


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
