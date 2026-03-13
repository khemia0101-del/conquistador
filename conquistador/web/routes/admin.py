"""Admin dashboard and API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.models.lead import Lead
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.models.payment import Payment
from conquistador.web.auth import get_admin
from conquistador.billing.tracker import get_revenue_summary

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def admin_dashboard(
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    leads_stmt = select(func.count(Lead.id))
    leads_result = await db.execute(leads_stmt)
    total_leads = leads_result.scalar() or 0

    contractors_stmt = select(func.count(Contractor.id)).where(Contractor.is_active.is_(True))
    contractors_result = await db.execute(contractors_stmt)
    active_contractors = contractors_result.scalar() or 0

    revenue = await get_revenue_summary(db, days=30)

    return {
        "total_leads": total_leads,
        "active_contractors": active_contractors,
        "monthly_revenue": revenue["total_revenue"],
        "pending_payments": revenue["pending_amount"],
    }


@router.get("/leads")
async def admin_leads(
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Lead.status == status)
    result = await db.execute(stmt)
    leads = result.scalars().all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "phone": l.phone,
            "zip_code": l.zip_code,
            "service_type": l.service_type,
            "urgency": l.urgency,
            "status": l.status,
            "lead_score": l.lead_score,
            "source": l.source,
            "created_at": l.created_at.isoformat(),
        }
        for l in leads
    ]


@router.get("/contractors")
async def admin_contractors(
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Contractor).order_by(Contractor.created_at.desc())
    result = await db.execute(stmt)
    contractors = result.scalars().all()
    return [
        {
            "id": c.id,
            "company_name": c.company_name,
            "contact_name": c.contact_name,
            "phone": c.phone,
            "email": c.email,
            "service_types": c.service_types,
            "quality_score": float(c.quality_score) if c.quality_score else None,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat(),
        }
        for c in contractors
    ]


@router.post("/contractors/{contractor_id}/activate")
async def activate_contractor(
    contractor_id: int,
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Contractor).where(Contractor.id == contractor_id)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor.is_active = True
    await db.commit()
    return {"status": "activated"}


@router.post("/contractors/{contractor_id}/deactivate")
async def deactivate_contractor(
    contractor_id: int,
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Contractor).where(Contractor.id == contractor_id)
    result = await db.execute(stmt)
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor.is_active = False
    await db.commit()
    return {"status": "deactivated"}


@router.get("/revenue")
async def admin_revenue(
    days: int = 30,
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_revenue_summary(db, days=days)


@router.get("/quality")
async def admin_quality(
    auth: dict = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Contractor)
        .where(Contractor.quality_score.isnot(None))
        .order_by(Contractor.quality_score.desc())
    )
    result = await db.execute(stmt)
    contractors = result.scalars().all()

    from conquistador.quality.scoring import get_quality_status
    return [
        {
            "id": c.id,
            "company_name": c.company_name,
            "quality_score": float(c.quality_score),
            "status": get_quality_status(c.quality_score),
            "acceptance_rate": float(c.acceptance_rate) if c.acceptance_rate else None,
        }
        for c in contractors
    ]
