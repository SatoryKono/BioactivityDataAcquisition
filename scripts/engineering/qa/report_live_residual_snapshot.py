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


def _closeout_program_residuals() -> dict[str, int]:
    """Residual counts for closeout-freeze fold program (#7464 / #6891)."""
    arch = ROOT / "tests" / "architecture"
    closeout_files = sorted(arch.glob("test_tech_debt*closeout*.py"))
    retained_count = 0
    facade_path = ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
    if facade_path.is_file():
        try:
            import yaml

            facade = yaml.safe_load(facade_path.read_text(encoding="utf-8"))
            if isinstance(facade, dict):
                retained = facade.get("retained_entrypoints") or []
                if isinstance(retained, list):
                    retained_count = len(retained)
        except Exception:
            retained_count = 0
    zero_ref = 0
    manifest_path = ROOT / "configs" / "quality" / "scripts_inventory_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            scripts = manifest.get("scripts") or []
            if isinstance(scripts, list):
                zero_ref = sum(
                    1
                    for row in scripts
                    if isinstance(row, dict)
                    and row.get("status") == "supporting"
                    and int(row.get("reference_count") or 0) == 0
                )
        except Exception:
            zero_ref = 0
    return {
        "tech_debt_closeout_test_file_count": len(closeout_files),
        "retained_public_entrypoint_count": retained_count,
        "zero_reference_supporting_script_count": zero_ref,
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
        "follow_up_issue": "#7464",
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
        "closeout_program": _closeout_program_residuals(),
    }


def write_snapshot(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    snapshot = build_snapshot()
    safe_path = resolve_output_path(path, root=REPO_ROOT)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(  # NOSONAR - confined by resolve_output_path
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return snapshot


def _check_hotspot_family_non_growth(
    committed_families: dict[str, Any],
    live_families: dict[str, Any],
) -> None:
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
        if (
            float(live_row.get("helper_function_ratio", 0.0))
            > float(committed_row.get("helper_function_ratio", 0.0)) + 1e-9
        ):
            raise SystemExit(
                f"residual growth for {name}.helper_function_ratio: "
                f"live={live_row.get('helper_function_ratio')} "
                f"committed={committed_row.get('helper_function_ratio')}"
            )


def _check_int_metric_non_growth(
    *,
    live_value: int,
    committed_value: int,
    label: str,
) -> None:
    if live_value > committed_value:
        raise SystemExit(
            f"residual growth for {label}: live={live_value} committed={committed_value}"
        )


def check_snapshot(path: Path = DEFAULT_OUTPUT) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    if not safe_path.is_file():
        raise SystemExit(f"missing live residual snapshot: {safe_path}")
    committed = json.loads(
        safe_path.read_text(encoding="utf-8")  # NOSONAR - confined
    )
    live = build_snapshot()
    # Hotspot residual must not grow vs committed snapshot.
    committed_families = committed.get("hotspot_families", {})
    live_families = live.get("hotspot_families", {})
    assert isinstance(committed_families, dict)
    assert isinstance(live_families, dict)
    _check_hotspot_family_non_growth(committed_families, live_families)
    # Dead-code untriaged must stay zero; candidate counts may not grow.
    for key in (
        "repo_wide_zero_import_candidate_count",
        "repo_wide_untriaged_zero_import_candidate_count",
        "repo_wide_candidates_without_owner_tests_count",
    ):
        _check_int_metric_non_growth(
            live_value=int(live["dead_code"][key]),
            committed_value=int(committed["dead_code"][key]),
            label=f"dead_code.{key}",
        )
    _check_int_metric_non_growth(
        live_value=int(live["config_surface"]["duplicate_cluster_count"]),
        committed_value=int(committed["config_surface"]["duplicate_cluster_count"]),
        label="config_surface.duplicate_cluster_count",
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
