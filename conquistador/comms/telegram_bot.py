"""Telegram bot for contractor notifications and admin alerts."""

import logging
import httpx
from conquistador.config import get_settings

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: str, text: str, reply_markup: dict | None = None) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot not configured, skipping message to %s", chat_id)
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            response.raise_for_status()
        logger.info("Telegram message sent to %s", chat_id)
        return True
    except Exception as e:
        logger.error("Failed to send Telegram message to %s: %s", chat_id, e)
        return False


async def send_admin_alert(text: str) -> bool:
    """Send an alert to the admin Telegram chat."""
    settings = get_settings()
    if not settings.admin_telegram_chat_id:
        logger.warning("Admin Telegram chat not configured")
        return False
    return await send_telegram_message(settings.admin_telegram_chat_id, text)
