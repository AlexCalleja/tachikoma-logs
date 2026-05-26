from collections import defaultdict
from statistics import median


def compute_tips(sessions: list) -> list:
    """Returns list of {level, title_es, body_es, title_en, body_en} dicts."""
    if not sessions:
        return []

    tips = []
    total_cost         = sum(s["estimated_cost"] for s in sessions)
    total_cache_read   = sum(s["cache_read"] for s in sessions)
    total_cache_create = sum(s["cache_create"] for s in sessions)
    total_input        = sum(s["input_tokens"] for s in sessions)

    # 1. Cache hit rate
    cacheable  = total_input + total_cache_read + total_cache_create
    cache_rate = total_cache_read / cacheable if cacheable > 0 else 0
    if cache_rate < 0.15:
        tips.append({
            "level":    "warn",
            "title_es": "Baja tasa de cache",
            "body_es":  (
                f"Solo el {cache_rate:.0%} de los tokens de entrada viene de cache. "
                "Sesiones mas largas y reusar contexto entre mensajes mejora esto."
            ),
            "title_en": "Low cache hit rate",
            "body_en":  (
                f"Only {cache_rate:.0%} of input tokens come from cache. "
                "Longer sessions and reusing context between messages improves this."
            ),
        })
    elif cache_rate >= 0.40:
        tips.append({
            "level":    "ok",
            "title_es": "Buena tasa de cache",
            "body_es":  f"{cache_rate:.0%} de tokens viene de cache -- buen uso del contexto de sesion.",
            "title_en": "Good cache hit rate",
            "body_en":  f"{cache_rate:.0%} of tokens come from cache — good use of session context.",
        })

    # 2. Opus proportion
    opus_sessions = [s for s in sessions if s["primary_model"] in ("opus", "mixed")]
    opus_pct      = len(opus_sessions) / len(sessions) if sessions else 0
    opus_cost     = sum(s["estimated_cost"] for s in opus_sessions)
    opus_cost_pct = opus_cost / total_cost if total_cost > 0 else 0
    if opus_pct > 0.35:
        tips.append({
            "level":    "warn",
            "title_es": "Alto uso de Opus",
            "body_es":  (
                f"{opus_pct:.0%} de sesiones usan Opus ({opus_cost_pct:.0%} del costo). "
                "Opus es ideal para planning y debugging complejo -- "
                "revisa si todas las sesiones lo justifican."
            ),
            "title_en": "High Opus usage",
            "body_en":  (
                f"{opus_pct:.0%} of sessions use Opus ({opus_cost_pct:.0%} of cost). "
                "Opus is ideal for planning and complex debugging — "
                "review whether all sessions justify it."
            ),
        })

    # 3. Short sessions (probable context startup waste)
    short     = [s for s in sessions if s["duration_min"] < 3]
    short_pct = len(short) / len(sessions)
    if short_pct > 0.30:
        tips.append({
            "level":    "info",
            "title_es": "Muchas sesiones muy cortas",
            "body_es":  (
                f"{short_pct:.0%} de sesiones duran menos de 3 min. "
                "Cada sesion paga el costo de contexto inicial -- "
                "considera consolidar tareas cortas."
            ),
            "title_en": "Many very short sessions",
            "body_en":  (
                f"{short_pct:.0%} of sessions last under 3 min. "
                "Each session pays the initial context cost — "
                "consider consolidating short tasks."
            ),
        })

    # 4. Long sessions (context degradation)
    long_sessions = [s for s in sessions if s["duration_min"] > 120]
    if len(long_sessions) >= 3:
        avg_cost_long = sum(s["estimated_cost"] for s in long_sessions) / len(long_sessions)
        tips.append({
            "level":    "info",
            "title_es": "Sesiones muy largas",
            "body_es":  (
                f"{len(long_sessions)} sesiones superan 2 h "
                f"(costo promedio ${avg_cost_long:.2f}). "
                "Claude pierde efectividad en contextos muy largos -- "
                "considera /compact o dividir en sesiones."
            ),
            "title_en": "Very long sessions",
            "body_en":  (
                f"{len(long_sessions)} sessions exceed 2 h "
                f"(avg cost ${avg_cost_long:.2f}). "
                "Claude loses effectiveness in very long contexts — "
                "consider /compact or splitting into sessions."
            ),
        })

    # 5. Project cost concentration
    by_proj_cost = defaultdict(float)
    for s in sessions:
        by_proj_cost[s["project"]] += s["estimated_cost"]
    top_proj, top_cost = max(by_proj_cost.items(), key=lambda x: x[1])
    top_pct = top_cost / total_cost if total_cost > 0 else 0
    if top_pct > 0.60 and len(by_proj_cost) > 2:
        tips.append({
            "level":    "info",
            "title_es": "Costo concentrado en un proyecto",
            "body_es":  (
                f"'{top_proj}' representa el {top_pct:.0%} del costo total "
                f"(${top_cost:.2f}). "
                "Puede ser intencional, pero vale revisarlo si el proyecto ya esta estable."
            ),
            "title_en": "Cost concentrated in one project",
            "body_en":  (
                f"'{top_proj}' accounts for {top_pct:.0%} of total cost "
                f"(${top_cost:.2f}). "
                "May be intentional, but worth reviewing if the project is already stable."
            ),
        })

    # 6. High output:input ratio (expensive generation)
    total_output = sum(s["output_tokens"] for s in sessions)
    if total_input > 0:
        ratio = total_output / total_input
        if ratio > 0.8:
            tips.append({
                "level":    "info",
                "title_es": "Relacion output/input alta",
                "body_es":  (
                    f"Output es el {ratio:.0%} del input. "
                    "El output es 5-25x mas caro que el input -- "
                    "prompts mas precisos reducen los tokens generados."
                ),
                "title_en": "High output/input ratio",
                "body_en":  (
                    f"Output is {ratio:.0%} of input. "
                    "Output costs 5-25x more than input — "
                    "more precise prompts reduce generated tokens."
                ),
            })

    # 7. Median session duration
    durations = [s["duration_min"] for s in sessions]
    med = median(durations)
    if med >= 20:
        tips.append({
            "level":    "ok",
            "title_es": "Sesiones de buena duracion",
            "body_es":  f"Duracion mediana de {med:.0f} min -- sesiones bien aprovechadas.",
            "title_en": "Good session duration",
            "body_en":  f"Median duration of {med:.0f} min — sessions are well-utilized.",
        })

    return tips
