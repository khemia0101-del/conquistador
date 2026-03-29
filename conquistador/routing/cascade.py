"""Cascade logic for declined or expired leads."""

import logging
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.assignment import LeadAssignment
from conquistador.models.contractor import Contractor
from conquistador.models.lead import Lead
from conquistador.models.outreach import OutreachLog
from conquistador.comms.contractor_notify import notify_contractor
from conquistador.comms.telegram_bot import send_admin_alert
from conquistador.comms.customer_notify import notify_customer_cascading

logger = logging.getLogger(__name__)


async def cascade_to_next(lead_id: int, db: AsyncSession) -> bool:
    """After a contractor declines, cascade to the next in line."""
    # Find next pending assignment
    stmt = (
        select(LeadAssignment)
        .where(
            and_(
                LeadAssignment.lead_id == lead_id,
                LeadAssignment.status == "pending",
            )
        )
        .order_by(LeadAssignment.cascade_order)
        .limit(1)
    )
    result = await db.execute(stmt)
    next_assignment = result.scalar_one_or_none()

    if not next_assignment:
        logger.info("No more contractors to cascade for lead %d", lead_id)
        lead_stmt = select(Lead).where(Lead.id == lead_id)
        lead_result = await db.execute(lead_stmt)
        lead = lead_result.scalar_one_or_none()
        if lead:
            lead.status = "unmatched"
            await db.commit()
            # Alert admin — all contractors exhausted
            await send_admin_alert(
                f"<b>ALL CONTRACTORS EXHAUSTED</b>\n\n"
                f"Lead #{lead.id} — {lead.service_type}\n"
                f"Area: {lead.zip_code}\n"
                f"Customer: {lead.name or 'Unknown'} ({lead.phone})\n"
                f"Urgency: {lead.urgency}\n\n"
                f"Every contractor declined or timed out. Manual action needed."
            )
        return False

    # Get contractor
    contractor_stmt = select(Contractor).where(Contractor.id == next_assignment.contractor_id)
    contractor_result = await db.execute(contractor_stmt)
    contractor = contractor_result.scalar_one_or_none()

    lead_stmt = select(Lead).where(Lead.id == lead_id)
    lead_result = await db.execute(lead_stmt)
    lead = lead_result.scalar_one_or_none()

    if contractor and lead:
        # Let the customer know we're finding the next tech
        await notify_customer_cascading(lead)

        channel = await notify_contractor(contractor, lead)
        outreach = OutreachLog(
            lead_id=lead_id,
            contractor_id=contractor.id,
            channel=channel,
            direction="outbound",
            content=f"Cascaded lead notification for {lead.service_type}",
            status="sent",
        )
        db.add(outreach)
        await db.commit()
        logger.info("Cascaded lead %d to contractor %d (order %d)",
                     lead_id, contractor.id, next_assignment.cascade_order)
        return True

    return False
