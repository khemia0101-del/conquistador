"""Quality score calculation for contractors."""

import logging
from decimal import Decimal
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.review import CustomerReview
from conquistador.models.contractor import Contractor

logger = logging.getLogger(__name__)

# Weights for quality score
ON_TIME_WEIGHT = Decimal("0.30")
PROFESSIONALISM_WEIGHT = Decimal("0.30")
PROBLEM_SOLVED_WEIGHT = Decimal("0.40")

# Quality thresholds
EXCELLENT_THRESHOLD = Decimal("4.5")
GOOD_THRESHOLD = Decimal("4.0")
WARNING_THRESHOLD = Decimal("3.5")
PROBATION_THRESHOLD = Decimal("3.0")


def calculate_overall_rating(on_time: int, professionalism: int, problem_solved: int) -> Decimal:
    """Calculate weighted overall rating from individual ratings."""
    return (
        Decimal(on_time) * ON_TIME_WEIGHT
        + Decimal(professionalism) * PROFESSIONALISM_WEIGHT
        + Decimal(problem_solved) * PROBLEM_SOLVED_WEIGHT
    )


async def update_contractor_quality_score(contractor_id: int, db: AsyncSession) -> Decimal | None:
    """Recalculate a contractor's quality score from their last 50 reviews."""
    stmt = (
        select(CustomerReview)
        .where(CustomerReview.contractor_id == contractor_id)
        .order_by(desc(CustomerReview.created_at))
        .limit(50)
    )
    result = await db.execute(stmt)
    reviews = list(result.scalars().all())

    if not reviews:
        return None

    total = sum(
        calculate_overall_rating(r.on_time_rating, r.professionalism_rating, r.problem_solved_rating)
        for r in reviews
    )
    avg_score = total / len(reviews)

    contractor_stmt = select(Contractor).where(Contractor.id == contractor_id)
    contractor_result = await db.execute(contractor_stmt)
    contractor = contractor_result.scalar_one_or_none()
    if contractor:
        contractor.quality_score = avg_score
        await db.commit()

    return avg_score


async def update_contractor_acceptance_rate(contractor_id: int, db: AsyncSession) -> Decimal | None:
    """Recalculate a contractor's acceptance rate from their assignments."""
    from conquistador.models.assignment import LeadAssignment
    from sqlalchemy import func

    total_stmt = select(func.count(LeadAssignment.id)).where(
        LeadAssignment.contractor_id == contractor_id,
        LeadAssignment.status.in_(["accepted", "declined", "expired"]),
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    if total == 0:
        return None

    accepted_stmt = select(func.count(LeadAssignment.id)).where(
        LeadAssignment.contractor_id == contractor_id,
        LeadAssignment.status == "accepted",
    )
    accepted_result = await db.execute(accepted_stmt)
    accepted = accepted_result.scalar() or 0

    rate = (Decimal(accepted) / Decimal(total) * 100).quantize(Decimal("0.01"))

    contractor_stmt = select(Contractor).where(Contractor.id == contractor_id)
    contractor_result = await db.execute(contractor_stmt)
    contractor = contractor_result.scalar_one_or_none()
    if contractor:
        contractor.acceptance_rate = rate
        await db.commit()

    return rate


async def update_contractor_response_time(contractor_id: int, db: AsyncSession) -> Decimal | None:
    """Recalculate a contractor's average response time from recent assignments."""
    from conquistador.models.assignment import LeadAssignment

    stmt = (
        select(LeadAssignment)
        .where(
            LeadAssignment.contractor_id == contractor_id,
            LeadAssignment.responded_at.isnot(None),
        )
        .order_by(desc(LeadAssignment.responded_at))
        .limit(20)
    )
    result = await db.execute(stmt)
    assignments = list(result.scalars().all())

    if not assignments:
        return None

    total_minutes = Decimal(0)
    count = 0
    for a in assignments:
        if a.assigned_at and a.responded_at:
            delta = a.responded_at - a.assigned_at
            total_minutes += Decimal(str(delta.total_seconds() / 60))
            count += 1

    if count == 0:
        return None

    avg = (total_minutes / count).quantize(Decimal("0.01"))

    contractor_stmt = select(Contractor).where(Contractor.id == contractor_id)
    contractor_result = await db.execute(contractor_stmt)
    contractor = contractor_result.scalar_one_or_none()
    if contractor:
        contractor.avg_response_min = avg
        await db.commit()

    return avg


async def check_quality_and_alert(contractor_id: int, db: AsyncSession):
    """Check if a contractor's quality has dropped below thresholds and alert admin."""
    from conquistador.comms.telegram_bot import send_admin_alert

    contractor_stmt = select(Contractor).where(Contractor.id == contractor_id)
    contractor_result = await db.execute(contractor_stmt)
    contractor = contractor_result.scalar_one_or_none()

    if not contractor or not contractor.quality_score:
        return

    score = contractor.quality_score
    status = get_quality_status(score)

    if status == "suspended":
        # Auto-deactivate contractors with very poor quality
        contractor.is_active = False
        await db.commit()
        await send_admin_alert(
            f"<b>CONTRACTOR AUTO-SUSPENDED</b>\n\n"
            f"{contractor.company_name} (ID: {contractor.id})\n"
            f"Quality score: {score}\n"
            f"Account deactivated due to poor reviews.\n"
            f"Reactivate manually after review."
        )
    elif status == "probation":
        await send_admin_alert(
            f"<b>Contractor Quality Warning</b>\n\n"
            f"{contractor.company_name} (ID: {contractor.id})\n"
            f"Quality score: {score} — on probation.\n"
            f"Will be auto-suspended if score drops below {PROBATION_THRESHOLD}."
        )


def get_quality_status(score: Decimal) -> str:
    """Get quality status label for a score."""
    if score >= EXCELLENT_THRESHOLD:
        return "excellent"
    elif score >= GOOD_THRESHOLD:
        return "good"
    elif score >= WARNING_THRESHOLD:
        return "warning"
    elif score >= PROBATION_THRESHOLD:
        return "probation"
    else:
        return "suspended"
