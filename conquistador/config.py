"""Central configuration for Conquistador application."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://conquistador:changeme@localhost:5432/conquistador"
    database_url_sync: str = "postgresql://conquistador:changeme@localhost:5432/conquistador"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"

    # AI Engine
    ai_provider: str = "nvidia"  # nvidia, ollama, openrouter, anthropic
    ai_model: str = "meta/llama-3.1-70b-instruct"
    ai_base_url: str = "https://integrate.api.nvidia.com/v1"
    ai_api_key: str = ""
    nvidia_api_key: str = ""
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""

    # Email (SMTP)
    email_host: str = "smtp.zoho.com"
    email_port: int = 465
    email_user: str = ""
    email_pass: str = ""
    email_from: str = "Conquistador Oil <leads@conquistadoroil.com>"

    # Telegram
    telegram_bot_token: str = ""
    admin_telegram_chat_id: str = ""

    # Base URL for links in notifications
    base_url: str = "https://conquistadoroil.com"

    # Business
    business_phone: str = "717-397-9800"
    business_address: str = "931 N Shippen St, Lancaster, PA 17602"
    business_name: str = "Conquistador Oil, Heating & Air Conditioning Inc."

    # CORS — allowed origins for embeddable widget
    cors_origins: list[str] = [
        "https://conquistadoroil.com",
        "https://www.conquistadoroil.com",
        "http://localhost:8000",
    ]

    # Webhooks — notify external site of events
    webhook_url: str = ""  # e.g. https://conquistadoroil.com/api/webhook
    webhook_secret: str = ""  # HMAC signing key for webhook payloads

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
