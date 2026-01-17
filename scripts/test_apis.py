#!/usr/bin/env python3
"""Test that all LLM provider APIs are working.

Usage:
    uv run python scripts/test_apis.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from src.providers import OpenAIProvider, AnthropicProvider, GoogleProvider, XAIProvider

console = Console()

# Test configurations: (provider_class, model, env_var)
TESTS = [
    (OpenAIProvider, "gpt-4o-mini", "OPENAI_API_KEY"),
    (OpenAIProvider, "gpt-5.1", "OPENAI_API_KEY"),
    (AnthropicProvider, "claude-haiku-4-5", "ANTHROPIC_API_KEY"),
    (GoogleProvider, "gemini-2.5-flash", "GOOGLE_API_KEY"),
    (XAIProvider, "grok-3", "XAI_API_KEY"),
]

TEST_PROMPT = "Say 'API test successful' and nothing else."


async def test_provider(provider_class, model: str) -> tuple[bool, str]:
    """Test a single provider/model combination."""
    try:
        provider = provider_class(model=model)
        response = await provider.generate(
            prompt=TEST_PROMPT,
            temperature=0.0,
            max_tokens=50,
        )
        if response.content:
            return True, response.content[:50].replace("\n", " ")
        return False, "Empty response"
    except ValueError as e:
        # Missing API key
        return False, f"Missing key: {e}"
    except Exception as e:
        return False, str(e)[:60]


async def main():
    console.print("\n[bold]AFIM API Connection Test[/bold]\n")

    table = Table(title="Provider API Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="blue")
    table.add_column("Status", style="bold")
    table.add_column("Response/Error")

    results = []

    for provider_class, model, env_var in TESTS:
        provider_name = provider_class.__name__.replace("Provider", "")
        console.print(f"Testing {provider_name} ({model})...", end=" ")

        success, message = await test_provider(provider_class, model)
        results.append((provider_name, model, success, message))

        if success:
            console.print("[green]OK[/green]")
            table.add_row(provider_name, model, "[green]✓ OK[/green]", message)
        else:
            console.print("[red]FAIL[/red]")
            table.add_row(provider_name, model, "[red]✗ FAIL[/red]", message)

    console.print()
    console.print(table)

    # Summary
    passed = sum(1 for _, _, success, _ in results if success)
    total = len(results)

    console.print()
    if passed == total:
        console.print(f"[bold green]All {total} API tests passed![/bold green]")
        return 0
    else:
        console.print(f"[bold yellow]{passed}/{total} API tests passed[/bold yellow]")
        console.print("\n[dim]Missing API keys? Add them to your .env file.[/dim]")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
