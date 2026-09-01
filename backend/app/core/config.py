from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    reminder_lead_hours: int = 24

    # How long "recuérdame más tarde" waits. Worth lowering to a minute or two for a demo.
    reminder_snooze_minutes: int = 60

    # Telegram. Leaving the token unset is a supported mode: the notification port falls
    # back to logging, which is exactly how the project behaved before the bot existed.
    telegram_bot_token: str | None = None
    telegram_bot_username: str = "where_do_x_bot"

    # The database stores UTC and the web client converts in the browser. Telegram has no
    # browser, so the bot needs to be told which wall clock its readers are on.
    display_timezone: str = "America/Santiago"


@lru_cache
def get_settings() -> Settings:
    return Settings()
