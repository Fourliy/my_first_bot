import logging

logger = logging.getLogger("my_first_bot")

# Схемы инструментов для chat completions. Пока пусто: rag_search, web_search и
# capture_lead добавляются в итерациях 12–14.
TOOLS: list[dict] = []
TOOL_HANDLERS: dict = {}


async def run_tool(name: str, arguments: str) -> str:
    """Вызывает инструмент по имени. Сбой не роняет агента: модель получает текст ошибки."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"Инструмент {name} недоступен."
    try:
        return await handler(arguments)
    except Exception:
        logger.error("event=tool_error tool=%s", name, exc_info=True)
        return "Инструмент не сработал. Сообщи пользователю, что не удалось выполнить действие."
