"""Payment model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey
from conquistador.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("lead_assignments.id"))
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    amount = Column(DECIMAL(10, 2))
    payment_method = Column(String(30))  # manual, stripe, zelle, venmo
    payment_reference = Column(String(100))
    status = Column(String(20), default="pending")  # pending, paid, disputed, refunded
    created_at = Column(DateTime, default=datetime.utcnow)
