from collections import defaultdict

DUR_EDGES  = [0, 5, 15, 30, 60, 120, 9999]
DUR_LABELS = ["<5 min", "5-15 min", "15-30 min", "30-60 min", "1-2 h", ">2 h"]


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
