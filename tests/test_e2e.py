"""
End-to-end tests using Playwright.

Catches JS runtime errors that unit tests cannot see: undefined functions,
broken chart APIs, sortTbl crashes, filter/toggle regressions.

Run locally (first time only):
    pip install pytest-playwright
    playwright install chromium

Then:
    python generate.py
    python -m pytest tests/test_e2e.py -v
"""
import json
import pathlib
import shutil
import subprocess

import pytest

HTML_PATH = pathlib.Path("docs/usage.html")
_MOCK_DIR = pathlib.Path.home() / ".claude" / "projects" / "_e2e-mock"

# ── Mock session data for CI environments without real Claude logs ─────────────

_MOCK_SESSIONS = [
    {
        "type": "assistant",
        "timestamp": f"2026-01-{day:02d}T{hour:02d}:00:00Z",
        "cwd": f"/home/user/{proj}",
        "entrypoint": entrypoint,
        "permissionMode": perm,
        "message": {
            "id": f"msg_{i:03d}",
            "model": model,
            "stop_reason": stop,
            "usage": {
                "input_tokens": 1200,
                "output_tokens": 600,
                "cache_read_input_tokens": 300,
                "cache_creation_input_tokens": 100,
            },
            "content": [{"type": "tool_use", "name": tool, "input": {}}],
        },
    }
    for i, (day, hour, proj, model, tool, entrypoint, perm, stop) in enumerate(
        [
            (1,  10, "project-a", "claude-sonnet-4-6", "Read",      "cli", "default",             "end_turn"),
            (1,  14, "project-a", "claude-sonnet-4-6", "Edit",      "cli", "default",             "end_turn"),
            (2,   9, "project-b", "claude-opus-4-7",   "Bash",      "cli", "bypassPermissions",   "end_turn"),
            (2,  15, "project-a", "claude-sonnet-4-6", "WebSearch", "ide", "default",             "end_turn"),
            (3,  11, "project-b", "claude-sonnet-4-6", "Read",      "cli", "default",             "max_tokens"),
            (3,  16, "project-c", "claude-haiku-4-5",  "Read",      "cli", "default",             "end_turn"),
            (4,  10, "project-a", "claude-opus-4-7",   "Edit",      "ide", "default",             "end_turn"),
            (4,  13, "project-b", "claude-sonnet-4-6", "Bash",      "cli", "bypassPermissions",   "end_turn"),
            (5,  10, "project-c", "claude-sonnet-4-6", "Glob",      "cli", "default",             "end_turn"),
            (5,  14, "project-a", "claude-haiku-4-5",  "Read",      "cli", "default",             "end_turn"),
            (6,   9, "project-b", "claude-sonnet-4-6", "Edit",      "cli", "default",             "end_turn"),
            (6,  12, "project-a", "claude-opus-4-7",   "Bash",      "ide", "bypassPermissions",   "end_turn"),
            (7,  10, "project-c", "claude-sonnet-4-6", "Read",      "cli", "default",             "end_turn"),
            (7,  15, "project-a", "claude-sonnet-4-6", "Edit",      "cli", "default",             "end_turn"),
            (8,  11, "project-b", "claude-sonnet-4-6", "WebFetch",  "cli", "default",             "end_turn"),
            (8,  14, "project-c", "claude-haiku-4-5",  "Read",      "ide", "default",             "end_turn"),
            (9,  10, "project-a", "claude-sonnet-4-6", "Bash",      "cli", "default",             "end_turn"),
            (9,  16, "project-b", "claude-opus-4-7",   "Edit",      "cli", "bypassPermissions",   "end_turn"),
            (10, 10, "project-a", "claude-sonnet-4-6", "Read",      "cli", "default",             "end_turn"),
            (10, 14, "project-c", "claude-sonnet-4-6", "Grep",      "cli", "default",             "end_turn"),
        ]
    )
]


@pytest.fixture(scope="session", autouse=True)
def generate_dashboard():
    projects_root = pathlib.Path.home() / ".claude" / "projects"
    created_mock = False

    if not projects_root.exists() or not any(projects_root.rglob("*.jsonl")):
        _MOCK_DIR.mkdir(parents=True, exist_ok=True)
        (_MOCK_DIR / "session.jsonl").write_text(
            "\n".join(json.dumps(s) for s in _MOCK_SESSIONS),
            encoding="utf-8",
        )
        created_mock = True

    subprocess.run(["python", "generate.py"], check=True)

    yield

    if created_mock:
        shutil.rmtree(_MOCK_DIR, ignore_errors=True)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def dash(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(HTML_PATH.resolve().as_uri(), timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    yield page, errors


def no_errors(errors):
    assert not errors, "JS errors:\n" + "\n".join(errors)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_no_js_errors_on_load(dash):
    _, errors = dash
    no_errors(errors)


def test_all_canvases_render(dash):
    page, errors = dash
    assert page.locator("canvas").count() >= 9
    no_errors(errors)


def test_date_filters(dash):
    page, errors = dash
    for days in ["7", "90", "0", "30"]:
        page.locator(f'button[data-days="{days}"]').click()
    no_errors(errors)


def test_model_checkboxes(dash):
    page, errors = dash
    page.locator('input[value="opus"]').click()
    page.locator('input[value="opus"]').click()
    no_errors(errors)


def test_sort_proj_table(dash):
    page, errors = dash
    for n in range(1, 7):
        page.locator(f"#tProj th:nth-child({n})").click()
    no_errors(errors)


def test_sort_skills_table(dash):
    page, errors = dash
    for n in range(1, 6):
        page.locator(f"#tSkills th:nth-child({n})").click()
    no_errors(errors)


def test_sort_skills_last_used_changes_order(dash):
    page, errors = dash
    # Click Last Used (col 5) twice — rows must flip order if >1 distinct value
    col = page.locator("#tSkills th:nth-child(5)")
    rows = page.locator("#tSkills-body tr")
    if rows.count() < 2:
        pytest.skip("not enough rows to verify sort order")
    col.click()
    first_asc = page.locator("#tSkills-body tr:first-child td:last-child").inner_text()
    col.click()
    first_desc = page.locator("#tSkills-body tr:first-child td:last-child").inner_text()
    assert first_asc != first_desc, "Last Used sort did not change order"
    no_errors(errors)


def test_sort_model_table(dash):
    page, errors = dash
    page.locator("#tModel th").first.click()
    no_errors(errors)


def test_language_toggle(dash):
    page, errors = dash
    page.locator("#btn-lang").click()
    page.locator("#btn-lang").click()
    no_errors(errors)


def test_theme_toggle(dash):
    page, errors = dash
    page.locator("#btn-theme").click()
    page.locator("#btn-theme").click()
    no_errors(errors)


def test_show_all_sessions(dash):
    page, errors = dash
    btn = page.locator("#btn-show-all")
    if btn.is_visible():
        btn.click()
    no_errors(errors)
