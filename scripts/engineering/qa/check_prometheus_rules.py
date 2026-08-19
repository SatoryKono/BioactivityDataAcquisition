#!/usr/bin/env python3
"""Deterministic preflight for repo-backed Prometheus rules."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
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
EXPECTED_ALERT_DEFINITIONS = 57
EXPECTED_RECORD_DEFINITIONS = 110
# Floor after partial-rule-failure alerts (eval failures + iterations missed).
MIN_TESTED_ALERTS = 38
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
    parser.add_argument(
        "--expr-parity",
        action="store_true",
        help="Compare live /api/v1/rules to tracked YAML (skips if Prometheus is down).",
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://127.0.0.1:9090",
        help="Prometheus base URL for --expr-parity.",
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


def list_shipped_rule_files(rules_dir: Path) -> list[Path]:
    """Return top-level rule YAML files (exclude tests/ and non-YAML)."""
    if not rules_dir.is_dir():
        return []
    return sorted(
        p for p in rules_dir.iterdir() if p.is_file() and p.suffix in {".yml", ".yaml"}
    )


def validate_recording_rule_identity_uniqueness(
    rules_files: Sequence[Path],
) -> list[str]:
    """Fail closed on same-timestamp write conflicts.

    Two recording rules with the same metric name **and** the same static
    ``labels:`` map will ingest two samples with identical labels at the same
    evaluation timestamp → Prometheus WARN
    \"Error on ingesting results from rule evaluation with different value but
    same timestamp\", dropped samples, and elevated WAL/head memory churn.

    Same metric name with **different** static labels (e.g. reason=…) is OK.
    """
    import yaml

    seen: dict[tuple[str, tuple[tuple[str, str], ...]], list[str]] = {}
    for rules_file in rules_files:
        try:
            payload = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            return [f"{rules_file.as_posix()}: YAML parse failed: {exc}"]
        if not isinstance(payload, dict):
            continue
        for group in payload.get("groups") or []:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name") or "?")
            for index, rule in enumerate(group.get("rules") or []):
                if not isinstance(rule, dict) or "record" not in rule:
                    continue
                record = str(rule["record"])
                labels_raw = rule.get("labels") or {}
                if not isinstance(labels_raw, dict):
                    labels_raw = {}
                label_key = tuple(
                    sorted((str(k), str(v)) for k, v in labels_raw.items())
                )
                loc = f"{rules_file.as_posix()} group={group_name} rule[{index}]"
                seen.setdefault((record, label_key), []).append(loc)
    violations: list[str] = []
    for (record, label_key), locs in sorted(seen.items()):
        if len(locs) < 2:
            continue
        labels_fmt = ",".join(f"{k}={v}" for k, v in label_key) or "(no static labels)"
        violations.append(
            f"duplicate recording identity record={record!r} labels={{{labels_fmt}}} "
            f"at: {'; '.join(locs)}"
        )
    return violations


def validate_rule_expr_presence(rules_files: Sequence[Path]) -> list[str]:
    """Structural gate: every alert/record rule must declare a non-empty expr.

    Does not parse PromQL; catches missing/empty expr before promtool.
    """
    import yaml

    violations: list[str] = []
    for rules_file in rules_files:
        try:
            payload = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            violations.append(f"{rules_file.as_posix()}: YAML parse failed: {exc}")
            continue
        if not isinstance(payload, dict):
            violations.append(f"{rules_file.as_posix()}: root must be a mapping")
            continue
        for group in payload.get("groups") or []:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name") or "?")
            for index, rule in enumerate(group.get("rules") or []):
                if not isinstance(rule, dict):
                    violations.append(
                        f"{rules_file.as_posix()} group={group_name} "
                        f"rule[{index}]: not a mapping"
                    )
                    continue
                if "alert" in rule:
                    kind = f"alert={rule['alert']}"
                elif "record" in rule:
                    kind = f"record={rule['record']}"
                else:
                    kind = f"rule[{index}]"
                expr = rule.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    violations.append(
                        f"{rules_file.as_posix()} group={group_name} "
                        f"{kind}: missing or empty expr"
                    )
    return violations


class RulesSyntaxResult(TypedDict):
    """Result of promtool check rules (syntax only, no unit-test vectors)."""

    ok: bool
    runner: str
    returncode: int
    command: list[str]
    stdout: str
    stderr: str
    rules_files: list[str]


def check_rules_syntax(
    rules_files: Sequence[Path],
    *,
    root: Path | None = None,
    promtool: str = "promtool",
    image: str = PROMETHEUS_IMAGE,
    timeout: float = 120.0,
    prefer: str = "auto",
) -> RulesSyntaxResult:
    """Run ``promtool check rules`` (PromQL + rule YAML schema).

    ``prefer``:
      - ``auto``: local promtool if on PATH, else Docker pinned image
      - ``local``: promtool only
      - ``docker``: Docker only

    Returns structured result; does not print or exit.
    """
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    workspace = (root or Path.cwd()).resolve()
    rel_files: list[str] = []
    for path in rules_files:
        resolved = (
            path.resolve() if path.is_absolute() else (workspace / path).resolve()
        )
        rel_files.append(resolved.relative_to(workspace).as_posix())
    empty: RulesSyntaxResult = {
        "ok": False,
        "runner": "none",
        "returncode": 127,
        "command": [],
        "stdout": "",
        "stderr": "",
        "rules_files": rel_files,
    }
    if not rel_files:
        empty["stderr"] = "no rule files provided"
        return empty

    def _exec(command: list[str], runner: str) -> RulesSyntaxResult:
        safe = ensure_safe_cli_argv(command)
        try:
            completed = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
                safe,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workspace),
                check=False,
            )
        except FileNotFoundError as exc:
            return {
                "ok": False,
                "runner": runner,
                "returncode": 127,
                "command": safe,
                "stdout": "",
                "stderr": str(exc),
                "rules_files": rel_files,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "runner": runner,
                "returncode": 124,
                "command": safe,
                "stdout": "",
                "stderr": f"promtool check rules timed out after {timeout}s",
                "rules_files": rel_files,
            }
        return {
            "ok": completed.returncode == 0,
            "runner": runner,
            "returncode": int(completed.returncode),
            "command": safe,
            "stdout": (completed.stdout or "")[-4000:],
            "stderr": (completed.stderr or "")[-4000:],
            "rules_files": rel_files,
        }

    if prefer == "local":
        runners = ["local"]
    elif prefer == "docker":
        runners = ["docker"]
    else:
        runners = ["local", "docker"]

    last = empty
    for runner in runners:
        if runner == "local":
            resolved = shutil.which(promtool)
            if resolved is None:
                last = {
                    **empty,
                    "runner": "local",
                    "stderr": _missing_promtool_message(promtool),
                }
                continue
            return _exec([resolved, "check", "rules", *rel_files], "local")
        docker = shutil.which("docker")
        if docker is None:
            last = {
                **empty,
                "runner": "docker",
                "stderr": (
                    "docker executable not found for promtool check rules. "
                    "Install Docker or promtool."
                ),
            }
            continue
        return _exec(
            [
                docker,
                "run",
                "--rm",
                "-v",
                f"{workspace.as_posix()}:/workspace",
                "-w",
                "/workspace",
                "--entrypoint",
                "promtool",
                image,
                "check",
                "rules",
                *rel_files,
            ],
            "docker",
        )
    return last


def _run_local(
    *,
    promtool: str,
    rules_files: tuple[Path, ...],
    test_file: Path,
) -> int:
    syntax = check_rules_syntax(rules_files, promtool=promtool, prefer="local")
    if syntax["returncode"] == 127 and not syntax["ok"]:
        print(syntax["stderr"], file=sys.stderr)
        return 127
    if not syntax["ok"]:
        if syntax["stdout"]:
            print(syntax["stdout"], end="")
        if syntax["stderr"]:
            print(syntax["stderr"], file=sys.stderr, end="")
        return syntax["returncode"] or 1
    print("+ " + " ".join(syntax["command"]))
    resolved = shutil.which(promtool)
    if resolved is None:
        print(_missing_promtool_message(promtool), file=sys.stderr)
        return 127
    return _run([resolved, "test", "rules", test_file.as_posix()])


def _run_docker(
    *,
    image: str,
    rules_files: tuple[Path, ...],
    test_file: Path,
) -> int:
    syntax = check_rules_syntax(rules_files, image=image, prefer="docker")
    if syntax["returncode"] == 127 and not syntax["ok"]:
        print(syntax["stderr"], file=sys.stderr)
        return 127
    if not syntax["ok"]:
        if syntax["stdout"]:
            print(syntax["stdout"], end="")
        if syntax["stderr"]:
            print(syntax["stderr"], file=sys.stderr, end="")
        return syntax["returncode"] or 1
    print("+ " + " ".join(syntax["command"]))
    docker = shutil.which("docker")
    if docker is None:
        print(
            "docker executable not found for --runner docker. "
            "Install Docker or run with --runner local after installing promtool.",
            file=sys.stderr,
        )
        return 127
    workspace = Path.cwd().as_posix()
    return _run(
        [
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
            "test",
            "rules",
            test_file.as_posix(),
        ]
    )



def _run_expr_parity(*, prometheus_url: str) -> int:
    from scripts.ops.observability.check_prometheus_rules_health import (
        check_rules_health,
    )

    report = check_rules_health(
        prometheus_url=prometheus_url,
        expr_parity=True,
        skip_if_unreachable=True,
    )
    print(
        "expr-parity checked="
        f"{report.expr_parity_checked} skipped={report.expr_parity_skipped} "
        f"sha256={report.tracked_rules_sha256} issues={len(report.expr_parity_issues)}"
    )
    for issue in report.expr_parity_issues:
        print(f"expr-parity violation: {issue}")
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    """Validate Prometheus rules and test coverage.

    NOSONAR - S3776: complexity 18 exceeds 15; extraction would obscure validation orchestration logic
    """
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
    # Same-timestamp write conflicts (record name + static labels identity).
    identity_files = (
        tuple(list_shipped_rule_files(Path("grafana/prometheus-rules")))
        if rules_files == DEFAULT_RULES_FILES
        else rules_files
    )
    identity_violations = validate_recording_rule_identity_uniqueness(identity_files)
    if identity_violations:
        for violation in identity_violations:
            print(f"Recording identity conflict: {violation}", file=sys.stderr)
        return 1
    expr_violations = validate_rule_expr_presence(identity_files)
    if expr_violations:
        for violation in expr_violations:
            print(f"Rule expr violation: {violation}", file=sys.stderr)
        return 1
    if args.expr_parity:
        parity_rc = _run_expr_parity(prometheus_url=args.prometheus_url)
        if parity_rc != 0:
            return parity_rc
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
