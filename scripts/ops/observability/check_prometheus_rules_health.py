#!/usr/bin/env python3
"""Detect partial Prometheus rule failures that skip metrics without crashing.

Prometheus stays healthy when individual rules fail evaluation or groups miss
iterations — recording series simply stop updating (silent gaps). This checker
queries the live Rules API and evaluation metrics so operators fail closed.

Usage::

    python scripts/ops/observability/check_prometheus_rules_health.py
    python scripts/ops/observability/check_prometheus_rules_health.py \\
        --prometheus-url http://127.0.0.1:9090 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_PROMETHEUS_URL = "http://127.0.0.1:9090"
BIOETL_RULE_FILE_HINT = "bioetl"


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


def collect_rule_issues(
    rules_payload: Mapping[str, Any],
) -> tuple[list[RuleIssue], int, int]:
    """Return (issues, bioetl_group_count, bioetl_rule_count)."""
    issues: list[RuleIssue] = []
    groups = 0
    rules_n = 0
    data = rules_payload.get("data")
    group_rows = data.get("groups") if isinstance(data, Mapping) else None
    if not isinstance(group_rows, list):
        return issues, 0, 0
    for group in group_rows:
        if not isinstance(group, Mapping):
            continue
        file_path = str(group.get("file") or "")
        group_name = str(group.get("name") or "")
        if not _is_bioetl_group(file_path, group_name):
            continue
        groups += 1
        for rule in group.get("rules") or []:
            if not isinstance(rule, Mapping):
                continue
            rules_n += 1
            name = str(
                rule.get("name") or rule.get("alert") or rule.get("record") or "?"
            )
            kind = str(
                rule.get("type") or ("alerting" if "alert" in rule else "recording")
            )
            health = str(rule.get("health") or "unknown")
            last_error = str(rule.get("lastError") or "").strip()
            if health.lower() in {"err", "error"} or last_error:
                issues.append(
                    RuleIssue(
                        group=group_name,
                        file=file_path,
                        rule=name,
                        kind=kind,
                        health=health,
                        last_error=last_error or health,
                    )
                )
    return issues, groups, rules_n


def check_rules_health(
    *,
    prometheus_url: str = DEFAULT_PROMETHEUS_URL,
    timeout: float = 10.0,
    fail_on_metric_signals: bool = True,
) -> HealthReport:
    """Inspect /api/v1/rules + evaluation counters for silent partial failures."""
    query_errors: list[str] = []
    issues: list[RuleIssue] = []
    groups = 0
    rules_n = 0
    try:
        payload = _fetch_json(
            f"{prometheus_url.rstrip('/')}/api/v1/rules", timeout=timeout
        )
        if payload.get("status") != "success":
            query_errors.append(f"rules API status={payload.get('status')!r}")
        else:
            issues, groups, rules_n = collect_rule_issues(payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        query_errors.append(f"rules API: {exc}")

    failures, err_f = _instant_query(
        prometheus_url,
        (
            "sum(increase(prometheus_rule_evaluation_failures_total"
            '{rule_group=~".*bioetl.*[.]yml;.*"}[10m])) or vector(0)'
        ),
        timeout=timeout,
    )
    if err_f:
        query_errors.append(f"evaluation_failures query: {err_f}")

    missed, err_m = _instant_query(
        prometheus_url,
        (
            "sum(increase(prometheus_rule_group_iterations_missed_total"
            '{rule_group=~".*bioetl.*[.]yml;.*"}[10m])) or vector(0)'
        ),
        timeout=timeout,
    )
    if err_m:
        query_errors.append(f"iterations_missed query: {err_m}")

    metric_bad = fail_on_metric_signals and (
        (failures is not None and failures > 0) or (missed is not None and missed > 0)
    )
    ok = (not issues) and (not query_errors) and (not metric_bad)
    return HealthReport(
        ok=ok,
        prometheus_url=prometheus_url,
        bioetl_groups=groups,
        bioetl_rules=rules_n,
        issues=issues,
        evaluation_failures_10m=failures,
        iterations_missed_10m=missed,
        query_errors=query_errors,
    )


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    report = check_rules_health(
        prometheus_url=args.prometheus_url,
        timeout=args.timeout,
        fail_on_metric_signals=not args.allow_metric_signals,
    )
    payload = {
        "schema_version": "bioetl-prometheus-rules-health-v1",
        "ok": report.ok,
        "prometheus_url": report.prometheus_url,
        "bioetl_groups": report.bioetl_groups,
        "bioetl_rules": report.bioetl_rules,
        "evaluation_failures_10m": report.evaluation_failures_10m,
        "iterations_missed_10m": report.iterations_missed_10m,
        "query_errors": report.query_errors,
        "issues": [asdict(i) for i in report.issues],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
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
        for err in report.query_errors:
            print(f"[FAIL] {err}")
        if report.ok:
            print("\nOK: no partial BioETL rule errors detected.")
        else:
            print(
                "\nFAIL: partial rule errors cause silent metric gaps "
                "(Prometheus may still be /-/healthy)."
            )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
