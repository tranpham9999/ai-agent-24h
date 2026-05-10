from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM (OpenAI-compatible, e.g. DeepSeek)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # Telegram
    telegram_bot_token: str = ""

    # Default Telegram chat for scheduled briefings
    default_telegram_chat_id: str = ""

    # Schedule (24h)
    briefing_morning_hour: int = 7
    briefing_midday_hour: int = 12
    briefing_evening_hour: int = 20

    # Cache
    cache_ttl_seconds: int = 300

    # App
    app_version: str = "0.1.0"
