import json
from datetime import datetime
from pathlib import Path

_TEMPLATE = Path(__file__).parent / "templates" / "dashboard.html"


def generate_html(sessions: list[dict], output_path: Path) -> None:
    html = _TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__SESSIONS_JSON__", json.dumps(sessions, ensure_ascii=False))
    html = html.replace("__GENERATED_AT__",  datetime.now().strftime("%Y-%m-%d %H:%M"))

    output_path.write_text(html, encoding="utf-8")
    print(f"  -> {output_path}")
