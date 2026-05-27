import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PRICES = {
    "opus":   {"input": 15.0,  "output": 75.0,  "cache_read": 1.50,  "cache_create": 18.75},
    "sonnet": {"input": 3.0,   "output": 15.0,  "cache_read": 0.30,  "cache_create": 3.75},
    "haiku":  {"input": 0.80,  "output": 4.0,   "cache_read": 0.08,  "cache_create": 1.0},
}


def get_tier(model: str) -> str:
    m = model.lower()
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    return "sonnet"


def calc_cost(usage: dict[str, int], tier: str) -> float:
    p = PRICES.get(tier, PRICES["sonnet"])
    return (
        usage.get("input_tokens", 0)                * p["input"]        / 1e6 +
        usage.get("output_tokens", 0)               * p["output"]       / 1e6 +
        usage.get("cache_read_input_tokens", 0)     * p["cache_read"]   / 1e6 +
        usage.get("cache_creation_input_tokens", 0) * p["cache_create"] / 1e6
    )


def parse_sessions() -> list[dict]:
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

        cwd = ""
        entrypoint = "unknown"
        perm_counter: Counter = Counter()
        for e in entries:
            if not cwd and e.get("cwd"):
                cwd = e["cwd"]
            if entrypoint == "unknown" and e.get("entrypoint"):
                entrypoint = e["entrypoint"]
            if e.get("permissionMode"):
                perm_counter[e["permissionMode"]] += 1

        project = Path(cwd.replace("\\", "/")).name if cwd else "unknown"
        permission_mode = perm_counter.most_common(1)[0][0] if perm_counter else "unknown"

        seen_msg_ids: set = set()
        total = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
        models_used: set = set()
        timestamps = []
        estimated_cost = 0.0
        stop_reason_counter: Counter = Counter()
        tool_counter: Counter = Counter()

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

            sr = msg.get("stop_reason")
            if sr and sr != "tool_use":
                stop_reason_counter[sr] += 1

            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_counter[block.get("name", "unknown")] += 1

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

        stop_reason = stop_reason_counter.most_common(1)[0][0] if stop_reason_counter else "end_turn"

        sessions[session_id] = {
            "session_id":      session_id,
            "project":         project,
            "date":            t0.strftime("%Y-%m-%d"),
            "datetime":        t0.isoformat(),
            "duration_min":    duration_min,
            "input_tokens":    total["input"],
            "output_tokens":   total["output"],
            "cache_read":      total["cache_read"],
            "cache_create":    total["cache_create"],
            "total_tokens":    total["input"] + total["output"],
            "primary_model":   primary,
            "estimated_cost":  round(estimated_cost, 4),
            "entrypoint":      entrypoint,
            "permission_mode": permission_mode,
            "stop_reason":     stop_reason,
            "tools":           dict(tool_counter),
        }

    result = sorted(sessions.values(), key=lambda s: s["datetime"])
    print(f"Parsed {len(result)} sessions across {len({s['project'] for s in result})} projects")
    return result
