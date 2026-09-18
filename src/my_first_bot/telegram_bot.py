from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from .config import Config
from .logger import setup_logger

def setup_bot(config: Config):
    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = Dispatcher()
    setup_logger(config.LOG_LEVEL)

    @dp.message(Command("start"))
    async def send_welcome(message: types.Message):
        await message.reply("Привет! Я — ваш LLM-ассистент.")

    return bot, dp
```
```tool
TOOL_NAME: edit_existing_file
BEGIN_ARG: filepath
"src/my_first_bot/runner.py"
