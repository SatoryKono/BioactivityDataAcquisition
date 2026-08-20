#!/usr/bin/env python3
"""Detect partial Prometheus rule failures that skip metrics without crashing.

Prometheus stays healthy when individual rules fail evaluation or groups miss
iterations — recording series simply stop updating (silent gaps). This checker
queries the live Rules API and evaluation metrics so operators fail closed.

Usage::

    python scripts/ops/observability/check_prometheus_rules_health.py
    python scripts/ops/observability/check_prometheus_rules_health.py \\
        --prometheus-url http://127.0.0.1:9090 --json
    python scripts/ops/observability/check_prometheus_rules_health.py \\
        --expr-parity --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.engineering.common.repo_paths import REPO_ROOT

DEFAULT_PROMETHEUS_URL = "http://127.0.0.1:9090"
BIOETL_RULE_FILE_HINT = "bioetl"
DEFAULT_RULES_DIR = REPO_ROOT / "grafana" / "prometheus-rules"
EXPR_PARITY_SENTINELS = (
    "bioetl_provider_current_status",
    "bioetl_provider_current_status_info",
    "bioetl_control_plane_telemetry_missing_5m",
    "bioetl_control_plane_current_status_trusted",
    "bioetl_dq_current_status",
    "bioetl_l0_status",
)
NAN_FALLBACK_NEEDLE = "* 0 + 3"
NAN_DIVISION_NEEDLE = "/"


@dataclass(frozen=True)
class RuleIssue:
    group: str
    file: str
    rule: str
    kind: str
    health: str
    last_error: str


@dataclass(frozen=True)
class HealthReport:
    ok: bool
    prometheus_url: str
    bioetl_groups: int
    bioetl_rules: int
    issues: list[RuleIssue]
    evaluation_failures_10m: float | None
    iterations_missed_10m: float | None
    query_errors: list[str]
    expr_parity_checked: bool = False
    expr_parity_skipped: bool = False
    expr_parity_issues: list[str] = field(default_factory=list)
    skipped_unreachable: bool = False
    tracked_rules_sha256: str | None = None


def _fetch_json(url: str, *, timeout: float) -> Any:
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    safe = ensure_local_http_url(url)
    request = Request(safe, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:  # NOSONAR - local URL gated
        return json.loads(response.read().decode("utf-8"))


def _instant_query(
    prometheus_url: str, query: str, *, timeout: float
) -> tuple[float | None, str | None]:
    params = urlencode({"query": query})
    url = f"{prometheus_url.rstrip('/')}/api/v1/query?{params}"
    try:
        payload = _fetch_json(url, timeout=timeout)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, str(exc)
    if payload.get("status") != "success":
        return None, f"query status={payload.get('status')!r}"
    results = (payload.get("data") or {}).get("result") or []
    if not results:
        return 0.0, None
    try:
        value = float(results[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return None, f"cannot parse query value: {exc}"
    return value, None


def _is_bioetl_group(file_path: str, group_name: str) -> bool:
    haystack = f"{file_path};{group_name}".lower()
    return BIOETL_RULE_FILE_HINT in haystack


def _group_rows(rules_payload: Mapping[str, Any]) -> list[object]:
    data = rules_payload.get("data")
    rows = data.get("groups") if isinstance(data, Mapping) else None
    return rows if isinstance(rows, list) else []


def _iter_bioetl_groups(
    rules_payload: Mapping[str, Any],
) -> Iterator[tuple[str, str, Mapping[str, Any]]]:
    for group in _group_rows(rules_payload):
        if not isinstance(group, Mapping):
            continue
        file_path = str(group.get("file") or "")
        group_name = str(group.get("name") or "")
        if _is_bioetl_group(file_path, group_name):
            yield file_path, group_name, group


def _iter_mapping_rules(group: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    rules = group.get("rules")
    if not isinstance(rules, list):
        return
    yield from (rule for rule in rules if isinstance(rule, Mapping))


def collect_rule_issues(
    rules_payload: Mapping[str, Any],
) -> tuple[list[RuleIssue], int, int]:
    """Return (issues, bioetl_group_count, bioetl_rule_count)."""
    issues: list[RuleIssue] = []
    groups = 0
    rules_n = 0
    for file_path, group_name, group in _iter_bioetl_groups(rules_payload):
        groups += 1
        for rule in _iter_mapping_rules(group):
            rules_n += 1
            issue = _rule_issue_from_payload(
                rule, group_name=group_name, file_path=file_path
            )
            if issue is not None:
                issues.append(issue)
    return issues, groups, rules_n


def _rule_issue_from_payload(
    rule: Mapping[str, Any], *, group_name: str, file_path: str
) -> RuleIssue | None:
    name = str(rule.get("name") or rule.get("alert") or rule.get("record") or "?")
    kind = str(rule.get("type") or ("alerting" if "alert" in rule else "recording"))
    health = str(rule.get("health") or "unknown")
    last_error = str(rule.get("lastError") or "").strip()
    if health.lower() not in {"err", "error"} and not last_error:
        return None
    return RuleIssue(
        group=group_name,
        file=file_path,
        rule=name,
        kind=kind,
        health=health,
        last_error=last_error or health,
    )


def normalize_promql(expr: str) -> str:
    """Collapse whitespace so git YAML and live API text can be compared."""
    return " ".join(expr.split())


def tracked_rules_bundle_sha256(rules_dir: Path) -> str:
    """Return SHA-256 of tracked Prometheus YAML files in stable path order."""
    digest = hashlib.sha256()
    for path in sorted(rules_dir.glob("*.yml")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_tracked_recording_exprs(rules_dir: Path) -> dict[str, tuple[str, ...]]:
    """Load recording-rule expressions from tracked Prometheus YAML files."""
    import yaml

    collected: dict[str, list[str]] = {}
    for path in sorted(rules_dir.glob("*.yml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        groups = payload.get("groups") if isinstance(payload, dict) else None
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, Mapping):
                continue
            for rule in _iter_mapping_rules(group):
                name = str(rule.get("record") or "").strip()
                expr = rule.get("expr")
                if not name or not isinstance(expr, str) or not expr.strip():
                    continue
                collected.setdefault(name, []).append(normalize_promql(expr))
    return {name: tuple(exprs) for name, exprs in collected.items()}


def collect_live_recording_exprs(
    rules_payload: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Collect live recording-rule expressions from /api/v1/rules."""
    collected: dict[str, list[str]] = {}
    for _file_path, _group_name, group in _iter_bioetl_groups(rules_payload):
        for rule in _iter_mapping_rules(group):
            name = str(rule.get("name") or rule.get("record") or "").strip()
            expr = rule.get("query") or rule.get("expr")
            if not name or not isinstance(expr, str) or not expr.strip():
                continue
            collected.setdefault(name, []).append(normalize_promql(expr))
    return {name: tuple(exprs) for name, exprs in collected.items()}


def compare_expr_parity(
    *,
    tracked: Mapping[str, tuple[str, ...]],
    live: Mapping[str, tuple[str, ...]],
    sentinels: tuple[str, ...] = EXPR_PARITY_SENTINELS,
) -> list[str]:
    """Return human-readable mismatches for the sentinel recording suite."""
    issues: list[str] = []
    for name in sentinels:
        tracked_exprs = tuple(sorted(tracked.get(name, ())))
        live_exprs = tuple(sorted(live.get(name, ())))
        if not tracked_exprs:
            issues.append(f"{name}: missing from tracked grafana/prometheus-rules")
            continue
        if not live_exprs:
            issues.append(f"{name}: missing from live /api/v1/rules")
            continue
        if tracked_exprs != live_exprs:
            issues.append(
                f"{name}: live expr drift vs git "
                f"tracked={tracked_exprs!r} live={live_exprs!r}"
            )
        if name == "bioetl_provider_current_status":
            issues.extend(_provider_status_expr_issues(name, live_exprs))
    return issues


def _provider_status_expr_issues(name: str, live_exprs: tuple[str, ...]) -> list[str]:
    joined = " | ".join(live_exprs)
    issues: list[str] = []
    if NAN_FALLBACK_NEEDLE not in joined:
        issues.append(
            f"{name}: live expr missing finite UNKNOWN fallback {NAN_FALLBACK_NEEDLE!r}"
        )
    if NAN_DIVISION_NEEDLE in joined:
        issues.append(
            f"{name}: live expr still contains division "
            "(NaN fallback x*0/x*0 is forbidden)"
        )
    return issues


def _fetch_rule_health(
    prometheus_url: str, *, timeout: float, query_errors: list[str]
) -> tuple[Mapping[str, Any] | None, list[RuleIssue], int, int]:
    try:
        payload = _fetch_json(
            f"{prometheus_url.rstrip('/')}/api/v1/rules", timeout=timeout
        )
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        query_errors.append(f"rules API: {exc}")
        return None, [], 0, 0
    if payload.get("status") != "success":
        query_errors.append(f"rules API status={payload.get('status')!r}")
        return None, [], 0, 0
    issues, groups, rules_n = collect_rule_issues(payload)
    return payload, issues, groups, rules_n


def _evaluation_signals(
    prometheus_url: str, *, timeout: float, query_errors: list[str]
) -> tuple[float | None, float | None]:
    queries = (
        (
            "evaluation_failures",
            "sum(increase(prometheus_rule_evaluation_failures_total"
            '{rule_group=~".*bioetl.*[.]yml;.*"}[10m])) or vector(0)',
        ),
        (
            "iterations_missed",
            "sum(increase(prometheus_rule_group_iterations_missed_total"
            '{rule_group=~".*bioetl.*[.]yml;.*"}[10m])) or vector(0)',
        ),
    )
    values: list[float | None] = []
    for label, query in queries:
        value, error = _instant_query(prometheus_url, query, timeout=timeout)
        values.append(value)
        if error:
            query_errors.append(f"{label} query: {error}")
    return values[0], values[1]


def _expr_parity_result(
    *,
    enabled: bool,
    unreachable: bool,
    rules_payload: Mapping[str, Any] | None,
    rules_dir: Path | None,
) -> tuple[bool, bool, list[str], str | None]:
    if not enabled:
        return False, False, [], None
    if unreachable:
        return False, True, [], None
    rules_root = rules_dir or DEFAULT_RULES_DIR
    tracked_sha = tracked_rules_bundle_sha256(rules_root)
    tracked = load_tracked_recording_exprs(rules_root)
    live = collect_live_recording_exprs(rules_payload or {})
    return True, False, compare_expr_parity(tracked=tracked, live=live), tracked_sha


def check_rules_health(
    *,
    prometheus_url: str = DEFAULT_PROMETHEUS_URL,
    timeout: float = 10.0,
    fail_on_metric_signals: bool = True,
    expr_parity: bool = False,
    rules_dir: Path | None = None,
    skip_if_unreachable: bool = False,
) -> HealthReport:
    """Inspect /api/v1/rules + evaluation counters for silent partial failures."""
    query_errors: list[str] = []
    rules_payload, issues, groups, rules_n = _fetch_rule_health(
        prometheus_url, timeout=timeout, query_errors=query_errors
    )
    failures, missed = _evaluation_signals(
        prometheus_url, timeout=timeout, query_errors=query_errors
    )

    metric_bad = fail_on_metric_signals and (
        (failures is not None and failures > 0) or (missed is not None and missed > 0)
    )
    unreachable = any(item.startswith("rules API") for item in query_errors)
    skipped_unreachable = bool(skip_if_unreachable and unreachable)
    expr_parity_checked, expr_parity_skipped, expr_parity_issues, tracked_sha = (
        _expr_parity_result(
            enabled=expr_parity,
            unreachable=unreachable,
            rules_payload=rules_payload,
            rules_dir=rules_dir,
        )
    )
    ok = skipped_unreachable or (
        (not issues)
        and (not query_errors)
        and (not metric_bad)
        and (not expr_parity_issues)
    )
    return HealthReport(
        ok=ok,
        prometheus_url=prometheus_url,
        bioetl_groups=groups,
        bioetl_rules=rules_n,
        issues=issues,
        evaluation_failures_10m=failures,
        iterations_missed_10m=missed,
        query_errors=query_errors,
        expr_parity_checked=expr_parity_checked,
        expr_parity_skipped=expr_parity_skipped,
        expr_parity_issues=expr_parity_issues,
        skipped_unreachable=skipped_unreachable,
        tracked_rules_sha256=tracked_sha,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prometheus-url",
        default=DEFAULT_PROMETHEUS_URL,
        help="Prometheus base URL (default 127.0.0.1:9090)",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--allow-metric-signals",
        action="store_true",
        help="Do not fail on evaluation_failures/iterations_missed counters "
        "(still fails on /api/v1/rules lastError)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--expr-parity",
        action="store_true",
        help="Compare live /api/v1/rules expressions against tracked YAML sentinels",
    )
    parser.add_argument(
        "--rules-dir",
        default=str(DEFAULT_RULES_DIR),
        help="Tracked Prometheus rules directory (default grafana/prometheus-rules)",
    )
    parser.add_argument(
        "--skip-if-unreachable",
        action="store_true",
        help="Exit 0 when Prometheus is unreachable (ADR-010 optional monitoring)",
    )
    return parser


def _report_payload(report: HealthReport) -> dict[str, object]:
    return {
        "schema_version": "bioetl-prometheus-rules-health-v1",
        "ok": report.ok,
        "prometheus_url": report.prometheus_url,
        "bioetl_groups": report.bioetl_groups,
        "bioetl_rules": report.bioetl_rules,
        "evaluation_failures_10m": report.evaluation_failures_10m,
        "iterations_missed_10m": report.iterations_missed_10m,
        "query_errors": report.query_errors,
        "issues": [asdict(issue) for issue in report.issues],
        "expr_parity_checked": report.expr_parity_checked,
        "expr_parity_skipped": report.expr_parity_skipped,
        "expr_parity_issues": report.expr_parity_issues,
        "skipped_unreachable": report.skipped_unreachable,
        "tracked_rules_sha256": report.tracked_rules_sha256,
    }


def _print_text_report(report: HealthReport) -> None:
    print(
        f"=== Prometheus rules health ({report.prometheus_url}) ===\n"
        f"bioetl groups={report.bioetl_groups} rules={report.bioetl_rules}\n"
        f"evaluation_failures_10m={report.evaluation_failures_10m}\n"
        f"iterations_missed_10m={report.iterations_missed_10m}"
    )
    for issue in report.issues:
        print(
            f"[FAIL] {issue.kind} {issue.rule!r} "
            f"group={issue.group!r} health={issue.health} "
            f"lastError={issue.last_error!r}"
        )
    for error in report.query_errors:
        print(f"[FAIL] {error}")
    for error in report.expr_parity_issues:
        print(f"[FAIL] expr-parity {error}")
    if report.expr_parity_skipped or report.skipped_unreachable:
        print("[SKIP] Prometheus unreachable (ADR-010 optional monitoring)")
    if report.ok:
        print("\nOK: no partial BioETL rule errors detected.")
    else:
        print(
            "\nFAIL: partial rule errors cause silent metric gaps "
            "(Prometheus may still be /-/healthy)."
        )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    skip_if_unreachable = args.skip_if_unreachable or args.expr_parity
    report = check_rules_health(
        prometheus_url=args.prometheus_url,
        timeout=args.timeout,
        fail_on_metric_signals=not args.allow_metric_signals,
        expr_parity=args.expr_parity,
        rules_dir=Path(args.rules_dir),
        skip_if_unreachable=skip_if_unreachable,
    )
    if args.json:
        print(json.dumps(_report_payload(report), indent=2, sort_keys=True))
    else:
        _print_text_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
