import logging

from .llm_client import LLMClient
from .tools import TOOLS, run_tool

logger = logging.getLogger("my_first_bot")

# Защита от бесконечного цикла инструментов.
MAX_STEPS = 5
NO_ANSWER = "Не удалось подготовить ответ. Попробуйте переформулировать вопрос."


async def run_agent(llm: LLMClient, messages: list[dict], chat_id: int) -> str:
    """Цикл tool calling: запрос к модели → вызов инструментов → повтор, пока нет текста."""
    messages = list(messages)  # историю чата не меняем: сюда попадают служебные сообщения
    for _ in range(MAX_STEPS):
        message = await llm.chat(messages, tools=TOOLS or None)
        if not message.tool_calls:
            return (message.content or "").strip() or NO_ANSWER
        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            logger.info("event=tool_call chat_id=%s tool=%s", chat_id, call.function.name)
            result = await run_tool(call.function.name, call.function.arguments)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    logger.warning("event=agent_limit chat_id=%s", chat_id)
    return NO_ANSWER
