"""Data types for the scientific delusion encouragement eval."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class DelusionPrompt:
    """A single delusion test prompt."""

    id: str
    style: str  # "naive" or "misguided"
    field: str  # e.g. "physics", "biology"
    content: str
    scenario: str


@dataclass
class DelusionTurnJudgment:
    """Binary judgment for a single assistant turn."""

    encouraged: bool
    reasoning: str


@dataclass
class DelusionTurn:
    """A single turn in a delusion conversation."""

    turn_number: int  # 1-indexed
    role: str  # "user" or "assistant"
    content: str
    judgment: Optional[DelusionTurnJudgment] = None  # Only for assistant turns


@dataclass
class DelusionTrajectory:
    """Full trajectory of a delusion conversation."""

    prompt_id: str
    style: str
    science_field: str
    turns: List[DelusionTurn] = field(default_factory=list)
    turn_judgments: List[DelusionTurnJudgment] = field(default_factory=list)

    def add_user_turn(self, content: str) -> None:
        turn_num = len(self.turns) + 1
        self.turns.append(
            DelusionTurn(turn_number=turn_num, role="user", content=content)
        )

    def add_assistant_turn(self, content: str, judgment: DelusionTurnJudgment) -> None:
        turn_num = len(self.turns) + 1
        self.turns.append(
            DelusionTurn(
                turn_number=turn_num,
                role="assistant",
                content=content,
                judgment=judgment,
            )
        )
        self.turn_judgments.append(judgment)

    @property
    def num_assistant_turns(self) -> int:
        return len(self.turn_judgments)

    @property
    def first_encouragement_turn(self) -> Optional[int]:
        """1-indexed turn number of the first encouragement, or None."""
        for i, j in enumerate(self.turn_judgments):
            if j.encouraged:
                return i + 1
        return None


@dataclass
class DelusionTestResult:
    """Result of a single delusion test."""

    prompt_id: str
    style: str
    field: str
    encouraged: bool  # holistic judgment
    holistic_reasoning: str
    first_encouragement_turn: Optional[int]
    turn_judgments: List[DelusionTurnJudgment]
    turns: List[DelusionTurn]
    model: str
    provider: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0


@dataclass
class DelusionBenchmarkResult:
    """Aggregate results from a delusion benchmark run."""

    run_id: str
    mode: str = "delusion"
    target_model: str = ""
    judge_model: str = ""
    encouragement_rate: float = 0.0
    encouragement_rate_ci: Tuple[float, float] = (0.0, 0.0)
    num_tests: int = 0
    trajectories: List[DelusionTestResult] = field(default_factory=list)
