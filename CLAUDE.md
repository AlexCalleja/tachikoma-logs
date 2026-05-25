# tachikoma-logs

Dashboard de uso de Claude Code. Genera un HTML estático a partir de los logs JSONL de `~/.claude/projects/`.

## Stack

- Python 3.9+ stdlib only (sin dependencias externas)
- Chart.js 4.4.0 via CDN (cargado en el browser al abrir el HTML)
- Output: un único archivo `docs/usage.html` autocontenido
- Sin servidor, sin base de datos, sin build step

## Cómo generar el dashboard

```bash
python generate.py
# output: docs/usage.html (gitignoreado)
```

## Estructura de módulos

```
tachikoma-logs/
├── generate.py      ← entrypoint: argparse + orquestación
├── log_parser.py    ← PRICING, get_tier(), calc_cost(), parse_sessions()
├── charts.py        ← DUR_EDGES, DUR_LABELS, build_chart_data()
├── tips.py          ← compute_tips()
└── html_builder.py  ← build_claude_prompt(), generate_html()
```

Flujo de datos: `parse_sessions()` → `compute_tips()` + `build_chart_data()` → `build_claude_prompt()` → `generate_html()`

## Fuente de datos

- Archivos: `~/.claude/projects/**/*.jsonl` (glob recursivo)
- Se omiten paths que contengan `subagents` en algún componente
- Deduplicación por `message.id` dentro de cada sesión — obligatoria (sin ella los tokens se inflan 2-3x por streaming)
- Solo se procesan entradas con `type == "assistant"` y `message.usage` con tokens > 0

## Precios

Hardcodeados en `parser.py` (dict `PRICES`). Actualizar al inicio de cada versión si Anthropic cambia los precios. Última actualización: 2026-05 (Opus $15/$75, Sonnet $3/$15, Haiku $0.80/$4 por 1M tokens).

## Linter

```bash
ruff check .
ruff format .
```

Configurado en `pyproject.toml`. Correr antes de cada commit.
