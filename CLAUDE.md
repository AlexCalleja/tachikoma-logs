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
├── generate_demo.py ← genera dashboard con datos sintéticos obfuscados (seed=42, 90 sesiones)
├── log_parser.py    ← PRICING, get_tier(), calc_cost(), parse_sessions()
├── tips.py          ← compute_tips() — spec canónica de las 8 reglas (Python); la implementación
│                      viva está portada a JS en dashboard.html (computeTips / buildClaudePrompt)
├── html_builder.py  ← generate_html(): inyecta __SESSIONS_JSON__ y __GENERATED_AT__ en el template
├── templates/
│   └── dashboard.html  ← HTML/CSS/JS del dashboard; generate_html() inyecta datos via __PLACEHOLDER__
└── tests/
    ├── test_log_parser.py
    ├── test_tips.py
    └── test_e2e.py  ← Playwright e2e: errores JS en carga, filtros, sort, toggles idioma/tema
```

Flujo de datos: `parse_sessions()` → `generate_html()` → browser computes tips + prompt en JS

La estructura es plana por diseño (YAGNI) — mover los módulos a un paquete `tachikoma/` tiene sentido cuando haya suficientes módulos que lo justifiquen.

## Fuente de datos

- Archivos: `~/.claude/projects/**/*.jsonl` (glob recursivo)
- Se omiten paths que contengan `subagents` en algún componente
- Deduplicación por `message.id` dentro de cada sesión — obligatoria (sin ella los tokens se inflan 2-3x por streaming)
- Solo se procesan entradas con `type == "assistant"` y `message.usage` con tokens > 0
- Sesiones bajo paths con `AppData` en el nombre de directorio del proyecto se agrupan como proyecto `"temp"` (operaciones internas de Claude Code con Haiku)
- Campos adicionales extraídos por sesión: `entrypoint` (primer valor no-nulo), `permission_mode` (el más frecuente), `stop_reason` (el más frecuente excluyendo `tool_use`), `tools` (dict `{nombre: llamadas_totales}`), `message_count` (máximo `messageCount` visto)
- `tool_use` se excluye de `stop_reason` porque domina (cada llamada a herramienta lo genera) y oculta los valores informativos

## Precios

Hardcodeados en `log_parser.py` (dict `PRICES`). Actualizar al inicio de cada versión si Anthropic cambia los precios. Última actualización: 2026-05 (Opus $15/$75, Sonnet $3/$15, Haiku $0.80/$4 por 1M tokens).

## Tests

### Unit tests
```bash
# primera vez
pip install pytest pytest-cov ruff

python -m pytest tests/test_log_parser.py tests/test_tips.py -v
```

Cubre `get_tier()`, `calc_cost()`, las reglas de `compute_tips()`, y los campos de sesión (`entrypoint`, `permission_mode`, `stop_reason`, `tools`, `message_count`, filtro AppData, skill/agent expansion). 29 tests.

### E2E tests (Playwright)

Detecta errores JS que los unit tests no pueden ver: funciones no definidas, charts que no cargan, `sortTbl` crasheando, regressions en filtros y toggles.

```bash
# primera vez
pip install pytest-playwright
playwright install chromium

# generar el dashboard primero
python generate.py

python -m pytest tests/test_e2e.py -v
```

Cubre: carga sin errores JS, todos los canvases, filtros de fecha/modelo, sort en tSkills/tProj/tModel, toggles de idioma y tema.

## Linter

```bash
ruff check .
ruff format .
```

Configurado en `pyproject.toml`. Correr antes de cada commit.

## CI

GitHub Actions corre automáticamente en cada push y PR a `develop` o `master`. Dos jobs en paralelo:

- **`unit`**: `ruff check .` + `pytest test_log_parser.py test_tips.py`
- **`e2e`**: genera el dashboard + `pytest test_e2e.py` con Chromium (Playwright)

La rama `master` tiene branch protection activa: ambos jobs deben estar en verde antes de poder mergear.
