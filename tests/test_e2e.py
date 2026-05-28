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
import pathlib
import subprocess
import pytest

HTML_PATH = pathlib.Path("docs/usage.html")


@pytest.fixture(scope="session", autouse=True)
def generate_dashboard():
    subprocess.run(["python", "generate.py"], check=True)


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


def test_no_js_errors_on_load(dash):
    _, errors = dash
    no_errors(errors)


def test_all_canvases_render(dash):
    page, errors = dash
    # cTime, cLine, cProj, cModel, cDur, cEntrypoint, cPerm,
    # cStopReason, cCategory, cTools, cCatProj
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
