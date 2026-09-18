from aiogram.utils import executor
from .telegram_bot import setup_bot
from .config import Config

def run():
    config = Config()
    dp = setup_bot(config)
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    run()
