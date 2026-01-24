#!/usr/bin/env python3
"""CLI entry point for the scientific delusion encouragement eval."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.delusion import DelusionBenchmarkResult, DelusionConfig, DelusionRunner
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


def print_delusion_results(result: DelusionBenchmarkResult) -> None:
    """Print delusion eval results."""
    console.print()
    rate_pct = result.encouragement_rate * 100
    ci_lo = result.encouragement_rate_ci[0] * 100
    ci_hi = result.encouragement_rate_ci[1] * 100
    console.print(
        Panel.fit(
            f"[bold]Encouragement Rate: {rate_pct:.1f}%[/bold]"
            f" [95% CI: {ci_lo:.1f}% - {ci_hi:.1f}%]\n"
            f"Tests run: {result.num_tests}",
            title=f"Delusion Eval — {result.target_model}",
        )
    )

    # Per-field breakdown
    field_counts: dict = {}  # field -> (encouraged, total)
    for t in result.trajectories:
        prev = field_counts.get(t.field, (0, 0))
        field_counts[t.field] = (prev[0] + int(t.encouraged), prev[1] + 1)

    table = Table(title="Encouragement Rate by Field")
    table.add_column("Field", style="cyan")
    table.add_column("Encouraged", style="red")
    table.add_column("Total", style="white")
    table.add_column("Rate", style="magenta")

    for f in sorted(field_counts):
        enc, total = field_counts[f]
        pct = (enc / total) * 100 if total > 0 else 0
        table.add_row(f, str(enc), str(total), f"{pct:.0f}%")

    console.print(table)

    # Per-style breakdown
    style_counts: dict = {}
    for t in result.trajectories:
        prev = style_counts.get(t.style, (0, 0))
        style_counts[t.style] = (prev[0] + int(t.encouraged), prev[1] + 1)

    style_table = Table(title="Encouragement Rate by Style")
    style_table.add_column("Style", style="cyan")
    style_table.add_column("Encouraged", style="red")
    style_table.add_column("Total", style="white")
    style_table.add_column("Rate", style="magenta")

    for s in sorted(style_counts):
        enc, total = style_counts[s]
        pct = (enc / total) * 100 if total > 0 else 0
        style_table.add_row(s, str(enc), str(total), f"{pct:.0f}%")

    console.print(style_table)

    console.print(
        f"\n[dim]Results saved to: data/results/{result.run_id}_final.json[/dim]"
    )


async def run_eval(args) -> None:
    console.print(
        Panel.fit(
            "[bold]Scientific Delusion Encouragement Eval[/bold]\n"
            "Measures whether models encourage users' unsubstantiated scientific claims",
            title="Starting Eval",
        )
    )

    console.print(f"[cyan]Target:[/cyan] {args.model} ({args.provider})")
    target = get_provider(args.provider, args.model)

    # Create judge provider
    if args.judge_provider and args.judge_model:
        judge_provider_name = args.judge_provider
        judge_model_name = args.judge_model
    else:
        judge_provider_name = "anthropic"
        judge_model_name = args.judge_model or "claude-sonnet-4-5"

    console.print(f"[cyan]Judge:[/cyan] {judge_model_name} ({judge_provider_name})")
    judge = get_provider(judge_provider_name, judge_model_name)

    console.print(f"[cyan]Max turns:[/cyan] {args.max_turns}")
    console.print()

    config = DelusionConfig(
        max_turns=args.max_turns,
        output_dir=Path(args.output_dir),
    )

    runner = DelusionRunner(
        target_provider=target,
        judge_provider=judge,
        config=config,
    )

    if args.pilot:
        console.print("[yellow]Running in pilot mode (5 prompts)[/yellow]")

    result = await runner.run_benchmark(pilot_mode=args.pilot)
    print_delusion_results(result)


def main():
    parser = argparse.ArgumentParser(
        description="Scientific Delusion Encouragement Eval — binary scoring of delusion encouragement"
    )

    parser.add_argument(
        "--provider", "-p",
        choices=["openai", "anthropic", "google", "xai"],
        default="openai",
        help="Target LLM provider to evaluate",
    )
    parser.add_argument(
        "--model", "-m", default="gpt-4o", help="Target model name"
    )
    parser.add_argument(
        "--judge-provider",
        choices=["openai", "anthropic", "google", "xai"],
        help="Judge LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--judge-model", help="Judge model name (default: claude-sonnet-4-5)"
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Maximum conversation turns (default: 10)",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Run pilot mode with 5 prompts from different fields",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="data/results",
        help="Directory for output files",
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_eval(args))
    except KeyboardInterrupt:
        console.print("\n[red]Eval interrupted[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
