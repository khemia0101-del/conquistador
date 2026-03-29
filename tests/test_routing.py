"""Tests for routing, matching, and pricing logic."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from conquistador.routing.matcher import score_contractor
from conquistador.routing.pricing import get_markup_rate, calculate_customer_price


class TestContractorScoring:
    def _make_contractor(self, quality=None, acceptance=None, daily=0, max_daily=5, avg_response=None):
        c = MagicMock()
        c.quality_score = Decimal(str(quality)) if quality else None
        c.acceptance_rate = Decimal(str(acceptance)) if acceptance else None
        c.current_daily_leads = daily
        c.max_daily_leads = max_daily
        c.avg_response_min = Decimal(str(avg_response)) if avg_response is not None else None
        return c

    def test_high_quality_scores_higher(self):
        lead = MagicMock()
        high = self._make_contractor(quality=4.8, acceptance=90)
        low = self._make_contractor(quality=3.0, acceptance=50)
        assert score_contractor(high, lead) > score_contractor(low, lead)

    def test_full_capacity_scores_lower(self):
        lead = MagicMock()
        available = self._make_contractor(quality=4.0, daily=0, max_daily=5)
        full = self._make_contractor(quality=4.0, daily=5, max_daily=5)
        assert score_contractor(available, lead) > score_contractor(full, lead)

    def test_no_quality_data(self):
        lead = MagicMock()
        c = self._make_contractor()
        score = score_contractor(c, lead)
        assert score >= 0

    def test_fast_responder_scores_higher(self):
        lead = MagicMock()
        fast = self._make_contractor(quality=4.0, avg_response=3)
        slow = self._make_contractor(quality=4.0, avg_response=45)
        assert score_contractor(fast, lead) > score_contractor(slow, lead)

    def test_moderate_responder_gets_some_bonus(self):
        lead = MagicMock()
        moderate = self._make_contractor(quality=4.0, avg_response=10)
        none_resp = self._make_contractor(quality=4.0, avg_response=None)
        assert score_contractor(moderate, lead) > score_contractor(none_resp, lead)


class TestDynamicPricing:
    def test_emergency_higher_markup(self):
        emergency_rate = get_markup_rate("emergency", "hvac_repair")
        routine_rate = get_markup_rate("routine", "hvac_repair")
        assert emergency_rate > routine_rate

    def test_routine_lowest_markup(self):
        # Use summer date (no seasonal boost) for base rate test
        summer = datetime(2026, 7, 15)
        rate = get_markup_rate("routine", "hvac_repair", now=summer)
        assert rate == Decimal("0.15")

    def test_emergency_markup_rate(self):
        summer = datetime(2026, 7, 15)
        rate = get_markup_rate("emergency", "hvac_repair", now=summer)
        assert rate == Decimal("0.28")

    def test_seasonal_boost_winter(self):
        # January = heating season
        winter = datetime(2026, 1, 15)
        summer = datetime(2026, 7, 15)
        winter_rate = get_markup_rate("routine", "heating_oil", now=winter)
        summer_rate = get_markup_rate("routine", "heating_oil", now=summer)
        assert winter_rate > summer_rate

    def test_seasonal_boost_not_applied_to_ac(self):
        winter = datetime(2026, 1, 15)
        ac_rate = get_markup_rate("routine", "ac_service", now=winter)
        assert ac_rate == Decimal("0.15")  # No seasonal boost for AC

    def test_customer_price_calculation(self):
        # Use AC service (no seasonal boost) for clean base rate test
        quote = Decimal("500.00")
        effective, markup_pct, price = calculate_customer_price(
            quote, "routine", "ac_service"
        )
        assert effective == quote
        assert markup_pct == Decimal("15.00")
        assert price == Decimal("575.00")

    def test_backup_premium(self):
        quote = Decimal("500.00")
        primary_q, _, primary_p = calculate_customer_price(
            quote, "routine", "hvac_repair", is_backup=False
        )
        backup_q, _, backup_p = calculate_customer_price(
            quote, "routine", "hvac_repair", is_backup=True
        )
        assert backup_q > primary_q  # Backup quote is higher
        assert backup_p > primary_p  # Backup customer price is higher
        assert backup_q == Decimal("575.00")  # 500 * 1.15

    def test_emergency_winter_heating_oil_max_markup(self):
        """Emergency + heating oil + winter = highest markup."""
        winter = datetime(2026, 1, 15)
        rate = get_markup_rate("emergency", "heating_oil", now=winter)
        assert rate == Decimal("0.31")  # 0.28 + 0.03 seasonal
