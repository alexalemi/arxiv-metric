"""Benchmark execution runner with rate limiting and progress tracking."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from tqdm import tqdm

from ..evaluation.judge import Judge, JudgmentResult
from ..evaluation.taxonomy import EscalationLevel
from ..metrics.afim_score import AFIMCalculator, AFIMResult, TestResult
from ..multiturn.runner import MultiTurnRunner, MultiTurnConfig
from ..multiturn.types import MultiTurnBenchmarkResult
from ..prompts.loader import PromptLoader, TestPrompt
from ..providers.base import LLMProvider, LLMResponse


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark execution."""

    # Rate limiting (requests per minute per provider)
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "openai": 60,
        "anthropic": 50,
        "google": 60,
        "xai": 60,
    })

    # Concurrency settings
    max_concurrent_per_provider: int = 5

    # Temperature for target models (higher = more variance in responses)
    target_temperature: float = 0.7

    # Use ensemble judging for more robust evaluation
    use_ensemble_judging: bool = False

    # Output directory for results
    output_dir: Path = field(default_factory=lambda: Path("data/results"))

    # Save intermediate results
    save_incremental: bool = True


@dataclass
class BenchmarkRun:
    """Results from a complete benchmark run."""

    run_id: str
    timestamp: datetime
    config: BenchmarkConfig
    target_model: str
    target_provider: str
    judge_model: str
    judge_provider: str
    afim_result: AFIMResult
    raw_results: List[Dict] = field(default_factory=list, repr=False)


class BenchmarkRunner:
    """Orchestrates benchmark execution across models."""

    def __init__(
        self,
        target_provider: LLMProvider,
        judge_provider: LLMProvider,
        config: Optional[BenchmarkConfig] = None,
    ):
        """Initialize the benchmark runner.

        Args:
            target_provider: The LLM provider being evaluated.
            judge_provider: The LLM provider used for judging (should be different family).
            config: Benchmark configuration.
        """
        self.target = target_provider
        self.judge = Judge(judge_provider)
        self.config = config or BenchmarkConfig()
        self.calculator = AFIMCalculator()

        # Rate limiting semaphores
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._rate_limiters: Dict[str, asyncio.Lock] = {}

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_semaphore(self, provider_name: str) -> asyncio.Semaphore:
        """Get or create semaphore for a provider."""
        if provider_name not in self._semaphores:
            max_concurrent = self.config.max_concurrent_per_provider
            self._semaphores[provider_name] = asyncio.Semaphore(max_concurrent)
        return self._semaphores[provider_name]

    async def _rate_limited_request(
        self,
        provider: LLMProvider,
        coro,
    ):
        """Execute a request with rate limiting."""
        semaphore = self._get_semaphore(provider.provider_name)
        rate_limit = self.config.rate_limits.get(provider.provider_name, 60)
        delay = 60.0 / rate_limit  # Seconds between requests

        async with semaphore:
            # Simple rate limiting via delay
            await asyncio.sleep(delay)
            return await coro

    async def run_single_prompt(
        self,
        prompt: TestPrompt,
    ) -> tuple[TestResult, str]:
        """Run a single prompt through target and judge.

        Args:
            prompt: The test prompt to execute.

        Returns:
            Tuple of (TestResult with judgment, full model response text).
        """
        # Get response from target model
        target_response: LLMResponse = await self._rate_limited_request(
            self.target,
            self.target.generate(
                prompt=prompt.content,
                temperature=self.config.target_temperature,
            ),
        )

        # Judge the response
        if self.config.use_ensemble_judging:
            judgment: JudgmentResult = await self._rate_limited_request(
                self.judge.provider,
                self.judge.evaluate_with_ensemble(
                    original_prompt=prompt.content,
                    response=target_response.content,
                ),
            )
        else:
            judgment: JudgmentResult = await self._rate_limited_request(
                self.judge.provider,
                self.judge.evaluate(
                    original_prompt=prompt.content,
                    response=target_response.content,
                ),
            )

        test_result = TestResult(
            prompt_id=prompt.id,
            escalation_level=EscalationLevel(prompt.escalation_level),
            judgment=judgment,
            model=self.target.model,
            provider=self.target.provider_name,
        )

        return test_result, target_response.content

    async def run_benchmark(
        self,
        prompts: Optional[List[TestPrompt]] = None,
        pilot_mode: bool = False,
    ) -> BenchmarkRun:
        """Run the full benchmark.

        Args:
            prompts: Optional list of prompts. If None, loads from files.
            pilot_mode: If True, run with reduced prompt set for validation.

        Returns:
            BenchmarkRun with complete results.
        """
        # Load prompts
        loader = PromptLoader()
        if prompts is None:
            if pilot_mode:
                prompts = loader.load_pilot_set(per_level=6)
            else:
                prompts = loader.load_all()

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        results: List[TestResult] = []
        raw_results: List[Dict] = []
        results_lock = asyncio.Lock()

        async def process_prompt(prompt: TestPrompt, pbar: tqdm) -> None:
            """Process a single prompt and add results to shared list."""
            try:
                result, model_response = await self.run_single_prompt(prompt)

                # Save raw result for inspection (includes full transcript)
                raw_result = {
                    "prompt_id": prompt.id,
                    "prompt_content": prompt.content,
                    "model_response": model_response,
                    "escalation_level": prompt.escalation_level,
                    "category": result.judgment.category.name,
                    "score": result.judgment.score,
                    "confidence": result.judgment.confidence,
                    "evidence": result.judgment.evidence,
                    "reasoning": result.judgment.reasoning,
                }

                async with results_lock:
                    results.append(result)
                    raw_results.append(raw_result)

                    # Incremental save
                    if self.config.save_incremental:
                        self._save_incremental(run_id, raw_results)

            except Exception as e:
                tqdm.write(f"Error on {prompt.id}: {e}")
            finally:
                pbar.update(1)

        # Execute prompts concurrently with progress bar
        with tqdm(total=len(prompts), desc=f"Testing {self.target.model}") as pbar:
            tasks = [process_prompt(prompt, pbar) for prompt in prompts]
            await asyncio.gather(*tasks)

        # Calculate AFIM score
        afim_result = self.calculator.calculate(results)

        # Create benchmark run
        benchmark_run = BenchmarkRun(
            run_id=run_id,
            timestamp=datetime.now(),
            config=self.config,
            target_model=self.target.model,
            target_provider=self.target.provider_name,
            judge_model=self.judge.provider.model,
            judge_provider=self.judge.provider.provider_name,
            afim_result=afim_result,
            raw_results=raw_results,
        )

        # Save final results
        self._save_final(benchmark_run)

        return benchmark_run

    def _save_incremental(self, run_id: str, results: List[Dict]) -> None:
        """Save incremental results to disk."""
        path = self.config.output_dir / f"{run_id}_incremental.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2)

    def _save_final(self, run: BenchmarkRun) -> None:
        """Save final benchmark results."""
        path = self.config.output_dir / f"{run.run_id}_final.json"

        # Convert to serializable format
        data = {
            "run_id": run.run_id,
            "timestamp": run.timestamp.isoformat(),
            "target_model": run.target_model,
            "target_provider": run.target_provider,
            "judge_model": run.judge_model,
            "judge_provider": run.judge_provider,
            "afim_score": run.afim_result.afim_score,
            "confidence_interval": run.afim_result.confidence_interval,
            "num_tests": run.afim_result.num_tests,
            "level_scores": {
                level.name: score
                for level, score in run.afim_result.level_scores.items()
            },
            "category_distribution": {
                cat.name: count
                for cat, count in run.afim_result.category_distribution.items()
            },
            "raw_results": run.raw_results,
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Also save summary
        summary_path = self.config.output_dir / f"{run.run_id}_summary.txt"
        with open(summary_path, "w") as f:
            f.write(self._generate_summary(run))

    def _generate_summary(self, run: BenchmarkRun) -> str:
        """Generate human-readable summary of results."""
        lines = [
            "=" * 60,
            "AFIM Benchmark Results",
            "=" * 60,
            f"Run ID: {run.run_id}",
            f"Timestamp: {run.timestamp.isoformat()}",
            f"",
            f"Target Model: {run.target_model} ({run.target_provider})",
            f"Judge Model: {run.judge_model} ({run.judge_provider})",
            f"",
            "-" * 60,
            "AFIM SCORE",
            "-" * 60,
            f"Score: {run.afim_result.afim_score:.2f} / 100",
            f"95% CI: [{run.afim_result.confidence_interval[0]:.2f}, {run.afim_result.confidence_interval[1]:.2f}]",
            f"Tests Run: {run.afim_result.num_tests}",
            f"",
            "-" * 60,
            "SCORES BY ESCALATION LEVEL",
            "-" * 60,
        ]

        for level, score in sorted(run.afim_result.level_scores.items()):
            lines.append(f"  {level.name}: {score:.2f}")

        lines.extend([
            f"",
            "-" * 60,
            "CATEGORY DISTRIBUTION",
            "-" * 60,
        ])

        for cat, count in sorted(run.afim_result.category_distribution.items()):
            pct = (count / run.afim_result.num_tests) * 100
            lines.append(f"  {cat.name}: {count} ({pct:.1f}%)")

        lines.append("=" * 60)

        return "\n".join(lines)


async def run_benchmark(
    target_provider: LLMProvider,
    judge_provider: LLMProvider,
    multiturn: bool = False,
    max_turns: int = 7,
    pilot_mode: bool = False,
    prompts: Optional[List[TestPrompt]] = None,
    output_dir: Optional[Path] = None,
    use_ensemble_judging: bool = False,
) -> Union[BenchmarkRun, MultiTurnBenchmarkResult]:
    """Run benchmark in either single-turn or multi-turn mode.

    Args:
        target_provider: The LLM being evaluated.
        judge_provider: The LLM for judging.
        multiturn: If True, run multi-turn evaluation.
        max_turns: Maximum turns for multi-turn mode.
        pilot_mode: If True, use reduced prompt set.
        prompts: Optional explicit list of prompts.
        output_dir: Output directory for results.
        use_ensemble_judging: Use ensemble judging (single-turn only).

    Returns:
        BenchmarkRun for single-turn, MultiTurnBenchmarkResult for multi-turn.
    """
    if multiturn:
        config = MultiTurnConfig(max_turns=max_turns)
        if output_dir:
            config.output_dir = output_dir

        runner = MultiTurnRunner(
            target_provider=target_provider,
            judge_provider=judge_provider,
            config=config,
        )
        return await runner.run_benchmark(prompts=prompts, pilot_mode=pilot_mode)
    else:
        config = BenchmarkConfig(use_ensemble_judging=use_ensemble_judging)
        if output_dir:
            config.output_dir = output_dir

        runner = BenchmarkRunner(
            target_provider=target_provider,
            judge_provider=judge_provider,
            config=config,
        )
        return await runner.run_benchmark(prompts=prompts, pilot_mode=pilot_mode)
