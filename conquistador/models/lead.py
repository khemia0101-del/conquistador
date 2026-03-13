"""Lead model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from conquistador.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    phone = Column(String(20), nullable=False)
    carrier = Column(String(20))  # verizon, att, tmobile, sprint, other
    email = Column(String(100))
    address = Column(String(300))
    zip_code = Column(String(10), nullable=False)
    service_type = Column(String(50), nullable=False)
    urgency = Column(String(20), nullable=False)  # emergency, urgent, routine
    property_type = Column(String(30))  # residential, commercial, multi
    description = Column(Text)
    lead_score = Column(Integer)  # 1-100
    status = Column(String(20), default="new")  # new, assigned, accepted, completed, cancelled
    source = Column(String(30), default="chatbot")  # chatbot, form, phone
    conversation_log = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
