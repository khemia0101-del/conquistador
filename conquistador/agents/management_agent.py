"""Management Agent — audits all agents, monitors KPIs, flags anomalies.

Runs as Celery Beat (hourly). Reports to admin via Telegram.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.lead import Lead
from conquistador.models.contractor import Contractor
from conquistador.models.assignment import LeadAssignment
from conquistador.quality.scoring import get_quality_status, PROBATION_THRESHOLD
from conquistador.comms.telegram_bot import send_admin_alert

logger = logging.getLogger(__name__)


async def run_hourly_audit(db: AsyncSession):
    """Run hourly system audit and alert on anomalies."""
    alerts = []

    # Check for unmatched leads in the last hour
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    unmatched_stmt = select(func.count(Lead.id)).where(
        and_(Lead.status == "unmatched", Lead.created_at >= hour_ago)
    )
    result = await db.execute(unmatched_stmt)
    unmatched = result.scalar() or 0
    if unmatched > 0:
        alerts.append(f"Unmatched leads in last hour: {unmatched}")

    # Check for contractors with quality score below probation
    low_quality_stmt = select(Contractor).where(
        and_(
            Contractor.is_active.is_(True),
            Contractor.quality_score.isnot(None),
            Contractor.quality_score < PROBATION_THRESHOLD,
        )
    )
    result = await db.execute(low_quality_stmt)
    low_quality = list(result.scalars().all())
    for c in low_quality:
        alerts.append(
            f"Contractor '{c.company_name}' quality score: {c.quality_score} "
            f"({get_quality_status(c.quality_score)})"
        )

    # Check for expired assignments (contractors not responding)
    expired_stmt = select(func.count(LeadAssignment.id)).where(
        and_(LeadAssignment.status == "expired", LeadAssignment.assigned_at >= hour_ago)
    )
    result = await db.execute(expired_stmt)
    expired = result.scalar() or 0
    if expired > 0:
        alerts.append(f"Expired (unresponsive) assignments in last hour: {expired}")

    if alerts:
        msg = "<b>Hourly Audit Alerts</b>\n\n" + "\n".join(f"- {a}" for a in alerts)
        await send_admin_alert(msg)
        logger.warning("Audit alerts: %s", alerts)
    else:
        logger.info("Hourly audit: all clear")


async def send_daily_summary(db: AsyncSession):
    """Send daily KPI summary to admin."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Leads today
    leads_stmt = select(func.count(Lead.id)).where(Lead.created_at >= today)
    result = await db.execute(leads_stmt)
    leads_today = result.scalar() or 0

    # Accepted today
    accepted_stmt = select(func.count(LeadAssignment.id)).where(
        and_(LeadAssignment.status == "accepted", LeadAssignment.responded_at >= today)
    )
    result = await db.execute(accepted_stmt)
    accepted_today = result.scalar() or 0

    # Active contractors
    active_stmt = select(func.count(Contractor.id)).where(Contractor.is_active.is_(True))
    result = await db.execute(active_stmt)
    active_contractors = result.scalar() or 0

    msg = (
        "<b>Daily Summary</b>\n\n"
        f"Leads Today: {leads_today}\n"
        f"Accepted: {accepted_today}\n"
        f"Active Contractors: {active_contractors}\n"
    )

    await send_admin_alert(msg)
