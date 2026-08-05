"""Residual scanner for Grafana 3-cycle closed-loop audits."""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests"))

from integration.grafana_contract_specs import SUMMARY_ZERO_FALLBACK_EXPECTATIONS  # noqa: E402


def walk(panels: list | None):
    for panel in panels or []:
        if panel.get("type") == "row":
            yield from walk(panel.get("panels"))
            continue
        yield panel
        yield from walk(panel.get("panels"))


def pquery(expr: str) -> list:
    q = urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(
        f"http://127.0.0.1:9090/api/v1/query?{q}", timeout=30
    ) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("data", {}).get("result", [])


def greenish_pct(path: Path) -> float:
    from PIL import Image

    image = Image.open(path).convert("RGB")
    width, height = image.size
    pixels = image.load()
    green = total = 0
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            r, g, b = pixels[x, y]
            total += 1
            if g > 140 and g > r + 20 and g > b + 20:
                green += 1
    return round(100 * green / total, 2) if total else 0.0


def scan(iteration_dir: Path) -> dict:
    findings: list[dict] = []
    dash_dir = ROOT / "grafana" / "dashboards"

    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        uid = data.get("uid")
        for panel in walk(data.get("panels")):
            title = str(panel.get("title") or "")
            panel_id = panel.get("id")
            panel_type = panel.get("type")
            steps = ((panel.get("fieldConfig") or {}).get("defaults") or {}).get(
                "thresholds", {}
            ).get("steps") or []
            for step in steps:
                color = str(step.get("color") or "").lower().replace(" ", "")
                if color in {"transparent", "rgba(0,0,0,0)"}:
                    findings.append(
                        {
                            "sev": "P1",
                            "kind": "transparent_threshold",
                            "uid": uid,
                            "id": panel_id,
                            "title": title,
                            "evidence": "DASHBOARD_JSON",
                            "confidence": "FACT",
                        }
                    )
            for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
                display_name = None
                for prop in override.get("properties") or []:
                    if prop.get("id") == "displayName":
                        display_name = prop.get("value")
                for prop in override.get("properties") or []:
                    if prop.get("id") != "custom.cellOptions":
                        continue
                    value = prop.get("value") or {}
                    if (
                        isinstance(value, dict)
                        and value.get("type") == "color-text"
                        and "mode" in value
                    ):
                        findings.append(
                            {
                                "sev": "P1",
                                "kind": "invalid_color_text_mode",
                                "uid": uid,
                                "id": panel_id,
                                "title": title,
                                "evidence": "DASHBOARD_JSON",
                                "confidence": "FACT",
                                "detail": value,
                            }
                        )
                    if (
                        display_name == "Status"
                        and isinstance(value, dict)
                        and value.get("type") == "color-background"
                        and not value.get("applyToRow")
                    ):
                        findings.append(
                            {
                                "sev": "P2",
                                "kind": "status_color_background",
                                "uid": uid,
                                "id": panel_id,
                                "title": title,
                                "evidence": "DASHBOARD_JSON",
                                "confidence": "FACT",
                            }
                        )
            if panel_type == "stat":
                no_value = ((panel.get("fieldConfig") or {}).get("defaults") or {}).get(
                    "noValue"
                )
                if no_value is None:
                    findings.append(
                        {
                            "sev": "P2",
                            "kind": "stat_missing_noValue",
                            "uid": uid,
                            "id": panel_id,
                            "title": title,
                            "evidence": "DASHBOARD_JSON",
                            "confidence": "FACT",
                        }
                    )
            if "Processed Records" in title:
                for transform in panel.get("transformations") or []:
                    if transform.get("id") != "organize":
                        continue
                    exclude = (transform.get("options") or {}).get(
                        "excludeByName"
                    ) or {}
                    if not exclude.get("percintage"):
                        findings.append(
                            {
                                "sev": "P1",
                                "kind": "missing_percintage_exclude",
                                "uid": uid,
                                "id": panel_id,
                                "title": title,
                                "evidence": "DASHBOARD_JSON",
                                "confidence": "FACT",
                            }
                        )
                for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
                    if override.get("matcher", {}).get("options") != "value":
                        continue
                    for prop in override.get("properties") or []:
                        if (
                            prop.get("id") == "custom.align"
                            and prop.get("value") != "right"
                        ):
                            findings.append(
                                {
                                    "sev": "P2",
                                    "kind": "value_align_not_right",
                                    "uid": uid,
                                    "id": panel_id,
                                    "title": title,
                                    "evidence": "DASHBOARD_JSON",
                                    "confidence": "FACT",
                                    "detail": prop.get("value"),
                                }
                            )
            if not title.strip() and panel_type not in (None, "row"):
                findings.append(
                    {
                        "sev": "P2",
                        "kind": "empty_title",
                        "uid": uid,
                        "id": panel_id,
                        "type": panel_type,
                        "evidence": "DASHBOARD_JSON",
                        "confidence": "FACT",
                    }
                )

    for dash_name, expectations in SUMMARY_ZERO_FALLBACK_EXPECTATIONS.items():
        path = dash_dir / dash_name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        by_title = {
            panel.get("title"): panel
            for panel in walk(data.get("panels"))
            if panel.get("title")
        }
        for title, snippet in expectations.items():
            panel = by_title.get(title)
            if panel is None:
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "missing_summary_panel",
                        "dash": dash_name,
                        "title": title,
                        "evidence": "DASHBOARD_JSON",
                        "confidence": "FACT",
                    }
                )
                continue
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets") or []
                if isinstance(target.get("expr"), str)
            ]
            if not any(snippet in expr for expr in expressions):
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "missing_vector0",
                        "dash": dash_name,
                        "title": title,
                        "id": panel.get("id"),
                        "evidence": "DASHBOARD_JSON",
                        "confidence": "FACT",
                    }
                )

    live: dict[str, object] = {}
    for key, expr in {
        "l0_status": "count(bioetl_l0_status)",
        "next_action": "count(bioetl_l0_next_action_route)",
        "bronze": "count(bioetl_processed_records_bronze_current)",
        "up": 'up{job="bioetl"}',
    }.items():
        results = pquery(expr)
        live[key] = [item.get("value", [None, None])[1] for item in results]

    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8000/ops/observability/processed-records"
            "?pipeline=chembl_activity&run_type=backfill&run_id=-",
            timeout=15,
        ) as resp:
            body = json.loads(resp.read().decode())
        rows = body.get("rows") or []
        keys: set[str] = set()
        for row in rows:
            keys |= set(row.keys())
        live["processed_keys"] = sorted(keys)
        if "percintage" in keys:
            findings.append(
                {
                    "sev": "P2",
                    "kind": "live_percintage_field",
                    "evidence": "HTTP",
                    "confidence": "FACT",
                    "detail": "Ops HTTP still returns percintage (stale runtime)",
                }
            )
    except Exception as exc:  # noqa: BLE001
        findings.append(
            {
                "sev": "P2",
                "kind": "ops_http_error",
                "detail": str(exc),
                "confidence": "FACT",
                "evidence": "HTTP",
            }
        )

    overview = json.loads(
        (dash_dir / "bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    first_action = next(
        panel for panel in walk(overview.get("panels")) if panel.get("id") == 215
    )
    first_action_expr = (first_action.get("targets") or [{}])[0].get("expr", "")
    if "topk(4" not in first_action_expr:
        findings.append(
            {
                "sev": "P2",
                "kind": "first_action_topk",
                "detail": first_action_expr[:160],
                "confidence": "FACT",
                "evidence": "DASHBOARD_JSON",
            }
        )

    greenish = {
        png.name: greenish_pct(png)
        for png in sorted((iteration_dir / "dashboards").glob("*.png"))
    }

    registry = {
        "iteration": int(iteration_dir.name.split("-")[-1]),
        "captured_at": datetime.now(UTC).isoformat(),
        "findings_count": len(findings),
        "findings": findings,
        "live_queries": live,
        "greenish_pct": greenish,
        "first_action_expr": first_action_expr[:240],
    }
    out = iteration_dir / "inventory" / "findings-registry.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def main() -> None:
    iteration = sys.argv[1] if len(sys.argv) > 1 else "01"
    base = (
        ROOT
        / "reports"
        / "observability"
        / "grafana-3cycle-20260805-r2"
        / f"iteration-{iteration}"
    )
    registry = scan(base)
    print("findings", registry["findings_count"])
    for finding in registry["findings"]:
        print(finding)
    print("greenish", registry["greenish_pct"])
    print("live", registry["live_queries"])
    print("fa", registry["first_action_expr"][:120])


if __name__ == "__main__":
    main()
