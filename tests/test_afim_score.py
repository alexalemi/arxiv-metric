"""Tests for AFIM score calculation."""

import pytest

from src.evaluation.taxonomy import EscalationLevel, FraudCategory
from src.evaluation.judge import JudgmentResult
from src.metrics.afim_score import AFIMCalculator, TestResult


class TestAFIMCalculator:
    @pytest.fixture
    def calculator(self):
        return AFIMCalculator(bootstrap_samples=100, random_seed=42)

    @pytest.fixture
    def sample_results(self):
        """Create sample test results for testing."""
        results = []
        for i, level in enumerate(EscalationLevel):
            # Vary the category based on level to simulate realistic data
            if level <= EscalationLevel.MISGUIDED_AMATEUR:
                category = FraudCategory.EDUCATIONAL_REDIRECT
            elif level == EscalationLevel.SEEKING_SHORTCUTS:
                category = FraudCategory.PASSIVE_INFORMATION
            else:
                category = FraudCategory.EXPLICIT_REFUSAL

            judgment = JudgmentResult(
                category=category,
                score=0.1 * category.value,
                confidence=0.9,
                evidence="test evidence",
                reasoning="test reasoning",
            )
            results.append(TestResult(
                prompt_id=f"test-{i}",
                escalation_level=level,
                judgment=judgment,
                model="test-model",
                provider="test-provider",
            ))
        return results

    def test_calculate_basic(self, calculator, sample_results):
        """Test basic AFIM calculation."""
        result = calculator.calculate(sample_results)

        assert result.model == "test-model"
        assert result.provider == "test-provider"
        assert 0 <= result.afim_score <= 100
        assert result.num_tests == len(sample_results)

    def test_confidence_interval(self, calculator, sample_results):
        """Test that confidence interval is calculated."""
        result = calculator.calculate(sample_results)

        ci_low, ci_high = result.confidence_interval
        assert ci_low <= result.afim_score <= ci_high

    def test_level_scores(self, calculator, sample_results):
        """Test per-level score breakdown."""
        result = calculator.calculate(sample_results)

        for level in EscalationLevel:
            if level in result.level_scores:
                assert 0 <= result.level_scores[level] <= 100

    def test_category_distribution(self, calculator, sample_results):
        """Test category distribution counting."""
        result = calculator.calculate(sample_results)

        total_count = sum(result.category_distribution.values())
        assert total_count == len(sample_results)

    def test_empty_results_raises(self, calculator):
        """Test that empty results raise error."""
        with pytest.raises(ValueError):
            calculator.calculate([])

    def test_perfect_refusal_score(self, calculator):
        """Test that all refusals give score near 0."""
        results = []
        for level in EscalationLevel:
            judgment = JudgmentResult(
                category=FraudCategory.EXPLICIT_REFUSAL,
                score=0.0,
                confidence=1.0,
                evidence="refused",
                reasoning="refused",
            )
            results.append(TestResult(
                prompt_id=f"test-{level}",
                escalation_level=level,
                judgment=judgment,
                model="test-model",
                provider="test-provider",
            ))

        result = calculator.calculate(results)
        assert result.afim_score == 0.0

    def test_full_facilitation_score(self, calculator):
        """Test that all facilitation gives high score."""
        results = []
        for level in EscalationLevel:
            judgment = JudgmentResult(
                category=FraudCategory.FULL_FACILITATION,
                score=1.0,
                confidence=1.0,
                evidence="facilitated",
                reasoning="facilitated",
            )
            results.append(TestResult(
                prompt_id=f"test-{level}",
                escalation_level=level,
                judgment=judgment,
                model="test-model",
                provider="test-provider",
            ))

        result = calculator.calculate(results)
        # Should be close to 100 but exact value depends on weights
        assert result.afim_score > 50.0
