import asyncio
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("my_first_bot")

DB_PATH = Path("data/leads.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def init_db() -> None:
    conn = _connect()
    conn.close()


def _save_sync(name: str, contact: str, chat_id: int) -> int:
    conn = _connect()
    try:
        cursor = conn.execute(
            "INSERT INTO leads (name, contact, chat_id, created_at) VALUES (?, ?, ?, datetime('now'))",
            (name, contact, chat_id),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


async def save_lead(name: str, contact: str, chat_id: int) -> int:
    """Пишет лида в sqlite вне цикла событий. Контакт в лог не попадает."""
    return await asyncio.to_thread(_save_sync, name, contact, chat_id)
