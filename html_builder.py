import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median


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

    durations  = [s["duration_min"] for s in sessions]
    med_dur    = median(durations)
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


def generate_html(sessions: list, tips: list, output_path: Path):
    claude_prompt = build_claude_prompt(sessions, tips)

    sessions_json = json.dumps(sessions,       ensure_ascii=False)
    tips_json     = json.dumps(tips,           ensure_ascii=False)
    prompt_json   = json.dumps(claude_prompt,  ensure_ascii=False)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>tachikoma-logs</title>
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
    .meta {{ font-size:.7rem; color:var(--muted); font-family:'JetBrains Mono','Fira Code',monospace; margin-bottom:1rem }}

    /* ── Filters ── */
    .filters {{ display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap; margin-bottom:1.25rem; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.65rem 1rem }}
    .filter-group {{ display:flex; gap:.35rem }}
    .filter-btn {{ background:transparent; color:var(--muted); border:1px solid var(--border); border-radius:5px; padding:.3rem .7rem; font-size:.72rem; font-weight:600; cursor:pointer; transition:all .15s }}
    .filter-btn:hover {{ color:var(--text); border-color:var(--accent) }}
    .filter-btn.active {{ background:var(--accent); color:#0d1117; border-color:var(--accent) }}
    .filter-sep {{ width:1px; background:var(--border); align-self:stretch }}
    .model-filters {{ display:flex; gap:.85rem; flex-wrap:wrap }}
    .model-check {{ display:flex; align-items:center; gap:.35rem; font-size:.72rem; color:var(--muted); cursor:pointer; user-select:none }}
    .model-check input {{ accent-color:var(--accent); cursor:pointer }}
    .model-check:hover {{ color:var(--text) }}

    /* ── Stats ── */
    .stats {{ display:grid; grid-template-columns:repeat(5,1fr); gap:.75rem; margin-bottom:1.25rem }}
    .stat {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.9rem 1.1rem }}
    .stat .lbl {{ font-size:.6rem; color:var(--muted); text-transform:uppercase; letter-spacing:.07em }}
    .stat .val {{ font-size:1.35rem; font-weight:700; margin-top:.2rem }}
    .stat .sub {{ font-size:.6rem; color:var(--muted); margin-top:.1rem }}

    /* ── Charts ── */
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:.85rem; margin-bottom:1.25rem }}
    .card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1.1rem }}
    .card.full {{ grid-column:1/-1 }}
    .card h2 {{ font-size:.62rem; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:.85rem }}
    canvas {{ max-height:240px }}

    /* ── Tips ── */
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

    /* ── Tables ── */
    .tables-section {{ margin-bottom:1.25rem }}
    .data-table {{ width:100%; border-collapse:collapse; font-size:.72rem }}
    .data-table th {{ text-align:left; padding:.5rem .75rem; color:var(--muted); font-size:.6rem; text-transform:uppercase; letter-spacing:.07em; border-bottom:1px solid var(--border); cursor:pointer; white-space:nowrap; user-select:none }}
    .data-table th:hover {{ color:var(--text) }}
    .data-table th.sort-asc::after  {{ content:' ↑'; color:var(--accent) }}
    .data-table th.sort-desc::after {{ content:' ↓'; color:var(--accent) }}
    .data-table td {{ padding:.45rem .75rem; border-bottom:1px solid rgba(48,54,61,.5); color:var(--text) }}
    .data-table tr:last-child td {{ border-bottom:none }}
    .data-table tr:hover td {{ background:rgba(255,255,255,.03) }}
    .model-tag {{ display:inline-block; padding:.1rem .45rem; border-radius:4px; font-size:.65rem; font-weight:600 }}
    .model-tag.opus   {{ background:rgba(188,140,255,.15); color:var(--purple) }}
    .model-tag.sonnet {{ background:rgba(88,166,255,.15);  color:var(--accent) }}
    .model-tag.haiku  {{ background:rgba(63,185,80,.15);   color:var(--green) }}
    .model-tag.mixed  {{ background:rgba(240,136,62,.15);  color:var(--orange) }}
    .empty-row {{ color:var(--muted); font-style:italic }}

    /* ── Claude prompt ── */
    .claude-section {{ margin-bottom:1.25rem }}
    .claude-card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.25rem; display:flex; align-items:center; gap:1rem }}
    .claude-desc {{ flex:1; font-size:.75rem; color:var(--muted); line-height:1.5 }}
    .claude-desc strong {{ color:var(--text) }}
    .btn-copy {{ background:var(--accent); color:#0d1117; border:none; border-radius:6px; padding:.55rem 1.1rem; font-size:.75rem; font-weight:700; cursor:pointer; white-space:nowrap; transition:opacity .15s }}
    .btn-copy:hover {{ opacity:.85 }}
    .btn-copy.copied {{ background:var(--green) }}

    @media(max-width:900px) {{ .stats{{grid-template-columns:repeat(3,1fr)}} .grid{{grid-template-columns:1fr}} }}
    @media(max-width:600px) {{ .stats{{grid-template-columns:1fr 1fr}} body{{padding:1rem}} .filters{{flex-direction:column;align-items:flex-start}} }}
  </style>
</head>
<body>
  <h1>tachikoma-logs</h1>
  <p class="meta">generado {generated_at} &middot; Chart.js 4.4 &middot; datos de ~/.claude/projects/</p>

  <div class="filters">
    <div class="filter-group">
      <button class="filter-btn" onclick="setDateFilter(7)">7d</button>
      <button class="filter-btn active" onclick="setDateFilter(30)">30d</button>
      <button class="filter-btn" onclick="setDateFilter(90)">90d</button>
      <button class="filter-btn" onclick="setDateFilter(0)">All</button>
    </div>
    <div class="filter-sep"></div>
    <div class="model-filters">
      <label class="model-check"><input type="checkbox" value="opus"   checked onchange="toggleModel('opus')">   Opus</label>
      <label class="model-check"><input type="checkbox" value="sonnet" checked onchange="toggleModel('sonnet')"> Sonnet</label>
      <label class="model-check"><input type="checkbox" value="haiku"  checked onchange="toggleModel('haiku')">  Haiku</label>
      <label class="model-check"><input type="checkbox" value="mixed"  checked onchange="toggleModel('mixed')">  Mixed</label>
    </div>
  </div>

  <div class="stats">
    <div class="stat"><div class="lbl">Sesiones</div><div class="val" id="s-sessions"></div></div>
    <div class="stat"><div class="lbl">Tokens totales</div><div class="val" id="s-tokens"></div><div class="sub">input + output</div></div>
    <div class="stat"><div class="lbl">Costo estimado</div><div class="val" id="s-cost"></div><div class="sub">USD aproximado</div></div>
    <div class="stat"><div class="lbl">Proyectos</div><div class="val" id="s-projects"></div></div>
    <div class="stat"><div class="lbl">Duracion media</div><div class="val" id="s-duration"></div><div class="sub">por sesion</div></div>
  </div>

  <div class="grid">
    <div class="card full"><h2>Tokens por dia (input / output / cache)</h2><canvas id="cTime"></canvas></div>
    <div class="card"><h2>Top proyectos (tokens)</h2><canvas id="cProj"></canvas></div>
    <div class="card"><h2>Modelo primario por sesion</h2><canvas id="cModel"></canvas></div>
    <div class="card full"><h2>Distribucion de duracion de sesiones</h2><canvas id="cDur"></canvas></div>
  </div>

  <div class="tips-section">
    <div class="section-title">Consejos de uso</div>
    <div id="tips-container"></div>
  </div>

  <div class="tables-section">
    <div class="card" style="margin-bottom:.85rem">
      <h2>Costo por modelo</h2>
      <table class="data-table" id="tModel">
        <thead><tr>
          <th onclick="sortTbl('tModel',0)">Modelo</th>
          <th onclick="sortTbl('tModel',1)">Sesiones</th>
          <th onclick="sortTbl('tModel',2)">Input (k)</th>
          <th onclick="sortTbl('tModel',3)">Output (k)</th>
          <th onclick="sortTbl('tModel',4)">Cache read (k)</th>
          <th onclick="sortTbl('tModel',5)">Cache create (k)</th>
          <th onclick="sortTbl('tModel',6)">Costo USD</th>
        </tr></thead>
        <tbody id="tModel-body"></tbody>
      </table>
    </div>
    <div class="card">
      <h2>Sesiones recientes <span id="sessions-count-label" style="font-weight:400;text-transform:none;font-size:.6rem;color:var(--muted)"></span></h2>
      <table class="data-table" id="tSessions">
        <thead><tr>
          <th onclick="sortTbl('tSessions',0)">Fecha</th>
          <th onclick="sortTbl('tSessions',1)">Proyecto</th>
          <th onclick="sortTbl('tSessions',2)">Dur.</th>
          <th onclick="sortTbl('tSessions',3)">Modelo</th>
          <th onclick="sortTbl('tSessions',4)">Tokens</th>
          <th onclick="sortTbl('tSessions',5)">Costo</th>
        </tr></thead>
        <tbody id="tSessions-body"></tbody>
      </table>
    </div>
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
const ALL_SESSIONS  = {sessions_json};
const TIPS          = {tips_json};
const CLAUDE_PROMPT = {prompt_json};

const MODEL_COLORS = {{ sonnet:'#58a6ff', opus:'#bc8cff', haiku:'#3fb950', mixed:'#f0883e' }};
const PALETTE = ['#58a6ff','#3fb950','#f0883e','#bc8cff','#f85149','#56d364','#e3b341','#d2a8ff','#ffa657','#ff7b72'];
const DUR_EDGES  = [0,5,15,30,60,120,9999];
const DUR_LABELS = ['<5 min','5-15 min','15-30 min','30-60 min','1-2 h','>2 h'];

// ── Filter state ────────────────────────────────────────────────────────────
let activeDays   = 30;
let activeModels = new Set(['opus','sonnet','haiku','mixed']);

function filterSessions() {{
  const cutoff = activeDays > 0
    ? new Date(Date.now() - activeDays * 86400 * 1000)
    : null;
  return ALL_SESSIONS.filter(s => {{
    if (cutoff && new Date(s.date + 'T00:00:00') < cutoff) return false;
    return activeModels.has(s.primary_model);
  }});
}}

function setDateFilter(days) {{
  activeDays = days;
  const vals = [7, 30, 90, 0];
  document.querySelectorAll('.filter-btn').forEach((btn, i) => {{
    btn.classList.toggle('active', vals[i] === days);
  }});
  applyFilters();
}}

function toggleModel(model) {{
  if (activeModels.has(model)) {{ activeModels.delete(model); }}
  else {{ activeModels.add(model); }}
  applyFilters();
}}

// ── Aggregation helpers ─────────────────────────────────────────────────────
function aggrByDate(sessions) {{
  const map = {{}};
  for (const s of sessions) {{
    if (!map[s.date]) map[s.date] = {{input:0,output:0,cache_read:0,cache_create:0,cost:0,sessions:0}};
    const d = map[s.date];
    d.input        += s.input_tokens;
    d.output       += s.output_tokens;
    d.cache_read   += s.cache_read;
    d.cache_create += s.cache_create;
    d.cost         += s.estimated_cost;
    d.sessions     += 1;
  }}
  const dates = Object.keys(map).sort();
  return {{dates, map}};
}}

function aggrByProject(sessions) {{
  const map = {{}};
  for (const s of sessions) {{
    if (!map[s.project]) map[s.project] = {{tokens:0,sessions:0,cost:0}};
    map[s.project].tokens   += s.total_tokens;
    map[s.project].sessions += 1;
    map[s.project].cost     += s.estimated_cost;
  }}
  return Object.entries(map).sort((a,b) => b[1].tokens - a[1].tokens).slice(0,10);
}}

function aggrByModel(sessions) {{
  const map = {{}};
  for (const s of sessions) {{
    if (!map[s.primary_model]) map[s.primary_model] = {{sessions:0,input:0,output:0,cache_read:0,cache_create:0,cost:0}};
    const m = map[s.primary_model];
    m.sessions     += 1;
    m.input        += s.input_tokens;
    m.output       += s.output_tokens;
    m.cache_read   += s.cache_read;
    m.cache_create += s.cache_create;
    m.cost         += s.estimated_cost;
  }}
  return map;
}}

function aggrDuration(sessions) {{
  const counts = new Array(DUR_LABELS.length).fill(0);
  for (const s of sessions) {{
    for (let i = 0; i < DUR_EDGES.length - 1; i++) {{
      if (s.duration_min >= DUR_EDGES[i] && s.duration_min < DUR_EDGES[i+1]) {{
        counts[i]++; break;
      }}
    }}
  }}
  return counts;
}}

// ── KPIs ────────────────────────────────────────────────────────────────────
function updateKPIs(sessions) {{
  if (!sessions.length) {{
    ['s-sessions','s-tokens','s-cost','s-projects','s-duration'].forEach(id =>
      document.getElementById(id).textContent = '—');
    return;
  }}
  const totalTokens = sessions.reduce((a,s) => a + s.total_tokens, 0);
  const totalCost   = sessions.reduce((a,s) => a + s.estimated_cost, 0);
  const projects    = new Set(sessions.map(s => s.project)).size;
  const avgDur      = sessions.reduce((a,s) => a + s.duration_min, 0) / sessions.length;
  document.getElementById('s-sessions').textContent = sessions.length.toLocaleString();
  document.getElementById('s-tokens').textContent   = (totalTokens / 1000).toFixed(0) + 'k';
  document.getElementById('s-cost').textContent     = '$' + totalCost.toFixed(2);
  document.getElementById('s-projects').textContent = projects;
  document.getElementById('s-duration').textContent = avgDur.toFixed(1) + ' min';
}}

// ── Charts ──────────────────────────────────────────────────────────────────
Chart.defaults.color       = '#7d8590';
Chart.defaults.borderColor = '#30363d';
const GRID  = {{ color: 'rgba(48,54,61,.5)' }};
const TICKS = {{ color: '#7d8590', font: {{ size:11 }} }};

const charts = {{}};

function initCharts(sessions) {{
  const {{dates, map}} = aggrByDate(sessions);
  const proj   = aggrByProject(sessions);
  const mCount = aggrByModel(sessions);
  const mKeys  = Object.keys(mCount);
  const dur    = aggrDuration(sessions);

  charts.time = new Chart(document.getElementById('cTime'), {{
    data: {{
      labels: dates,
      datasets: [
        {{ type:'bar',  label:'Input',        data:dates.map(d=>map[d].input),        backgroundColor:'rgba(88,166,255,.5)',  borderColor:'#58a6ff',borderWidth:1,borderRadius:2,stack:'t',yAxisID:'y' }},
        {{ type:'bar',  label:'Output',       data:dates.map(d=>map[d].output),       backgroundColor:'rgba(188,140,255,.5)',borderColor:'#bc8cff',borderWidth:1,borderRadius:2,stack:'t',yAxisID:'y' }},
        {{ type:'bar',  label:'Cache read',   data:dates.map(d=>map[d].cache_read),   backgroundColor:'rgba(63,185,80,.4)',  borderColor:'#3fb950',borderWidth:1,borderRadius:2,stack:'t',yAxisID:'y' }},
        {{ type:'bar',  label:'Cache create', data:dates.map(d=>map[d].cache_create), backgroundColor:'rgba(240,136,62,.4)', borderColor:'#f0883e',borderWidth:1,borderRadius:2,stack:'t',yAxisID:'y' }},
        {{ type:'line', label:'Costo USD',    data:dates.map(d=>+map[d].cost.toFixed(4)), borderColor:'#f85149',backgroundColor:'transparent',borderWidth:1.5,pointRadius:2,tension:0.3,yAxisID:'y2' }},
      ],
    }},
    options:{{
      responsive:true,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{labels:{{color:'#7d8590',font:{{size:11}},boxWidth:12}}}},
        tooltip:{{callbacks:{{afterBody:ctx => ctx[0] ? ['sesiones: '+(map[ctx[0].label]?.sessions??'')] : []}}}}
      }},
      scales:{{
        x: {{stacked:true,grid:GRID,ticks:TICKS}},
        y: {{stacked:true,grid:GRID,ticks:TICKS,title:{{display:true,text:'Tokens',color:'#7d8590',font:{{size:10}}}}}},
        y2:{{grid:{{display:false}},ticks:TICKS,position:'right',title:{{display:true,text:'USD',color:'#f85149',font:{{size:10}}}}}},
      }},
    }},
  }});

  charts.proj = new Chart(document.getElementById('cProj'), {{
    type:'doughnut',
    data:{{
      labels:proj.map(e=>e[0]),
      datasets:[{{data:proj.map(e=>e[1].tokens),backgroundColor:PALETTE,borderWidth:0}}],
    }},
    options:{{responsive:true,plugins:{{
      legend:{{position:'right',labels:{{color:'#e6edf3',font:{{size:11}},boxWidth:12}}}},
      tooltip:{{callbacks:{{afterLabel:ctx=>['sesiones: '+proj[ctx.dataIndex][1].sessions,'costo: $'+proj[ctx.dataIndex][1].cost.toFixed(2)]}}}}
    }}}},
  }});

  charts.model = new Chart(document.getElementById('cModel'), {{
    type:'doughnut',
    data:{{
      labels:mKeys,
      datasets:[{{data:mKeys.map(m=>mCount[m].sessions),backgroundColor:mKeys.map(m=>MODEL_COLORS[m]||'#7d8590'),borderWidth:0}}],
    }},
    options:{{responsive:true,plugins:{{legend:{{position:'right',labels:{{color:'#e6edf3',font:{{size:11}},boxWidth:12}}}}}}}},
  }});

  charts.dur = new Chart(document.getElementById('cDur'), {{
    type:'bar',
    data:{{labels:DUR_LABELS,datasets:[{{label:'Sesiones',data:dur,backgroundColor:'rgba(63,185,80,.45)',borderColor:'#3fb950',borderWidth:1,borderRadius:3}}]}},
    options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:GRID,ticks:TICKS}},y:{{grid:GRID,ticks:TICKS}}}}}},
  }});
}}

function updateCharts(sessions) {{
  const {{dates, map}} = aggrByDate(sessions);
  const ds = charts.time.data.datasets;
  charts.time.data.labels = dates;
  ds[0].data = dates.map(d=>map[d].input);
  ds[1].data = dates.map(d=>map[d].output);
  ds[2].data = dates.map(d=>map[d].cache_read);
  ds[3].data = dates.map(d=>map[d].cache_create);
  ds[4].data = dates.map(d=>+map[d].cost.toFixed(4));
  charts.time.options.plugins.tooltip.callbacks.afterBody =
    ctx => ctx[0] ? ['sesiones: '+(map[ctx[0].label]?.sessions??'')] : [];
  charts.time.update();

  const proj = aggrByProject(sessions);
  charts.proj.data.labels = proj.map(e=>e[0]);
  charts.proj.data.datasets[0].data = proj.map(e=>e[1].tokens);
  charts.proj.options.plugins.tooltip.callbacks.afterLabel =
    ctx => ['sesiones: '+proj[ctx.dataIndex][1].sessions,'costo: $'+proj[ctx.dataIndex][1].cost.toFixed(2)];
  charts.proj.update();

  const mCount = aggrByModel(sessions);
  const mKeys  = Object.keys(mCount);
  charts.model.data.labels = mKeys;
  charts.model.data.datasets[0].data            = mKeys.map(m=>mCount[m].sessions);
  charts.model.data.datasets[0].backgroundColor = mKeys.map(m=>MODEL_COLORS[m]||'#7d8590');
  charts.model.update();

  charts.dur.data.datasets[0].data = aggrDuration(sessions);
  charts.dur.update();
}}

// ── Tables ──────────────────────────────────────────────────────────────────
const tblData = {{}};
const sortSt  = {{}};

function renderTblBody(id, rows) {{
  const tbody = document.getElementById(id + '-body');
  tbody.replaceChildren();
  if (!rows.length) {{
    const tr = tbody.insertRow();
    const td = tr.insertCell();
    td.colSpan = 10;
    td.className = 'empty-row';
    td.textContent = 'Sin datos para el filtro seleccionado.';
    return;
  }}
  const modelCol = id === 'tSessions' ? 3 : 0;
  for (const row of rows) {{
    const tr = tbody.insertRow();
    for (let i = 0; i < row.length; i++) {{
      const td = tr.insertCell();
      if (i === modelCol && row[i] in MODEL_COLORS) {{
        const span = document.createElement('span');
        span.className = 'model-tag ' + row[i];
        span.textContent = row[i];
        td.appendChild(span);
      }} else {{
        td.textContent = row[i];
      }}
    }}
  }}
}}

function sortTbl(id, col) {{
  if (!sortSt[id]) sortSt[id] = {{col:-1,asc:true}};
  const st = sortSt[id];
  st.asc = st.col === col ? !st.asc : true;
  st.col = col;
  const rows = [...tblData[id]].sort((a,b) => {{
    const av = String(a[col]), bv = String(b[col]);
    const an = parseFloat(av.replace(/[^0-9.-]/g,'')), bn = parseFloat(bv.replace(/[^0-9.-]/g,''));
    const cmp = (!isNaN(an) && !isNaN(bn)) ? an-bn : av.localeCompare(bv);
    return st.asc ? cmp : -cmp;
  }});
  renderTblBody(id, rows);
  document.querySelectorAll('#'+id+' th').forEach((th,i) => {{
    th.classList.remove('sort-asc','sort-desc');
    if (i===col) th.classList.add(st.asc?'sort-asc':'sort-desc');
  }});
}}

function updateModelTable(sessions) {{
  const aggr = aggrByModel(sessions);
  const rows = Object.entries(aggr)
    .sort((a,b) => b[1].cost - a[1].cost)
    .map(([model,d]) => [
      model,
      d.sessions,
      (d.input/1000).toFixed(0),
      (d.output/1000).toFixed(0),
      (d.cache_read/1000).toFixed(0),
      (d.cache_create/1000).toFixed(0),
      '$'+d.cost.toFixed(2),
    ]);
  tblData['tModel'] = rows;
  renderTblBody('tModel', rows);
}}

function updateSessionsTable(sessions) {{
  const sorted = [...sessions].sort((a,b) => b.datetime.localeCompare(a.datetime));
  const label  = document.getElementById('sessions-count-label');
  label.textContent = sessions.length > 20
    ? '(mostrando 20 de '+sessions.length+')'
    : '('+sessions.length+' sesiones)';
  const rows = sorted.slice(0,20).map(s => [
    s.datetime.slice(0,16).replace('T',' '),
    s.project,
    s.duration_min.toFixed(0)+' min',
    s.primary_model,
    (s.total_tokens/1000).toFixed(0)+'k',
    '$'+s.estimated_cost.toFixed(4),
  ]);
  tblData['tSessions'] = rows;
  renderTblBody('tSessions', rows);
}}

// ── Tips ────────────────────────────────────────────────────────────────────
function renderTips() {{
  const container = document.getElementById('tips-container');
  if (!TIPS.length) {{
    const p = document.createElement('p');
    p.style.cssText = 'font-size:.75rem;color:var(--muted)';
    p.textContent = 'Sin alertas -- todo se ve bien.';
    container.appendChild(p);
    return;
  }}
  for (const t of TIPS) {{
    const wrap  = document.createElement('div');
    wrap.className = 'tip ' + t.level;
    const icon  = document.createElement('div');
    icon.className = 'tip-icon';
    icon.textContent = t.level==='warn' ? '!' : t.level==='ok' ? 'v' : 'i';
    const body  = document.createElement('div');
    const title = document.createElement('div');
    title.className  = 'tip-title';
    title.textContent = t.title;
    const desc  = document.createElement('div');
    desc.className  = 'tip-body';
    desc.textContent = t.body;
    body.appendChild(title);
    body.appendChild(desc);
    wrap.appendChild(icon);
    wrap.appendChild(body);
    container.appendChild(wrap);
  }}
}}

// ── Apply filters ───────────────────────────────────────────────────────────
function applyFilters() {{
  const f = filterSessions();
  updateKPIs(f);
  updateCharts(f);
  updateModelTable(f);
  updateSessionsTable(f);
}}

// ── Claude prompt copy ──────────────────────────────────────────────────────
function copyClaudePrompt() {{
  const btn   = document.getElementById('btn-copy');
  const reset = () => {{ btn.textContent='Copiar prompt para Claude'; btn.classList.remove('copied'); }};
  const done  = () => {{ btn.textContent='Copiado!'; btn.classList.add('copied'); setTimeout(reset,2500); }};
  if (navigator.clipboard?.writeText) {{
    navigator.clipboard.writeText(CLAUDE_PROMPT).then(done).catch(fallback);
  }} else {{ fallback(); }}
  function fallback() {{
    const ta = document.createElement('textarea');
    ta.value = CLAUDE_PROMPT;
    ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try {{ document.execCommand('copy'); done(); }} catch(_) {{}}
    document.body.removeChild(ta);
  }}
}}

// ── Init ────────────────────────────────────────────────────────────────────
const initial = filterSessions();
initCharts(initial);
updateKPIs(initial);
updateModelTable(initial);
updateSessionsTable(initial);
renderTips();
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"  -> {output_path}")
