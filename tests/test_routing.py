"""Tests for routing and matching logic."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from conquistador.routing.matcher import score_contractor


class TestContractorScoring:
    def _make_contractor(self, quality=None, acceptance=None, daily=0, max_daily=5):
        c = MagicMock()
        c.quality_score = Decimal(str(quality)) if quality else None
        c.acceptance_rate = Decimal(str(acceptance)) if acceptance else None
        c.current_daily_leads = daily
        c.max_daily_leads = max_daily
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
