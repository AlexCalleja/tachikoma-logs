# tachikoma-logs

[![CI](https://github.com/AlexCalleja/tachikoma-logs/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexCalleja/tachikoma-logs/actions/workflows/ci.yml)

Local usage analytics dashboard for Claude Code. Reads `~/.claude/projects/**/*.jsonl` and generates a self-contained HTML dashboard — no server required.

## Demo

**[→ Live demo](https://alexcalleja.github.io/tachikoma-logs/demo.html)** — synthetic data, no real sessions.

To generate the demo locally:

```bash
python generate_demo.py
# outputs docs/demo.html
```

## Setup

```bash
python generate.py
# outputs docs/usage.html
```

Open `docs/usage.html` in your browser.

## Features

**Charts**
- Tokens and cost per day — stacked bar (input / output / cache read / cache create) + cost line
- Top 10 projects by token consumption — horizontal bar
- Session distribution by model — horizontal bar (Sonnet / Opus / Haiku / Mixed)
- Session duration distribution — stacked bar by model
- Session type by project — stacked horizontal bar (coding / exploration / automation / research / conversation / mixed)
- Entrypoint, permission mode, stop reason, session category — doughnut charts
- Top 10 tools by total calls
- Activity heatmap — hour × day-of-week grid

**Tables**
- Cost and usage by project (sortable)
- Token and cost breakdown by model (sortable)
- Skills & Agents by project — calls, unique sessions, last used (sortable)
- Recent sessions with individual metrics (sortable)

**UI**
- Dark / light theme toggle (persists via localStorage)
- Spanish / English language toggle — all labels, tips, and Claude prompt
- Collapsible info panel on every chart and KPI (`ℹ` per element, `?` to expand all)
- Date range filter (7d / 30d / 90d / all) and model checkboxes — all charts reactive
- Rule-based usage tips with contextual alerts
- "Copy prompt for Claude" — pre-formatted metrics ready for deeper AI analysis

## Options

```bash
python generate.py --output path/to/output.html
python generate_demo.py --output path/to/demo.html --sessions 90
```

## Requirements

- Python 3.9+ (stdlib only — no pip install required)
- Chart.js 4.4 via CDN (loaded in browser when you open the HTML)

## Dev setup

```bash
pip install pytest pytest-cov ruff pytest-playwright
playwright install chromium

ruff check .
python -m pytest tests/test_log_parser.py tests/test_tips.py -v
python generate.py && python -m pytest tests/test_e2e.py -v
```

## Notes

- Pricing is approximate based on Anthropic's documented rates (updated 2026-05).
- Subagent sessions (`/subagents/` path) are excluded — counted as part of the parent session.
- Duplicate JSONL entries (streaming artefact) are deduplicated by `message.id`, keeping the last chunk.
- Sessions under `AppData` paths are grouped as project `temp` (Claude Code internal Haiku ops).

## License

MIT — see [LICENSE](LICENSE).
