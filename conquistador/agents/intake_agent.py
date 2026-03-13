"""Intake Agent — chatbot, lead capture, qualification, scheduling.

Runs as the WebSocket service via FastAPI. The actual implementation is in
conquistador.chatbot.engine — this module provides the lead scoring logic
and ties the chatbot to the routing pipeline.
"""

import logging
from conquistador.config import get_settings

logger = logging.getLogger(__name__)

# Lead scoring factors
URGENCY_SCORES = {"emergency": 40, "urgent": 25, "routine": 10}
SERVICE_SCORES = {
    "hvac_install": 30,
    "hvac_repair": 25,
    "heating_oil": 20,
    "furnace_maintenance": 15,
    "ac_service": 15,
    "emergency": 35,
}


def calculate_lead_score(lead_data: dict) -> int:
    """Calculate a lead quality score from 1-100."""
    score = 0
    score += URGENCY_SCORES.get(lead_data.get("urgency", ""), 10)
    score += SERVICE_SCORES.get(lead_data.get("service_type", ""), 15)

    # Bonus for complete contact info
    if lead_data.get("email"):
        score += 10
    if lead_data.get("phone"):
        score += 10
    if lead_data.get("address"):
        score += 10

    return min(score, 100)
