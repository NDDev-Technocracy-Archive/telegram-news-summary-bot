from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
    )

    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str

    DATABASE_PATH: str = "bot.db"
    MAX_CHANNELS_PER_USER: int = 10
    MAX_SCROLLS: int = 100
    OPENAI_MODEL: str = "gpt-4o-mini"


settings = Settings()
