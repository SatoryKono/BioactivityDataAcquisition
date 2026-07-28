#!/usr/bin/env python3
"""Generate the live residual snapshot for architecture freeze non-growth (#6891).

Usage:
    python -m scripts.engineering.qa.report_live_residual_snapshot
    python -m scripts.engineering.qa.report_live_residual_snapshot --check
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUTPUT = ROOT / "reports" / "quality" / "live-residual-snapshot.json"


def _hotspot_rows() -> list[dict[str, Any]]:
    """Always measure live hotspot residual for snapshot generation."""
    from scripts.engineering.qa.hotspot_family_metrics import (
        collect_hotspot_family_metrics,
    )

    return [asdict(row) for row in collect_hotspot_family_metrics(active_only=True)]


def _dead_code_summary() -> dict[str, Any]:
    path = ROOT / "reports" / "quality" / "dead-code-inventory.json"
    if path.is_file():
        inventory = json.loads(path.read_text(encoding="utf-8"))
    else:
        from scripts.engineering.qa.report_dead_code_inventory import (
            build_dead_code_inventory,
        )

        inventory = build_dead_code_inventory(ROOT)
    summary = inventory.get("summary", {})
    assert isinstance(summary, dict)
    return {
        "repo_wide_zero_import_candidate_count": int(
            summary.get("repo_wide_zero_import_candidate_count", 0)
        ),
        "repo_wide_untriaged_zero_import_candidate_count": int(
            summary.get("repo_wide_untriaged_zero_import_candidate_count", 0)
        ),
        "repo_wide_classified_zero_import_candidate_count": int(
            summary.get("repo_wide_classified_zero_import_candidate_count", 0)
        ),
        "repo_wide_candidates_without_owner_tests_count": int(
            summary.get("repo_wide_candidates_without_owner_tests_count", 0)
        ),
    }


def _config_duplicate_clusters() -> int:
    """Prefer committed backlog artifact; fall back to live scan only if missing."""
    path = ROOT / "reports" / "quality" / "config-surface-backlog.json"
    if path.is_file():
        backlog = json.loads(path.read_text(encoding="utf-8"))
        clusters = backlog.get("duplication_audit", {}).get("clusters", [])
        if isinstance(clusters, list):
            return len(clusters)
        summary = backlog.get("duplication_audit", {}).get("summary", {})
        if isinstance(summary, dict) and "duplicate_cluster_count" in summary:
            return int(summary["duplicate_cluster_count"])
    from scripts.engineering.qa.report_config_surface_backlog import build_backlog

    backlog = build_backlog()
    clusters = backlog.get("duplication_audit", {}).get("clusters", [])
    if not isinstance(clusters, list):
        return 0
    return len(clusters)


def _module_coverage_residuals() -> dict[str, int]:
    path = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
    if not path.is_file():
        return {"uncovered_module_count": 0, "unmeasured_module_count": 0}
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return {"uncovered_module_count": 0, "unmeasured_module_count": 0}
    # Inventory may expose status_counts at top-level rows instead of summary keys.
    rows = payload.get("rows", [])
    uncovered = 0
    unmeasured = 0
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            status = str(row.get("coverage_status") or "")
            if status == "uncovered":
                uncovered += 1
            if status in {"unmeasured", "coverage_xml_missing"}:
                unmeasured += 1
    return {
        "uncovered_module_count": uncovered,
        "unmeasured_module_count": unmeasured,
    }


def build_snapshot() -> dict[str, Any]:
    """Build the current residual snapshot used by non-growth freezes."""
    hotspots = _hotspot_rows()
    families: dict[str, dict[str, Any]] = {}
    for row in hotspots:
        name = str(row.get("name") or "")
        if not name:
            continue
        budgets = row.get("bounded_growth_budgets") or {}
        families[name] = {
            "files_ge_250_loc": int(row.get("files_ge_250_loc") or 0),
            "max_internal_fan_in": int(row.get("max_internal_fan_in") or 0),
            "helper_function_ratio": float(row.get("helper_function_ratio") or 0.0),
            "files": int(row.get("files") or 0),
            "total_loc": int(row.get("total_loc") or 0),
            "budget_files_ge_250_loc": int(
                budgets.get("files_ge_250_loc", row.get("files_ge_250_loc") or 0)
            ),
            "budget_max_internal_fan_in": int(
                budgets.get("max_internal_fan_in", row.get("max_internal_fan_in") or 0)
            ),
        }

    return {
        "schema_version": "live-residual-snapshot-v1",
        "linked_issue": "#6891",
        "parent_epic": "#6890",
        "snapshot_date": date.today().isoformat(),
        "generated_by": "scripts.engineering.qa.report_live_residual_snapshot",
        "policy": {
            "direction": "shrink_only",
            "tech_debt_budget_growth": "forbidden",
            "freeze_mode": "live_snapshot_non_growth",
        },
        "hotspot_families": families,
        "dead_code": _dead_code_summary(),
        "config_surface": {
            "duplicate_cluster_count": _config_duplicate_clusters(),
        },
        "module_coverage": _module_coverage_residuals(),
    }


def write_snapshot(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    snapshot = build_snapshot()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return snapshot


def check_snapshot(path: Path = DEFAULT_OUTPUT) -> None:
    if not path.is_file():
        raise SystemExit(f"missing live residual snapshot: {path}")
    committed = json.loads(path.read_text(encoding="utf-8"))
    live = build_snapshot()
    # Hotspot residual must not grow vs committed snapshot.
    committed_families = committed.get("hotspot_families", {})
    live_families = live.get("hotspot_families", {})
    assert isinstance(committed_families, dict)
    assert isinstance(live_families, dict)
    for name, committed_row in committed_families.items():
        live_row = live_families.get(name)
        if not isinstance(committed_row, dict) or not isinstance(live_row, dict):
            continue
        for key in ("files_ge_250_loc", "max_internal_fan_in", "total_loc"):
            if int(live_row.get(key, 0)) > int(committed_row.get(key, 0)):
                raise SystemExit(
                    f"residual growth for {name}.{key}: "
                    f"live={live_row.get(key)} committed={committed_row.get(key)}"
                )
        if float(live_row.get("helper_function_ratio", 0.0)) > float(
            committed_row.get("helper_function_ratio", 0.0)
        ) + 1e-9:
            raise SystemExit(
                f"residual growth for {name}.helper_function_ratio: "
                f"live={live_row.get('helper_function_ratio')} "
                f"committed={committed_row.get('helper_function_ratio')}"
            )
    # Dead-code untriaged must stay zero; candidate counts may not grow.
    for key in (
        "repo_wide_zero_import_candidate_count",
        "repo_wide_untriaged_zero_import_candidate_count",
        "repo_wide_candidates_without_owner_tests_count",
    ):
        live_v = int(live["dead_code"][key])
        committed_v = int(committed["dead_code"][key])
        if live_v > committed_v:
            raise SystemExit(
                f"residual growth for dead_code.{key}: live={live_v} committed={committed_v}"
            )
    live_clusters = int(live["config_surface"]["duplicate_cluster_count"])
    committed_clusters = int(committed["config_surface"]["duplicate_cluster_count"])
    if live_clusters > committed_clusters:
        raise SystemExit(
            "residual growth for config_surface.duplicate_cluster_count: "
            f"live={live_clusters} committed={committed_clusters}"
        )
    print(f"[ok] live residual snapshot non-growth holds: {path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed snapshot still matches shrink-only residual policy.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path for the snapshot JSON.",
    )
    args = parser.parse_args(argv)
    if args.check:
        check_snapshot(args.json_out)
        return
    snapshot = write_snapshot(args.json_out)
    print(
        "[updated] wrote live residual snapshot: "
        f"{args.json_out} families={len(snapshot['hotspot_families'])} "
        f"clusters={snapshot['config_surface']['duplicate_cluster_count']}"
    )


if __name__ == "__main__":
    main()
