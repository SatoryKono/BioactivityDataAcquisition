"""Generate the JSON-to-Scenes semantic parity ledger for ADR-053."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DASHBOARDS = ROOT / "grafana" / "dashboards"
ROUTES = (
    ROOT
    / "grafana"
    / "plugins"
    / "bioetl-scenes-app"
    / "src"
    / "routes"
    / "routes.json"
)
DEFAULT_JSON = ROOT / "reports" / "observability" / "scenes-parity-ledger.json"
DEFAULT_MD = ROOT / "reports" / "observability" / "scenes-parity-ledger.md"


def _sha256(path: Path) -> str:
    """Hash UTF-8 text with platform-independent newline normalization."""
    payload = path.read_text(encoding="utf-8").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _walk_panels(panels: object) -> Iterator[dict[str, Any]]:
    if not isinstance(panels, list):
        return
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        yield panel
        yield from _walk_panels(panel.get("panels"))


def _display_title(panel: dict[str, Any]) -> str:
    options = panel.get("options")
    if isinstance(options, dict):
        custom_title = options.get("bioetlDisplayTitle")
        if isinstance(custom_title, str) and custom_title.strip():
            return custom_title.strip()
    return str(panel.get("title") or "")


def _targets(panel: dict[str, Any]) -> list[dict[str, Any]]:
    targets = panel.get("targets")
    if not isinstance(targets, list):
        return []
    return [target for target in targets if isinstance(target, dict)]


def _source_summary(panel: dict[str, Any]) -> dict[str, object]:
    targets = _targets(panel)
    datasource = panel.get("datasource")
    datasource_uid = None
    datasource_type = None
    if isinstance(datasource, dict):
        datasource_uid = datasource.get("uid")
        datasource_type = datasource.get("type")
    expressions = [
        str(target.get("expr") or target.get("url") or target.get("query") or "")
        for target in targets
    ]
    return {
        "datasource_uid": datasource_uid,
        "datasource_type": datasource_type,
        "target_count": len(targets),
        "expressions": [expression for expression in expressions if expression],
    }


def build_payload() -> dict[str, object]:
    contract = json.loads(ROUTES.read_text(encoding="utf-8"))
    routes = contract["routes"]
    uid_to_route: dict[str, dict[str, Any]] = {}
    for route in routes:
        for uid in route["compatibilityUids"]:
            uid_to_route[uid] = route

    rows: list[dict[str, object]] = []
    run_id_prometheus_violations: list[str] = []
    dashboard_hashes: dict[str, str] = {}

    for path in sorted(DASHBOARDS.glob("*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        uid = str(dashboard["uid"])
        route = uid_to_route[uid]
        primary_ids = {int(panel_id) for panel_id in route["primaryPanelIds"]}
        dashboard_hashes[uid] = _sha256(path)

        for panel in _walk_panels(dashboard.get("panels")):
            if panel.get("type") == "row":
                continue
            panel_id = int(panel["id"])
            source = _source_summary(panel)
            raw_expressions = source["expressions"]
            expressions = (
                [str(value) for value in raw_expressions]
                if isinstance(raw_expressions, list)
                else []
            )
            if source["datasource_type"] == "prometheus" and any(
                "run_id" in expression for expression in expressions
            ):
                run_id_prometheus_violations.append(f"{uid}#{panel_id}")

            raw_target_count = source["target_count"]
            has_query = isinstance(raw_target_count, int) and raw_target_count > 0
            # NOSONAR - S3358: nested ternary is intentional for disposition classification
            if panel_id in primary_ids:
                disposition = "route-primary"
            elif has_query:
                disposition = "advanced-evidence"
            else:
                disposition = "fallback-only"
            rows.append(
                {
                    "dashboard_uid": uid,
                    "panel_id": panel_id,
                    "panel_title": _display_title(panel),
                    "route": route["slug"],
                    "component": (
                        route["decisionObjects"][0]
                        if disposition == "route-primary"
                        else "JSON fallback"
                    ),
                    "disposition": disposition,
                    "source": source,
                    "basis": "preserved-from-json",
                    "empty_semantics": "preserved-from-json",
                    "json_fallback": f"/d/{uid}",
                }
            )

    mapped_uids = sorted(uid_to_route)
    shipped_uids = sorted(dashboard_hashes)
    return {
        "schema_version": "bioetl-scenes-parity-v1",
        "adr": "ADR-053",
        "authoritative_surface": "grafana/dashboards/*.json",
        "route_contract_sha256": _sha256(ROUTES),
        "dashboard_sha256": dashboard_hashes,
        "summary": {
            "route_count": len(routes),
            "dashboard_uid_count": len(shipped_uids),
            "panel_disposition_count": len(rows),
            "unmapped_dashboard_uids": sorted(set(shipped_uids) - set(mapped_uids)),
            "missing_dashboard_uids": sorted(set(mapped_uids) - set(shipped_uids)),
            "run_id_prometheus_violations": run_id_prometheus_violations,
            "hidden_datasources": contract["hidden_datasources"],
            "write_actions": contract["write_actions"],
            "parity_status": (
                "pass"
                if not run_id_prometheus_violations
                and set(shipped_uids) == set(mapped_uids)
                else "fail"
            ),
        },
        "context_contract": {
            "allow_list": [
                "workflow",
                "pipeline",
                "from",
                "to",
                "run_type",
                "run_id",
                "provider",
                "stage",
                "reason",
                "basis",
                "origin",
            ],
            "preserves_time": True,
            "preserves_origin": True,
            "round_trip_test": "src/kernel/contracts.test.ts",
        },
        "visual_upgrade_gates": {
            "pipeline_stage_swimlane": "disabled_pending_ordered_stage_frame_fixture",
            "accounting_funnel": "disabled_pending_conservation_frame_fixture",
            "event_annotations": "disabled_pending_stable_event_source",
            "heatmap": "disabled_pending_bounded_dimension_fixture",
            "topology_sankey_waterfall": "forbidden_without_separate_contract",
        },
        "panels": rows,
    }


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    assert isinstance(summary, dict)
    panels = payload["panels"]
    assert isinstance(panels, list)
    by_disposition: dict[str, int] = {}
    for row in panels:
        assert isinstance(row, dict)
        disposition = str(row["disposition"])
        by_disposition[disposition] = by_disposition.get(disposition, 0) + 1
    lines = [
        "# JSON ↔ Scenes semantic parity ledger",
        "",
        "Generated by `python -m scripts.engineering.qa.report_dashboard_scenes_parity`.",
        "",
        f"- Status: **{summary['parity_status']}**",
        f"- Routes: {summary['route_count']}",
        f"- JSON UIDs: {summary['dashboard_uid_count']}",
        f"- Panel dispositions: {summary['panel_disposition_count']}",
        f"- `run_id` Prometheus violations: {len(summary['run_id_prometheus_violations'])}",
        "",
        "## Dispositions",
        "",
    ]
    lines.extend(
        f"- `{name}`: {count}" for name, count in sorted(by_disposition.items())
    )
    lines.extend(
        [
            "",
            "All query functionality remains reachable through the authoritative JSON",
            "fallback. Shadow routes add no datasource or write path. Visual upgrades",
            "remain disabled until their explicit frame contracts exist.",
            "",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = build_payload()
    json_text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    md_text = _render_markdown(payload)
    if args.check:
        if (
            not args.json_out.exists()
            or args.json_out.read_text(encoding="utf-8") != json_text
            or not args.md_out.exists()
            or args.md_out.read_text(encoding="utf-8") != md_text
        ):
            raise SystemExit("Scenes parity ledger is stale; rerun without --check")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_text, encoding="utf-8")
        args.md_out.write_text(md_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
