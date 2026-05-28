# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.7.0] — 2026-05-28

### Added
- `cCatProj`: stacked horizontal bar showing session category mix per project (coding / exploration / automation / research / conversation / mixed), top 8 projects by session count, i18n labels
- Skills & Agents table: sortable columns (all 5 headers — skill/agent, project, calls, sessions, last used)
- Playwright end-to-end tests (`tests/test_e2e.py`): JS error detection on load, filter buttons, model checkboxes, all sortable tables, language and theme toggles; CI split into `unit` + `e2e` jobs

### Changed
- `cDur`: replaced single aggregate bar with stacked bar by model (sonnet/opus/haiku/mixed per duration bucket) — all models now visible
- `cEntrypoint`, `cPerm`, `cStopReason`, `cCategory`: converted back to doughnut with bottom legend
- Usage tips: replaced colored backgrounds with `var(--surface)` + 3px colored left border (orange warn / blue info / green ok), consistent with stat card style; full border transitions to level color on hover

### Fixed
- Skills table "Last used" column stayed in previous language after ES/EN toggle — `renderSkillsBody()` now called from `setLang`
- `barOpts` undefined crashed `charts.tools` and `charts.catproj` init after radar refactor

## [0.6.0] — 2026-05-28

### Added
- `skill/*` and `agent/*` tool tracking: Skill/Agent tool calls expand to `skill/<name>` / `agent/<subagent_type>` in session tools dict
- Session categorization: 6 types (coding / exploration / automation / research / conversation / mixed) based on tool usage ratios; dedicated `cCategory` chart
- Skills & Agents table per project: calls, projects, unique sessions, last used columns
- Cost by project table: sessions, tokens, cost, % total, primary model (sortable)
- `aggrDurStacked`, `aggrCatByProject`, `aggrModelProfile`, `aggrCacheTrend` aggregation helpers
- `_setBar`, `_setPolar` update helpers for reliable Chart.js reactivity (splice in-place + `update('none')`)
- Visual polish: blinking cursor on h1, `>` prefix on section titles, radial gradient background, threshold-based KPI border colors, orchestrated load animations

### Changed
- 6 doughnut charts replaced with horizontal bar charts (`indexAxis:'y'`) with `maintainAspectRatio:false` + `.ch-wrap` wrapper for correct sizing
- Streaming deduplication: keep LAST chunk per message ID (not first) — first chunk lacks complete tool_use blocks and token counts

### Fixed
- 7 bugs from post-release code review: `initCharts` proj tooltip crash (stale object API), `sortTbl('tProj')` crash (`tblData` not populated), `categorizeSession` over-classifying sessions with `skill/*`/`agent/*` tools as mixed, `_setBar` stripping colors on empty filter, mixed model tag showing wrong CSS class, `updateChartLabels` diverging from `_setBar`, `charts.dur` inconsistent update path
- 29 unit tests (+ 2 new for skill/agent tool name expansion)

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
