#!/usr/bin/env python3
"""Generate a static results site from benchmark data.

Creates:
- index.html with results selector
- manifest.json listing all available results

Usage:
    python scripts/generate_site.py [--output-dir data/results]
"""

import argparse
import json
from pathlib import Path
from datetime import datetime


def find_result_files(results_dir: Path) -> list[dict]:
    """Find all *_final.json files and extract metadata."""
    results = []

    for path in sorted(results_dir.glob("*_final.json"), reverse=True):
        try:
            with open(path) as f:
                data = json.load(f)

            is_multiturn = data.get("mode") == "multiturn" or "trajectories" in data

            results.append({
                "filename": path.name,
                "run_id": data.get("run_id", path.stem.replace("_final", "")),
                "target_model": data.get("target_model", "Unknown"),
                "target_provider": data.get("target_provider", "unknown"),
                "judge_model": data.get("judge_model", "Unknown"),
                "afim_score": data.get("afim_score", 0),
                "resistance_score": data.get("resistance_score"),
                "softening_rate": data.get("softening_rate"),
                "num_tests": data.get("num_tests", 0),
                "mode": "multiturn" if is_multiturn else "single",
                "timestamp": data.get("timestamp"),
            })
        except Exception as e:
            print(f"Warning: Could not parse {path}: {e}")

    return results


def generate_manifest(results: list[dict], output_path: Path) -> None:
    """Generate manifest.json listing all results."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated: {output_path}")


def generate_index_html(output_path: Path) -> None:
    """Generate index.html with embedded viewer and results selector."""

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFIM Benchmark Results</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #475569;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }

        h1 { font-size: 1.75rem; font-weight: 600; margin-bottom: 0.5rem; }
        h2 { font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; color: var(--text-secondary); }

        .subtitle { color: var(--text-muted); margin-bottom: 1.5rem; }

        /* Results Selector */
        .selector-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .selector-row {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }

        .selector-group {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .selector-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .selector-select {
            padding: 0.625rem 1rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 0.875rem;
            min-width: 200px;
        }

        .selector-select:focus {
            outline: none;
            border-color: var(--accent-blue);
        }

        /* Results Grid */
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .result-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.25rem;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 2px solid transparent;
        }

        .result-card:hover {
            border-color: var(--accent-blue);
            transform: translateY(-2px);
        }

        .result-card.selected {
            border-color: var(--accent-purple);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.75rem;
        }

        .result-model {
            font-weight: 600;
            font-size: 1rem;
        }

        .result-score {
            font-size: 1.5rem;
            font-weight: 700;
        }

        .result-meta {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 0.5rem;
        }

        .badge {
            display: inline-block;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-size: 0.6875rem;
            font-weight: 500;
            text-transform: uppercase;
        }

        .badge-single { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .badge-multiturn { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
        .badge-openai { background: rgba(16, 163, 127, 0.2); color: #10a37f; }
        .badge-anthropic { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
        .badge-google { background: rgba(234, 179, 8, 0.2); color: #eab308; }
        .badge-xai { background: rgba(239, 68, 68, 0.2); color: #f87171; }

        .result-date {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Viewer iframe */
        .viewer-container {
            background: var(--bg-secondary);
            border-radius: 12px;
            overflow: hidden;
            display: none;
        }

        .viewer-container.visible {
            display: block;
        }

        .viewer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .viewer-title {
            font-weight: 600;
        }

        .viewer-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.25rem;
            line-height: 1;
        }

        .viewer-close:hover {
            color: var(--text-primary);
        }

        #viewerFrame {
            width: 100%;
            height: 80vh;
            border: none;
            background: var(--bg-primary);
        }

        /* Loading state */
        .loading {
            text-align: center;
            padding: 3rem;
            color: var(--text-muted);
        }

        .no-results {
            text-align: center;
            padding: 3rem;
            color: var(--text-muted);
        }

        /* Score colors */
        .score-excellent { color: #22c55e; }
        .score-good { color: #84cc16; }
        .score-moderate { color: #eab308; }
        .score-concerning { color: #f97316; }
        .score-poor { color: #ef4444; }

        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }

        /* Navigation Bar */
        .site-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .nav-brand {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .nav-tabs {
            display: flex;
            gap: 0.25rem;
        }

        .nav-tab {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .nav-tab:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .nav-tab.active {
            background: var(--accent-blue);
            color: white;
        }

        @media (max-width: 640px) {
            .site-nav {
                flex-direction: column;
                gap: 0.75rem;
                padding: 1rem;
            }

            .nav-tabs {
                flex-wrap: wrap;
                justify-content: center;
            }

            .nav-tab {
                padding: 0.375rem 0.75rem;
                font-size: 0.8125rem;
            }
        }
    </style>
</head>
<body>
    <nav class="site-nav">
        <div class="nav-brand">AFIM Benchmark</div>
        <div class="nav-tabs">
            <a href="index.html" class="nav-tab active">Results</a>
            <a href="docs.html?page=summary" class="nav-tab">Summary</a>
            <a href="docs.html?page=scoring" class="nav-tab">Scoring</a>
            <a href="docs.html?page=prompts" class="nav-tab">Prompts</a>
            <a href="docs.html?page=readme" class="nav-tab">About</a>
        </div>
    </nav>

    <div class="container">
        <h1>AFIM Benchmark Results</h1>
        <p class="subtitle">Academic Fraud Inclination Metric - Model Evaluation Results</p>

        <!-- Filters -->
        <div class="selector-card">
            <div class="selector-row">
                <div class="selector-group">
                    <span class="selector-label">Provider</span>
                    <select id="providerFilter" class="selector-select">
                        <option value="">All Providers</option>
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="google">Google</option>
                        <option value="xai">xAI (Grok)</option>
                    </select>
                </div>
                <div class="selector-group">
                    <span class="selector-label">Mode</span>
                    <select id="modeFilter" class="selector-select">
                        <option value="">All Modes</option>
                        <option value="single">Single-Turn</option>
                        <option value="multiturn">Multi-Turn</option>
                    </select>
                </div>
                <div class="selector-group">
                    <span class="selector-label">Sort By</span>
                    <select id="sortBy" class="selector-select">
                        <option value="date">Date (Newest)</option>
                        <option value="score_asc">Score (Best First)</option>
                        <option value="score_desc">Score (Worst First)</option>
                        <option value="model">Model Name</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Results Grid -->
        <div id="resultsGrid" class="results-grid">
            <div class="loading">Loading results...</div>
        </div>

        <!-- Viewer -->
        <div id="viewerContainer" class="viewer-container">
            <div class="viewer-header">
                <span id="viewerTitle" class="viewer-title">Result Details</span>
                <button class="viewer-close" onclick="closeViewer()">&times;</button>
            </div>
            <iframe id="viewerFrame" src="about:blank"></iframe>
        </div>

        <div class="footer">
            Generated by AFIM Benchmark
        </div>
    </div>

    <script>
        let manifest = null;
        let currentResult = null;

        // Load manifest on page load
        async function loadManifest() {
            try {
                const response = await fetch('manifest.json');
                manifest = await response.json();
                renderResults();
            } catch (e) {
                document.getElementById('resultsGrid').innerHTML =
                    '<div class="no-results">No results found. Run the benchmark first.</div>';
            }
        }

        function getScoreClass(score) {
            if (score <= 10) return 'score-excellent';
            if (score <= 25) return 'score-good';
            if (score <= 40) return 'score-moderate';
            if (score <= 60) return 'score-concerning';
            return 'score-poor';
        }

        function getProviderClass(provider) {
            if (!provider) return '';
            const p = provider.toLowerCase();
            if (p.includes('openai')) return 'badge-openai';
            if (p.includes('anthropic')) return 'badge-anthropic';
            if (p.includes('google')) return 'badge-google';
            if (p.includes('xai') || p.includes('grok')) return 'badge-xai';
            return '';
        }

        function formatDate(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }

        function filterAndSort() {
            if (!manifest) return [];

            const providerFilter = document.getElementById('providerFilter').value;
            const modeFilter = document.getElementById('modeFilter').value;
            const sortBy = document.getElementById('sortBy').value;

            let results = [...manifest.results];

            // Filter
            if (providerFilter) {
                results = results.filter(r => r.target_provider.toLowerCase().includes(providerFilter));
            }
            if (modeFilter) {
                results = results.filter(r => r.mode === modeFilter);
            }

            // Sort
            switch (sortBy) {
                case 'date':
                    results.sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));
                    break;
                case 'score_asc':
                    results.sort((a, b) => (a.afim_score || 0) - (b.afim_score || 0));
                    break;
                case 'score_desc':
                    results.sort((a, b) => (b.afim_score || 0) - (a.afim_score || 0));
                    break;
                case 'model':
                    results.sort((a, b) => (a.target_model || '').localeCompare(b.target_model || ''));
                    break;
            }

            return results;
        }

        function renderResults() {
            const results = filterAndSort();
            const grid = document.getElementById('resultsGrid');

            if (results.length === 0) {
                grid.innerHTML = '<div class="no-results">No results match your filters.</div>';
                return;
            }

            grid.innerHTML = results.map(r => `
                <div class="result-card" onclick="openResult('${r.filename}')" data-filename="${r.filename}">
                    <div class="result-header">
                        <div>
                            <div class="result-model">${escapeHtml(r.target_model)}</div>
                            <div class="result-meta">
                                <span class="badge ${getProviderClass(r.target_provider)}">${escapeHtml(r.target_provider)}</span>
                                <span class="badge badge-${r.mode}">${r.mode === 'multiturn' ? 'Multi-Turn' : 'Single-Turn'}</span>
                            </div>
                        </div>
                        <div class="result-score ${getScoreClass(r.afim_score)}">${r.afim_score.toFixed(1)}</div>
                    </div>
                    ${r.mode === 'multiturn' && r.resistance_score !== undefined ? `
                        <div style="font-size: 0.75rem; color: var(--text-muted);">
                            Resistance: ${r.resistance_score.toFixed(1)} | Softening: ${((r.softening_rate || 0) * 100).toFixed(0)}%
                        </div>
                    ` : ''}
                    <div class="result-date">${formatDate(r.timestamp)} &bull; ${r.num_tests} tests</div>
                </div>
            `).join('');
        }

        function openResult(filename) {
            currentResult = filename;

            // Update selection state
            document.querySelectorAll('.result-card').forEach(card => {
                card.classList.toggle('selected', card.dataset.filename === filename);
            });

            // Load in iframe with viewer
            const frame = document.getElementById('viewerFrame');
            frame.src = 'view_results.html?file=' + encodeURIComponent(filename);

            document.getElementById('viewerTitle').textContent = filename.replace('_final.json', '');
            document.getElementById('viewerContainer').classList.add('visible');

            // Scroll to viewer
            document.getElementById('viewerContainer').scrollIntoView({ behavior: 'smooth' });
        }

        function closeViewer() {
            document.getElementById('viewerContainer').classList.remove('visible');
            document.querySelectorAll('.result-card').forEach(card => {
                card.classList.remove('selected');
            });
            currentResult = null;
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Event listeners
        document.getElementById('providerFilter').addEventListener('change', renderResults);
        document.getElementById('modeFilter').addEventListener('change', renderResults);
        document.getElementById('sortBy').addEventListener('change', renderResults);

        // Initialize
        loadManifest();
    </script>
</body>
</html>
'''

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Generated: {output_path}")


def generate_docs_html(output_path: Path) -> None:
    """Generate docs.html for viewing markdown documentation."""

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AFIM Documentation</title>
    <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #475569;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }

        /* Navigation Bar */
        .site-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .nav-brand {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .nav-tabs {
            display: flex;
            gap: 0.25rem;
        }

        .nav-tab {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .nav-tab:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .nav-tab.active {
            background: var(--accent-blue);
            color: white;
        }

        @media (max-width: 640px) {
            .site-nav {
                flex-direction: column;
                gap: 0.75rem;
                padding: 1rem;
            }

            .nav-tabs {
                flex-wrap: wrap;
                justify-content: center;
            }

            .nav-tab {
                padding: 0.375rem 0.75rem;
                font-size: 0.8125rem;
            }
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }

        .loading {
            text-align: center;
            padding: 3rem;
            color: var(--text-muted);
        }

        .error {
            text-align: center;
            padding: 3rem;
            color: #ef4444;
        }

        /* Markdown content styling */
        .doc-content {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 2rem;
        }

        .doc-content h1 {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.75rem;
        }

        .doc-content h2 {
            font-size: 1.5rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
            color: var(--text-primary);
        }

        .doc-content h3 {
            font-size: 1.25rem;
            font-weight: 600;
            margin: 1.5rem 0 0.75rem 0;
            color: var(--text-primary);
        }

        .doc-content h4, .doc-content h5, .doc-content h6 {
            font-size: 1rem;
            font-weight: 600;
            margin: 1.25rem 0 0.5rem 0;
            color: var(--text-secondary);
        }

        .doc-content p {
            margin: 0.75rem 0;
            color: var(--text-primary);
        }

        .doc-content ul, .doc-content ol {
            margin: 0.75rem 0;
            padding-left: 1.5rem;
        }

        .doc-content li {
            margin: 0.375rem 0;
        }

        .doc-content code {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
            font-size: 0.875rem;
        }

        .doc-content pre {
            background: var(--bg-primary);
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1rem 0;
            border: 1px solid var(--border-color);
        }

        .doc-content pre code {
            background: none;
            padding: 0;
            font-size: 0.8125rem;
            line-height: 1.6;
        }

        .doc-content blockquote {
            border-left: 4px solid var(--accent-blue);
            padding-left: 1rem;
            margin: 1rem 0;
            color: var(--text-secondary);
            font-style: italic;
        }

        .doc-content a {
            color: var(--accent-blue);
            text-decoration: none;
        }

        .doc-content a:hover {
            text-decoration: underline;
        }

        .doc-content table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }

        .doc-content th, .doc-content td {
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }

        .doc-content th {
            background: var(--bg-tertiary);
            font-weight: 600;
        }

        .doc-content tr:nth-child(even) {
            background: rgba(255, 255, 255, 0.02);
        }

        .doc-content img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 1rem 0;
        }

        .doc-content hr {
            border: none;
            border-top: 1px solid var(--border-color);
            margin: 2rem 0;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }
    </style>
</head>
<body>
    <nav class="site-nav">
        <div class="nav-brand">AFIM Benchmark</div>
        <div class="nav-tabs">
            <a href="index.html" class="nav-tab">Results</a>
            <a href="docs.html?page=summary" class="nav-tab" data-page="summary">Summary</a>
            <a href="docs.html?page=scoring" class="nav-tab" data-page="scoring">Scoring</a>
            <a href="docs.html?page=prompts" class="nav-tab" data-page="prompts">Prompts</a>
            <a href="docs.html?page=readme" class="nav-tab" data-page="readme">About</a>
        </div>
    </nav>

    <div class="container">
        <div id="docContent" class="doc-content">
            <div class="loading">Loading documentation...</div>
        </div>
    </div>

    <script>
        // Page to file mapping
        const pageFiles = {
            'summary': 'SUMMARY.md',
            'scoring': 'SCORING.md',
            'prompts': 'PROMPTS.md',
            'readme': 'README.md'
        };

        const pageTitles = {
            'summary': 'Summary',
            'scoring': 'Scoring Methodology',
            'prompts': 'Prompts',
            'readme': 'About AFIM'
        };

        // Configure marked
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });

        // Get page from URL
        function getPageParam() {
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get('page') || 'summary';
        }

        // Update active nav tab
        function updateActiveTab(page) {
            document.querySelectorAll('.nav-tab[data-page]').forEach(tab => {
                tab.classList.toggle('active', tab.dataset.page === page);
            });
        }

        // Load markdown file
        async function loadMarkdown(page) {
            const file = pageFiles[page];
            if (!file) {
                document.getElementById('docContent').innerHTML =
                    '<div class="error">Page not found</div>';
                return;
            }

            updateActiveTab(page);
            document.title = `${pageTitles[page]} - AFIM Documentation`;

            try {
                const response = await fetch(file);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const markdown = await response.text();
                document.getElementById('docContent').innerHTML = marked.parse(markdown);
            } catch (e) {
                document.getElementById('docContent').innerHTML =
                    `<div class="error">Failed to load ${file}: ${e.message}</div>`;
            }
        }

        // Handle navigation without page reload
        document.querySelectorAll('.nav-tab[data-page]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const page = tab.dataset.page;
                history.pushState({page}, '', `docs.html?page=${page}`);
                loadMarkdown(page);
            });
        });

        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            loadMarkdown(e.state?.page || getPageParam());
        });

        // Initial load
        loadMarkdown(getPageParam());
    </script>
</body>
</html>
'''

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Generated: {output_path}")


def copy_markdown_files(source_dir: Path, output_dir: Path) -> None:
    """Copy markdown documentation files to output directory."""
    import shutil

    md_files = ['SUMMARY.md', 'SCORING.md', 'PROMPTS.md', 'README.md']

    for filename in md_files:
        src = source_dir / filename
        dst = output_dir / filename
        if src.exists():
            shutil.copy(src, dst)
            print(f"Copied: {dst}")
        else:
            print(f"Warning: {src} not found")


def main():
    parser = argparse.ArgumentParser(description="Generate static results site")
    parser.add_argument(
        "--output-dir", "-o",
        default="data/results",
        help="Directory containing results (default: data/results)"
    )
    args = parser.parse_args()

    results_dir = Path(args.output_dir)
    if not results_dir.exists():
        print(f"Error: Directory not found: {results_dir}")
        return 1

    # Find all results
    print(f"Scanning {results_dir} for results...")
    results = find_result_files(results_dir)
    print(f"Found {len(results)} result files")

    if not results:
        print("No results found. Run the benchmark first.")
        return 1

    # Generate manifest
    manifest_path = results_dir / "manifest.json"
    generate_manifest(results, manifest_path)

    # Generate index
    index_path = results_dir / "index.html"
    generate_index_html(index_path)

    # Generate docs page
    docs_path = results_dir / "docs.html"
    generate_docs_html(docs_path)

    # Copy viewer to results dir
    viewer_src = Path(__file__).parent / "view_results.html"
    viewer_dst = results_dir / "view_results.html"

    if viewer_src.exists():
        import shutil
        shutil.copy(viewer_src, viewer_dst)
        print(f"Copied: {viewer_dst}")
    else:
        print(f"Warning: {viewer_src} not found")

    # Copy markdown documentation files
    project_root = Path(__file__).parent.parent
    copy_markdown_files(project_root, results_dir)

    print(f"\nStatic site generated in: {results_dir}")
    print(f"Serve with: python -m http.server -d {results_dir}")
    print(f"Or copy to your public_html directory")

    return 0


if __name__ == "__main__":
    exit(main())
