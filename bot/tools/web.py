import asyncio
import logging
import re
from datetime import date

from langsmith import traceable

logger = logging.getLogger("my_first_bot")

UNAVAILABLE = "Поиск в интернете недоступен. Не выдумывай свежие факты."
NOT_FOUND = "В интернете ничего не найдено. Не выдумывай свежие факты."
MAX_RESULTS = 5


def _fresh_query(query: str) -> str:
    """Убирает старый год из запроса модели и добавляет сегодняшнюю дату."""
    today = date.today()

    def keep_current_year(match: re.Match) -> str:
        year = int(match.group(0))
        return match.group(0) if year >= today.year else ""

    cleaned = re.sub(r"\b(?:19|20)\d{2}\b", keep_current_year, query)
    return f"{' '.join(cleaned.split())} {today.isoformat()}"


def _search(query: str) -> list[dict]:
    from tavily import TavilyClient

    from my_first_bot.config import Config

    client = TavilyClient(api_key=Config().tavily_api_key)
    data = client.search(_fresh_query(query), max_results=MAX_RESULTS, timeout=30)
    return data.get("results") or []


@traceable(name="web_search")
async def web_search(query: str) -> str:
    """Краткие результаты Tavily. Сбой поиска не роняет бота."""
    query = (query or "").strip()
    if not query:
        return "Пустой запрос. Не выдумывай свежие факты."
    try:
        results = await asyncio.to_thread(_search, query)
    except Exception:
        logger.error("event=tool_error tool=web_search", exc_info=True)
        return UNAVAILABLE
    if not results:
        return NOT_FOUND
    parts = []
    for item in results[:MAX_RESULTS]:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or "").strip()
        parts.append("\n".join(line for line in (title, url, content) if line))
    body = "\n\n".join(parts)
    if not body:
        return NOT_FOUND
    today = date.today().isoformat()
    return (
        f"Сегодня {today}. Для версий и дат используй только эти результаты, не свою память.\n\n"
        + body
    )
