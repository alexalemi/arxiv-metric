"""Tests for fraud evaluation taxonomy."""

import pytest

from src.evaluation.taxonomy import (
    EscalationLevel,
    FraudCategory,
    FRAUD_RUBRIC,
    ESCALATION_WEIGHTS,
    get_category_score,
    get_escalation_weight,
)


class TestFraudCategory:
    def test_category_values(self):
        """Test that fraud categories have correct integer values."""
        assert FraudCategory.EXPLICIT_REFUSAL == 0
        assert FraudCategory.FULL_FACILITATION == 6

    def test_all_categories_in_rubric(self):
        """Test that all categories have rubric entries."""
        for category in FraudCategory:
            assert category in FRAUD_RUBRIC

    def test_score_range(self):
        """Test that all scores are in [0, 1]."""
        for entry in FRAUD_RUBRIC.values():
            assert 0.0 <= entry.score <= 1.0

    def test_scores_are_monotonic(self):
        """Test that scores increase with category level."""
        scores = [FRAUD_RUBRIC[cat].score for cat in sorted(FraudCategory)]
        assert scores == sorted(scores)


class TestEscalationLevel:
    def test_level_values(self):
        """Test that escalation levels have correct integer values."""
        assert EscalationLevel.NAIVE_CURIOUS == 1
        assert EscalationLevel.DELIBERATE_FRAUD == 5

    def test_all_levels_in_weights(self):
        """Test that all levels have weight configurations."""
        for level in EscalationLevel:
            assert level in ESCALATION_WEIGHTS

    def test_weight_range(self):
        """Test that weights are positive."""
        for config in ESCALATION_WEIGHTS.values():
            assert config.weight > 0

    def test_lower_levels_weighted_higher(self):
        """Test that naive users are weighted more heavily."""
        naive_weight = ESCALATION_WEIGHTS[EscalationLevel.NAIVE_CURIOUS].weight
        fraud_weight = ESCALATION_WEIGHTS[EscalationLevel.DELIBERATE_FRAUD].weight
        assert naive_weight > fraud_weight


class TestHelperFunctions:
    def test_get_category_score(self):
        """Test score retrieval function."""
        assert get_category_score(FraudCategory.EXPLICIT_REFUSAL) == 0.0
        assert get_category_score(FraudCategory.FULL_FACILITATION) == 1.0

    def test_get_escalation_weight(self):
        """Test weight retrieval function."""
        weight = get_escalation_weight(EscalationLevel.NAIVE_CURIOUS)
        assert weight == 2.0
