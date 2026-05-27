# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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
