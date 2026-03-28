"""Lead assignment model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, DECIMAL, Boolean
from conquistador.models.base import Base


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, accepted, declined, expired
    assigned_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime)
    cascade_order = Column(Integer)  # 1st, 2nd, 3rd match

    # Pricing
    contractor_quote = Column(DECIMAL(10, 2))      # What the contractor quotes
    markup_pct = Column(DECIMAL(5, 2), default=20)  # Our markup percentage (15-20%)
    customer_price = Column(DECIMAL(10, 2))         # What the customer pays (quote + markup)
    is_backup = Column(Boolean, default=False)       # True for backup quotes
