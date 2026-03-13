"""Outreach log model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from conquistador.models.base import Base


class OutreachLog(Base):
    __tablename__ = "outreach_log"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    contractor_id = Column(Integer, ForeignKey("contractors.id"))
    channel = Column(String(10))  # sms, email, telegram
    direction = Column(String(10))  # outbound, inbound
    content = Column(Text)
    status = Column(String(20))  # sent, delivered, failed
    created_at = Column(DateTime, default=datetime.utcnow)
