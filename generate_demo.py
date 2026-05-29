#!/usr/bin/env python3
"""Generate a demo dashboard with obfuscated synthetic data.

Usage:
    python generate_demo.py [--output docs/demo.html]

Produces a realistic-looking dashboard without real project names,
paths, or cost figures. Useful for README screenshots and demos.
"""

import argparse
import random
from datetime import datetime, timezone
from pathlib import Path

from html_builder import generate_html

# ── Reproducible seed ─────────────────────────────────────────────────────────
random.seed(42)

# ── Demo configuration ────────────────────────────────────────────────────────
PROJECTS = ["web-app", "api-service", "data-pipeline", "infra-scripts", "research"]
MODELS = (
    ["claude-sonnet-4-6"] * 55
    + ["claude-opus-4-7"] * 20
    + ["claude-haiku-4-5"] * 18
    + ["claude-sonnet-4-6-claude-opus-4-7"] * 7  # mixed
)
ENTRYPOINTS = ["cli"] * 70 + ["ide"] * 28 + ["unknown"] * 2
PERMS = ["default"] * 78 + ["bypassPermissions"] * 22
STOP_REASONS = ["end_turn"] * 82 + ["max_tokens"] * 12 + ["end_turn"] * 6

TOOL_PROFILES = {
    "coding":      {"Read": 8, "Edit": 6, "Write": 2, "Glob": 3, "Grep": 4, "Bash": 2},
    "exploration": {"Read": 12, "Glob": 5, "Grep": 7, "LS": 3, "Bash": 1},
    "automation":  {"Bash": 10, "Read": 3, "Glob": 2, "Write": 1},
    "research":    {"WebSearch": 5, "WebFetch": 3, "Read": 4, "Bash": 1},
    "conversation":{},
}
SKILL_AGENTS = [
    ("skill/verify", 0.12),
    ("skill/code-review", 0.08),
    ("agent/feature-dev:code-reviewer", 0.06),
    ("agent/general-purpose", 0.05),
    ("skill/frontend-design:frontend-design", 0.04),
]


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _make_session(idx: int, base_date: datetime) -> dict:
    rng = random.Random(idx)
    project = rng.choice(PROJECTS)
    model = rng.choice(MODELS)
    primary = (
        "mixed" if "-claude-" in model
        else "opus" if "opus" in model
        else "haiku" if "haiku" in model
        else "sonnet"
    )

    day_offset = rng.randint(0, 59)
    hour = rng.randint(7, 22)
    from datetime import timedelta
    session_dt = base_date + timedelta(days=day_offset, hours=hour, minutes=rng.randint(0, 59))

    duration = rng.choice([
        rng.uniform(1, 4),    # short
        rng.uniform(5, 20),   # medium
        rng.uniform(20, 60),  # long
        rng.uniform(60, 150), # very long
    ][:rng.randint(1, 4)])

    profile_key = rng.choices(
        list(TOOL_PROFILES.keys()),
        weights=[35, 20, 15, 15, 15],
    )[0]
    tools: dict[str, int] = {}
    for tool, base_count in TOOL_PROFILES[profile_key].items():
        count = max(1, int(rng.gauss(base_count, base_count * 0.3)))
        tools[tool] = count
    for skill, prob in SKILL_AGENTS:
        if rng.random() < prob:
            tools[skill] = rng.randint(1, 4)

    input_t = int(rng.gauss(8_000, 4_000))
    output_t = int(rng.gauss(2_500, 1_200))
    cache_r = int(input_t * rng.uniform(0.1, 0.6))
    cache_c = int(input_t * rng.uniform(0.05, 0.25))
    input_t = max(500, input_t)
    output_t = max(100, output_t)

    prices = {"sonnet": (3.0, 15.0, 0.30, 3.75),
              "opus":   (15.0, 75.0, 1.50, 18.75),
              "haiku":  (0.80, 4.0, 0.08, 1.0),
              "mixed":  (3.0, 15.0, 0.30, 3.75)}
    pi, po, pr, pc = prices[primary]
    cost = (input_t * pi + output_t * po + cache_r * pr + cache_c * pc) / 1e6

    return {
        "session_id":      f"demo-{idx:04d}",
        "project":         project,
        "date":            session_dt.strftime("%Y-%m-%d"),
        "datetime":        _iso(session_dt),
        "duration_min":    round(duration, 1),
        "input_tokens":    input_t,
        "output_tokens":   output_t,
        "cache_read":      cache_r,
        "cache_create":    cache_c,
        "total_tokens":    input_t + output_t,
        "primary_model":   primary,
        "estimated_cost":  round(cost, 4),
        "entrypoint":      rng.choice(ENTRYPOINTS),
        "permission_mode": rng.choice(PERMS),
        "stop_reason":     rng.choice(STOP_REASONS),
        "tools":           tools,
        "message_count":   rng.randint(3, 40),
    }


def build_demo_sessions(n: int = 90) -> list[dict]:
    from datetime import timedelta
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    sessions = [_make_session(i, base + timedelta(days=i % 60)) for i in range(n)]
    return sorted(sessions, key=lambda s: s["datetime"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate demo dashboard with synthetic data")
    ap.add_argument("--output", default="docs/demo.html")
    ap.add_argument("--sessions", type=int, default=90)
    args = ap.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    sessions = build_demo_sessions(args.sessions)
    generate_html(sessions, out)
    print(f"Demo dashboard: {out.resolve()}")
    print(f"  {len(sessions)} sessions · {len({s['project'] for s in sessions})} projects")
