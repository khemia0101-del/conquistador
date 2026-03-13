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
