"""Revenue tracking."""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.payment import Payment

logger = logging.getLogger(__name__)


async def get_revenue_summary(db: AsyncSession, days: int = 30) -> dict:
    """Get revenue summary for the specified period."""
    since = datetime.utcnow() - timedelta(days=days)

    # Total revenue
    total_stmt = select(func.sum(Payment.amount)).where(
        and_(Payment.status == "paid", Payment.created_at >= since)
    )
    total_result = await db.execute(total_stmt)
    total_revenue = total_result.scalar() or Decimal("0.00")

    # Pending payments
    pending_stmt = select(func.sum(Payment.amount)).where(Payment.status == "pending")
    pending_result = await db.execute(pending_stmt)
    pending_amount = pending_result.scalar() or Decimal("0.00")

    # Payment count
    count_stmt = select(func.count(Payment.id)).where(
        and_(Payment.status == "paid", Payment.created_at >= since)
    )
    count_result = await db.execute(count_stmt)
    payment_count = count_result.scalar() or 0

    return {
        "period_days": days,
        "total_revenue": float(total_revenue),
        "pending_amount": float(pending_amount),
        "payment_count": payment_count,
        "avg_payment": float(total_revenue / max(payment_count, 1)),
    }
