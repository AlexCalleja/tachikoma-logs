#!/usr/bin/env python3
"""Claude Code usage dashboard generator.

Usage:
    python generate.py [--output docs/usage.html]

Outputs a self-contained HTML file with:
  - 4 Chart.js charts (dark theme, no pip required)
  - Rule-based usage tips
  - "Copy prompt for Claude" button for deeper AI analysis
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from statistics import median

# ── Pricing (per 1M tokens) ────────────────────────────────────────────────
PRICES = {
    "opus":   {"input": 15.0,  "output": 75.0,  "cache_read": 1.50,  "cache_create": 18.75},
    "sonnet": {"input": 3.0,   "output": 15.0,  "cache_read": 0.30,  "cache_create": 3.75},
    "haiku":  {"input": 0.80,  "output": 4.0,   "cache_read": 0.08,  "cache_create": 1.0},
}

DUR_EDGES  = [0, 5, 15, 30, 60, 120, 9999]
DUR_LABELS = ["<5 min", "5-15 min", "15-30 min", "30-60 min", "1-2 h", ">2 h"]


def get_tier(model: str) -> str:
    m = model.lower()
    if "opus" in m:  return "opus"
    if "haiku" in m: return "haiku"
    return "sonnet"


def calc_cost(usage: dict, tier: str) -> float:
    p = PRICES.get(tier, PRICES["sonnet"])
    return (
        usage.get("input_tokens", 0)                * p["input"]        / 1e6 +
        usage.get("output_tokens", 0)               * p["output"]       / 1e6 +
        usage.get("cache_read_input_tokens", 0)     * p["cache_read"]   / 1e6 +
        usage.get("cache_creation_input_tokens", 0) * p["cache_create"] / 1e6
    )


# ── Parser ─────────────────────────────────────────────────────────────────
def parse_sessions() -> list:
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        print(f"ERROR: {projects_dir} not found", file=sys.stderr)
        return []

    sessions = {}

    for jsonl_file in sorted(projects_dir.rglob("*.jsonl")):
        if "subagents" in jsonl_file.parts:
            continue

        session_id = jsonl_file.stem
        entries = []
        try:
            with open(jsonl_file, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            continue

        cwd = next((e.get("cwd", "") for e in entries if e.get("cwd")), "")
        project = Path(cwd.replace("\\", "/")).name if cwd else "unknown"

        seen_msg_ids: set = set()
        total = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
        models_used: set = set()
        timestamps = []
        estimated_cost = 0.0

        for entry in entries:
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message", {})
            msg_id = msg.get("id", "")
            if msg_id and msg_id in seen_msg_ids:
                continue
            if msg_id:
                seen_msg_ids.add(msg_id)

            usage = msg.get("usage", {})
            if not usage or not (usage.get("output_tokens") or usage.get("input_tokens")):
                continue

            model = msg.get("model", "unknown")
            models_used.add(model)
            tier = get_tier(model)

            total["input"]        += usage.get("input_tokens", 0)
            total["output"]       += usage.get("output_tokens", 0)
            total["cache_read"]   += usage.get("cache_read_input_tokens", 0)
            total["cache_create"] += usage.get("cache_creation_input_tokens", 0)
            estimated_cost        += calc_cost(usage, tier)

            ts = entry.get("timestamp", "")
            if ts:
                timestamps.append(ts)

        if not timestamps or total["output"] == 0:
            continue

        timestamps.sort()
        t0 = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
        duration_min = round((t1 - t0).total_seconds() / 60, 1)

        tiers = {get_tier(m) for m in models_used}
        if len(tiers) == 1:
            primary = next(iter(tiers))
        elif "opus" in tiers:
            primary = "mixed"
        else:
            primary = "sonnet"

        sessions[session_id] = {
            "session_id":     session_id,
            "project":        project,
            "date":           t0.strftime("%Y-%m-%d"),
            "datetime":       t0.isoformat(),
            "duration_min":   duration_min,
            "input_tokens":   total["input"],
            "output_tokens":  total["output"],
            "cache_read":     total["cache_read"],
            "cache_create":   total["cache_create"],
            "total_tokens":   total["input"] + total["output"],
            "primary_model":  primary,
            "estimated_cost": round(estimated_cost, 4),
        }

    result = sorted(sessions.values(), key=lambda s: s["datetime"])
    print(f"Parsed {len(result)} sessions across {len({s['project'] for s in result})} projects")
    return result


# ── Rule-based tips ─────────────────────────────────────────────────────────
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
            "title": f"Costo concentrado en un proyecto",
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


# ── Claude prompt builder ────────────────────────────────────────────────────
def build_claude_prompt(sessions: list, tips: list) -> str:
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

    durations = [s["duration_min"] for s in sessions]
    med_dur   = median(durations)

    cacheable  = total_input + total_cache_read + total_cache_create
    cache_rate = total_cache_read / cacheable if cacheable > 0 else 0

    tip_lines  = "\n".join(
        f"- [{t['level'].upper()}] {t['title']}: {t['body']}" for t in tips
    )
    proj_lines = "\n".join(
        f"  - {name}: {d['sessions']} sesiones, {d['tokens']:,} tokens, ${d['cost']:.2f}"
        for name, d in top5
    )
    model_lines = "\n".join(
        f"  - {m}: {c} sesiones" for m, c in sorted(model_counts.items())
    )

    first_date = sessions[0]["date"]
    last_date  = sessions[-1]["date"]

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


# ── Chart data builder ──────────────────────────────────────────────────────
def build_chart_data(sessions: list) -> dict:
    by_date = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "sessions": 0})
    for s in sessions:
        by_date[s["date"]]["tokens"]   += s["total_tokens"]
        by_date[s["date"]]["cost"]     += s["estimated_cost"]
        by_date[s["date"]]["sessions"] += 1
    dates = sorted(by_date)

    by_proj = defaultdict(lambda: {"tokens": 0, "sessions": 0, "cost": 0.0})
    for s in sessions:
        by_proj[s["project"]]["tokens"]   += s["total_tokens"]
        by_proj[s["project"]]["sessions"] += 1
        by_proj[s["project"]]["cost"]     += s["estimated_cost"]
    by_proj = dict(sorted(by_proj.items(), key=lambda x: -x[1]["tokens"])[:10])

    model_counts = defaultdict(int)
    for s in sessions:
        model_counts[s["primary_model"]] += 1

    dur_counts = [0] * len(DUR_LABELS)
    for s in sessions:
        d = s["duration_min"]
        for i, (lo, hi) in enumerate(zip(DUR_EDGES, DUR_EDGES[1:])):
            if lo <= d < hi:
                dur_counts[i] += 1
                break

    return {
        "dates":          dates,
        "tokensByDate":   [by_date[d]["tokens"] for d in dates],
        "costByDate":     [round(by_date[d]["cost"], 4) for d in dates],
        "sessionsByDate": [by_date[d]["sessions"] for d in dates],
        "projLabels":     list(by_proj.keys()),
        "projTokens":     [by_proj[p]["tokens"] for p in by_proj],
        "projSessions":   [by_proj[p]["sessions"] for p in by_proj],
        "projCost":       [round(by_proj[p]["cost"], 2) for p in by_proj],
        "modelLabels":    list(model_counts.keys()),
        "modelValues":    list(model_counts.values()),
        "durLabels":      DUR_LABELS,
        "durCounts":      dur_counts,
        "stats": {
            "sessions":    len(sessions),
            "totalTokens": sum(s["total_tokens"] for s in sessions),
            "totalCost":   round(sum(s["estimated_cost"] for s in sessions), 2),
            "projects":    len({s["project"] for s in sessions}),
            "avgDuration": round(sum(s["duration_min"] for s in sessions) / len(sessions), 1),
        },
    }


# ── HTML generator ──────────────────────────────────────────────────────────
def generate_html(sessions: list, tips: list, output_path: Path):
    chart_data    = build_chart_data(sessions)
    claude_prompt = build_claude_prompt(sessions, tips)

    data_json    = json.dumps(chart_data,    ensure_ascii=False)
    tips_json    = json.dumps(tips,          ensure_ascii=False)
    prompt_json  = json.dumps(claude_prompt, ensure_ascii=False)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Claude Code - Usage Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg:#0d1117; --surface:#161b22; --border:#30363d;
      --text:#e6edf3; --muted:#7d8590; --accent:#58a6ff;
      --green:#3fb950; --purple:#bc8cff; --orange:#f0883e; --red:#f85149;
      --warn-bg:rgba(240,136,62,.12); --warn-border:rgba(240,136,62,.4);
      --info-bg:rgba(88,166,255,.10); --info-border:rgba(88,166,255,.35);
      --ok-bg:rgba(63,185,80,.10);    --ok-border:rgba(63,185,80,.35);
    }}
    * {{ box-sizing:border-box; margin:0; padding:0 }}
    body {{ background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; padding:2rem; max-width:1200px; margin:0 auto }}
    h1   {{ font-size:1.15rem; font-weight:700; margin-bottom:.25rem }}
    .meta {{ font-size:.7rem; color:var(--muted); font-family:'JetBrains Mono','Fira Code',monospace; margin-bottom:1.75rem }}

    .stats {{ display:grid; grid-template-columns:repeat(5,1fr); gap:.75rem; margin-bottom:1.25rem }}
    .stat {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.9rem 1.1rem }}
    .stat .lbl {{ font-size:.6rem; color:var(--muted); text-transform:uppercase; letter-spacing:.07em }}
    .stat .val {{ font-size:1.35rem; font-weight:700; margin-top:.2rem }}
    .stat .sub {{ font-size:.6rem; color:var(--muted); margin-top:.1rem }}

    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:.85rem; margin-bottom:1.25rem }}
    .card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1.1rem }}
    .card.full {{ grid-column:1/-1 }}
    .card h2 {{ font-size:.62rem; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:.85rem }}
    canvas {{ max-height:240px }}

    .section-title {{ font-size:.62rem; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:.6rem }}
    .tips-section {{ margin-bottom:1.25rem }}
    .tip {{ border-radius:7px; padding:.75rem 1rem; margin-bottom:.5rem; display:flex; gap:.75rem; align-items:flex-start }}
    .tip.warn {{ background:var(--warn-bg); border:1px solid var(--warn-border) }}
    .tip.info {{ background:var(--info-bg); border:1px solid var(--info-border) }}
    .tip.ok   {{ background:var(--ok-bg);   border:1px solid var(--ok-border) }}
    .tip-icon {{ font-size:.85rem; flex-shrink:0; margin-top:.05rem; width:1rem; text-align:center }}
    .tip-title {{ font-size:.75rem; font-weight:600; margin-bottom:.2rem }}
    .tip.warn .tip-title {{ color:var(--orange) }}
    .tip.info .tip-title {{ color:var(--accent) }}
    .tip.ok   .tip-title {{ color:var(--green) }}
    .tip-body {{ font-size:.72rem; color:var(--muted); line-height:1.5 }}

    .claude-section {{ margin-bottom:1.25rem }}
    .claude-card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.25rem; display:flex; align-items:center; gap:1rem }}
    .claude-desc {{ flex:1; font-size:.75rem; color:var(--muted); line-height:1.5 }}
    .claude-desc strong {{ color:var(--text) }}
    .btn-copy {{ background:var(--accent); color:#0d1117; border:none; border-radius:6px; padding:.55rem 1.1rem; font-size:.75rem; font-weight:700; cursor:pointer; white-space:nowrap; transition:opacity .15s }}
    .btn-copy:hover {{ opacity:.85 }}
    .btn-copy.copied {{ background:var(--green) }}

    @media(max-width:900px) {{ .stats{{grid-template-columns:repeat(3,1fr)}} .grid{{grid-template-columns:1fr}} }}
    @media(max-width:600px) {{ .stats{{grid-template-columns:1fr 1fr}} body{{padding:1rem}} }}
  </style>
</head>
<body>
  <h1>Claude Code - Usage Dashboard</h1>
  <p class="meta">generado {generated_at} &middot; Chart.js 4.4 &middot; datos de ~/.claude/projects/</p>

  <div class="stats">
    <div class="stat"><div class="lbl">Sesiones</div><div class="val" id="s-sessions"></div></div>
    <div class="stat"><div class="lbl">Tokens totales</div><div class="val" id="s-tokens"></div><div class="sub">input + output</div></div>
    <div class="stat"><div class="lbl">Costo estimado</div><div class="val" id="s-cost"></div><div class="sub">USD aproximado</div></div>
    <div class="stat"><div class="lbl">Proyectos</div><div class="val" id="s-projects"></div></div>
    <div class="stat"><div class="lbl">Duracion media</div><div class="val" id="s-duration"></div><div class="sub">por sesion</div></div>
  </div>

  <div class="grid">
    <div class="card full"><h2>Tokens y costo por dia</h2><canvas id="cTime"></canvas></div>
    <div class="card"><h2>Top proyectos (tokens)</h2><canvas id="cProj"></canvas></div>
    <div class="card"><h2>Modelo primario por sesion</h2><canvas id="cModel"></canvas></div>
    <div class="card full"><h2>Distribucion de duracion de sesiones</h2><canvas id="cDur"></canvas></div>
  </div>

  <div class="tips-section">
    <div class="section-title">Consejos de uso</div>
    <div id="tips-container"></div>
  </div>

  <div class="claude-section">
    <div class="section-title">Analisis con Claude</div>
    <div class="claude-card">
      <div class="claude-desc">
        <strong>Copia un prompt pre-armado</strong> con todas tus metricas y pegalo en Claude
        para obtener analisis mas profundo, recomendaciones personalizadas y patrones
        que las reglas automaticas no capturan.
      </div>
      <button class="btn-copy" id="btn-copy" onclick="copyClaudePrompt()">Copiar prompt para Claude</button>
    </div>
  </div>

<script>
const D = {data_json};
const TIPS = {tips_json};
const CLAUDE_PROMPT = {prompt_json};

// ── Stats ──────────────────────────────────────────────────────────────────
document.getElementById('s-sessions').textContent  = D.stats.sessions.toLocaleString();
document.getElementById('s-tokens').textContent    = (D.stats.totalTokens / 1000).toFixed(0) + 'k';
document.getElementById('s-cost').textContent      = '$' + D.stats.totalCost.toFixed(2);
document.getElementById('s-projects').textContent  = D.stats.projects;
document.getElementById('s-duration').textContent  = D.stats.avgDuration + ' min';

// ── Charts ─────────────────────────────────────────────────────────────────
Chart.defaults.color       = '#7d8590';
Chart.defaults.borderColor = '#30363d';
const GRID  = {{ color: 'rgba(48,54,61,.5)' }};
const TICKS = {{ color: '#7d8590', font: {{ size: 11 }} }};

const PALETTE = [
  '#58a6ff','#3fb950','#f0883e','#bc8cff','#f85149',
  '#56d364','#e3b341','#d2a8ff','#ffa657','#ff7b72',
];
const MODEL_COLORS = {{ sonnet:'#58a6ff', opus:'#bc8cff', haiku:'#3fb950', mixed:'#f0883e' }};

new Chart(document.getElementById('cTime'), {{
  type: 'bar',
  data: {{
    labels: D.dates,
    datasets: [
      {{
        label: 'Tokens',
        data: D.tokensByDate,
        backgroundColor: 'rgba(88,166,255,.45)',
        borderColor: '#58a6ff',
        borderWidth: 1,
        borderRadius: 3,
        yAxisID: 'y',
      }},
      {{
        label: 'Costo USD',
        data: D.costByDate,
        type: 'line',
        borderColor: '#f0883e',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        pointRadius: 2,
        tension: 0.3,
        yAxisID: 'y2',
      }},
    ],
  }},
  options: {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ labels: {{ color: '#7d8590', font: {{ size: 11 }}, boxWidth: 12 }} }},
      tooltip: {{ callbacks: {{
        afterBody: ctx => ctx[0] ? ['sesiones: ' + D.sessionsByDate[ctx[0].dataIndex]] : [],
      }} }},
    }},
    scales: {{
      x:  {{ grid: GRID, ticks: TICKS }},
      y:  {{ grid: GRID, ticks: TICKS, title: {{ display:true, text:'Tokens', color:'#7d8590', font:{{ size:10 }} }} }},
      y2: {{ grid: {{ display:false }}, ticks: TICKS, position:'right',
             title: {{ display:true, text:'USD', color:'#f0883e', font:{{ size:10 }} }} }},
    }},
  }},
}});

new Chart(document.getElementById('cProj'), {{
  type: 'doughnut',
  data: {{
    labels: D.projLabels,
    datasets: [{{ data: D.projTokens, backgroundColor: PALETTE, borderWidth: 0 }}],
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position:'right', labels: {{ color:'#e6edf3', font:{{ size:11 }}, boxWidth:12 }} }},
      tooltip: {{ callbacks: {{
        afterLabel: ctx => [
          'sesiones: ' + D.projSessions[ctx.dataIndex],
          'costo: $'   + D.projCost[ctx.dataIndex],
        ],
      }} }},
    }},
  }},
}});

new Chart(document.getElementById('cModel'), {{
  type: 'doughnut',
  data: {{
    labels: D.modelLabels,
    datasets: [{{
      data: D.modelValues,
      backgroundColor: D.modelLabels.map(m => MODEL_COLORS[m] || '#7d8590'),
      borderWidth: 0,
    }}],
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position:'right', labels: {{ color:'#e6edf3', font:{{ size:11 }}, boxWidth:12 }} }},
    }},
  }},
}});

new Chart(document.getElementById('cDur'), {{
  type: 'bar',
  data: {{
    labels: D.durLabels,
    datasets: [{{
      label: 'Sesiones',
      data: D.durCounts,
      backgroundColor: 'rgba(63,185,80,.45)',
      borderColor: '#3fb950',
      borderWidth: 1,
      borderRadius: 3,
    }}],
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display:false }} }},
    scales: {{ x: {{ grid:GRID, ticks:TICKS }}, y: {{ grid:GRID, ticks:TICKS }} }},
  }},
}});

// ── Tips (safe DOM construction, no innerHTML with data) ────────────────────
const ICONS = {{ warn: 'o', info: 'i', ok: 'v' }};
const container = document.getElementById('tips-container');

function makeTip(t) {{
  const wrap  = document.createElement('div');
  wrap.className = 'tip ' + t.level;

  const icon = document.createElement('div');
  icon.className = 'tip-icon';
  icon.textContent = t.level === 'warn' ? '!' : t.level === 'ok' ? 'v' : 'i';

  const body = document.createElement('div');

  const title = document.createElement('div');
  title.className = 'tip-title';
  title.textContent = t.title;

  const desc = document.createElement('div');
  desc.className = 'tip-body';
  desc.textContent = t.body;

  body.appendChild(title);
  body.appendChild(desc);
  wrap.appendChild(icon);
  wrap.appendChild(body);
  return wrap;
}}

if (TIPS.length === 0) {{
  const p = document.createElement('p');
  p.style.cssText = 'font-size:.75rem;color:var(--muted)';
  p.textContent = 'Sin alertas -- todo se ve bien.';
  container.appendChild(p);
}} else {{
  TIPS.forEach(t => container.appendChild(makeTip(t)));
}}

// ── Claude prompt copy ──────────────────────────────────────────────────────
function copyClaudePrompt() {{
  const btn = document.getElementById('btn-copy');
  const reset = () => {{
    btn.textContent = 'Copiar prompt para Claude';
    btn.classList.remove('copied');
  }};
  const onCopied = () => {{
    btn.textContent = 'Copiado!';
    btn.classList.add('copied');
    setTimeout(reset, 2500);
  }};

  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(CLAUDE_PROMPT).then(onCopied).catch(() => fallbackCopy());
  }} else {{
    fallbackCopy();
  }}

  function fallbackCopy() {{
    const ta = document.createElement('textarea');
    ta.value = CLAUDE_PROMPT;
    ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {{ document.execCommand('copy'); onCopied(); }} catch (_) {{}}
    document.body.removeChild(ta);
  }}
}}
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"  -> {output_path}")


# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Generate Claude Code usage dashboard")
    ap.add_argument("--output", default="docs/usage.html", help="Output HTML path")
    args = ap.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sessions = parse_sessions()
    if not sessions:
        print("No sessions found.")
        raise SystemExit(1)

    tips = compute_tips(sessions)
    print(f"Tips: {len(tips)} generated")

    generate_html(sessions, tips, output_path)
    print(f"Done: {output_path.resolve()}")
