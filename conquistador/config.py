"""Central configuration for Conquistador application."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://conquistador:changeme@localhost:5432/conquistador"
    database_url_sync: str = "postgresql://conquistador:changeme@localhost:5432/conquistador"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"

    # AI Engine
    ai_provider: str = "ollama"  # ollama, openrouter, anthropic
    ai_model: str = "llama3.1:8b"
    ai_base_url: str = "http://localhost:11434/v1"
    ai_api_key: str = "ollama"

    # Email
    email_user: str = ""
    email_pass: str = ""
    email_from: str = "Conquistador Oil <leads@conquistadoroil.com>"

    # Telegram
    telegram_bot_token: str = ""
    admin_telegram_chat_id: str = ""

    # Business
    business_phone: str = "717-397-9800"
    business_address: str = "931 N Shippen St, Lancaster, PA 17602"
    business_name: str = "Conquistador Oil, Heating & Air Conditioning Inc."

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Service area zip codes
    service_zips: list[str] = [
        # Lancaster County
        "17601", "17602", "17603", "17604", "17605", "17606",
        "17543", "17545", "17554", "17557", "17560", "17572", "17576", "17584",
        # York County
        "17401", "17402", "17403", "17404", "17405", "17406", "17407",
        # Harrisburg / Dauphin County
        "17101", "17102", "17103", "17104", "17105", "17106", "17107",
        "17108", "17109", "17110", "17111", "17112",
        # Lebanon County
        "17042", "17046",
        # Berks County / Reading
        "19601", "19602", "19603", "19604", "19605", "19606",
        "19607", "19608", "19609", "19610", "19611",
    ]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
