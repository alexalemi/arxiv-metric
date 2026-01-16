"""Data types for multi-turn conversation evaluation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from ..evaluation.taxonomy import FraudCategory, EscalationLevel


class ConversationTrend(Enum):
    """Trend of model behavior across conversation turns."""

    STABLE_REFUSAL = "stable_refusal"  # Consistent refusal throughout
    STABLE_COMPLIANCE = "stable_compliance"  # Consistently problematic
    SOFTENING = "softening"  # Started refusing, became more helpful
    HARDENING = "hardening"  # Started helpful, became more resistant
    OSCILLATING = "oscillating"  # Inconsistent behavior


class FollowUpTactic(Enum):
    """Type of follow-up prompt tactic used."""

    CONTINUE = "continue"  # Encourage model to continue what it offered
    PERSIST = "persist"  # Gently push back on refusal
    ELABORATE = "elaborate"  # Ask for more detail


@dataclass
class ConversationTurn:
    """A single turn in a multi-turn conversation."""

    turn_number: int  # 1-indexed
    role: str  # "user" or "assistant"
    content: str
    category: Optional[FraudCategory] = None  # Only set for assistant turns
    tactic: Optional[FollowUpTactic] = None  # Only set for user follow-up turns


@dataclass
class TurnJudgment:
    """Judgment for a single assistant turn."""

    category: FraudCategory
    score: float  # 0.0-1.0
    confidence: float
    evidence: str
    reasoning: str


@dataclass
class ConversationTrajectory:
    """Full trajectory of a multi-turn conversation."""

    prompt_id: str
    escalation_level: EscalationLevel
    turns: List[ConversationTurn] = field(default_factory=list)
    category_progression: List[FraudCategory] = field(default_factory=list)
    trend: Optional[ConversationTrend] = None

    def add_user_turn(
        self,
        content: str,
        tactic: Optional[FollowUpTactic] = None,
    ) -> None:
        """Add a user turn to the trajectory."""
        turn_num = len(self.turns) + 1
        self.turns.append(ConversationTurn(
            turn_number=turn_num,
            role="user",
            content=content,
            tactic=tactic,
        ))

    def add_assistant_turn(
        self,
        content: str,
        category: FraudCategory,
    ) -> None:
        """Add an assistant turn to the trajectory."""
        turn_num = len(self.turns) + 1
        self.turns.append(ConversationTurn(
            turn_number=turn_num,
            role="assistant",
            content=content,
            category=category,
        ))
        self.category_progression.append(category)

    @property
    def num_turns(self) -> int:
        """Number of assistant turns (responses)."""
        return len(self.category_progression)

    @property
    def peak_category(self) -> Optional[FraudCategory]:
        """Highest (most problematic) category reached."""
        if not self.category_progression:
            return None
        return max(self.category_progression)

    @property
    def final_category(self) -> Optional[FraudCategory]:
        """Category of the last assistant turn."""
        if not self.category_progression:
            return None
        return self.category_progression[-1]

    @property
    def initial_category(self) -> Optional[FraudCategory]:
        """Category of the first assistant turn."""
        if not self.category_progression:
            return None
        return self.category_progression[0]


@dataclass
class MultiTurnJudgment:
    """Judgment result for a complete multi-turn conversation."""

    trajectory: ConversationTrajectory
    resistance_score: float  # 0-100, higher = more resistant
    softening_index: float  # 0-1, higher = more softening
    trajectory_afim: float  # 0-100, considering full conversation
    turns_to_compliance: Optional[int]  # Turn when first crossed threshold, or None
    trend: ConversationTrend
    single_turn_equivalent_category: FraudCategory  # For comparison with single-turn


@dataclass
class MultiTurnTestResult:
    """Result of a single multi-turn test."""

    prompt_id: str
    escalation_level: EscalationLevel
    judgment: MultiTurnJudgment
    model: str
    provider: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0


@dataclass
class MultiTurnBenchmarkResult:
    """Aggregate results from a multi-turn benchmark run."""

    run_id: str
    mode: str = "multiturn"
    afim_score: float = 0.0  # Trajectory-weighted AFIM
    resistance_score: float = 0.0  # Average resistance score
    softening_rate: float = 0.0  # Proportion showing softening
    avg_turns_to_compliance: Optional[float] = None
    trajectories: List[MultiTurnTestResult] = field(default_factory=list)

    # Category distribution across all final turns
    category_distribution: dict = field(default_factory=dict)

    # Trend distribution
    trend_distribution: dict = field(default_factory=dict)
