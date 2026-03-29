"""Customer notification — text updates on lead status changes."""

import logging
from conquistador.comms.sms import send_sms
from conquistador.comms.email import send_email

logger = logging.getLogger(__name__)


async def notify_customer_assigned(lead) -> bool:
    """Notify customer that a technician has been found."""
    msg = (
        f"Conquistador: Great news, {lead.name or 'there'}! "
        f"We've matched you with a technician for your {_friendly_service(lead.service_type)}. "
        f"They'll reach out shortly to confirm your appointment. "
        f"Questions? Call us at (717) 397-9800."
    )
    return await _send_to_customer(lead, msg)


async def notify_customer_cascading(lead) -> bool:
    """Notify customer we're finding the next available technician."""
    msg = (
        f"Conquistador: We're finding the best available technician for your "
        f"{_friendly_service(lead.service_type)}. "
        f"We'll update you shortly. Call (717) 397-9800 if urgent."
    )
    return await _send_to_customer(lead, msg)


async def notify_customer_accepted(lead) -> bool:
    """Notify customer that a technician has accepted and is on the way."""
    msg = (
        f"Conquistador: Your technician is confirmed for your "
        f"{_friendly_service(lead.service_type)}! "
        f"They'll contact you to finalize timing. "
        f"Thank you for choosing Conquistador!"
    )
    return await _send_to_customer(lead, msg)


async def _send_to_customer(lead, message: str) -> bool:
    """Send a message to customer via SMS (preferred) or email."""
    sent = False

    # Try SMS first
    if lead.phone and lead.carrier and lead.carrier != "other":
        sent = await send_sms(lead.phone, lead.carrier, message)

    # Also send email if available
    if lead.email:
        html_body = f"<p>{message}</p>"
        email_sent = await send_email(lead.email, "Conquistador Service Update", html_body)
        sent = sent or email_sent

    if not sent:
        logger.warning("Could not notify customer for lead %d — no valid contact", lead.id)

    return sent


def _friendly_service(service_type: str) -> str:
    """Convert service_type slug to friendly display name."""
    labels = {
        "heating_oil": "heating oil delivery",
        "hvac_repair": "HVAC repair",
        "hvac_install": "HVAC installation",
        "furnace_maintenance": "furnace maintenance",
        "ac_service": "AC service",
        "emergency": "emergency service",
    }
    return labels.get(service_type, "service request")
