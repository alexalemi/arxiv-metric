"""Scientific Delusion Encouragement eval — binary scoring of whether models encourage users' unsubstantiated scientific claims."""

from .judge import DelusionJudge
from .runner import DelusionConfig, DelusionRunner
from .types import (
    DelusionBenchmarkResult,
    DelusionPrompt,
    DelusionTestResult,
    DelusionTrajectory,
    DelusionTurnJudgment,
)

__all__ = [
    "DelusionBenchmarkResult",
    "DelusionConfig",
    "DelusionJudge",
    "DelusionPrompt",
    "DelusionRunner",
    "DelusionTestResult",
    "DelusionTrajectory",
    "DelusionTurnJudgment",
]
