import json
import pathlib
from pathlib import Path

from log_parser import calc_cost, get_tier, parse_sessions


def test_get_tier_opus():
    assert get_tier("claude-opus-4-7") == "opus"


def test_get_tier_haiku():
    assert get_tier("claude-haiku-4-5") == "haiku"


def test_get_tier_sonnet():
    assert get_tier("claude-sonnet-4-6") == "sonnet"


def test_get_tier_default_for_unknown():
    assert get_tier("unknown-model") == "sonnet"


def test_get_tier_default_for_empty():
    assert get_tier("") == "sonnet"


def test_calc_cost_zero_usage():
    assert calc_cost({}, "sonnet") == 0.0


def test_calc_cost_output_tokens_sonnet():
    # sonnet output: $15 per 1M tokens
    assert calc_cost({"output_tokens": 1_000_000}, "sonnet") == 15.0


def test_calc_cost_input_tokens_opus():
    # opus input: $15 per 1M tokens
    assert calc_cost({"input_tokens": 1_000_000}, "opus") == 15.0


def test_calc_cost_cache_read_opus():
    # opus cache_read: $1.50 per 1M tokens
    assert calc_cost({"cache_read_input_tokens": 1_000_000}, "opus") == 1.50


def test_calc_cost_all_components_sonnet():
    # sonnet: input $3, output $15, cache_read $0.30, cache_create $3.75 per 1M
    usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "cache_read_input_tokens": 1_000_000,
        "cache_creation_input_tokens": 1_000_000,
    }
    assert calc_cost(usage, "sonnet") == 3.0 + 15.0 + 0.30 + 3.75


# ── parse_sessions new fields ──────────────────────────────────────────────────

def _make_jsonl(entries: list[dict]) -> str:
    return "\n".join(json.dumps(e) for e in entries)


def _write_session(projects_dir: Path, session_id: str, entries: list[dict]) -> None:
    proj_dir = projects_dir / "test-project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / f"{session_id}.jsonl").write_text(_make_jsonl(entries), encoding="utf-8")


def _base_assistant(msg_id: str = "msg_001", stop_reason: str = "end_turn", tools: list[str] | None = None) -> dict:
    content = [{"type": "tool_use", "name": t} for t in (tools or [])]
    return {
        "type": "assistant",
        "timestamp": "2026-01-01T10:00:00Z",
        "cwd": "/home/user/test-project",
        "entrypoint": "cli",
        "permissionMode": "default",
        "message": {
            "id": msg_id,
            "model": "claude-sonnet-4-6",
            "stop_reason": stop_reason,
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "content": content,
        },
    }


def test_parse_sessions_extracts_entrypoint(monkeypatch, tmp_path):
    projects_dir = tmp_path / ".claude" / "projects"
    _write_session(projects_dir, "sess1", [_base_assistant()])
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    sessions = parse_sessions()
    assert sessions[0]["entrypoint"] == "cli"


def test_parse_sessions_extracts_permission_mode(monkeypatch, tmp_path):
    projects_dir = tmp_path / ".claude" / "projects"
    _write_session(projects_dir, "sess1", [_base_assistant()])
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    sessions = parse_sessions()
    assert sessions[0]["permission_mode"] == "default"


def test_parse_sessions_extracts_stop_reason(monkeypatch, tmp_path):
    projects_dir = tmp_path / ".claude" / "projects"
    _write_session(projects_dir, "sess1", [_base_assistant(msg_id="msg_002", stop_reason="max_tokens")])
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    sessions = parse_sessions()
    assert sessions[0]["stop_reason"] == "max_tokens"


def test_parse_sessions_excludes_tool_use_from_stop_reason(monkeypatch, tmp_path):
    projects_dir = tmp_path / ".claude" / "projects"
    entries = [
        _base_assistant(msg_id="msg_003", stop_reason="tool_use"),
        {
            "type": "assistant",
            "timestamp": "2026-01-01T10:01:00Z",
            "message": {
                "id": "msg_004",
                "model": "claude-sonnet-4-6",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 50, "output_tokens": 30},
                "content": [],
            },
        },
    ]
    _write_session(projects_dir, "sess1", entries)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    sessions = parse_sessions()
    assert sessions[0]["stop_reason"] == "end_turn"


def test_parse_sessions_extracts_tools(monkeypatch, tmp_path):
    projects_dir = tmp_path / ".claude" / "projects"
    _write_session(projects_dir, "sess1", [_base_assistant(msg_id="msg_005", tools=["Read", "Read", "Edit"])])
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    sessions = parse_sessions()
    assert sessions[0]["tools"] == {"Read": 2, "Edit": 1}
