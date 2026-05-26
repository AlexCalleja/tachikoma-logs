# tachikoma-logs

Dashboard de uso de Claude Code. Genera un HTML estático a partir de los logs JSONL de `~/.claude/projects/`.

## Stack

- Python 3.9+ stdlib only (sin dependencias externas)
- Chart.js 4.4.0 via CDN (cargado en el browser al abrir el HTML)
- Output: un único archivo `docs/usage.html` autocontenido
- Sin servidor, sin base de datos, sin build step

## Cómo generar el dashboard

```bash
python generate.py                        # output: docs/usage.html (gitignoreado)
python generate.py --output path/out.html # ruta personalizada
```

## Estructura de módulos

```
tachikoma-logs/
├── generate.py      ← entrypoint: argparse + orquestación
├── log_parser.py    ← PRICING, get_tier(), calc_cost(), parse_sessions()
├── tips.py          ← compute_tips() → tips bilingües {level, title_es, body_es, title_en, body_en}
├── html_builder.py  ← build_claude_prompt(sessions, tips, lang), generate_html()
└── tests/
    ├── test_log_parser.py
    └── test_tips.py
```

Flujo de datos: `parse_sessions()` → `compute_tips()` → `build_claude_prompt()` → `generate_html()`

La estructura es plana por diseño (YAGNI) — mover los módulos a un paquete `tachikoma/` tiene sentido cuando haya suficientes módulos que lo justifiquen.

## Fuente de datos

- Archivos: `~/.claude/projects/**/*.jsonl` (glob recursivo)
- Se omiten paths que contengan `subagents` en algún componente
- Deduplicación por `message.id` dentro de cada sesión — obligatoria (sin ella los tokens se inflan 2-3x por streaming)
- Solo se procesan entradas con `type == "assistant"` y `message.usage` con tokens > 0

## Precios

Hardcodeados en `log_parser.py` (dict `PRICES`). Actualizar al inicio de cada versión si Anthropic cambia los precios. Última actualización: 2026-05 (Opus $15/$75, Sonnet $3/$15, Haiku $0.80/$4 por 1M tokens).

## Tests

```bash
# desarrollo local (solo la primera vez)
pip install pytest pytest-cov

python -m pytest -v
```

Cubre `get_tier()`, `calc_cost()` y las reglas de `compute_tips()`.

## Linter

```bash
ruff check .
ruff format .
```

Configurado en `pyproject.toml`. Correr antes de cada commit.

## CI

GitHub Actions corre automáticamente en cada push y PR a `develop` o `master`:

1. `ruff check .` — lint
2. `python -m pytest -v` — tests

La rama `master` tiene branch protection activa: el CI debe estar en verde antes de poder mergear.
