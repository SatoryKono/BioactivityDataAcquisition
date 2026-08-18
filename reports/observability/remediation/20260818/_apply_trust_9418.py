#!/usr/bin/env python3
"""Patch Trust 9418 JSON and first-window wrap overrides. Local helper."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _dump(rel: str, payload: dict) -> None:
    path = ROOT / rel
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _panel(dashboard: dict, panel_id: int) -> dict:
    for panel in dashboard.get("panels") or []:
        if isinstance(panel, dict) and panel.get("id") == panel_id:
            return panel
        for child in panel.get("panels") or []:
            if isinstance(child, dict) and child.get("id") == panel_id:
                return child
    raise KeyError(panel_id)


def _wrap_override(field_name: str, *, width: int) -> dict:
    return {
        "matcher": {"id": "byName", "options": field_name},
        "properties": [
            {"id": "custom.width", "value": width},
            {
                "id": "custom.cellOptions",
                "value": {"type": "auto", "wrapText": True},
            },
            {"id": "custom.inspect", "value": True},
        ],
    }


def _narrow_enum(field_name: str, width: int) -> dict:
    return {
        "matcher": {"id": "byName", "options": field_name},
        "properties": [
            {"id": "custom.width", "value": width},
            {
                "id": "custom.cellOptions",
                "value": {"type": "auto", "wrapText": False},
            },
        ],
    }


def patch_9418() -> None:
    rel = "grafana/dashboards/bioetl-control-plane-v1.json"
    dashboard = _load(rel)
    panel = _panel(dashboard, 9418)
    panel["description"] = (
        "SELECTED RUN HTTP trust summary on the first screen. "
        "processing_status is the data-processing outcome; trust_status is "
        "fail-closed exact-run evidence (INCOMPLETE/ERROR/UNKNOWN are not OK). "
        "First screen shows top-3 trust.reasons_text (newline-joined); the full "
        "reason list stays in rows / panel 9414. Scope is exact_run when run_id "
        "resolves. No-data or backend unavailable is not a health verdict."
    )
    panel["fieldConfig"]["overrides"] = [
        {
            "matcher": {"id": "byName", "options": "evidence_observed_at"},
            "properties": [{"id": "unit", "value": "time:YYYY-MM-DD HH:mm"}],
        },
        _narrow_enum("processing_status", 110),
        _narrow_enum("trust_status", 110),
        _narrow_enum("scope_kind", 90),
        _narrow_enum("evidence_freshness", 100),
        {
            "matcher": {"id": "byName", "options": "reasons_text"},
            "properties": [
                {"id": "displayName", "value": "reasons"},
                {"id": "custom.width", "value": 320},
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "auto", "wrapText": True},
                },
                {"id": "custom.inspect", "value": True},
            ],
        },
    ]
    for transform in panel.get("transformations") or []:
        if transform.get("id") == "limit":
            transform["options"]["limitField"] = 1
        if transform.get("id") == "organize":
            options = transform.setdefault("options", {})
            options["excludeByName"] = {
                "reasons": True,
                "reasons_truncated": True,
            }
            options["indexByName"] = {
                "processing_status": 0,
                "trust_status": 1,
                "scope_kind": 2,
                "evidence_freshness": 3,
                "reasons_text": 4,
                "evidence_observed_at": 5,
            }
            options["renameByName"] = {"reasons_text": "reasons"}
    _dump(rel, dashboard)
    print("patched 9418")


def _ensure_wrap(panel: dict, names: tuple[str, ...], *, width: int) -> None:
    overrides = panel.setdefault("fieldConfig", {}).setdefault("overrides", [])
    existing = {
        item.get("matcher", {}).get("options")
        for item in overrides
        if item.get("matcher", {}).get("id") == "byName"
    }
    for name in names:
        if name in existing:
            for item in overrides:
                if item.get("matcher", {}).get("options") == name:
                    props = item.setdefault("properties", [])
                    has_wrap = False
                    for prop in props:
                        if prop.get("id") == "custom.cellOptions":
                            value = prop.setdefault("value", {})
                            value["wrapText"] = True
                            value.setdefault("type", "auto")
                            has_wrap = True
                    if not has_wrap:
                        props.append(
                            {
                                "id": "custom.cellOptions",
                                "value": {"type": "auto", "wrapText": True},
                            }
                        )
                    if not any(prop.get("id") == "custom.width" for prop in props):
                        props.append({"id": "custom.width", "value": width})
            continue
        overrides.append(_wrap_override(name, width=width))


def patch_wrap_others() -> None:
    runtime = _load("grafana/dashboards/bioetl-runtime.json")
    _ensure_wrap(_panel(runtime, 9101), ("reason", "Reason"), width=280)
    _dump("grafana/dashboards/bioetl-runtime.json", runtime)
    print("patched runtime 9101")

    provider = _load("grafana/dashboards/bioetl-provider-health-v2.json")
    _ensure_wrap(_panel(provider, 9103), ("cause", "Cause"), width=280)
    _dump("grafana/dashboards/bioetl-provider-health-v2.json", provider)
    print("patched provider 9103")

    explorer = _load("grafana/dashboards/bioetl-run-explorer-v1.json")
    _ensure_wrap(_panel(explorer, 3010), ("message", "Message"), width=360)
    _dump("grafana/dashboards/bioetl-run-explorer-v1.json", explorer)
    print("patched explorer 3010")


def main() -> int:
    patch_9418()
    patch_wrap_others()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
