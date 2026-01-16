"""Tests for prompt loading."""

import pytest
from pathlib import Path

from src.prompts.loader import PromptLoader, EscalationLevel, TestPrompt


class TestPromptLoader:
    @pytest.fixture
    def loader(self):
        return PromptLoader()

    def test_load_all_prompts(self, loader):
        """Test that prompts load successfully."""
        prompts = loader.load_all()
        assert len(prompts) > 0

    def test_prompts_have_required_fields(self, loader):
        """Test that all prompts have required fields."""
        prompts = loader.load_all()
        for prompt in prompts:
            assert prompt.id
            assert prompt.content
            assert prompt.scenario
            assert prompt.escalation_level in EscalationLevel

    def test_load_by_level(self, loader):
        """Test filtering prompts by escalation level."""
        for level in EscalationLevel:
            level_prompts = loader.load_by_level(level)
            for prompt in level_prompts:
                assert prompt.escalation_level == level

    def test_pilot_set_balanced(self, loader):
        """Test that pilot set has prompts from all levels."""
        pilot = loader.load_pilot_set(per_level=2)
        levels_present = set(p.escalation_level for p in pilot)
        # Should have prompts from multiple levels
        assert len(levels_present) >= 3

    def test_expected_category_range_valid(self, loader):
        """Test that expected category ranges are valid."""
        prompts = loader.load_all()
        for prompt in prompts:
            low, high = prompt.expected_category_range
            assert 0 <= low <= 6
            assert 0 <= high <= 6
            assert low <= high
