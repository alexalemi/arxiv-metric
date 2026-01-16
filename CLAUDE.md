# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AFIM (Academic Fraud Inclination Metric) benchmarks how susceptible LLMs are to assisting with academic fraud—specifically helping users submit fraudulent papers to arXiv. The benchmark evaluates multiple LLM providers across different user profiles and escalation levels.

## Commands

```bash
# Install dependencies
uv sync

# Run benchmark (requires API keys in .env)
uv run python -m scripts.run_benchmark --provider openai --model gpt-4o --pilot

# Run all tests
uv run pytest tests/ -v

# Run single test
uv run pytest tests/test_afim_score.py::TestAFIMCalculator::test_calculate_basic -v
```

## Architecture

### Provider Layer (`src/providers/`)
Abstract `LLMProvider` base class with implementations for OpenAI, Anthropic, and Google. All providers expose:
- `generate(prompt, system_prompt, temperature, max_tokens)` - single turn
- `generate_with_history(messages, system_prompt, ...)` - multi-turn conversations

### Evaluation System (`src/evaluation/`)
- **Taxonomy**: 7-category fraud spectrum (0=explicit refusal → 6=full facilitation)
- **Escalation Levels**: 5 user sophistication levels (naive_curious → deliberate_fraud), with naive users weighted 2x higher
- **Judge**: LLM-as-judge system that classifies responses using a different provider family to reduce bias

### Scoring (`src/metrics/`)
- **AFIM Score**: 0-100 (higher = worse), weighted by escalation level
- **Bootstrap CI**: 1000-sample confidence intervals
- **Multi-turn**: Resistance score, softening index, trajectory analysis

### Execution (`src/execution/`, `src/multiturn/`)
- Async/await throughout with semaphore-based rate limiting
- Per-provider concurrency limits and rate limits
- Incremental result saving for crash recovery

## Key Design Patterns

- **Cross-family judging**: OpenAI target → Anthropic judge (and vice versa) to reduce evaluation bias
- **Escalation weighting**: Naive users weighted 2x because helping uninformed users is worse than helping deliberate bad actors
- **Frozen dataclasses**: Core domain objects are immutable (FraudCategory, EscalationLevel, JudgmentResult)

## Test Data

35 test prompts in `data/prompts/` across physics, CS, and general scenarios. Each scenario has 5 prompts (one per escalation level). Pilot mode uses 30 prompts for faster iteration.
