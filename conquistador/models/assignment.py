"""Lead assignment model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
