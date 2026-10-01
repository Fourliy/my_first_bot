import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .models import Ticket

logger = logging.getLogger("my_first_bot")


class TicketService(ABC):
    """Система сервисных заявок. Реальный адаптер заменит заглушку без правок бота."""

    @abstractmethod
    async def create(
        self, title: str, description: str, source_chat_id: int, source_message_id: int
    ) -> Ticket: ...

    @abstractmethod
    async def close(self, ticket_id: int) -> Ticket: ...

    @abstractmethod
    async def get_by_source(self, chat_id: int, message_id: int) -> Ticket | None: ...


class StubTicketService(TicketService):
    """Заглушка: заявки только в памяти, номера по порядку, пропадают при перезапуске."""

    def __init__(self) -> None:
        self._tickets: dict[int, Ticket] = {}
        self._by_source: dict[tuple[int, int], int] = {}
        self._next_id = 1

    async def create(
        self, title: str, description: str, source_chat_id: int, source_message_id: int
    ) -> Ticket:
        ticket = Ticket(self._next_id, title, description, source_chat_id, source_message_id)
        self._next_id += 1
        self._tickets[ticket.id] = ticket
        self._by_source[(source_chat_id, source_message_id)] = ticket.id
        logger.info(
            "event=ticket_created ticket_id=%s chat_id=%s", ticket.id, source_chat_id
        )
        return ticket

    async def close(self, ticket_id: int) -> Ticket:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise ValueError(f"Заявка №{ticket_id} не найдена")
        ticket.status = "closed"
        ticket.closed_at = datetime.now(timezone.utc)
        logger.info("event=ticket_closed ticket_id=%s", ticket_id)
        return ticket

    async def get_by_source(self, chat_id: int, message_id: int) -> Ticket | None:
        ticket_id = self._by_source.get((chat_id, message_id))
        return self._tickets.get(ticket_id) if ticket_id is not None else None
