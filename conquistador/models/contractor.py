"""Contractor model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, DateTime, ARRAY
from conquistador.models.base import Base


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True)
    company_name = Column(String(200), nullable=False)
    contact_name = Column(String(100))
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    telegram_chat_id = Column(String(50))
    address = Column(String(300))
    license_number = Column(String(50))
    insurance_verified = Column(Boolean, default=False)
    service_types = Column(ARRAY(String), nullable=False)
    service_zips = Column(ARRAY(String), nullable=False)
    max_daily_leads = Column(Integer, default=5)
    current_daily_leads = Column(Integer, default=0)
    commission_rate = Column(DECIMAL(5, 2))
    quality_score = Column(DECIMAL(3, 2))
    acceptance_rate = Column(DECIMAL(5, 2))
    avg_response_min = Column(DECIMAL(8, 2))
    is_active = Column(Boolean, default=False)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Availability windows — days/hours the contractor works
    # available_days: e.g. ["mon","tue","wed","thu","fri"] (empty = all days)
    available_days = Column(ARRAY(String), default=list)
    # available_start/end: 24h format, e.g. "08:00" / "18:00" (null = anytime)
    available_start = Column(String(5))   # e.g. "08:00"
    available_end = Column(String(5))     # e.g. "18:00"
    # Temporary unavailability (vacation, booked out, etc.)
    unavailable_until = Column(DateTime)  # null = currently available
