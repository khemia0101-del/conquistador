"""Extract structured lead data from chatbot conversations."""

import json
import logging
from conquistador.ai.engine import get_ai_engine
from conquistador.chatbot.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


def lead_complete(conversation: list[dict]) -> bool:
    """Check if the conversation has collected all lead info."""
    if not conversation:
        return False
    last_msg = conversation[-1].get("content", "")
    return "[LEAD_COMPLETE]" in last_msg


async def extract_lead_data(conversation: list[dict]) -> dict | None:
    """Use AI to extract structured lead data from the conversation."""
    engine = get_ai_engine()
    try:
        raw = await engine.extract_json(conversation, EXTRACTION_PROMPT)
        # Try to parse JSON from the response
        # Handle cases where model wraps in markdown code blocks
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        data = json.loads(cleaned)
        logger.info("Extracted lead data: %s", data)
        return data
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Failed to extract lead data: %s", e)
        return None
