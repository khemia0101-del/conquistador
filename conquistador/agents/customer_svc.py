"""Customer Service Agent — post-service surveys, follow-ups, review management.

Runs as Celery Beat scheduled tasks.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.lead import Lead
from conquistador.models.assignment import LeadAssignment
from conquistador.models.contractor import Contractor
from conquistador.models.review import CustomerReview
from conquistador.quality.survey import send_survey
from conquistador.quality.scoring import update_contractor_quality_score
from conquistador.comms.email import send_email

logger = logging.getLogger(__name__)


async def send_pending_surveys(db: AsyncSession):
    """Send surveys for recently completed leads that haven't been surveyed yet."""
    # Find accepted assignments from 1-2 days ago without reviews
    since = datetime.utcnow() - timedelta(days=2)
    until = datetime.utcnow() - timedelta(days=1)

    stmt = (
        select(LeadAssignment, Lead, Contractor)
        .join(Lead, Lead.id == LeadAssignment.lead_id)
        .join(Contractor, Contractor.id == LeadAssignment.contractor_id)
        .outerjoin(CustomerReview, CustomerReview.lead_id == Lead.id)
        .where(
            and_(
                LeadAssignment.status == "accepted",
                LeadAssignment.responded_at >= since,
                LeadAssignment.responded_at <= until,
                CustomerReview.id.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    for assignment, lead, contractor in rows:
        await send_survey(lead, contractor)
        logger.info("Survey sent for lead %d to %s", lead.id, lead.email or lead.phone)


async def process_survey_submission(
    lead_id: int,
    contractor_id: int,
    on_time: int,
    professionalism: int,
    problem_solved: int,
    comments: str,
    db: AsyncSession,
) -> CustomerReview:
    """Process a submitted survey and update contractor quality score."""
    from conquistador.quality.scoring import calculate_overall_rating

    overall = calculate_overall_rating(on_time, professionalism, problem_solved)

    review = CustomerReview(
        lead_id=lead_id,
        contractor_id=contractor_id,
        on_time_rating=on_time,
        professionalism_rating=professionalism,
        problem_solved_rating=problem_solved,
        overall_rating=overall,
        comments=comments,
    )
    db.add(review)
    await db.commit()

    # Update contractor quality score
    await update_contractor_quality_score(contractor_id, db)

    logger.info("Survey processed for lead %d, contractor %d, overall: %s",
                lead_id, contractor_id, overall)
    return review
