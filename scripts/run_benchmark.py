#!/usr/bin/env python3
"""CLI entry point for AFIM benchmark."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.execution.runner import BenchmarkConfig, BenchmarkRunner
from src.multiturn import MultiTurnRunner, MultiTurnConfig, MultiTurnBenchmarkResult
from src.providers import AnthropicProvider, GoogleProvider, OpenAIProvider, XAIProvider

console = Console()


def get_provider(provider_name: str, model: str):
    """Create a provider instance."""
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "xai": XAIProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    return providers[provider_name](model=model)


def get_default_judge() -> tuple[str, str]:
    """Get default judge provider/model (Claude for consistency)."""
    return ("anthropic", "claude-sonnet-4-5")


def print_results(run) -> None:
    """Print benchmark results in a nice format."""
    console.print()
    console.print(Panel.fit(
        f"[bold green]AFIM Score: {run.afim_result.afim_score:.1f}[/bold green] / 100\n"
        f"95% CI: [{run.afim_result.confidence_interval[0]:.1f}, {run.afim_result.confidence_interval[1]:.1f}]",
        title=f"Results for {run.target_model}",
    ))

    # Level scores table
    table = Table(title="Scores by Escalation Level")
    table.add_column("Level", style="cyan")
    table.add_column("Score", style="magenta")

    for level, score in sorted(run.afim_result.level_scores.items()):
        table.add_row(level.name, f"{score:.1f}")

    console.print(table)

    # Category distribution
    cat_table = Table(title="Category Distribution")
    cat_table.add_column("Category", style="cyan")
    cat_table.add_column("Count", style="magenta")
    cat_table.add_column("Percentage", style="green")

    total = run.afim_result.num_tests
    for cat, count in sorted(run.afim_result.category_distribution.items()):
        pct = (count / total) * 100 if total > 0 else 0
        cat_table.add_row(cat.name, str(count), f"{pct:.1f}%")

    console.print(cat_table)

    console.print(f"\n[dim]Results saved to: data/results/{run.run_id}_final.json[/dim]")


def print_multiturn_results(result: MultiTurnBenchmarkResult) -> None:
    """Print multi-turn benchmark results in a nice format."""
    console.print()
    console.print(Panel.fit(
        f"[bold green]Trajectory AFIM: {result.afim_score:.1f}[/bold green] / 100\n"
        f"Resistance Score: {result.resistance_score:.1f} / 100\n"
        f"Softening Rate: {result.softening_rate * 100:.1f}%",
        title=f"Multi-Turn Results",
    ))

    # Trend distribution table
    table = Table(title="Behavioral Trends")
    table.add_column("Trend", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Percentage", style="green")

    total = len(result.trajectories)
    for trend, count in sorted(result.trend_distribution.items()):
        pct = (count / total) * 100 if total > 0 else 0
        # Color-code concerning trends
        trend_display = trend
        if trend == "softening":
            trend_display = f"[red]{trend}[/red]"
        elif trend == "stable_refusal":
            trend_display = f"[green]{trend}[/green]"
        table.add_row(trend_display, str(count), f"{pct:.1f}%")

    console.print(table)

    # Category distribution (final turns)
    cat_table = Table(title="Final Category Distribution")
    cat_table.add_column("Category", style="cyan")
    cat_table.add_column("Count", style="magenta")
    cat_table.add_column("Percentage", style="green")

    for cat, count in sorted(result.category_distribution.items()):
        pct = (count / total) * 100 if total > 0 else 0
        cat_table.add_row(cat, str(count), f"{pct:.1f}%")

    console.print(cat_table)

    if result.avg_turns_to_compliance:
        console.print(f"\n[yellow]Average turns to compliance: {result.avg_turns_to_compliance:.1f}[/yellow]")

    console.print(f"\n[dim]Results saved to: data/results/{result.run_id}_final.json[/dim]")


async def run_benchmark(args) -> None:
    """Run the benchmark with given arguments."""
    mode_str = "Multi-Turn " if args.multiturn else ""
    console.print(Panel.fit(
        f"[bold]{mode_str}AFIM Benchmark[/bold]\n"
        "Academic Fraud Inclination Metric",
        title="Starting Benchmark",
    ))

    # Create target provider
    console.print(f"[cyan]Target:[/cyan] {args.model} ({args.provider})")
    target = get_provider(args.provider, args.model)

    # Create judge provider
    if args.judge_provider and args.judge_model:
        judge_provider_name = args.judge_provider
        judge_model_name = args.judge_model
    else:
        judge_provider_name, judge_model_name = get_default_judge()

    console.print(f"[cyan]Judge:[/cyan] {judge_model_name} ({judge_provider_name})")
    judge = get_provider(judge_provider_name, judge_model_name)

    console.print()

    if args.multiturn:
        # Multi-turn mode
        console.print(f"[cyan]Mode:[/cyan] Multi-turn (max {args.max_turns} turns)")

        config = MultiTurnConfig(
            max_turns=args.max_turns,
            output_dir=Path(args.output_dir),
        )

        runner = MultiTurnRunner(
            target_provider=target,
            judge_provider=judge,
            config=config,
        )

        if args.pilot:
            console.print("[yellow]Running in pilot mode (1 prompt per level)[/yellow]")

        result = await runner.run_benchmark(pilot_mode=args.pilot)
        print_multiturn_results(result)

    else:
        # Single-turn mode
        console.print("[cyan]Mode:[/cyan] Single-turn")

        config = BenchmarkConfig(
            use_ensemble_judging=args.ensemble,
            output_dir=Path(args.output_dir),
        )

        runner = BenchmarkRunner(
            target_provider=target,
            judge_provider=judge,
            config=config,
        )

        if args.pilot:
            console.print("[yellow]Running in pilot mode (30 prompts)[/yellow]")

        run = await runner.run_benchmark(pilot_mode=args.pilot)
        print_results(run)


def main():
    parser = argparse.ArgumentParser(
        description="AFIM Benchmark - Measure LLM academic fraud facilitation"
    )

    # Target model
    parser.add_argument(
        "--provider", "-p",
        choices=["openai", "anthropic", "google", "xai"],
        default="openai",
        help="Target LLM provider to evaluate"
    )
    parser.add_argument(
        "--model", "-m",
        default="gpt-4o",
        help="Target model name"
    )

    # Judge model (optional, auto-selects cross-family if not specified)
    parser.add_argument(
        "--judge-provider",
        choices=["openai", "anthropic", "google", "xai"],
        help="Judge LLM provider (defaults to different family)"
    )
    parser.add_argument(
        "--judge-model",
        help="Judge model name"
    )

    # Execution options
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Run pilot mode with reduced prompt set (~30 prompts for single-turn, 5 for multi-turn)"
    )
    parser.add_argument(
        "--ensemble",
        action="store_true",
        help="Use ensemble judging for more robust evaluation (single-turn only)"
    )

    # Multi-turn options
    parser.add_argument(
        "--multiturn", "-mt",
        action="store_true",
        help="Run multi-turn evaluation to test model resistance over conversation"
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=7,
        help="Maximum conversation turns for multi-turn mode (default: 7)"
    )

    # Output
    parser.add_argument(
        "--output-dir", "-o",
        default="data/results",
        help="Directory for output files"
    )

    args = parser.parse_args()

    # Warn if same provider for target and judge
    if args.judge_provider == args.provider:
        console.print(
            "[yellow]Warning: Using same provider for target and judge may introduce bias[/yellow]"
        )

    try:
        asyncio.run(run_benchmark(args))
    except KeyboardInterrupt:
        console.print("\n[red]Benchmark interrupted[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
