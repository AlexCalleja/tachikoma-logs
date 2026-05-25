from collections import defaultdict
from statistics import median


def compute_tips(sessions: list) -> list:
    """Returns list of {level, title, body} dicts. level: 'warn'|'info'|'ok'."""
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
            "level": "warn",
            "title": "Baja tasa de cache",
            "body": (
                f"Solo el {cache_rate:.0%} de los tokens de entrada viene de cache. "
                "Sesiones mas largas y reusar contexto entre mensajes mejora esto."
            ),
        })
    elif cache_rate >= 0.40:
        tips.append({
            "level": "ok",
            "title": "Buena tasa de cache",
            "body": f"{cache_rate:.0%} de tokens viene de cache -- buen uso del contexto de sesion.",
        })

    # 2. Opus proportion
    opus_sessions = [s for s in sessions if s["primary_model"] in ("opus", "mixed")]
    opus_pct      = len(opus_sessions) / len(sessions) if sessions else 0
    opus_cost     = sum(s["estimated_cost"] for s in opus_sessions)
    opus_cost_pct = opus_cost / total_cost if total_cost > 0 else 0
    if opus_pct > 0.35:
        tips.append({
            "level": "warn",
            "title": "Alto uso de Opus",
            "body": (
                f"{opus_pct:.0%} de sesiones usan Opus ({opus_cost_pct:.0%} del costo). "
                "Opus es ideal para planning y debugging complejo -- "
                "revisa si todas las sesiones lo justifican."
            ),
        })

    # 3. Short sessions (probable context startup waste)
    short     = [s for s in sessions if s["duration_min"] < 3]
    short_pct = len(short) / len(sessions)
    if short_pct > 0.30:
        tips.append({
            "level": "info",
            "title": "Muchas sesiones muy cortas",
            "body": (
                f"{short_pct:.0%} de sesiones duran menos de 3 min. "
                "Cada sesion paga el costo de contexto inicial -- "
                "considera consolidar tareas cortas."
            ),
        })

    # 4. Long sessions (context degradation)
    long_sessions = [s for s in sessions if s["duration_min"] > 120]
    if len(long_sessions) >= 3:
        avg_cost_long = sum(s["estimated_cost"] for s in long_sessions) / len(long_sessions)
        tips.append({
            "level": "info",
            "title": "Sesiones muy largas",
            "body": (
                f"{len(long_sessions)} sesiones superan 2 h "
                f"(costo promedio ${avg_cost_long:.2f}). "
                "Claude pierde efectividad en contextos muy largos -- "
                "considera /compact o dividir en sesiones."
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
            "level": "info",
            "title": "Costo concentrado en un proyecto",
            "body": (
                f"'{top_proj}' representa el {top_pct:.0%} del costo total "
                f"(${top_cost:.2f}). "
                "Puede ser intencional, pero vale revisarlo si el proyecto ya esta estable."
            ),
        })

    # 6. High output:input ratio (expensive generation)
    total_output = sum(s["output_tokens"] for s in sessions)
    if total_input > 0:
        ratio = total_output / total_input
        if ratio > 0.8:
            tips.append({
                "level": "info",
                "title": "Relacion output/input alta",
                "body": (
                    f"Output es el {ratio:.0%} del input. "
                    "El output es 5-25x mas caro que el input -- "
                    "prompts mas precisos reducen los tokens generados."
                ),
            })

    # 7. Median session duration
    durations = [s["duration_min"] for s in sessions]
    med = median(durations)
    if med >= 20:
        tips.append({
            "level": "ok",
            "title": "Sesiones de buena duracion",
            "body": f"Duracion mediana de {med:.0f} min -- sesiones bien aprovechadas.",
        })

    return tips
