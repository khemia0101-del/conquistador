"""Contractor Management Agent — lead routing, capacity management, tracking.

Runs as a Celery worker processing lead events.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.models.lead import Lead
from conquistador.routing.cascade import cascade_to_next
from conquistador.comms.telegram_bot import send_admin_alert
from conquistador.comms.customer_notify import notify_customer_accepted

logger = logging.getLogger(__name__)

LEAD_EXPIRY_MINUTES = 30  # Auto-decline if no response in 30 min


async def handle_lead_acceptance(assignment_id: int, db: AsyncSession):
    """Handle a contractor accepting a lead."""
    stmt = select(LeadAssignment).where(LeadAssignment.id == assignment_id)
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment or assignment.status != "pending":
        return

    assignment.status = "accepted"
    assignment.responded_at = datetime.utcnow()

    # Increment contractor's daily lead count
    contractor_stmt = select(Contractor).where(Contractor.id == assignment.contractor_id)
    contractor_result = await db.execute(contractor_stmt)
    contractor = contractor_result.scalar_one_or_none()
    if contractor:
        contractor.current_daily_leads += 1

    # Decline all other pending assignments for this lead
    decline_stmt = (
        update(LeadAssignment)
        .where(
            and_(
                LeadAssignment.lead_id == assignment.lead_id,
                LeadAssignment.id != assignment_id,
                LeadAssignment.status == "pending",
            )
        )
        .values(status="declined")
    )
    await db.execute(decline_stmt)
    await db.commit()

    # Notify the customer their technician is confirmed
    lead_stmt = select(Lead).where(Lead.id == assignment.lead_id)
    lead_result = await db.execute(lead_stmt)
    lead = lead_result.scalar_one_or_none()
    if lead:
        await notify_customer_accepted(lead)

    # Update contractor metrics
    from conquistador.quality.scoring import update_contractor_acceptance_rate, update_contractor_response_time
    await update_contractor_acceptance_rate(assignment.contractor_id, db)
    await update_contractor_response_time(assignment.contractor_id, db)

    logger.info("Lead %d accepted by contractor %d", assignment.lead_id, assignment.contractor_id)


async def handle_lead_decline(assignment_id: int, db: AsyncSession):
    """Handle a contractor declining a lead — cascade to next."""
    stmt = select(LeadAssignment).where(LeadAssignment.id == assignment_id)
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment or assignment.status != "pending":
        return

    assignment.status = "declined"
    assignment.responded_at = datetime.utcnow()
    await db.commit()

    # Update contractor acceptance rate
    from conquistador.quality.scoring import update_contractor_acceptance_rate
    await update_contractor_acceptance_rate(assignment.contractor_id, db)

    # Cascade to next contractor
    await cascade_to_next(assignment.lead_id, db)


async def expire_stale_assignments(db: AsyncSession):
    """Expire assignments that haven't been responded to within the timeout."""
    cutoff = datetime.utcnow() - timedelta(minutes=LEAD_EXPIRY_MINUTES)
    stmt = select(LeadAssignment).where(
        and_(
            LeadAssignment.status == "pending",
            LeadAssignment.assigned_at < cutoff,
        )
    )
    result = await db.execute(stmt)
    stale = list(result.scalars().all())

    for assignment in stale:
        assignment.status = "expired"
        await db.commit()
        await cascade_to_next(assignment.lead_id, db)
        logger.info("Assignment %d expired, cascading lead %d",
                     assignment.id, assignment.lead_id)


async def reset_daily_lead_counts(db: AsyncSession):
    """Reset all contractors' daily lead counts (run at midnight)."""
    stmt = update(Contractor).values(current_daily_leads=0)
    await db.execute(stmt)
    await db.commit()
    logger.info("Daily lead counts reset for all contractors")
