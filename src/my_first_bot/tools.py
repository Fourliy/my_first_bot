import json
import logging

from .leads import save_lead

logger = logging.getLogger("my_first_bot")

TOOLS: list[dict] = [
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


TOOL_HANDLERS = {"capture_lead": capture_lead}


async def run_tool(name: str, arguments: str, chat_id: int) -> str:
    """Вызывает инструмент по имени. Сбой не роняет агента: модель получает текст ошибки."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"Инструмент {name} недоступен."
    try:
        return await handler(arguments, chat_id)
    except Exception:
        logger.error("event=tool_error tool=%s chat_id=%s", name, chat_id, exc_info=True)
        return "Не удалось сохранить заявку. Попроси пользователя повторить имя и контакт."
