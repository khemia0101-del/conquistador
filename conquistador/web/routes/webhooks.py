"""Webhook routes — notify the Manus site of lead/contractor events."""

import hashlib
import hmac
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.config import get_settings
from conquistador.models.base import get_db

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def _sign_payload(payload: bytes, secret: str) -> str:
    """HMAC-SHA256 signature for outbound webhook payloads."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def fire_webhook(event: str, data: dict):
    """Send an event to the configured webhook URL (Manus site).

    Events:
        lead.created       — new lead submitted
        lead.assigned      — lead matched to contractor
        lead.accepted      — contractor accepted lead
        lead.declined      — contractor declined lead
        lead.completed     — service completed
        lead.unmatched     — no contractors available
        contractor.registered — new contractor signed up
        contractor.activated  — contractor approved & active
        review.submitted   — customer review received
        invoice.created    — invoice generated
    """
    settings = get_settings()
    if not settings.webhook_url:
        return

    payload = json.dumps({"event": event, "data": data}).encode()
    headers = {"Content-Type": "application/json"}
    if settings.webhook_secret:
        headers["X-Conquistador-Signature"] = _sign_payload(payload, settings.webhook_secret)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.webhook_url, content=payload, headers=headers, timeout=10)
            resp.raise_for_status()
        logger.info("Webhook fired: %s", event)
    except Exception as e:
        logger.error("Webhook failed (%s): %s", event, e)


@router.post("/inbound")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive inbound webhooks from the Manus site.

    Supports events like form submissions, page views, etc.
    """
    settings = get_settings()
    body = await request.body()

    # Verify signature if secret is configured
    if settings.webhook_secret:
        sig = request.headers.get("X-Conquistador-Signature", "")
        expected = _sign_payload(body, settings.webhook_secret)
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = json.loads(body)
    event = data.get("event", "unknown")
    logger.info("Inbound webhook received: %s", event)

    # Handle known inbound events from Manus
    if event == "contact_form":
        # Forward to lead submission pipeline
        from conquistador.web.routes.leads import submit_lead, LeadCreate
        lead_data = LeadCreate(**data.get("data", {}))
        return await submit_lead(lead_data, db)

    return {"status": "received", "event": event}
