"""Lead submission and status API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.models.lead import Lead
from conquistador.routing.matcher import route_lead
from conquistador.agents.intake_agent import calculate_lead_score
from conquistador.config import get_settings

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadCreate(BaseModel):
    name: str | None = None
    phone: str
    carrier: str | None = None
    email: str | None = None
    address: str | None = None
    zip_code: str
    service_type: str
    urgency: str = "routine"
    property_type: str | None = None
    description: str | None = None


class LeadStatus(BaseModel):
    id: int
    status: str
    service_type: str
    created_at: str


@router.post("/", response_model=dict)
async def submit_lead(lead_data: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Submit a lead via the contact form."""
    settings = get_settings()

    # Validate zip code is in service area
    if lead_data.zip_code not in settings.service_zips:
        raise HTTPException(status_code=400, detail="Sorry, we don't serve that area yet.")

    lead_dict = lead_data.model_dump()
    score = calculate_lead_score(lead_dict)

    lead = Lead(
        **lead_dict,
        lead_score=score,
        source="form",
        status="new",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Route to contractors
    await route_lead(lead, db)

    # Notify Manus site via webhook
    from conquistador.web.routes.webhooks import fire_webhook
    await fire_webhook("lead.created", {
        "id": lead.id,
        "service_type": lead.service_type,
        "zip_code": lead.zip_code,
        "urgency": lead.urgency,
        "lead_score": lead.lead_score,
        "status": lead.status,
    })

    return {"id": lead.id, "status": "submitted", "message": "We'll be in touch shortly!"}


@router.get("/{lead_id}/status", response_model=LeadStatus)
async def get_lead_status(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Check lead status (public, no auth needed)."""
    stmt = select(Lead).where(Lead.id == lead_id)
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return LeadStatus(
        id=lead.id,
        status=lead.status,
        service_type=lead.service_type,
        created_at=lead.created_at.isoformat(),
    )
