"""Lead-to-contractor matching algorithm."""

import logging
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.models.lead import Lead
from conquistador.comms.contractor_notify import notify_contractor
from conquistador.comms.telegram_bot import send_admin_alert
from conquistador.comms.customer_notify import notify_customer_assigned
from conquistador.models.outreach import OutreachLog

logger = logging.getLogger(__name__)

MIN_BACKUPS = 2  # Always try to have at least 2 backups


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

    # Response time bonus — fast responders get up to 25 extra points
    if contractor.avg_response_min is not None:
        avg_min = float(contractor.avg_response_min)
        if avg_min <= 5:
            score += 25  # Under 5 min = full bonus
        elif avg_min <= 15:
            score += 15  # Under 15 min = good
        elif avg_min <= 30:
            score += 5   # Under 30 min = small bonus
        # Over 30 min = no bonus

    return score


async def find_matching_contractors(lead: Lead, db: AsyncSession) -> list[Contractor]:
    """Find active contractors matching a lead's service type and zip code."""
    now = datetime.utcnow()

    stmt = select(Contractor).where(
        and_(
            Contractor.is_active.is_(True),
            Contractor.service_types.contains([lead.service_type]),
            Contractor.service_zips.contains([lead.zip_code]),
            Contractor.current_daily_leads < Contractor.max_daily_leads,
            # Exclude temporarily unavailable contractors
            or_(
                Contractor.unavailable_until.is_(None),
                Contractor.unavailable_until <= now,
            ),
        )
    )
    result = await db.execute(stmt)
    contractors = list(result.scalars().all())

    # Filter by availability windows (day of week + hours)
    day_name = now.strftime("%a").lower()[:3]  # mon, tue, wed, ...
    current_time = now.strftime("%H:%M")

    available = []
    for c in contractors:
        # Check day availability (empty list = available every day)
        if c.available_days and day_name not in c.available_days:
            # Exception: emergencies bypass day restrictions
            if lead.urgency != "emergency":
                continue

        # Check time window (null = anytime)
        if c.available_start and c.available_end:
            if not (c.available_start <= current_time <= c.available_end):
                # Exception: emergencies bypass time restrictions
                if lead.urgency != "emergency":
                    continue

        available.append(c)

    # Sort by score descending
    available.sort(key=lambda c: score_contractor(c, lead), reverse=True)
    return available


async def route_lead(lead: Lead, db: AsyncSession) -> bool:
    """Route a lead to all matching contractors (1 primary + all available backups)."""
    contractors = await find_matching_contractors(lead, db)
    if not contractors:
        logger.warning("No matching contractors for lead %d (zip=%s, type=%s)",
                       lead.id, lead.zip_code, lead.service_type)
        lead.status = "unmatched"
        await db.commit()

        # Alert admin that a lead has no contractors
        await send_admin_alert(
            f"<b>UNMATCHED LEAD — Action Required</b>\n\n"
            f"Lead #{lead.id}\n"
            f"Service: {lead.service_type}\n"
            f"Area: {lead.zip_code}\n"
            f"Urgency: {lead.urgency}\n"
            f"Customer: {lead.name or 'Unknown'}\n"
            f"Phone: {lead.phone}\n\n"
            f"No contractors available. Please find one manually."
        )
        return False

    # Assign to ALL matching contractors — 1st is primary, rest are backups
    for order, contractor in enumerate(contractors, start=1):
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

            # Notify customer that we've found a technician
            await notify_customer_assigned(lead)

    logger.info("Lead %d assigned to %d contractors (1 primary, %d backups)",
                lead.id, len(contractors), len(contractors) - 1)
    return True
