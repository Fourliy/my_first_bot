import json
import logging

from bot.tools.rag import rag_search as search_documents

from .leads import save_lead

logger = logging.getLogger("my_first_bot")

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": (
                "Найти фрагменты документов компании: портфолио, услуги, курсы. "
                "Вызывать на вопросы о компании."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "О чём искать в документах"},
                    "n_results": {
                        "type": "integer",
                        "description": "Сколько фрагментов вернуть, по умолчанию 4",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_lead",
            "description": (
                "Записать заявку на консультацию. Вызывать только когда пользователь "
                "назвал и имя, и контакт (телефон, email или Telegram)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Имя клиента"},
                    "contact": {
                        "type": "string",
                        "description": "Телефон, email или Telegram",
                    },
                },
                "required": ["name", "contact"],
            },
        },
    }
]


async def capture_lead(arguments: str, chat_id: int) -> str:
    try:
        data = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "Не хватает имени или контакта. Спроси недостающее, заявку не записывай."
    name = str(data.get("name") or "").strip()
    contact = str(data.get("contact") or "").strip()
    if not name or not contact:
        return "Не хватает имени или контакта. Спроси недостающее, заявку не записывай."
    lead_id = await save_lead(name, contact, chat_id)
    logger.info("event=lead_captured chat_id=%s lead_id=%s tool=capture_lead", chat_id, lead_id)
    return f"Заявка записана, номер {lead_id}. Подтверди пользователю, что заявка принята, и назови номер."


async def rag_search(arguments: str, chat_id: int) -> str:
    try:
        data = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "Пустой запрос. Уточни, что искать в документах."
    query = str(data.get("query") or "").strip()
    if not query:
        return "Пустой запрос. Уточни, что искать в документах."
    try:
        n_results = int(data.get("n_results") or 4)
    except (TypeError, ValueError):
        n_results = 4
    return await search_documents(query, n_results)


TOOL_HANDLERS = {"capture_lead": capture_lead, "rag_search": rag_search}


async def run_tool(name: str, arguments: str, chat_id: int) -> str:
    """Вызывает инструмент по имени. Сбой не роняет агента: модель получает текст ошибки."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"Инструмент {name} недоступен."
    try:
        return await handler(arguments, chat_id)
    except Exception:
        logger.error("event=tool_error tool=%s chat_id=%s", name, chat_id, exc_info=True)
        if name == "capture_lead":
            return "Не удалось сохранить заявку. Попроси пользователя повторить имя и контакт."
        return "Поиск по документам не сработал. Скажи, что сейчас не можешь проверить документы."
