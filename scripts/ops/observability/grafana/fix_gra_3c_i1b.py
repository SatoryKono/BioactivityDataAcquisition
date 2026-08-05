"""Follow-up I1 fixes: workflow counters vector(0), processed-records value align."""

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


def fix_runtime() -> None:
    path = DASH / "bioetl-runtime.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    titles = {
        "Track Failed Workflow Runs",
        "Track Failed Workflow Steps",
        "Monitor Pipeline Alert Conditions",
    }
    for panel in walk(data.get("panels")):
        title = str(panel.get("title") or "")
        if panel.get("id") not in (9996, 9997, 230) and title not in titles:
            continue
        for target in panel.get("targets") or []:
            expr = target.get("expr") or ""
            if not expr or "or vector(0)" in expr:
                continue
            if expr.startswith("round(") and expr.endswith(")"):
                inner = expr[len("round(") : -1]
                target["expr"] = f"round(({inner}) or vector(0))"
            else:
                target["expr"] = f"({expr}) or vector(0)"
            print("fixed", panel.get("id"), title, target["expr"][:120])
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def fix_value_align() -> None:
    for path in sorted(DASH.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for panel in walk(data.get("panels")):
            if "Processed Records" not in str(panel.get("title") or ""):
                continue
            for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
                if override.get("matcher", {}).get("options") != "value":
                    continue
                for prop in override.get("properties") or []:
                    if prop.get("id") == "custom.align" and prop.get("value") != "right":
                        print(path.name, "align", prop.get("value"), "-> right")
                        prop["value"] = "right"
                        changed = True
        if changed:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )


def main() -> None:
    fix_runtime()
    fix_value_align()
    print("done")


if __name__ == "__main__":
    main()
