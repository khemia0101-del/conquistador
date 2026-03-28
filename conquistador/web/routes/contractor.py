"""Contractor dashboard and API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.models.lead import Lead
from conquistador.web.auth import (
    get_current_contractor, get_admin, verify_password,
    create_access_token, hash_password,
)
from conquistador.agents.contractor_mgmt import handle_lead_acceptance, handle_lead_decline
from conquistador.config import BASE_DIR

router = APIRouter(tags=["contractor"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ─── Registration ────────────────────────────────────────────────────────────


class ContractorRegister(BaseModel):
    company_name: str
    contact_name: str
    phone: str
    email: str
    password: str
    address: str | None = None
    license_number: str | None = None
    service_types: list[str]
    service_zips: list[str]
    max_daily_leads: int = 5
    telegram_chat_id: str | None = None


@router.post("/api/contractors/register")
async def register_contractor(data: ContractorRegister, db: AsyncSession = Depends(get_db)):
    """Self-registration for new contractors. Account starts inactive pending admin approval."""
    # Check for duplicate email
    existing = await db.execute(select(Contractor).where(Contractor.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A contractor with this email already exists")

    contractor = Contractor(
        company_name=data.company_name,
        contact_name=data.contact_name,
        phone=data.phone,
        email=data.email,
        password_hash=hash_password(data.password),
        address=data.address,
        license_number=data.license_number,
        service_types=data.service_types,
        service_zips=data.service_zips,
        max_daily_leads=data.max_daily_leads,
        telegram_chat_id=data.telegram_chat_id,
        is_active=False,  # requires admin approval
    )
    db.add(contractor)
    await db.commit()
    await db.refresh(contractor)

    # Fire webhook to notify Manus site
    from conquistador.web.routes.webhooks import fire_webhook
    await fire_webhook("contractor.registered", {
        "id": contractor.id,
        "company_name": contractor.company_name,
        "email": contractor.email,
    })

    # Notify admin
    from conquistador.comms.telegram_bot import send_admin_alert
    await send_admin_alert(
        f"<b>New Contractor Registration</b>\n\n"
        f"Company: {contractor.company_name}\n"
        f"Contact: {contractor.contact_name}\n"
        f"Phone: {contractor.phone}\n"
        f"Email: {contractor.email}\n"
        f"License: {contractor.license_number or 'N/A'}\n"
        f"Services: {', '.join(contractor.service_types)}\n"
        f"Zips: {', '.join(contractor.service_zips[:5])}{'...' if len(contractor.service_zips) > 5 else ''}"
    )

    return {
        "id": contractor.id,
        "status": "pending_approval",
        "message": "Registration received. Your account will be activated after admin review.",
    }


@router.post("/api/contractors/{contractor_id}/activate")
async def activate_contractor(
    contractor_id: int,
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: activate a contractor's account."""
    stmt = select(Contractor).where(Contractor.id == contractor_id)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    contractor.is_active = True
    await db.commit()

    from conquistador.web.routes.webhooks import fire_webhook
    await fire_webhook("contractor.activated", {
        "id": contractor.id,
        "company_name": contractor.company_name,
    })

    return {"status": "activated", "contractor_id": contractor.id}


@router.post("/api/contractors/{contractor_id}/deactivate")
async def deactivate_contractor(
    contractor_id: int,
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: deactivate a contractor's account."""
    stmt = select(Contractor).where(Contractor.id == contractor_id)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    contractor.is_active = False
    await db.commit()
    return {"status": "deactivated", "contractor_id": contractor.id}


@router.get("/api/contractors")
async def list_contractors(
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: list all contractors with their status and metrics."""
    result = await db.execute(select(Contractor).order_by(Contractor.created_at.desc()))
    contractors = list(result.scalars().all())
    return [
        {
            "id": c.id,
            "company_name": c.company_name,
            "contact_name": c.contact_name,
            "phone": c.phone,
            "email": c.email,
            "is_active": c.is_active,
            "service_types": c.service_types,
            "service_zips": c.service_zips,
            "quality_score": float(c.quality_score) if c.quality_score else None,
            "acceptance_rate": float(c.acceptance_rate) if c.acceptance_rate else None,
            "current_daily_leads": c.current_daily_leads,
            "max_daily_leads": c.max_daily_leads,
            "insurance_verified": c.insurance_verified,
            "license_number": c.license_number,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in contractors
    ]


# ─── Auth & Dashboard ───────────────────────────────────────────────────────


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


class QuoteSubmission(BaseModel):
    quote_amount: float


@router.post("/api/contractor/leads/{lead_id}/quote")
async def submit_quote(
    lead_id: int,
    data: QuoteSubmission,
    auth: dict = Depends(get_current_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Contractor submits their quote. System adds 15-20% markup for the customer price."""
    from decimal import Decimal

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

    quote = Decimal(str(data.quote_amount))
    markup = Decimal("0.20")  # 20% default markup
    customer_price = (quote * (1 + markup)).quantize(Decimal("0.01"))

    assignment.contractor_quote = quote
    assignment.markup_pct = markup * 100
    assignment.customer_price = customer_price

    # Also update backup assignments for this lead with 15% higher pricing
    backup_stmt = select(LeadAssignment).where(
        and_(
            LeadAssignment.lead_id == lead_id,
            LeadAssignment.contractor_id != contractor_id,
            LeadAssignment.is_backup.is_(True),
        )
    )
    backup_result = await db.execute(backup_stmt)
    backups = list(backup_result.scalars().all())

    backup_markup = Decimal("0.15")
    for backup in backups:
        # Backup quote is 15% higher than primary contractor's quote
        backup_quote = (quote * (1 + backup_markup)).quantize(Decimal("0.01"))
        backup_customer_price = (backup_quote * (1 + markup)).quantize(Decimal("0.01"))
        backup.contractor_quote = backup_quote
        backup.markup_pct = markup * 100
        backup.customer_price = backup_customer_price

    await db.commit()
    return {
        "status": "quote_submitted",
        "contractor_quote": float(quote),
        "customer_price": float(customer_price),
    }


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
