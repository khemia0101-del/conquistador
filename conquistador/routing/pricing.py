"""Dynamic pricing engine — urgency-based markup with seasonal adjustments."""

from datetime import datetime
from decimal import Decimal

# Base markup rates by urgency
URGENCY_MARKUP = {
    "emergency": Decimal("0.28"),   # 28% for emergencies
    "urgent": Decimal("0.23"),      # 23% for urgent
    "routine": Decimal("0.15"),     # 15% for routine/maintenance
}
DEFAULT_MARKUP = Decimal("0.20")    # 20% default

# Seasonal adjustment: heating season (Nov-Mar) gets extra markup
HEATING_SEASON_MONTHS = {11, 12, 1, 2, 3}
HEATING_SEASON_BOOST = Decimal("0.03")  # +3% during peak heating season

# Service types that qualify for seasonal boost
SEASONAL_SERVICES = {"heating_oil", "hvac_repair", "emergency", "furnace_maintenance"}

# Backup quote premium over primary
BACKUP_PREMIUM = Decimal("0.15")  # 15% higher than primary


def get_markup_rate(urgency: str, service_type: str, now: datetime | None = None) -> Decimal:
    """Calculate the markup rate based on urgency, service type, and season."""
    now = now or datetime.utcnow()
    base_rate = URGENCY_MARKUP.get(urgency, DEFAULT_MARKUP)

    # Seasonal boost for heating-related services during winter
    if now.month in HEATING_SEASON_MONTHS and service_type in SEASONAL_SERVICES:
        base_rate += HEATING_SEASON_BOOST

    return base_rate


def calculate_customer_price(
    contractor_quote: Decimal,
    urgency: str,
    service_type: str,
    is_backup: bool = False,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate customer price from contractor quote.

    Returns (effective_quote, markup_pct, customer_price).
    For backups, the quote is inflated by BACKUP_PREMIUM first.
    """
    markup_rate = get_markup_rate(urgency, service_type)

    if is_backup:
        effective_quote = (contractor_quote * (1 + BACKUP_PREMIUM)).quantize(Decimal("0.01"))
    else:
        effective_quote = contractor_quote

    customer_price = (effective_quote * (1 + markup_rate)).quantize(Decimal("0.01"))
    markup_pct = (markup_rate * 100).quantize(Decimal("0.01"))

    return effective_quote, markup_pct, customer_price
