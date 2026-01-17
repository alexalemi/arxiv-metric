#!/bin/bash
# Deploy AFIM results to GitHub Pages
#
# Usage: ./scripts/deploy_pages.sh
#
# This script:
# 1. Generates the static site from data/results
# 2. Pushes it to the gh-pages branch
# 3. GitHub Pages serves from that branch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="${PROJECT_DIR}/data/results"

echo "======================================"
echo "AFIM Results - Deploy to GitHub Pages"
echo "======================================"

# Check for result files
if ! ls "${RESULTS_DIR}"/*_final.json 1> /dev/null 2>&1; then
    echo "Error: No result files found in ${RESULTS_DIR}"
    echo "Run benchmarks first with: uv run python scripts/run_benchmark.py"
    exit 1
fi

# Generate the static site
echo ""
echo "Generating static site..."
uv run python "${SCRIPT_DIR}/generate_site.py" --output-dir "${RESULTS_DIR}"

# Create a temp directory for deployment
DEPLOY_DIR=$(mktemp -d)
trap "rm -rf ${DEPLOY_DIR}" EXIT

# Copy site files
echo ""
echo "Preparing deployment..."
cp "${RESULTS_DIR}/index.html" "${DEPLOY_DIR}/"
cp "${RESULTS_DIR}/view_results.html" "${DEPLOY_DIR}/"
cp "${RESULTS_DIR}/manifest.json" "${DEPLOY_DIR}/"

# Copy all result JSON files
cp "${RESULTS_DIR}"/*_final.json "${DEPLOY_DIR}/"

# Add a .nojekyll file to prevent Jekyll processing
touch "${DEPLOY_DIR}/.nojekyll"

# Initialize git in deploy dir and push to gh-pages
cd "${DEPLOY_DIR}"
git init -q
git checkout -q -b gh-pages
git add -A
git commit -q -m "Deploy AFIM results $(date +%Y-%m-%d_%H:%M:%S)"

# Get the remote URL from the main repo
REMOTE_URL=$(git -C "${PROJECT_DIR}" remote get-url origin)

echo ""
echo "Pushing to gh-pages branch..."
git push -f "${REMOTE_URL}" gh-pages

echo ""
echo "======================================"
echo "Deployment complete!"
echo "======================================"
echo ""
echo "Your site will be available at:"
echo "  https://alexalemi.github.io/arxiv-metric/"
echo ""
echo "Note: It may take a few minutes for GitHub to build the site."
echo "You may need to enable GitHub Pages in repo settings:"
echo "  Settings > Pages > Source: Deploy from branch > gh-pages"
