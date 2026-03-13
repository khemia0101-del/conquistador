"""Contractor dashboard and API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.models.lead import Lead
from conquistador.web.auth import (
    get_current_contractor, verify_password, create_access_token
)
from conquistador.agents.contractor_mgmt import handle_lead_acceptance, handle_lead_decline

router = APIRouter(tags=["contractor"])
templates = Jinja2Templates(directory="templates")


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/api/auth/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Contractor).where(Contractor.email == data.email)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()

    if not contractor or not contractor.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, contractor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"contractor_id": contractor.id, "role": "contractor"})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/contractor/leads")
async def get_contractor_leads(
    auth: dict = Depends(get_current_contractor),
    db: AsyncSession = Depends(get_db),
):
    contractor_id = auth["contractor_id"]
    stmt = (
        select(LeadAssignment, Lead)
        .join(Lead, Lead.id == LeadAssignment.lead_id)
        .where(LeadAssignment.contractor_id == contractor_id)
        .order_by(LeadAssignment.assigned_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "assignment_id": assignment.id,
            "lead_id": lead.id,
            "service_type": lead.service_type,
            "zip_code": lead.zip_code,
            "urgency": lead.urgency,
            "description": (lead.description or "")[:100],
            "status": assignment.status,
            "assigned_at": assignment.assigned_at.isoformat(),
        }
        for assignment, lead in rows
    ]


@router.post("/api/contractor/leads/{lead_id}/accept")
async def accept_lead(
    lead_id: int,
    auth: dict = Depends(get_current_contractor),
    db: AsyncSession = Depends(get_db),
):
    contractor_id = auth["contractor_id"]
    stmt = select(LeadAssignment).where(
        and_(
            LeadAssignment.lead_id == lead_id,
            LeadAssignment.contractor_id == contractor_id,
        )
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await handle_lead_acceptance(assignment.id, db)
    return {"status": "accepted"}


@router.post("/api/contractor/leads/{lead_id}/decline")
async def decline_lead(
    lead_id: int,
    auth: dict = Depends(get_current_contractor),
    db: AsyncSession = Depends(get_db),
):
    contractor_id = auth["contractor_id"]
    stmt = select(LeadAssignment).where(
        and_(
            LeadAssignment.lead_id == lead_id,
            LeadAssignment.contractor_id == contractor_id,
        )
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await handle_lead_decline(assignment.id, db)
    return {"status": "declined"}


@router.get("/api/contractor/metrics")
async def get_metrics(
    auth: dict = Depends(get_current_contractor),
    db: AsyncSession = Depends(get_db),
):
    contractor_id = auth["contractor_id"]

    # Get contractor
    stmt = select(Contractor).where(Contractor.id == contractor_id)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()

    # Count leads
    total_stmt = select(func.count(LeadAssignment.id)).where(
        LeadAssignment.contractor_id == contractor_id
    )
    total_result = await db.execute(total_stmt)
    total_leads = total_result.scalar() or 0

    accepted_stmt = select(func.count(LeadAssignment.id)).where(
        and_(
            LeadAssignment.contractor_id == contractor_id,
            LeadAssignment.status == "accepted",
        )
    )
    accepted_result = await db.execute(accepted_stmt)
    accepted_leads = accepted_result.scalar() or 0

    return {
        "total_leads": total_leads,
        "accepted_leads": accepted_leads,
        "acceptance_rate": float(contractor.acceptance_rate or 0),
        "quality_score": float(contractor.quality_score or 0),
        "avg_response_min": float(contractor.avg_response_min or 0),
    }


class ProfileUpdate(BaseModel):
    phone: str | None = None
    email: str | None = None
    service_types: list[str] | None = None
    service_zips: list[str] | None = None
    max_daily_leads: int | None = None
    telegram_chat_id: str | None = None


@router.put("/api/contractor/profile")
async def update_profile(
    data: ProfileUpdate,
    auth: dict = Depends(get_current_contractor),
    db: AsyncSession = Depends(get_db),
):
    contractor_id = auth["contractor_id"]
    stmt = select(Contractor).where(Contractor.id == contractor_id)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()

    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(contractor, key, value)

    await db.commit()
    return {"status": "updated"}
