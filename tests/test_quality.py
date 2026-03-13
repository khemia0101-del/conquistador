"""Tests for quality control system."""

import pytest
from decimal import Decimal
from conquistador.quality.scoring import (
    calculate_overall_rating,
    get_quality_status,
    ON_TIME_WEIGHT,
    PROFESSIONALISM_WEIGHT,
    PROBLEM_SOLVED_WEIGHT,
)


class TestOverallRating:
    def test_perfect_scores(self):
        rating = calculate_overall_rating(5, 5, 5)
        assert rating == Decimal("5.00")

    def test_minimum_scores(self):
        rating = calculate_overall_rating(1, 1, 1)
        assert rating == Decimal("1.00")

    def test_weighted_calculation(self):
        # on_time=5 (30%), professionalism=3 (30%), problem_solved=4 (40%)
        expected = (
            Decimal("5") * ON_TIME_WEIGHT
            + Decimal("3") * PROFESSIONALISM_WEIGHT
            + Decimal("4") * PROBLEM_SOLVED_WEIGHT
        )
        rating = calculate_overall_rating(5, 3, 4)
        assert rating == expected

    def test_weights_sum_to_one(self):
        assert ON_TIME_WEIGHT + PROFESSIONALISM_WEIGHT + PROBLEM_SOLVED_WEIGHT == Decimal("1.00")


class TestQualityStatus:
    def test_excellent(self):
        assert get_quality_status(Decimal("4.8")) == "excellent"

    def test_good(self):
        assert get_quality_status(Decimal("4.2")) == "good"

    def test_warning(self):
        assert get_quality_status(Decimal("3.7")) == "warning"

    def test_probation(self):
        assert get_quality_status(Decimal("3.1")) == "probation"

    def test_suspended(self):
        assert get_quality_status(Decimal("2.5")) == "suspended"

    def test_boundary_excellent(self):
        assert get_quality_status(Decimal("4.5")) == "excellent"

    def test_boundary_good(self):
        assert get_quality_status(Decimal("4.0")) == "good"
