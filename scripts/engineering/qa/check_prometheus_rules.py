#!/usr/bin/env python3
"""Deterministic preflight for repo-backed Prometheus rules."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

OBSERVABILITY_RULES_FILE = Path("grafana/prometheus-rules/bioetl_observability.yml")
CONTROL_PLANE_RULES_FILE = Path(
    "grafana/prometheus-rules/bioetl_control_plane_current_status.yml"
)
DEFAULT_RULES_FILES = (OBSERVABILITY_RULES_FILE, CONTROL_PLANE_RULES_FILE)
TESTS_FILE = Path("grafana/prometheus-rules/tests/bioetl_observability.test.yml")
PROMETHEUS_IMAGE = (
    "prom/prometheus:v3.13.1@sha256:"
    "3c42b892cf723fa54d2f262c37a0e1f80aa8c8ddb1da7b9b0df9455a35a7f893"
)
PROMETHEUS_COMPATIBILITY_SERIES = "3.13.x"
PUSHGATEWAY_COMPATIBILITY_SERIES = "1.11.x"
EXPECTED_ALERT_DEFINITIONS = 55
EXPECTED_RECORD_DEFINITIONS = 105
# Floor after 2026-07-23: BioETLQuarantineExplorerUnavailable alert removed.
MIN_TESTED_ALERTS = 36
MIN_DIRECTLY_TESTED_RECORDS = 28


class RuleTestCoverage(TypedDict):
    """Deterministic coverage summary for shipped Prometheus rules."""

    alert_definitions: int
    tested_alerts: int
    firing_alerts: int
    non_firing_alerts: int
    record_definitions: int
    directly_tested_records: int
    control_plane_records: list[str]
    untested_control_plane_records: list[str]
    undefined_fixture_alerts: list[str]
    untested_alerts: list[str]
    untested_records: list[str]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run promtool syntax and rule-vector validation for BioETL "
            "Prometheus rules."
        )
    )
    parser.add_argument(
        "--rules-file",
        action="append",
        type=Path,
        default=None,
        help=(
            "Prometheus rule file to check. Repeat to check multiple files. "
            "Defaults to all shipped BioETL rule files."
        ),
    )
    parser.add_argument(
        "--coverage-json",
        action="store_true",
        help="Emit deterministic alert/record rule-test coverage as JSON before promtool",
    )
    parser.add_argument("--test-file", type=Path, default=TESTS_FILE)
    parser.add_argument(
        "--runner",
        choices=("local", "docker"),
        default="local",
        help="Use local promtool or the pinned Prometheus Docker image.",
    )
    parser.add_argument(
        "--promtool",
        default="promtool",
        help="promtool executable name/path for --runner local.",
    )
    parser.add_argument(
        "--image",
        default=PROMETHEUS_IMAGE,
        help="Docker image for --runner docker.",
    )
    return parser


def _run(command: list[str]) -> int:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    command = ensure_safe_cli_argv(command)
    print("+ " + " ".join(command))
    completed = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        command, check=False
    )
    return int(completed.returncode)


def _iter_rule_entries(payload: object) -> list[object]:
    if not isinstance(payload, dict):
        return []
    entries: list[object] = []
    for group in payload.get("groups", []) or []:
        if not isinstance(group, dict):
            continue
        for rule in group.get("rules", []) or []:
            entries.append(rule)
    return entries


def _ingest_rule_entry(
    rule: object,
    *,
    rules_file: Path,
    alert_definitions: set[str],
    record_definitions: set[str],
    control_plane_records: set[str],
) -> None:
    if not isinstance(rule, dict):
        return
    alert_name = rule.get("alert")
    if alert_name:
        alert_definitions.add(str(alert_name))
    record_name = rule.get("record")
    if not record_name:
        return
    record_name = str(record_name)
    record_definitions.add(record_name)
    if rules_file == CONTROL_PLANE_RULES_FILE:
        control_plane_records.add(record_name)


def _collect_rule_definitions(
    rules_files: tuple[Path, ...],
) -> tuple[set[str], set[str], set[str]]:
    import yaml

    alert_definitions: set[str] = set()
    record_definitions: set[str] = set()
    control_plane_records: set[str] = set()
    for rules_file in rules_files:
        payload = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
        for rule in _iter_rule_entries(payload):
            _ingest_rule_entry(
                rule,
                rules_file=rules_file,
                alert_definitions=alert_definitions,
                record_definitions=record_definitions,
                control_plane_records=control_plane_records,
            )
    return alert_definitions, record_definitions, control_plane_records


def _register_alert_assertion(
    assertion: object,
    *,
    tested_alerts: set[str],
    firing_alerts: set[str],
    non_firing_alerts: set[str],
) -> None:
    if not isinstance(assertion, dict):
        return
    alert_name = str(assertion.get("alertname", ""))
    if not alert_name:
        return
    tested_alerts.add(alert_name)
    if assertion.get("exp_alerts"):
        firing_alerts.add(alert_name)
    else:
        non_firing_alerts.add(alert_name)


def _collect_alert_fixture_coverage(
    test_cases: list[object],
) -> tuple[set[str], set[str], set[str]]:
    tested_alerts: set[str] = set()
    firing_alerts: set[str] = set()
    non_firing_alerts: set[str] = set()
    for test_case in test_cases:
        if not isinstance(test_case, dict):
            continue
        for assertion in test_case.get("alert_rule_test", []):
            _register_alert_assertion(
                assertion,
                tested_alerts=tested_alerts,
                firing_alerts=firing_alerts,
                non_firing_alerts=non_firing_alerts,
            )
    return tested_alerts, firing_alerts, non_firing_alerts


def _records_mentioned_in_expr(expr: str, record_definitions: set[str]) -> set[str]:
    import re

    return {
        record_name
        for record_name in record_definitions
        if re.search(rf"\b{re.escape(record_name)}\b", expr)
    }


def _collect_directly_tested_records(
    test_cases: list[object],
    record_definitions: set[str],
) -> set[str]:
    directly_tested_records: set[str] = set()
    for test_case in test_cases:
        if not isinstance(test_case, dict):
            continue
        for assertion in test_case.get("promql_expr_test", []):
            if not isinstance(assertion, dict) or not assertion.get("exp_samples"):
                continue
            expr = str(assertion.get("expr", ""))
            directly_tested_records.update(
                _records_mentioned_in_expr(expr, record_definitions)
            )
    return directly_tested_records


def collect_rule_test_coverage(
    *, rules_files: tuple[Path, ...], test_file: Path
) -> RuleTestCoverage:
    """Measure direct promtool fixture coverage for shipped alerts and records."""
    import yaml

    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    alert_definitions, record_definitions, control_plane_records = (
        _collect_rule_definitions(rules_files)
    )
    test_file = resolve_output_path(test_file, root=REPO_ROOT)
    fixture = yaml.safe_load(test_file.read_text(encoding="utf-8"))
    test_cases = list(fixture.get("tests", []) or [])
    tested_alerts, firing_alerts, non_firing_alerts = _collect_alert_fixture_coverage(
        test_cases
    )
    directly_tested_records = _collect_directly_tested_records(
        test_cases, record_definitions
    )

    return {
        "alert_definitions": len(alert_definitions),
        "tested_alerts": len(tested_alerts & alert_definitions),
        "firing_alerts": len(firing_alerts & alert_definitions),
        "non_firing_alerts": len(non_firing_alerts & alert_definitions),
        "record_definitions": len(record_definitions),
        "directly_tested_records": len(directly_tested_records),
        "control_plane_records": sorted(control_plane_records),
        "untested_control_plane_records": sorted(
            control_plane_records - directly_tested_records
        ),
        "undefined_fixture_alerts": sorted(tested_alerts - alert_definitions),
        "untested_alerts": sorted(alert_definitions - tested_alerts),
        "untested_records": sorted(record_definitions - directly_tested_records),
    }


def _coverage_count_violations(coverage: RuleTestCoverage) -> list[str]:
    violations: list[str] = []
    if coverage["alert_definitions"] != EXPECTED_ALERT_DEFINITIONS:
        violations.append(
            "alert definitions changed from baseline "
            f"{EXPECTED_ALERT_DEFINITIONS}: {coverage['alert_definitions']}"
        )
    if coverage["record_definitions"] != EXPECTED_RECORD_DEFINITIONS:
        violations.append(
            "record definitions changed from baseline "
            f"{EXPECTED_RECORD_DEFINITIONS}: {coverage['record_definitions']}"
        )
    if coverage["tested_alerts"] < MIN_TESTED_ALERTS:
        violations.append(
            f"tested alerts regressed below {MIN_TESTED_ALERTS}: "
            f"{coverage['tested_alerts']}"
        )
    if coverage["firing_alerts"] < MIN_TESTED_ALERTS:
        violations.append(
            f"firing alert fixtures regressed below {MIN_TESTED_ALERTS}: "
            f"{coverage['firing_alerts']}"
        )
    if coverage["directly_tested_records"] < MIN_DIRECTLY_TESTED_RECORDS:
        violations.append(
            f"directly tested records regressed below {MIN_DIRECTLY_TESTED_RECORDS}: "
            f"{coverage['directly_tested_records']}"
        )
    return violations


def _coverage_set_violations(coverage: RuleTestCoverage) -> list[str]:
    violations: list[str] = []
    if coverage["undefined_fixture_alerts"]:
        violations.append(
            "fixtures reference undefined alerts: "
            + ", ".join(coverage["undefined_fixture_alerts"])
        )
    if coverage["untested_control_plane_records"]:
        violations.append(
            "control-plane records lack direct promql fixtures: "
            + ", ".join(coverage["untested_control_plane_records"])
        )
    return violations


def validate_rule_test_coverage(coverage: RuleTestCoverage) -> list[str]:
    """Return fail-closed rule-test coverage violations."""
    return _coverage_count_violations(coverage) + _coverage_set_violations(coverage)


def _missing_promtool_message(promtool: str) -> str:
    return (
        f"promtool executable not found: {promtool!r}. "
        "Install Prometheus promtool, or run the deterministic Docker-backed "
        "surface: python -m scripts.engineering.qa check-prometheus-rules "
        "--runner docker."
    )


def _resolve_rules_files(raw_rules_files: list[Path] | None) -> tuple[Path, ...]:
    if raw_rules_files:
        return tuple(raw_rules_files)
    return DEFAULT_RULES_FILES


def _run_local(
    *,
    promtool: str,
    rules_files: tuple[Path, ...],
    test_file: Path,
) -> int:
    resolved = shutil.which(promtool)
    if resolved is None:
        print(_missing_promtool_message(promtool), file=sys.stderr)
        return 127
    checks = [
        [resolved, "check", "rules", *(path.as_posix() for path in rules_files)],
        [resolved, "test", "rules", test_file.as_posix()],
    ]
    for command in checks:
        result = _run(command)
        if result != 0:
            return result
    return 0


def _run_docker(
    *,
    image: str,
    rules_files: tuple[Path, ...],
    test_file: Path,
) -> int:
    docker = shutil.which("docker")
    if docker is None:
        print(
            "docker executable not found for --runner docker. "
            "Install Docker or run with --runner local after installing promtool.",
            file=sys.stderr,
        )
        return 127
    workspace = Path.cwd().as_posix()
    checks = [
        ["check", "rules", *(path.as_posix() for path in rules_files)],
        ["test", "rules", test_file.as_posix()],
    ]
    for check in checks:
        command = [
            docker,
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            "-w",
            "/workspace",
            "--entrypoint",
            "promtool",
            image,
            *check,
        ]
        result = _run(command)
        if result != 0:
            return result
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    rules_files = _resolve_rules_files(args.rules_file)
    coverage = collect_rule_test_coverage(
        rules_files=rules_files,
        test_file=args.test_file,
    )
    coverage_violations = (
        validate_rule_test_coverage(coverage)
        if rules_files == DEFAULT_RULES_FILES
        else []
    )
    if args.coverage_json:
        print(json.dumps(coverage, indent=2, sort_keys=True))
    else:
        print(
            "Rule test coverage: "
            f"alerts={coverage['tested_alerts']}/{coverage['alert_definitions']} "
            f"(firing={coverage['firing_alerts']}, non_firing={coverage['non_firing_alerts']}), "
            f"records={coverage['directly_tested_records']}/{coverage['record_definitions']}, "
            "control_plane="
            f"{len(coverage['control_plane_records']) - len(coverage['untested_control_plane_records'])}/"
            f"{len(coverage['control_plane_records'])}"
        )
    if coverage_violations:
        for violation in coverage_violations:
            print(f"Rule coverage violation: {violation}", file=sys.stderr)
        return 1
    if args.runner == "docker":
        return _run_docker(
            image=args.image,
            rules_files=rules_files,
            test_file=args.test_file,
        )
    return _run_local(
        promtool=args.promtool,
        rules_files=rules_files,
        test_file=args.test_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
