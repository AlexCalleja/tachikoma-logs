import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

_TEMPLATE = Path(__file__).parent / "templates" / "dashboard.html"


def build_claude_prompt(sessions: list[dict], tips: list[dict], lang: str = "es") -> str:
    if not sessions:
        return ""

    total_tokens       = sum(s["total_tokens"] for s in sessions)
    total_cost         = sum(s["estimated_cost"] for s in sessions)
    total_input        = sum(s["input_tokens"] for s in sessions)
    total_output       = sum(s["output_tokens"] for s in sessions)
    total_cache_read   = sum(s["cache_read"] for s in sessions)
    total_cache_create = sum(s["cache_create"] for s in sessions)

    by_proj = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "sessions": 0})
    for s in sessions:
        by_proj[s["project"]]["tokens"]   += s["total_tokens"]
        by_proj[s["project"]]["cost"]     += s["estimated_cost"]
        by_proj[s["project"]]["sessions"] += 1
    top5 = sorted(by_proj.items(), key=lambda x: -x[1]["cost"])[:5]

    model_counts = defaultdict(int)
    for s in sessions:
        model_counts[s["primary_model"]] += 1

    durations  = [s["duration_min"] for s in sessions]
    med_dur    = median(durations)
    cacheable  = total_input + total_cache_read + total_cache_create
    cache_rate = total_cache_read / cacheable if cacheable > 0 else 0

    sw = "sessions" if lang == "en" else "sesiones"
    tip_lines = "\n".join(
        f"- [{t['level'].upper()}] {t[f'title_{lang}']}: {t[f'body_{lang}']}" for t in tips
    )
    proj_lines = "\n".join(
        f"  - {name}: {d['sessions']} {sw}, {d['tokens']:,} tokens, ${d['cost']:.2f}"
        for name, d in top5
    )
    model_lines = "\n".join(
        f"  - {m}: {c} {sw}" for m, c in sorted(model_counts.items())
    )

    first_date = sessions[0]["date"]
    last_date  = sessions[-1]["date"]

    if lang == "en":
        return f"""Here are my Claude Code usage metrics. \
Analyze them and give me concrete recommendations to improve my workflow, \
reduce costs, and improve session quality.

## General summary
- Period: {first_date} -> {last_date}
- Total sessions: {len(sessions)}
- Active projects: {len(by_proj)}
- Total tokens: {total_tokens:,} (input: {total_input:,}, output: {total_output:,})
- Estimated cost: ${total_cost:.2f} USD
- Median session duration: {med_dur:.0f} min
- Cache rate: {cache_rate:.0%} (read: {total_cache_read:,}, create: {total_cache_create:,})

## Distribution by project (top 5)
{proj_lines}

## Distribution by model
{model_lines}

## Automatically detected tips
{tip_lines if tip_lines else "  (none)"}

## Questions I'd like to answer
1. What patterns suggest inefficient usage?
2. How could I improve the cache rate?
3. Does the Sonnet/Opus balance make sense for the type of work I do?
4. What should I change in my longer sessions?
5. Are there any warning signs I'm not capturing with the automatic rules?
""".strip()

    return f"""Aqui estan mis metricas de uso de Claude Code. \
Analizalas y dame recomendaciones concretas para mejorar mi flujo de trabajo, \
reducir costos y mejorar la calidad de mis sesiones.

## Resumen general
- Periodo: {first_date} -> {last_date}
- Sesiones totales: {len(sessions)}
- Proyectos activos: {len(by_proj)}
- Tokens totales: {total_tokens:,} (input: {total_input:,}, output: {total_output:,})
- Costo estimado: ${total_cost:.2f} USD
- Duracion mediana de sesion: {med_dur:.0f} min
- Tasa de cache: {cache_rate:.0%} (read: {total_cache_read:,}, create: {total_cache_create:,})

## Distribucion por proyecto (top 5)
{proj_lines}

## Distribucion por modelo
{model_lines}

## Tips automaticos detectados
{tip_lines if tip_lines else "  (ninguno)"}

## Preguntas que me gustaria responder
1. Que patrones ves que sugieran uso ineficiente?
2. Como podria mejorar la tasa de cache?
3. El balance Sonnet/Opus tiene sentido para el tipo de trabajo que hago?
4. Que deberia cambiar en mis sesiones mas largas?
5. Hay alguna senal de alerta que no este captando con las reglas automaticas?
""".strip()


def generate_html(sessions: list[dict], tips: list[dict], output_path: Path) -> None:
    claude_prompt_es = build_claude_prompt(sessions, tips, lang="es")
    claude_prompt_en = build_claude_prompt(sessions, tips, lang="en")

    html = _TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__SESSIONS_JSON__",   json.dumps(sessions,         ensure_ascii=False))
    html = html.replace("__TIPS_JSON__",        json.dumps(tips,             ensure_ascii=False))
    html = html.replace("__CLAUDE_PROMPT_ES__", json.dumps(claude_prompt_es, ensure_ascii=False))
    html = html.replace("__CLAUDE_PROMPT_EN__", json.dumps(claude_prompt_en, ensure_ascii=False))
    html = html.replace("__GENERATED_AT__",     datetime.now().strftime("%Y-%m-%d %H:%M"))

    output_path.write_text(html, encoding="utf-8")
    print(f"  -> {output_path}")
