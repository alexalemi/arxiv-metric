#!/bin/bash
# Run AFIM benchmark across all major providers and models
#
# Usage:
#   ./scripts/run_all_models.sh              # Full benchmark, single-turn
#   ./scripts/run_all_models.sh --multiturn  # Full benchmark, multi-turn
#   ./scripts/run_all_models.sh --pilot      # Quick pilot mode
#   ./scripts/run_all_models.sh --multiturn --pilot  # Quick multi-turn pilot

set -e

# Default settings
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${PROJECT_DIR}/data/results"

# Parse arguments (pass through to run_benchmark.py)
EXTRA_ARGS="$@"

echo "=============================================="
echo "AFIM Benchmark - All Models"
echo "=============================================="
echo "Output directory: ${OUTPUT_DIR}"
echo "Extra arguments: ${EXTRA_ARGS:-none}"
echo ""

# Models to test
# Format: "provider:model"
MODELS=(
    # OpenAI models
    "openai:gpt-5.1"
    "openai:gpt-4o"
    "openai:gpt-4o-mini"

    # Anthropic models
    "anthropic:claude-opus-4-5"
    "anthropic:claude-sonnet-4-5"
    "anthropic:claude-haiku-4-5"

    # Google models
    "google:gemini-3-pro-preview"
    "google:gemini-3-flash-preview"
    "google:gemini-2.5-flash"

    # xAI Grok models
    "xai:grok-4"
    "xai:grok-4-fast-reasoning"
    "xai:grok-3"
)

# Track results
PASSED=0
FAILED=0
FAILED_MODELS=()

for entry in "${MODELS[@]}"; do
    provider="${entry%%:*}"
    model="${entry##*:}"

    echo ""
    echo "----------------------------------------------"
    echo "Testing: ${model} (${provider})"
    echo "----------------------------------------------"

    if uv run python scripts/run_benchmark.py \
        --provider "$provider" \
        --model "$model" \
        --output-dir "$OUTPUT_DIR" \
        $EXTRA_ARGS; then
        echo "[PASS] ${model}"
        ((++PASSED))
    else
        echo "[FAIL] ${model}"
        ((++FAILED))
        FAILED_MODELS+=("${provider}:${model}")
    fi
done

echo ""
echo "=============================================="
echo "Summary"
echo "=============================================="
echo "Passed: ${PASSED}"
echo "Failed: ${FAILED}"

if [ ${FAILED} -gt 0 ]; then
    echo ""
    echo "Failed models:"
    for model in "${FAILED_MODELS[@]}"; do
        echo "  - ${model}"
    done
    exit 1
fi

echo ""
echo "All models completed successfully!"
echo "Results saved to: ${OUTPUT_DIR}"
