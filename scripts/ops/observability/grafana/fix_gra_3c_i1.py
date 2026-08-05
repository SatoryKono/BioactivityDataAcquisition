"""Iteration-1 fixes for GRA 3-cycle 2026-08-05: #7578 transparent thresholds, #7577 vector(0)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"


def _fix_transparent(path: Path) -> list[tuple]:
    data = json.loads(path.read_text(encoding="utf-8"))
    changed: list[tuple] = []

    def fix_steps(steps: object, loc: str, pid: object, title: object) -> None:
        if not isinstance(steps, list):
            return
        for step in steps:
            if not isinstance(step, dict):
                continue
            color = str(step.get("color") or "")
            normalized = color.lower().replace(" ", "")
            if normalized == "transparent" or normalized == "rgba(0,0,0,0)":
                step["color"] = "gray"
                changed.append((path.name, pid, title, loc, color))

    def walk(panels: list | None) -> None:
        for panel in panels or []:
            if panel.get("type") == "row":
                walk(panel.get("panels"))
                continue
            field_config = panel.get("fieldConfig") or {}
            defaults = field_config.get("defaults") or {}
            thresholds = defaults.get("thresholds") or {}
            fix_steps(
                thresholds.get("steps"),
                "defaults",
                panel.get("id"),
                panel.get("title"),
            )
            for override in field_config.get("overrides") or []:
                for prop in override.get("properties") or []:
                    if prop.get("id") != "thresholds":
                        continue
                    value = prop.get("value") or {}
                    fix_steps(
                        value.get("steps"),
                        "override",
                        panel.get("id"),
                        panel.get("title"),
                    )
            walk(panel.get("panels"))

    walk(data.get("panels"))
    if changed:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return changed


def _fix_failed_workflow_vector0(path: Path) -> str | None:
    data = json.loads(path.read_text(encoding="utf-8"))

    def walk(panels: list | None):
        for panel in panels or []:
            if panel.get("type") == "row":
                yield from walk(panel.get("panels"))
                continue
            yield panel
            yield from walk(panel.get("panels"))

    before = after = None
    for panel in walk(data.get("panels")):
        if panel.get("id") != 9996:
            continue
        for target in panel.get("targets") or []:
            expr = target.get("expr") or ""
            before = expr
            if "or vector(0)" in expr:
                after = expr
                continue
            if expr.startswith("round(") and expr.endswith(")"):
                inner = expr[len("round(") : -1]
                target["expr"] = f"round(({inner}) or vector(0))"
            else:
                target["expr"] = f"({expr}) or vector(0)"
            after = target["expr"]
    if before != after and after is not None:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return after


def main() -> None:
    all_changed: list[tuple] = []
    for path in sorted(DASH.glob("*.json")):
        all_changed.extend(_fix_transparent(path))
    print("transparent_fixed", len(all_changed))
    for item in all_changed:
        print(item)
    after = _fix_failed_workflow_vector0(DASH / "bioetl-runtime.json")
    print("failed_workflow_expr", after)


if __name__ == "__main__":
    main()
