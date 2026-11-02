#!/usr/bin/env python3
"""Enforce diagram quality budget across lint/quality/nightly JSON reports."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class BudgetCheck:
    metric: str
    value: int
    limit: int
    passed: bool
    source: str
    message: str


@dataclass(frozen=True)
class BudgetReport:
    mode: str
    checks: list[BudgetCheck]
    failed_checks: int
    passed: bool


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _err(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _ensure_repo_path(path: Path) -> Path:
    resolved_root = REPO_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(
            f"refusing to write path outside {resolved_root}: {resolved_path}"
        )
    return resolved_path


def _resolve_output_path(path: Path) -> Path:
    target = path if path.is_absolute() else REPO_ROOT / path
    return _ensure_repo_path(target)


def _write_output(path: Path, content: str) -> None:
    safe_path = _resolve_output_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    if not resolved.exists():
        raise FileNotFoundError(f"report file not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {resolved}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON report root must be object: {resolved}")
    return payload


def to_int(payload: dict[str, Any], key: str, default: int = 0) -> int:
    raw = payload.get(key, default)
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return default


def rule_violations(quality_payload: dict[str, Any], rule_id: str) -> int:
    rules = quality_payload.get("rules", [])
    if not isinstance(rules, list):
        return 0
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("rule_id") == rule_id:
            return to_int(rule, "violations", 0)
    return 0


def lint_counts(lint_payload: dict[str, Any]) -> tuple[int, int]:
    issues = lint_payload.get("issues", [])
    if not isinstance(issues, list):
        return (0, 0)
    errors = 0
    warnings = 0
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity", "")).upper()
        if severity == "ERROR":
            errors += 1
        elif severity == "WARNING":
            warnings += 1
    return errors, warnings


def build_check(
    metric: str, value: int, limit: int, source: str, message: str
) -> BudgetCheck:
    return BudgetCheck(
        metric=metric,
        value=value,
        limit=limit,
        passed=value <= limit,
        source=source,
        message=message,
    )


def _append_optional_check(
    checks: list[BudgetCheck],
    *,
    enabled: bool,
    metric: str,
    value: int,
    limit: int,
    source: str,
    message: str,
) -> None:
    if not enabled:
        return
    checks.append(
        build_check(
            metric=metric,
            value=value,
            limit=limit,
            source=source,
            message=message,
        )
    )


def render_markdown(report: BudgetReport) -> str:
    lines: list[str] = []
    lines.append("# Diagram Quality Budget Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Mode: {report.mode}")
    lines.append(f"- Total checks: {len(report.checks)}")
    lines.append(f"- Failed checks: {report.failed_checks}")
    lines.append(f"- Status: {'PASS' if report.passed else 'FAIL'}")
    lines.append("")
    lines.append("## Budget Checks")
    lines.append("")
    lines.append("| Metric | Source | Value | Limit | Status |")
    lines.append("|---|---|---:|---:|---|")
    for check in report.checks:
        lines.append(
            "| "
            f"{check.metric} | {check.source} | {check.value} | {check.limit} | "
            f"{'PASS' if check.passed else 'FAIL'} |"
        )

    if report.failed_checks > 0:
        lines.append("")
        lines.append("## Failed Details")
        lines.append("")
        for check in report.checks:
            if check.passed:
                continue
            lines.append(
                f"- `{check.metric}` ({check.source}): {check.message} "
                f"(value={check.value}, limit={check.limit})"
            )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enforce diagram quality budget")
    parser.add_argument("--mode", choices=("pr", "nightly"), default="pr")
    parser.add_argument("--quality-report", type=Path)
    parser.add_argument("--lint-report", type=Path)
    parser.add_argument("--nightly-report", type=Path)
    parser.add_argument("--max-hard-failures", type=int, default=0)
    parser.add_argument("--max-warning-failures", type=int, default=-1)
    parser.add_argument("--max-diag-t022", type=int, default=0)
    parser.add_argument("--max-diag-t023", type=int, default=0)
    parser.add_argument("--max-lint-errors", type=int, default=0)
    parser.add_argument("--max-lint-warnings", type=int, default=-1)
    parser.add_argument("--max-nightly-errors", type=int, default=0)
    parser.add_argument("--max-nightly-warnings", type=int, default=-1)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _quality_checks(args: argparse.Namespace) -> list[BudgetCheck]:
    if args.quality_report is None:
        return []
    quality_payload = load_json(args.quality_report)
    checks = [
        build_check(
            metric="quality.hard_failures",
            value=to_int(quality_payload, "hard_failures", 0),
            limit=args.max_hard_failures,
            source="check_diagram_quality_gates",
            message="hard quality-gate failures exceed budget",
        ),
        build_check(
            metric="quality.DIAG-T022",
            value=rule_violations(quality_payload, "DIAG-T022"),
            limit=args.max_diag_t022,
            source="check_diagram_quality_gates",
            message="label-length warnings (DIAG-T022) exceed budget",
        ),
        build_check(
            metric="quality.DIAG-T023",
            value=rule_violations(quality_payload, "DIAG-T023"),
            limit=args.max_diag_t023,
            source="check_diagram_quality_gates",
            message="multi-line label warnings (DIAG-T023) exceed budget",
        ),
    ]
    if args.max_warning_failures >= 0:
        checks.insert(
            1,
            build_check(
                metric="quality.warning_failures",
                value=to_int(quality_payload, "warning_failures", 0),
                limit=args.max_warning_failures,
                source="check_diagram_quality_gates",
                message="warning quality-gate failures exceed budget",
            ),
        )
    return checks


def _lint_checks(args: argparse.Namespace) -> list[BudgetCheck]:
    if args.lint_report is None:
        return []
    lint_payload = load_json(args.lint_report)
    lint_errors, lint_warnings = lint_counts(lint_payload)
    checks = [
        build_check(
            metric="lint.errors",
            value=lint_errors,
            limit=args.max_lint_errors,
            source="lint_diagrams",
            message="diagram lint errors exceed budget",
        )
    ]
    _append_optional_check(
        checks,
        enabled=args.max_lint_warnings >= 0,
        metric="lint.warnings",
        value=lint_warnings,
        limit=args.max_lint_warnings,
        source="lint_diagrams",
        message="diagram lint warnings exceed budget",
    )
    return checks


def _nightly_checks(args: argparse.Namespace) -> list[BudgetCheck]:
    if args.mode != "nightly":
        return []
    if args.nightly_report is None:
        raise ValueError("--nightly-report is required in nightly mode")
    nightly_payload = load_json(args.nightly_report)
    checks = [
        build_check(
            metric="nightly.errors",
            value=to_int(nightly_payload, "errors", 0),
            limit=args.max_nightly_errors,
            source="run_diagram_nightly_suite",
            message="nightly suite errors exceed budget",
        )
    ]
    _append_optional_check(
        checks,
        enabled=args.max_nightly_warnings >= 0,
        metric="nightly.warnings",
        value=to_int(nightly_payload, "warnings", 0),
        limit=args.max_nightly_warnings,
        source="run_diagram_nightly_suite",
        message="nightly suite warnings exceed budget",
    )
    return checks


def _report_payload(report: BudgetReport) -> dict[str, object]:
    return {
        "mode": report.mode,
        "failed_checks": report.failed_checks,
        "passed": report.passed,
        "checks": [asdict(check) for check in report.checks],
    }


def _write_optional_outputs(
    args: argparse.Namespace, report: BudgetReport, payload: dict[str, object]
) -> None:
    if args.json_out is not None:
        _write_output(
            args.json_out,
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        )
    if args.markdown_out is not None:
        _write_output(args.markdown_out, render_markdown(report))


def _budget_report(mode: str, checks: list[BudgetCheck]) -> BudgetReport:
    failed_checks = sum(1 for check in checks if not check.passed)
    return BudgetReport(
        mode=mode,
        checks=checks,
        failed_checks=failed_checks,
        passed=failed_checks == 0,
    )


def main() -> int:
    args = parse_args()

    try:
        checks = _quality_checks(args) + _lint_checks(args) + _nightly_checks(args)
    except (FileNotFoundError, ValueError) as exc:
        _err(f"[ERROR] {exc}")
        return 2

    if not checks:
        _err("[ERROR] no budget checks configured; provide at least one report input")
        return 2

    report = _budget_report(args.mode, checks)

    payload = _report_payload(report)

    try:
        _write_optional_outputs(args, report, payload)
    except ValueError as exc:
        _err(f"[ERROR] {exc}")
        return 2

    if args.json:
        _out(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        _out(
            "[INFO] Diagram quality budget: "
            f"checks={len(report.checks)}, failed={report.failed_checks}, "
            f"status={'PASS' if report.passed else 'FAIL'}"
        )
        for check in report.checks:
            _out(
                f"[INFO] {check.metric} [{check.source}] "
                f"value={check.value} limit={check.limit} "
                f"{'PASS' if check.passed else 'FAIL'}"
            )

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
