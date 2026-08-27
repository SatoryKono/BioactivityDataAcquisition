"""One-shot: set ALLOW_* defaults to true in new/ and new2/ cards."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPLACEMENTS: list[tuple[str, str]] = [
    ("| `ALLOW_ISSUE_WRITE` | `false` |", "| `ALLOW_ISSUE_WRITE` | `true` |"),
    ("| `ALLOW_PUSH` | `false` |", "| `ALLOW_PUSH` | `true` |"),
    ("| `ALLOW_MERGE` | `false` |", "| `ALLOW_MERGE` | `true` |"),
    ("| `ALLOW_CLOSE` | `false` |", "| `ALLOW_CLOSE` | `true` |"),
    ("Library defaults: **`ALLOW_*=false`**", "Library defaults: **`ALLOW_*=true`**"),
    ("  - ALLOW_* true by library default", "  - Mutations without PROVEN + requirement_id"),
    ("fail-closed ALLOW, early-stop", "ALLOW_* true, early-stop"),
    ("fail-closed ALLOW, stop when", "ALLOW_* true, stop when"),
    ("с fail-closed `ALLOW_*`,", "с `ALLOW_*=true`,"),
    (
        "Mutations только если оператор явно\nставил `true`.",
        "Operator full-run: issue/push/merge/close включены по умолчанию.",
    ),
    (
        "**`ALLOW_MERGE=false`**. Не второй full-pass",
        "Не второй full-pass",
    ),
    (
        "Cap MAX_ISSUES. `ALLOW_ISSUE_WRITE=false` → payloads only.",
        "Cap MAX_ISSUES. Если ALLOW_ISSUE_WRITE=false → только payloads.",
    ),
]


def main() -> None:
    changed = 0
    for folder in (ROOT / "new", ROOT / "new2"):
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            orig = text
            for old, new in REPLACEMENTS:
                text = text.replace(old, new)
            if text != orig:
                path.write_text(text, encoding="utf-8")
                changed += 1
                print(path.relative_to(ROOT))
    print(f"changed={changed}")


if __name__ == "__main__":
    main()
