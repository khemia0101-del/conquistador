"""Unified contractor notification — Telegram + email fallback."""

import json
import logging
from conquistador.comms.telegram_bot import send_telegram_message
from conquistador.comms.email import send_email

logger = logging.getLogger(__name__)


async def notify_contractor(contractor, lead) -> str:
    """Notify contractor of a new lead. Returns the channel used."""
    msg = (
        f"<b>New Lead!</b>\n"
        f"Service: {lead.service_type}\n"
        f"Area: {lead.zip_code}\n"
        f"Urgency: {lead.urgency}\n"
        f"Issue: {(lead.description or '')[:100]}"
    )

    # Try Telegram first
    if contractor.telegram_chat_id:
        reply_markup = {
            "inline_keyboard": [[
                {"text": "Accept", "callback_data": f"accept_{lead.id}"},
                {"text": "Decline", "callback_data": f"decline_{lead.id}"},
            ]]
        }
        success = await send_telegram_message(contractor.telegram_chat_id, msg, reply_markup)
        if success:
            return "telegram"

    # Fallback to email
    if contractor.email:
        email_body = f"""
        <h2>New Lead from Conquistador</h2>
        <p><strong>Service:</strong> {lead.service_type}</p>
        <p><strong>Area:</strong> {lead.zip_code}</p>
        <p><strong>Urgency:</strong> {lead.urgency}</p>
        <p><strong>Issue:</strong> {lead.description or 'N/A'}</p>
        <p>
            <a href="https://conquistadoroil.com/api/contractor/leads/{lead.id}/accept">Accept</a> |
            <a href="https://conquistadoroil.com/api/contractor/leads/{lead.id}/decline">Decline</a>
        </p>
        """
        success = await send_email(contractor.email, "New Lead from Conquistador", email_body)
        if success:
            return "email"

    logger.warning("Could not notify contractor %s — no Telegram or email", contractor.id)
    return "none"
