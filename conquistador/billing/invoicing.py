"""Manual invoice generation."""

import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.payment import Payment
from conquistador.models.assignment import LeadAssignment
from conquistador.models.contractor import Contractor
from conquistador.comms.email import send_email

logger = logging.getLogger(__name__)


async def create_invoice(
    assignment_id: int,
    contractor_id: int,
    amount: Decimal,
    db: AsyncSession,
) -> Payment:
    """Create a manual invoice for a contractor."""
    payment = Payment(
        assignment_id=assignment_id,
        contractor_id=contractor_id,
        amount=amount,
        payment_method="manual",
        payment_reference=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{assignment_id}",
        status="pending",
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    logger.info("Invoice %s created for contractor %d: $%s",
                payment.payment_reference, contractor_id, amount)
    return payment


async def send_invoice_email(payment: Payment, db: AsyncSession) -> bool:
    """Send invoice notification to contractor."""
    contractor_stmt = select(Contractor).where(Contractor.id == payment.contractor_id)
    result = await db.execute(contractor_stmt)
    contractor = result.scalar_one_or_none()

    if not contractor or not contractor.email:
        return False

    body = f"""
    <h2>Invoice from Conquistador Oil</h2>
    <p>Invoice: {payment.payment_reference}</p>
    <p>Amount: ${payment.amount}</p>
    <p>Status: {payment.status}</p>
    <p>Please submit payment via Zelle or Venmo to the Conquistador business account.</p>
    """

    return await send_email(contractor.email, f"Invoice {payment.payment_reference}", body)
