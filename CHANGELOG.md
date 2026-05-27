# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.5.0] — 2026-05-27

### Added
- Activity heatmap: hour × day-of-week grid (GitHub-style, reactive to filters)
- `message_count` field extracted per session
- Sessions table: relative timestamps ("hace 2h"), `stop_reason` column, "Ver todas" button with scrollable container
- Tips and Claude prompt fully reactive to filters — computed in JS (`computeTips`, `buildClaudePrompt`)
- Doughnut legends show count: "cli (45)", "end_turn (120)"
- Date range label in filter bar showing active period
- Expandable prompt preview before copying
- Mobile: `.grid-3` responds at 900px/600px, tables scroll horizontally, claude-card stacks vertically

### Changed
- AppData sessions (Claude Code internal Haiku ops) grouped as project `"temp"` instead of being discarded
- `html_builder.py` simplified — no longer embeds static tips or prompt; `generate.py` no longer calls `compute_tips`
- `tips.py` retained as canonical Python spec (tested); JS port is the live implementation

### Fixed
- AppData filter used full path instead of project dir name — broke all pytest sessions under `AppData/Local/Temp`

## [0.4.0] — 2026-05-26

### Added
- Session metadata: `entrypoint`, `permission_mode`, `stop_reason`, `tools` fields in `log_parser.py`
- New charts: entrypoint / permission mode / stop reason doughnuts + top-10 tools horizontal bar
- New tip: warns when >5% of sessions hit the context limit (`max_tokens` stop reason)
- 9 new unit tests covering the new session fields and max_tokens tip (24 total)

## [0.3.0] — 2026-05-26

### Added
- Dark / light theme toggle (persists via localStorage)
- Spanish / English language toggle — all UI labels, tips, and Claude prompt
- GitHub Actions CI: `ruff check .` + `python -m pytest -v` on every push/PR to `develop` and `master`
- Branch protection on `master`: CI must pass before merging
- Bilingual tips structure: `{title_es, body_es, title_en, body_en}`
- `build_claude_prompt(sessions, tips, lang)` generates language-specific prompt

## [0.2.0] — 2026-05-25

### Added
- Date range filter buttons (7 d, 30 d, 90 d, all)
- Model filter checkboxes (Sonnet, Opus, Haiku)
- Cache tokens chart (stacked bar: cache read vs. cache create)
- Cost per project table
- Sessions table (date, project, model, duration, cost)
- Unit tests: `test_log_parser.py` (10 tests), `test_tips.py` (7 tests)
- `pyproject.toml` with ruff config and pytest settings

### Changed
- Modularized codebase: `generate.py`, `log_parser.py`, `tips.py`, `html_builder.py`

### Removed
- `charts.py` — dead code; all data aggregation moved to JS for dynamic filtering

## [0.1.0] — 2026-05-25

### Added
- Initial dashboard: tokens/cost per day (bar + line), top projects (doughnut),
  model distribution (doughnut), session duration histogram
- Rule-based usage tips: cache rate, Opus %, short/long sessions,
  cost concentration, output/input ratio, median session duration
- "Copy prompt for Claude" button with pre-formatted metrics
