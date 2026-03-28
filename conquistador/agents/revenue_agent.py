"""Revenue Agent — invoice generation, payment tracking, billing alerts.

Runs as a Celery worker.
"""

import logging
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.payment import Payment
from conquistador.models.assignment import LeadAssignment
from conquistador.billing.invoicing import create_invoice, send_invoice_email
from conquistador.billing.tracker import get_revenue_summary
from conquistador.comms.telegram_bot import send_admin_alert

logger = logging.getLogger(__name__)


async def generate_invoices_for_completed_leads(db: AsyncSession):
    """Generate invoices for accepted leads that don't have invoices yet."""
    # Find accepted assignments without payments
    stmt = (
        select(LeadAssignment)
        .outerjoin(Payment, Payment.assignment_id == LeadAssignment.id)
        .where(
            and_(
                LeadAssignment.status == "accepted",
                Payment.id.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    assignments = list(result.scalars().all())

    for assignment in assignments:
        if not assignment.contractor_quote or not assignment.customer_price:
            logger.warning("Assignment %d has no quote/price set, skipping invoice", assignment.id)
            continue

        # Our revenue is the markup: customer_price - contractor_quote
        markup_revenue = assignment.customer_price - assignment.contractor_quote
        if markup_revenue <= 0:
            continue

        payment = await create_invoice(assignment.id, assignment.contractor_id, markup_revenue, db)
        await send_invoice_email(payment, db)
        logger.info("Invoice created for assignment %d: revenue=$%s (customer=$%s, contractor=$%s)",
                     assignment.id, markup_revenue, assignment.customer_price, assignment.contractor_quote)


async def send_daily_revenue_report(db: AsyncSession):
    """Send daily revenue summary to admin via Telegram."""
    summary = await get_revenue_summary(db, days=1)
    monthly = await get_revenue_summary(db, days=30)

    msg = (
        "<b>Daily Revenue Report</b>\n\n"
        f"Today's Revenue: ${summary['total_revenue']:.2f}\n"
        f"Today's Payments: {summary['payment_count']}\n\n"
        f"Monthly Revenue: ${monthly['total_revenue']:.2f}\n"
        f"Monthly Payments: {monthly['payment_count']}\n"
        f"Pending: ${monthly['pending_amount']:.2f}"
    )

    await send_admin_alert(msg)
