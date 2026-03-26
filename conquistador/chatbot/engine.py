"""WebSocket chat handler for the intake chatbot."""

import json
import logging
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.ai.engine import get_ai_engine
from conquistador.chatbot.prompts import SYSTEM_PROMPT
from conquistador.chatbot.extractor import lead_complete, extract_lead_data
from conquistador.models.lead import Lead
from conquistador.agents.intake_agent import calculate_lead_score

logger = logging.getLogger(__name__)


async def chat_handler(websocket: WebSocket, db: AsyncSession):
    """Handle a chatbot WebSocket connection."""
    await websocket.accept()
    conversation: list[dict] = []
    engine = get_ai_engine()

    try:
        while True:
            user_msg = await websocket.receive_text()
            conversation.append({"role": "user", "content": user_msg})

            reply = await engine.chat(conversation, SYSTEM_PROMPT)
            conversation.append({"role": "assistant", "content": reply})

            # Strip the completion marker before sending to user
            display_reply = reply.replace("[LEAD_COMPLETE]", "").strip()
            await websocket.send_text(display_reply)

            if lead_complete(conversation):
                lead_data = await extract_lead_data(conversation)
                if lead_data:
                    score = calculate_lead_score(lead_data)
                    lead = Lead(
                        name=lead_data.get("name"),
                        phone=lead_data.get("phone", "unknown"),
                        carrier=lead_data.get("carrier"),
                        email=lead_data.get("email"),
                        address=lead_data.get("address"),
                        zip_code=lead_data.get("zip_code", "00000"),
                        service_type=lead_data.get("service_type", "unknown"),
                        urgency=lead_data.get("urgency", "routine"),
                        description=lead_data.get("description"),
                        conversation_log=conversation,
                        lead_score=score,
                        source="chatbot",
                        status="new",
                    )
                    db.add(lead)
                    await db.commit()
                    await db.refresh(lead)
                    logger.info("Lead %d saved from chatbot", lead.id)

                    # Trigger routing asynchronously
                    from conquistador.routing.matcher import route_lead
                    await route_lead(lead, db)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("Chat handler error: %s", e)
