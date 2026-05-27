from tips import compute_tips


def make_session(**kwargs):
    base = {
        "session_id":      "test",
        "project":         "proj",
        "date":            "2026-01-01",
        "datetime":        "2026-01-01T00:00:00",
        "duration_min":    20.0,
        "input_tokens":    10_000,
        "output_tokens":   3_000,
        "cache_read":      2_000,
        "cache_create":    0,
        "total_tokens":    13_000,
        "primary_model":   "sonnet",
        "estimated_cost":  0.05,
        "entrypoint":      "cli",
        "permission_mode": "default",
        "stop_reason":     "end_turn",
        "tools":           {},
        "message_count":   10,
    }
    base.update(kwargs)
    return base


def tip_titles(sessions):
    return [t["title_es"] for t in compute_tips(sessions)]


def test_empty_sessions_returns_no_tips():
    assert compute_tips([]) == []


def test_low_cache_rate_produces_warn():
    sessions = [make_session(input_tokens=10_000, cache_read=0, cache_create=0)]
    titles = tip_titles(sessions)
    assert "Baja tasa de cache" in titles


def test_high_cache_rate_produces_ok():
    sessions = [make_session(input_tokens=500, cache_read=5_000, cache_create=0)]
    levels = {t["title_es"]: t["level"] for t in compute_tips(sessions)}
    assert levels.get("Buena tasa de cache") == "ok"


def test_high_opus_proportion_produces_warn():
    sessions = [
        make_session(primary_model="opus",   estimated_cost=1.0),
        make_session(primary_model="opus",   estimated_cost=1.0),
        make_session(primary_model="sonnet", estimated_cost=0.05),
        make_session(primary_model="sonnet", estimated_cost=0.05),
    ]
    assert "Alto uso de Opus" in tip_titles(sessions)


def test_many_short_sessions_produces_info():
    sessions = [
        make_session(duration_min=1.0),
        make_session(duration_min=2.0),
        make_session(duration_min=2.5),
        make_session(duration_min=20.0),
    ]
    assert "Muchas sesiones muy cortas" in tip_titles(sessions)


def test_high_output_ratio_produces_info():
    sessions = [make_session(input_tokens=10_000, output_tokens=9_000, cache_read=0)]
    assert "Relacion output/input alta" in tip_titles(sessions)


def test_tips_have_english_translations():
    sessions = [make_session(input_tokens=10_000, cache_read=0, cache_create=0)]
    tips = compute_tips(sessions)
    assert all("title_en" in t and "body_en" in t for t in tips)


def test_max_tokens_rate_produces_warn():
    sessions = [
        make_session(stop_reason="max_tokens"),
        make_session(stop_reason="max_tokens"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
        make_session(stop_reason="end_turn"),
    ]
    assert "Sesiones que alcanzan el limite de contexto" in tip_titles(sessions)


def test_low_max_tokens_rate_no_warn():
    sessions = [make_session(stop_reason="end_turn") for _ in range(20)]
    assert "Sesiones que alcanzan el limite de contexto" not in tip_titles(sessions)
