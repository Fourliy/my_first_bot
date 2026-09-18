from pydantic import BaseSettings

class Config(BaseSettings):
    TELEGRAM_TOKEN: str
    OPENROUTER_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"