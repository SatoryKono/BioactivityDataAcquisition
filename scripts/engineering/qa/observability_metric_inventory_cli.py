"""Rendering, persistence, and CLI for observability metric inventory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from scripts.engineering.qa.observability_metric_inventory_report import (
    _drift_allowlist_token,
    collect_typed_observability_inventory as collect_typed_observability_inventory,
    write_panel_contract_inventory as write_panel_contract_inventory,
)
from scripts.engineering.qa.observability_metric_inventory_runtime import (
    RuntimeCardinalityReviewSummary,
)
from scripts.engineering.qa.observability_metric_inventory_shared import (
    MetricInventoryReport,
    _ALLOWLIST_METADATA_REQUIRED_KEYS,
    _CHECK_DRIFT_KEYS,
    _DEFAULT_DRIFT_ALLOWLIST,
    _PROMETHEUS_BASE_URL_ENV_VAR,
)


def collect_metric_inventory(repo_root: Path) -> MetricInventoryReport:
    """Bind the facade collector without a static import cycle."""
    from importlib import import_module

    module = import_module("scripts.engineering.qa.report_observability_metric_inventory")
    return module.collect_metric_inventory(repo_root)


def _build_runtime_cardinality_review_summary(
    report: MetricInventoryReport,
    *,
    repo_root: Path,
    prometheus_base_url: str | None,
    allow_local_cardinality_fallback: bool = False,
) -> RuntimeCardinalityReviewSummary:
    """Bind the facade review summary without a static import cycle."""
    from importlib import import_module

    module = import_module("scripts.engineering.qa.report_observability_metric_inventory")
    return module._build_runtime_cardinality_review_summary(
        report,
        repo_root=repo_root,
        prometheus_base_url=prometheus_base_url,
        allow_local_cardinality_fallback=allow_local_cardinality_fallback,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--typed-observability-views",
        action="store_true",
        help=(
            "Emit the deterministic typed rule/dashboard/HTTP inventory and fail "
            "on one-way recording-rule or run_id selector drift"
        ),
    )
    parser.add_argument(
        "--update-panel-contracts",
        action="store_true",
        help=(
            "Regenerate docs/03-guides/dashboards/panel-contract-inventory.json "
            "from shipped dashboard JSON; requires --typed-observability-views"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when metric registry/runtime/docs drift exceeds the allowlist",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=_DEFAULT_DRIFT_ALLOWLIST,
        help="YAML file with allowed drift entries for --check",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to scan",
    )
    parser.add_argument(
        "--write-evidence",
        type=Path,
        help="Write collected inventory JSON to a replayable evidence artifact path",
    )
    parser.add_argument(
        "--review-json-out",
        type=Path,
        help="Write runtime cardinality live-review summary JSON to this path",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        help="Append a markdown runtime cardinality review summary to this path",
    )
    parser.add_argument(
        "--prometheus-base-url",
        help=(
            "Prometheus HTTP API base URL for live runtime-cardinality review. "
            f"Defaults to ${_PROMETHEUS_BASE_URL_ENV_VAR} when unset."
        ),
    )
    parser.add_argument(
        "--fail-on-degraded-live-review",
        action="store_true",
        help=(
            "Fail when the runtime-cardinality live review is degraded. "
            "Release gates should enable this so missing Prometheus evidence "
            "does not silently pass."
        ),
    )
    parser.add_argument(
        "--allow-local-cardinality-fallback",
        action="store_true",
        help=(
            "Allow PR/local gates to satisfy runtime-cardinality review from "
            "deterministic repo-local observed-series evidence when Prometheus is "
            "unconfigured. Release gates should keep using "
            "--fail-on-degraded-live-review without this flag."
        ),
    )
    return parser


def _parse_allowlist_metric_name(
    key: str, item: object
) -> str | None:  # pragma: no cover - exercised through _load_drift_allowlist
    if isinstance(item, str):
        if key in _ALLOWLIST_METADATA_REQUIRED_KEYS:
            raise ValueError(
                f"{key} entries must be mappings with metric/owner/reason/review_date"
            )
        return item
    if not isinstance(item, dict):
        raise ValueError(f"{key} entries must be strings or mappings")

    metric_name = item.get("metric")
    if not isinstance(metric_name, str) or not metric_name:
        raise ValueError(f"{key} mapping entries must declare a non-empty metric")

    if key in _ALLOWLIST_METADATA_REQUIRED_KEYS:
        for field_name in ("owner", "reason", "review_date"):
            field_value = item.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(
                    f"{key} metric {metric_name!r} is missing required {field_name}"
                )
        _validate_allowlist_review_date(
            key=key,
            metric_name=metric_name,
            raw_review_date=str(item["review_date"]),
        )
    return metric_name


def _validate_allowlist_review_date(
    *,
    key: str,
    metric_name: str,
    raw_review_date: str,
) -> None:
    try:
        review_date = date.fromisoformat(raw_review_date)
    except ValueError as exc:
        raise ValueError(
            f"{key} metric {metric_name!r} has invalid review_date "
            f"{raw_review_date!r}; expected ISO YYYY-MM-DD"
        ) from exc
    if review_date < date.today():
        raise ValueError(
            f"{key} metric {metric_name!r} has expired review_date "
            f"{raw_review_date}; refresh or remove this lifecycle exception"
        )


def _load_drift_allowlist(path: Path) -> dict[str, set[str]]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe = resolve_output_path(path, root=REPO_ROOT)
    if not safe.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    # Resolve again immediately before the read sink (pythonsecurity:S8707).
    safe = resolve_output_path(safe, root=REPO_ROOT)
    payload = yaml.safe_load(
        safe.read_text(encoding="utf-8")  # NOSONAR - path confined
    )
    if not isinstance(payload, dict):
        return {}
    raw_allowed = payload.get("allowed", payload)
    if not isinstance(raw_allowed, dict):
        return {}
    allowlist: dict[str, set[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = raw_allowed.get(key, [])
        if not isinstance(values, list):
            continue
        allowlist[key] = {
            metric_name
            for metric_name in (
                _parse_allowlist_metric_name(key, value) for value in values
            )
            if metric_name
        }
    return allowlist


def validate_metric_inventory(
    report: dict[str, list[str] | dict[str, list[str]]],
    *,
    allowlist: dict[str, set[str]] | None = None,
) -> dict[str, list[str]]:
    """Return unallowed metric drift grouped by deterministic check category."""
    allowed = allowlist or {}
    violations: dict[str, list[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = report.get(key, [])
        if not isinstance(values, list):
            continue
        allowed_values = allowed.get(key, set())
        unallowed = sorted(
            {
                value
                for value in values
                if _drift_allowlist_token(key, value) not in allowed_values
            }
        )
        if unallowed:
            violations[key] = unallowed
    return violations


def _render_text(report: dict[str, list[str] | dict[str, list[str]]]) -> str:
    lines = ["Observability metric inventory"]
    for key in (
        "declared_metrics",
        "emitted_metrics",
        "declared_observability_events",
        "emitted_observability_events",
        "unused_declared_observability_events",
        "retired_declared_observability_events",
        "retired_declared_observability_events_emitted",
        "emitted_observability_events_without_contract",
        "dashboarded_metrics",
        "alerted_metrics",
        "unused_declared_metrics",
        "emitted_without_declaration",
        "dashboarded_without_declaration",
        "alerted_without_declaration",
        "dashboarded_without_emission",
        "alerted_without_emission",
        "runtime_cardinality_review_candidates",
        "runtime_cardinality_reviewed",
        "runtime_cardinality_review_required",
        "declared_risky_label_review_candidates",
        "declared_risky_label_reviewed",
        "declared_risky_label_review_required",
        "runtime_label_contract_violations",
        "runtime_label_contract_unresolved",
        "runtime_cardinality_threshold_violations",
        "live_metrics",
        "direct_live_metrics",
        "helper_backed_live_metrics",
        "registered_without_runtime",
        "runtime_without_registry",
        "dead_metrics",
        "documented_without_registry",
        "rules_without_registry",
        "documented_without_runtime",
        "ruled_without_runtime",
        "compatibility_alias_candidates",
    ):
        values = report.get(key, [])
        assert isinstance(values, list)
        lines.append(f"\n{key} ({len(values)}):")
        if not values:
            lines.append("  - <none>")
            continue
        lines.extend(f"  - {value}" for value in values)
    return "\n".join(lines)


def _write_evidence_report(
    report: MetricInventoryReport, *, repo_root: Path, evidence_path: Path | None
) -> None:
    if evidence_path is None:
        return
    from scripts.engineering.common.repo_paths import resolve_output_path

    resolved_path = resolve_output_path(evidence_path, root=repo_root)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(  # NOSONAR - path confined by resolve_output_path
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolved_allowlist_path(repo_root: Path, allowlist_path: Path) -> Path:
    return (
        allowlist_path if allowlist_path.is_absolute() else repo_root / allowlist_path
    )


def _metric_inventory_violations(
    report: MetricInventoryReport, *, args: argparse.Namespace
) -> dict[str, list[str]]:
    if not args.check:
        return {}
    return validate_metric_inventory(
        report,
        allowlist=_load_drift_allowlist(
            _resolved_allowlist_path(args.repo_root, args.allowlist)
        ),
    )


def _emit_json_report(
    report: MetricInventoryReport, *, violations: dict[str, list[str]]
) -> int:
    if violations:
        report["check_violations"] = violations
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 1 if violations else 0


def _emit_text_report(
    report: MetricInventoryReport, *, violations: dict[str, list[str]]
) -> int:
    print(_render_text(report))
    if not violations:
        return 0
    print("\nMetric inventory drift check failed:", file=sys.stderr)
    for key, values in violations.items():
        print(f"{key} ({len(values)}):", file=sys.stderr)
        for value in values:
            print(f"  - {value}", file=sys.stderr)
    return 1


def _write_runtime_cardinality_review_summary(
    summary: RuntimeCardinalityReviewSummary,
    *,
    repo_root: Path,
    output_path: Path | None,
) -> None:
    if output_path is None:
        return
    from scripts.engineering.common.repo_paths import resolve_output_path

    resolved_path = resolve_output_path(output_path, root=repo_root)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(  # NOSONAR - path confined by resolve_output_path
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _render_runtime_cardinality_review_summary(
    summary: RuntimeCardinalityReviewSummary,
) -> str:
    reviewed_metrics = summary.get("reviewed_metrics", [])
    review_required_metrics = summary.get("review_required_metrics", [])
    reviewed_count = len(reviewed_metrics) if isinstance(reviewed_metrics, list) else 0
    review_required_count = (
        len(review_required_metrics) if isinstance(review_required_metrics, list) else 0
    )
    lines = [
        "## Observability Runtime Cardinality Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Mode: `{summary['mode']}`",
        f"- Prometheus source: `{summary['prometheus_base_url_source']}`",
        f"- Reviewed metrics: `{reviewed_count}`",
        f"- Review-required metrics: `{review_required_count}`",
    ]

    degraded_reasons = summary.get("degraded_reasons", [])
    if isinstance(degraded_reasons, list) and degraded_reasons:
        lines.append("- Degraded reasons:")
        lines.extend(f"  - `{reason}`" for reason in degraded_reasons)

    live_threshold_violations = summary.get("live_threshold_violations", [])
    if isinstance(live_threshold_violations, list) and live_threshold_violations:
        lines.append("- Live threshold violations:")
        lines.extend(f"  - `{row}`" for row in live_threshold_violations)

    query_errors = summary.get("query_errors", {})
    if isinstance(query_errors, dict) and query_errors:
        lines.append("- Query errors:")
        lines.extend(
            f"  - `{metric_name}`: `{message}`"
            for metric_name, message in sorted(query_errors.items())
        )
    return "\n".join(lines) + "\n"


def _append_runtime_cardinality_review_summary(
    summary: RuntimeCardinalityReviewSummary,
    *,
    repo_root: Path,
    summary_out: Path | None,
) -> None:
    if summary_out is None:
        return
    from scripts.engineering.common.repo_paths import resolve_output_path

    resolved_path = resolve_output_path(summary_out, root=repo_root)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if resolved_path.exists() and resolved_path.stat().st_size > 0:
        prefix = "\n"
    with resolved_path.open(  # NOSONAR - path confined by resolve_output_path
        "a", encoding="utf-8"
    ) as handle:
        handle.write(prefix + _render_runtime_cardinality_review_summary(summary))


def _typed_inventory_violations(
    typed_report: dict[str, object],
) -> dict[str, list[str]]:
    violations: dict[str, list[str]] = {}
    for key in (
        "recording_outputs_without_declaration",
        "recording_declarations_without_output",
        "policy_aliases_overlapping_outputs",
        "policy_aliases_overlapping_runtime_metrics",
        "policy_aliases_without_catalog",
        "catalog_aliases_without_declaration",
        "http_semantics_violations",
        "panel_contract_drift",
        "prometheus_run_id_selector_violations",
    ):
        value = typed_report.get(key)
        if isinstance(value, list) and value:
            violations[key] = [item for item in value if isinstance(item, str)]
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    violations: dict[str, list[str]]
    if args.typed_observability_views:
        typed_report = collect_typed_observability_inventory(args.repo_root)
        if args.update_panel_contracts:
            write_panel_contract_inventory(args.repo_root, typed_report)
            typed_report["panel_contract_drift"] = []
        violations = _typed_inventory_violations(typed_report)
        if args.json:
            json.dump(typed_report, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        else:
            print(json.dumps(typed_report, indent=2, sort_keys=True))
        return 1 if violations else 0
    report = collect_metric_inventory(args.repo_root)
    _write_evidence_report(
        report,
        repo_root=args.repo_root,
        evidence_path=args.write_evidence,
    )
    review_summary = _build_runtime_cardinality_review_summary(
        report,
        repo_root=args.repo_root,
        prometheus_base_url=args.prometheus_base_url,
        allow_local_cardinality_fallback=args.allow_local_cardinality_fallback,
    )
    _write_runtime_cardinality_review_summary(
        review_summary,
        repo_root=args.repo_root,
        output_path=args.review_json_out,
    )
    _append_runtime_cardinality_review_summary(
        review_summary,
        repo_root=args.repo_root,
        summary_out=args.summary_out,
    )
    violations = _metric_inventory_violations(report, args=args)
    live_review_failed = review_summary["status"] == "failed"
    live_review_degraded = (
        args.fail_on_degraded_live_review and review_summary["status"] == "degraded"
    )
    if args.json:
        exit_code = _emit_json_report(report, violations=violations)
    else:
        exit_code = _emit_text_report(report, violations=violations)
    if live_review_failed or live_review_degraded:
        return 1
    return exit_code
