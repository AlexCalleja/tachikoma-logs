# tachikoma-logs

[![CI](https://github.com/AlexCalleja/tachikoma-logs/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexCalleja/tachikoma-logs/actions/workflows/ci.yml)

Local usage analytics dashboard for Claude Code. Reads `~/.claude/projects/**/*.jsonl` and generates a self-contained HTML dashboard — no server required.

## Setup

```bash
python generate.py
# outputs docs/usage.html
```

Open `docs/usage.html` in your browser.

## Features

- Tokens and cost per day (bar + line overlay)
- Top projects by token consumption (doughnut)
- Model distribution per session: Sonnet / Opus / Haiku / Mixed (doughnut)
- Session duration histogram
- Rule-based usage tips (cache rate, Opus %, short/long sessions, cost concentration)
- "Copy prompt for Claude" button — pre-formatted metrics ready to paste for deeper AI analysis
- Dark / light theme toggle (persists via localStorage)
- Spanish / English language toggle — all labels, tips, and Claude prompt

## Options

```bash
python generate.py --output path/to/output.html
```

## Requirements

- Python 3.9+
- No external dependencies (stdlib only + Chart.js via CDN)

## License

MIT — see [LICENSE](LICENSE).

## Notes

- Pricing is approximate and based on Anthropic's documented rates.
- Subagent sessions (`/subagents/` path) are excluded — they are counted as part of the parent session.
- Duplicate JSONL entries (streaming artefact) are deduplicated by `message.id`.
