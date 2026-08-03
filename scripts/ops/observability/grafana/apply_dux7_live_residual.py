#!/usr/bin/env python3
"""DUX7 live residual: Copy affordance on ID panels + docs anchors.

Does not invent metrics or change L0 status tokens.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
DOCS = ROOT / "docs" / "03-guides" / "dashboards"

COPY_LINK = {
    "title": "Copy/Open full value (plain text)",
    "url": "data:text/plain,${__value.raw}",
    "targetBlank": True,
    "includeVars": False,
}


def walk(panels: list | None):
    for panel in panels or []:
        yield panel
        yield from walk(panel.get("panels"))


def ensure_value_copy_link(panel: dict[str, Any]) -> bool:
    """Attach data:text/plain link on identity value fields."""
    if panel.get("type") not in {"table", "table-old"}:
        return False
    title = panel.get("title") or ""
    pid = panel.get("id")
    is_id = title == "ID" or pid in {9402, 9300}
    is_copyable = "Copyable" in title or pid == 9407
    if not (is_id or is_copyable):
        return False

    fc = dict(panel.get("fieldConfig") or {})
    defaults = dict(fc.get("defaults") or {})
    overrides = list(fc.get("overrides") or [])
    changed = False

    # Prefer field-level link on value / copy_value columns
    target_fields = ("value", "copy_value", "Value", "run_id", "manifest_id")
    for field in target_fields:
        found = False
        for ov in overrides:
            matcher = ov.get("matcher") or {}
            if matcher.get("id") == "byName" and matcher.get("options") == field:
                found = True
                props = list(ov.get("properties") or [])
                has_link = any(p.get("id") == "links" for p in props)
                if not has_link:
                    props.append({"id": "links", "value": [COPY_LINK]})
                    ov["properties"] = props
                    changed = True
        if not found and field in {"value", "copy_value"}:
            # only add override if field likely exists
            if is_copyable or field == "value":
                overrides.append(
                    {
                        "matcher": {"id": "byName", "options": field},
                        "properties": [{"id": "links", "value": [COPY_LINK]}],
                    }
                )
                changed = True

    # Keep a defaults.links fallback for inspect menus
    links = list(defaults.get("links") or [])
    if not any("data:text/plain" in str(x.get("url", "")) for x in links):
        # Keep existing health links; append copy first for operator visibility
        links = [COPY_LINK, *links]
        defaults["links"] = links
        changed = True

    if changed:
        fc["defaults"] = defaults
        fc["overrides"] = overrides
        panel["fieldConfig"] = fc
        desc = panel.get("description") or ""
        marker = "DUX7: Copy/Open full identity value via data:text/plain link"
        if marker not in desc:
            panel["description"] = f"{marker}. {desc}".strip()
    return changed


def apply_boards() -> list[str]:
    changes: list[str] = []
    for path in sorted(DASH.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        board_changes = 0
        for panel in walk(data.get("panels")):
            if ensure_value_copy_link(panel):
                board_changes += 1
                changes.append(f"{path.name}:{panel.get('id')}:{panel.get('title')}")
        if board_changes:
            text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(text.encode("utf-8"))
            os.replace(tmp, path)
            print(f"{path.name}: {board_changes} copy-link panels")
    return changes


def write_docs() -> None:
    path = DOCS / "dux7-live-residual-protocol.md"
    path.write_text(
        """# DUX7 live residual protocol (a11y / contrast / theme / copy / screenshots)

**Status:** active
**Wave:** DUX7
**Predecessor residual:** DUX6 live-only items in `dux6-residual-readability.md`

## Scope

1. WCAG 2.2 AA contrast on real Grafana theme tokens (dark required; light measured or unsupported)
2. Keyboard/focus walkthrough for nav bus (`aria-current`, tab order, focus visible)
3. Light theme parity **or** explicit unsupported decision with evidence
4. Native Copy/Open for Run/Manifest identity values (data links on ID tables)
5. Live screenshot matrix SG-01..SG-07 at 1366×768, 1440×900, 1920×1080 (100%; 125% when feasible)

## Tooling

```bash
# auth from runtime env (GRAFANA_PASSWORD / token)
python -m scripts.ops check-grafana-audit-preflight --json --skip-screenshot-check

# copy affordance apply
python scripts/ops/observability/grafana/apply_dux7_live_residual.py

# live residual runner (contrast + a11y + screenshots)
python scripts/ops/observability/grafana/run_dux7_live_residual.py --output-dir reports/quality/dux7-live-evidence
```

## Acceptance

- Evidence JSON/markdown under `reports/quality/dux7-live-evidence/`
- Dark theme contrast report for nav chips + status colors
- Keyboard/nav focus notes with pass/fail
- Light theme: measured OR documented unsupported
- ID panels expose `data:text/plain` Copy/Open link
- Screenshot matrix covers 7 UIDs × target viewports (or explicit blocker)

## Constraints

- No invent metrics; no Prom `run_id` labels
- Do not edit `.env` files without explicit approval
- Grafana remains interface adapter for verdict semantics
""",
        encoding="utf-8",
        newline="\n",
    )
    residual = DOCS / "dux6-residual-readability.md"
    text = residual.read_text(encoding="utf-8")
    if "dux7-live-residual-protocol.md" not in text:
        residual.write_text(
            text.rstrip() + "\n\n## DUX7 live residual\n\n"
            "Live residual closeout protocol: "
            "[dux7-live-residual-protocol.md](dux7-live-residual-protocol.md).\n",
            encoding="utf-8",
            newline="\n",
        )


def main() -> int:
    ch = apply_boards()
    write_docs()
    print(f"copy_link_changes={len(ch)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
