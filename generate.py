#!/usr/bin/env python3
"""tachikoma-logs — Claude Code usage dashboard generator.

Usage:
    python generate.py [--output docs/usage.html]

Outputs a self-contained HTML file with:
  - 4 Chart.js charts (dark theme, no pip required)
  - Rule-based usage tips
  - "Copy prompt for Claude" button for deeper AI analysis
"""

import argparse
from pathlib import Path

from html_builder import generate_html
from log_parser import parse_sessions
from tips import compute_tips

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="tachikoma-logs — generate Claude Code usage dashboard")
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
