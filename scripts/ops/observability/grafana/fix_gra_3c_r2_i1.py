"""GRA-3C-20260805-r2 I1: percentage align right + helpers for residual check."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"


def walk(panels: list | None):
    for panel in panels or []:
        if panel.get("type") == "row":
            yield from walk(panel.get("panels"))
            continue
        yield panel
        yield from walk(panel.get("panels"))


def fix_percentage_align() -> list[dict]:
    changed: list[dict] = []
    for path in sorted(DASH.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        dirty = False
        for panel in walk(data.get("panels")):
            title = str(panel.get("title") or "")
            if "Processed Records" not in title:
                continue
            for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
                if override.get("matcher", {}).get("options") != "percentage":
                    continue
                for prop in override.get("properties") or []:
                    if prop.get("id") == "custom.align" and prop.get("value") != "right":
                        old = prop.get("value")
                        prop["value"] = "right"
                        dirty = True
                        changed.append(
                            {
                                "file": path.name,
                                "panel_id": panel.get("id"),
                                "title": title,
                                "old": old,
                                "new": "right",
                            }
                        )
        if dirty:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    return changed


def main() -> None:
    changed = fix_percentage_align()
    print("changed", len(changed))
    for item in changed:
        print(item)


if __name__ == "__main__":
    main()
