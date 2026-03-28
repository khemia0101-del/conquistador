"""Lead-to-contractor matching algorithm."""

import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.models.lead import Lead
from conquistador.comms.contractor_notify import notify_contractor
from conquistador.models.outreach import OutreachLog

logger = logging.getLogger(__name__)


def score_contractor(contractor: Contractor, lead: Lead) -> float:
    """Score a contractor's fit for a lead (higher is better)."""
    score = 0.0

    # Quality score (0-5 scale, weight heavily)
    if contractor.quality_score:
        score += float(contractor.quality_score) * 20  # max 100

    # Acceptance rate
    if contractor.acceptance_rate:
        score += float(contractor.acceptance_rate) * 0.5  # max 50

    # Capacity (prefer contractors with capacity remaining)
    capacity_used = contractor.current_daily_leads / max(contractor.max_daily_leads, 1)
    score += (1 - capacity_used) * 30  # max 30

    return score


async def find_matching_contractors(lead: Lead, db: AsyncSession) -> list[Contractor]:
    """Find active contractors matching a lead's service type and zip code."""
    stmt = select(Contractor).where(
        and_(
            Contractor.is_active.is_(True),
            Contractor.service_types.contains([lead.service_type]),
            Contractor.service_zips.contains([lead.zip_code]),
            Contractor.current_daily_leads < Contractor.max_daily_leads,
        )
    )
    result = await db.execute(stmt)
    contractors = list(result.scalars().all())

    # Sort by score descending
    contractors.sort(key=lambda c: score_contractor(c, lead), reverse=True)
    return contractors


async def route_lead(lead: Lead, db: AsyncSession) -> bool:
    """Route a lead to the best matching contractors (cascade up to 3)."""
    contractors = await find_matching_contractors(lead, db)
    if not contractors:
        logger.warning("No matching contractors for lead %d (zip=%s, type=%s)",
                       lead.id, lead.zip_code, lead.service_type)
        lead.status = "unmatched"
        await db.commit()
        return False

    # Assign to top 3 contractors in cascade order
    # 1st = primary, 2nd & 3rd = backups (quoted 15% higher than primary)
    for order, contractor in enumerate(contractors[:3], start=1):
        assignment = LeadAssignment(
            lead_id=lead.id,
            contractor_id=contractor.id,
            status="pending",
            cascade_order=order,
            is_backup=(order > 1),
        )
        db.add(assignment)
        await db.commit()

        # Notify the first contractor immediately; others wait for decline/expiry
        if order == 1:
            channel = await notify_contractor(contractor, lead)
            outreach = OutreachLog(
                lead_id=lead.id,
                contractor_id=contractor.id,
                channel=channel,
                direction="outbound",
                content=f"New lead notification for {lead.service_type}",
                status="sent",
            )
            db.add(outreach)
            lead.status = "assigned"
            await db.commit()

    return True
