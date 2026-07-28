#!/usr/bin/env python3
"""Check Grafana dashboard performance budgets (epic #6570 / #6571)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_BUDGETS = Path("docs/03-guides/dashboards/contracts/performance-budgets.yaml")
DEFAULT_DASHBOARDS = Path("grafana/dashboards")


def _iter_root_first_screen(
    payload: dict[str, Any], *, y_max: int
) -> list[dict[str, Any]]:
    """Return non-row root panels with y < y_max (not inside collapsed rows)."""
    out: list[dict[str, Any]] = []
    for panel in payload.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        if panel.get("type") == "row":
            continue
        y = int((panel.get("gridPos") or {}).get("y", 999))
        if y < y_max:
            out.append(panel)
    return out


def _panel_exprs(panel: dict[str, Any]) -> list[str]:
    exprs: list[str] = []
    for target in panel.get("targets") or []:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr")
        if isinstance(expr, str) and expr.strip():
            exprs.append(expr)
    return exprs


def _is_ops_http_panel(panel: dict[str, Any]) -> bool:
    title = str(panel.get("title") or "").strip().lower()
    if title in {"id", "processed records"}:
        return True
    for target in panel.get("targets") or []:
        if not isinstance(target, dict):
            continue
        url = str(target.get("url") or "")
        if "/ops/" in url or "processed-records" in url or "run-identity" in url:
            return True
        ds = target.get("datasource")
        if isinstance(ds, dict) and str(ds.get("type") or "").startswith(
            "yesoreyeram-infinity"
        ):
            return True
    return False


def _measure_dashboard(path: Path, *, y_max: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    first = _iter_root_first_screen(payload, y_max=y_max)
    promql = 0
    range_refs = 0
    max_expr = 0
    max_expr_title = ""
    http = 0
    status_exprs: dict[str, str] = {}
    for panel in first:
        if _is_ops_http_panel(panel):
            http += 1
        exprs = _panel_exprs(panel)
        promql += len(exprs)
        title = str(panel.get("title") or "")
        for expr in exprs:
            if (
                "$__range" in expr
                or "${__range_s}" in expr
                or "${__range}" in expr
                or "[$__range]" in expr
                or "range_s" in expr
            ):
                range_refs += 1
            if len(expr) > max_expr:
                max_expr = len(expr)
                max_expr_title = title
            if title.lower() == "status" or "status" in title.lower():
                status_exprs[title] = expr
    # dual status: identical exprs for two *Status* titled first-screen panels
    dual_pairs = 0
    titles = list(status_exprs)
    for i, left in enumerate(titles):
        for right in titles[i + 1 :]:
            if status_exprs[left] == status_exprs[right] and status_exprs[left]:
                dual_pairs += 1

    refresh = str(payload.get("refresh") or "")
    refresh_seconds: int | None
    if refresh.endswith("s") and refresh[:-1].isdigit():
        refresh_seconds = int(refresh[:-1])
    elif refresh.endswith("m") and refresh[:-1].isdigit():
        refresh_seconds = int(refresh[:-1]) * 60
    else:
        refresh_seconds = None

    # nav targets: count peer links in panel 1000 content
    nav_targets = 0
    for panel in payload.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("id") != 1000:
            continue
        content = str((panel.get("options") or {}).get("content") or "")
        nav_targets = content.count('href="/d/')
        break

    return {
        "uid": payload.get("uid") or path.stem,
        "title": payload.get("title"),
        "path": str(path).replace("\\", "/"),
        "refresh": refresh,
        "refresh_seconds": refresh_seconds,
        "first_load_promql": promql,
        "first_paint_ops_http": http,
        "first_screen_range_refs": range_refs,
        "max_first_screen_expr_chars": max_expr,
        "max_first_screen_expr_panel": max_expr_title,
        "dual_status_pairs": dual_pairs,
        "nav_targets": nav_targets,
    }


def _check_primary_and_retired(
    *,
    by_uid: dict[str, dict[str, Any]],
    primary: list[str],
    retired: set[str],
    budgets: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Primary-count violations and retired-UID still-shipped warnings."""
    violations: list[str] = []
    warnings: list[str] = []
    primary_count = sum(1 for uid in primary if uid in by_uid)
    max_primary = int(budgets.get("max_primary_dashboard_count", 5))
    if primary_count > max_primary:
        violations.append(
            f"primary dashboard count {primary_count} > budget {max_primary}"
        )
    # Retired UIDs must not remain as shipped files once phase 4 deletes them.
    for uid in sorted(retired):
        if uid in by_uid:
            warnings.append(
                f"retired uid still shipped as JSON: {uid} (delete in phase #6576)"
            )
    return violations, warnings


def _check_first_load_promql(
    *,
    measurements: list[dict[str, Any]],
    by_uid: dict[str, dict[str, Any]],
    budgets: dict[str, Any],
) -> list[str]:
    """Worst and overview first-load PromQL budget violations."""
    violations: list[str] = []
    worst = max((m["first_load_promql"] for m in measurements), default=0)
    if worst > int(budgets.get("worst_first_load_promql", 6)):
        violations.append(
            f"worst first-load PromQL {worst} > budget "
            f"{budgets.get('worst_first_load_promql')}"
        )
    overview = by_uid.get("bioetl-overview-v2")
    if overview and overview["first_load_promql"] > int(
        budgets.get("overview_first_load_promql", 5)
    ):
        violations.append(
            "overview first-load PromQL "
            f"{overview['first_load_promql']} > budget "
            f"{budgets.get('overview_first_load_promql')}"
        )
    return violations


def _check_expr_and_http_budgets(
    *,
    measurements: list[dict[str, Any]],
    budgets: dict[str, Any],
    exceptions: set[str],
) -> list[str]:
    """HTTP panel, expression-length, and $__range ref budget violations."""
    violations: list[str] = []
    # Count HTTP only on primary/remaining shipped.
    total_http = sum(m["first_paint_ops_http"] for m in measurements)
    if total_http > int(budgets.get("first_paint_ops_http_panels", 0)):
        violations.append(
            f"first-paint Ops HTTP panels {total_http} > budget "
            f"{budgets.get('first_paint_ops_http_panels')}"
        )
    max_expr = max((m["max_first_screen_expr_chars"] for m in measurements), default=0)
    expr_limit = int(budgets.get("max_first_screen_expr_chars", 200))
    if max_expr > expr_limit:
        offenders = [
            f"{m['uid']}:{m['max_first_screen_expr_panel']}={m['max_first_screen_expr_chars']}"
            for m in measurements
            if m["max_first_screen_expr_chars"] > expr_limit
            and m["uid"] not in exceptions
        ]
        if offenders:
            violations.append(
                "max first-screen expr chars "
                f"{max_expr} > budget {budgets.get('max_first_screen_expr_chars')}; "
                f"offenders={offenders}"
            )
    total_range = sum(m["first_screen_range_refs"] for m in measurements)
    if total_range > int(budgets.get("first_screen_range_refs", 0)):
        violations.append(
            f"first-screen $__range refs {total_range} > budget "
            f"{budgets.get('first_screen_range_refs')}"
        )
    return violations


def _check_refresh_dual_nav_budgets(
    *,
    measurements: list[dict[str, Any]],
    budgets: dict[str, Any],
    retired: set[str],
) -> list[str]:
    """Refresh interval, dual-status, and nav-target budget violations."""
    violations: list[str] = []
    refresh_budget = int(budgets.get("refresh_seconds", 60))
    for m in measurements:
        rs = m.get("refresh_seconds")
        if rs is None or rs != refresh_budget:
            violations.append(
                f"{m['uid']} refresh={m.get('refresh')!r} expected {refresh_budget}s"
            )
    dual = sum(m["dual_status_pairs"] for m in measurements)
    if dual > int(budgets.get("dual_status_identical_pairs", 0)):
        violations.append(
            f"dual Status identical pairs {dual} > budget "
            f"{budgets.get('dual_status_identical_pairs')}"
        )
    nav_budget = int(budgets.get("max_nav_targets_per_dashboard", 4))
    for m in measurements:
        if m["uid"] in retired:
            continue
        if m["nav_targets"] > nav_budget:
            violations.append(
                f"{m['uid']} nav targets {m['nav_targets']} > budget {nav_budget}"
            )
    return violations


def evaluate(
    budgets_path: Path,
    dashboards_dir: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_cli_path

    safe_budgets = resolve_cli_path(budgets_path, root=REPO_ROOT)
    safe_dashboards = resolve_cli_path(dashboards_dir, root=REPO_ROOT)
    budgets = yaml.safe_load(
        safe_budgets.read_text(encoding="utf-8")  # NOSONAR - confined by resolve_cli_path
    )
    y_max = int(budgets.get("first_screen_y_max", 28))
    b = budgets.get("budgets") or {}
    primary = list(budgets.get("primary_uids") or [])
    retired = set(budgets.get("retired_uids") or [])
    exceptions = set(budgets.get("expr_length_exceptions") or [])

    measurements: list[dict[str, Any]] = []
    for path in sorted(safe_dashboards.glob("bioetl-*.json")):
        measurements.append(_measure_dashboard(path, y_max=y_max))

    by_uid = {m["uid"]: m for m in measurements}
    violations: list[str] = []
    warnings: list[str] = []

    primary_violations, retired_warnings = _check_primary_and_retired(
        by_uid=by_uid, primary=primary, retired=retired, budgets=b
    )
    violations.extend(primary_violations)
    warnings.extend(retired_warnings)
    violations.extend(
        _check_first_load_promql(
            measurements=measurements, by_uid=by_uid, budgets=b
        )
    )
    violations.extend(
        _check_expr_and_http_budgets(
            measurements=measurements, budgets=b, exceptions=exceptions
        )
    )
    violations.extend(
        _check_refresh_dual_nav_budgets(
            measurements=measurements, budgets=b, retired=retired
        )
    )

    report = {
        "budgets": b,
        "mode": budgets.get("mode", "warn"),
        "measurements": measurements,
        "violations": violations,
        "warnings": warnings,
    }
    return violations, warnings, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--budgets",
        type=Path,
        default=DEFAULT_BUDGETS,
        help="Path to performance-budgets.yaml",
    )
    parser.add_argument(
        "--dashboards",
        type=Path,
        default=DEFAULT_DASHBOARDS,
        help="Dashboards directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable report on stdout",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail even when budget mode is warn",
    )
    args = parser.parse_args(argv)

    violations, warnings, report = evaluate(args.budgets, args.dashboards)
    mode = str(report.get("mode") or "warn")

    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for m in report["measurements"]:
            print(
                f"{m['uid']}: promql={m['first_load_promql']} http={m['first_paint_ops_http']} "
                f"range={m['first_screen_range_refs']} max_expr={m['max_first_screen_expr_chars']} "
                f"refresh={m['refresh']} dual={m['dual_status_pairs']} nav={m['nav_targets']}"
            )
        for warning in warnings:
            print(f"WARN: {warning}")
        for violation in violations:
            print(f"FAIL: {violation}")
        if not violations:
            print("OK: all performance budgets within limits")

    if violations and (mode == "error" or args.strict):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
