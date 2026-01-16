"""Prompt loading and management."""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import List, Optional

import yaml


class EscalationLevel(IntEnum):
    """Escalation levels for test prompts."""

    NAIVE_CURIOUS = 1
    MISGUIDED_AMATEUR = 2
    SEEKING_SHORTCUTS = 3
    EXPLICIT_FABRICATION = 4
    DELIBERATE_FRAUD = 5


@dataclass
class TestPrompt:
    """A single test prompt for the benchmark."""

    id: str
    escalation_level: EscalationLevel
    content: str
    scenario: str
    variation: int
    expected_category_range: tuple[int, int]  # Min/max expected fraud category


@dataclass
class PromptSet:
    """Collection of prompts for a scenario."""

    scenario: str
    description: str
    prompts: List[TestPrompt]


class PromptLoader:
    """Loader for test prompts from YAML files."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing YAML prompt files.
                        Defaults to data/prompts in project root.
        """
        if prompts_dir is None:
            # Default to data/prompts relative to this file
            prompts_dir = Path(__file__).parent.parent.parent / "data" / "prompts"
        self.prompts_dir = Path(prompts_dir)

    def load_all(self) -> List[TestPrompt]:
        """Load all prompts from all YAML files."""
        prompts = []
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            prompts.extend(self._load_file(yaml_file))
        return prompts

    def load_by_level(self, level: EscalationLevel) -> List[TestPrompt]:
        """Load prompts for a specific escalation level."""
        all_prompts = self.load_all()
        return [p for p in all_prompts if p.escalation_level == level]

    def load_pilot_set(self, per_level: int = 6) -> List[TestPrompt]:
        """Load a balanced pilot set of prompts.

        Args:
            per_level: Number of prompts per escalation level.

        Returns:
            Balanced list of prompts across all levels.
        """
        all_prompts = self.load_all()
        pilot_prompts = []

        for level in EscalationLevel:
            level_prompts = [p for p in all_prompts if p.escalation_level == level]
            # Take up to per_level prompts, cycling if needed
            selected = level_prompts[:per_level]
            pilot_prompts.extend(selected)

        return pilot_prompts

    def _load_file(self, path: Path) -> List[TestPrompt]:
        """Load prompts from a single YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        prompts = []
        for scenario_data in data.get("scenarios", []):
            scenario = scenario_data["scenario"]

            for prompt_data in scenario_data.get("prompts", []):
                prompt = TestPrompt(
                    id=prompt_data["id"],
                    escalation_level=EscalationLevel(prompt_data["escalation_level"]),
                    content=prompt_data["content"],
                    scenario=scenario,
                    variation=prompt_data.get("variation", 1),
                    expected_category_range=tuple(
                        prompt_data.get("expected_category_range", [0, 6])
                    ),
                )
                prompts.append(prompt)

        return prompts
