"""Post-service survey system."""

import logging
import secrets
from conquistador.comms.email import send_email
from conquistador.comms.sms import send_sms

logger = logging.getLogger(__name__)


def generate_survey_token() -> str:
    """Generate a secure survey access token."""
    return secrets.token_urlsafe(32)


async def send_survey(lead, contractor) -> bool:
    """Send a post-service survey link to the customer."""
    token = generate_survey_token()
    from conquistador.config import get_settings
    settings = get_settings()
    survey_url = f"{settings.base_url}/review/{lead.id}?token={token}"

    body = f"""
    <h2>How was your service?</h2>
    <p>Hi {lead.name or 'there'},</p>
    <p>We'd love to hear about your recent service from Conquistador.</p>
    <p>Please take a moment to rate your experience:</p>
    <p><a href="{survey_url}" style="background:#f97316;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;">Rate Your Service</a></p>
    <p>Thank you for choosing Conquistador!</p>
    """

    sent = False

    # Try email first
    if lead.email:
        sent = await send_email(lead.email, "How was your service? - Conquistador", body)

    # Also try SMS
    if lead.phone and lead.carrier and lead.carrier != "other":
        sms_msg = f"Conquistador: How was your service? Rate it here: {survey_url}"
        sms_sent = await send_sms(lead.phone, lead.carrier, sms_msg)
        sent = sent or sms_sent

    if sent:
        logger.info("Survey sent for lead %d", lead.id)
    else:
        logger.warning("Could not send survey for lead %d — no valid contact", lead.id)

    return sent
