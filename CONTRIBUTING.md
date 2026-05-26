# Contributing

## Prerequisites

- Python 3.9+
- No external runtime dependencies (stdlib only)

## Local setup

```bash
git clone https://github.com/alexcalleja/tachikoma-logs
cd tachikoma-logs
pip install pytest pytest-cov ruff   # dev dependencies only
python generate.py                    # generates docs/usage.html
```

Open `docs/usage.html` in your browser to verify the output.

## Git workflow

```
develop → feature/<description> → PR → develop → PR → master
```

- Base branch is always `develop` — branch off it before starting any work
- Use `feature/<description>` for new features; small changes can go directly on `develop`
- PRs always target `develop`, never `master` directly
- `master` is protected: CI must pass before merging

## Commit conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Refactor without behavior change |
| `test:` | Adding or fixing tests |
| `chore:` | Maintenance (deps, config) |

## Before opening a PR

```bash
ruff check .        # lint — must pass
python -m pytest -v # tests — must pass
```

CI runs both automatically on every push and PR. A red CI blocks merging to `master`.

## Adding new tips

Tips live in `tips.py`. Each tip must include both languages:

```python
tips.append({
    "level":    "warn",          # "warn" | "info" | "ok"
    "title_es": "...",
    "body_es":  "...",
    "title_en": "...",
    "body_en":  "...",
})
```

Add a corresponding test in `tests/test_tips.py`.

## Updating prices

Prices are hardcoded in `log_parser.py` (`PRICES` dict). Check
[Anthropic's pricing page](https://www.anthropic.com/pricing) and update
at the start of each version if rates have changed.
