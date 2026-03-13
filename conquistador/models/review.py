"""Customer review model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime, ForeignKey, CheckConstraint
from conquistador.models.base import Base


class CustomerReview(Base):
    __tablename__ = "customer_reviews"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    on_time_rating = Column(Integer)
    professionalism_rating = Column(Integer)
    problem_solved_rating = Column(Integer)
    overall_rating = Column(DECIMAL(3, 2))
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("on_time_rating BETWEEN 1 AND 5"),
        CheckConstraint("professionalism_rating BETWEEN 1 AND 5"),
        CheckConstraint("problem_solved_rating BETWEEN 1 AND 5"),
    )
