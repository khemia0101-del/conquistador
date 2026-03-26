"""SMTP email sender (Zoho, Gmail, or any SMTP provider)."""

import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from conquistador.config import get_settings

logger = logging.getLogger(__name__)


def _send_smtp(host: str, port: int, user: str, password: str, msg: MIMEMultipart):
    """Blocking SMTP send — run via asyncio.to_thread()."""
    with smtplib.SMTP_SSL(host, port) as server:
        server.login(user, password)
        server.send_message(msg)


async def send_email(to: str, subject: str, body: str, html: bool = True) -> bool:
    """Send an email via SMTP. Returns True on success."""
    settings = get_settings()
    if not settings.email_user or not settings.email_pass:
        logger.warning("Email not configured, skipping send to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type))

    try:
        await asyncio.to_thread(
            _send_smtp, settings.email_host, settings.email_port,
            settings.email_user, settings.email_pass, msg,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False
