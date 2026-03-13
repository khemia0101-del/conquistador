"""Free SMS via email-to-SMS carrier gateways."""

import logging
from conquistador.comms.email import send_email

logger = logging.getLogger(__name__)

CARRIER_GATEWAYS = {
    "verizon": "@vtext.com",
    "att": "@txt.att.net",
    "tmobile": "@tmomail.net",
    "sprint": "@messaging.sprintpcs.com",
    "uscellular": "@email.uscc.net",
}


async def send_sms(phone: str, carrier: str, message: str) -> bool:
    """Send SMS via email-to-SMS gateway. Returns True on success."""
    # Strip non-numeric characters from phone
    phone_clean = "".join(c for c in phone if c.isdigit())
    if len(phone_clean) == 11 and phone_clean.startswith("1"):
        phone_clean = phone_clean[1:]  # Remove country code

    carrier_key = carrier.lower().replace("-", "").replace(" ", "")
    gateway = CARRIER_GATEWAYS.get(carrier_key)

    if not gateway:
        logger.warning("Unknown carrier '%s' for phone %s, cannot send SMS", carrier, phone)
        return False

    gateway_email = f"{phone_clean}{gateway}"
    # SMS messages are plain text, no subject needed
    return await send_email(gateway_email, "", message, html=False)
