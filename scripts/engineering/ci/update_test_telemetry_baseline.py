#!/usr/bin/env python3
"""Write a committed test-telemetry baseline from CI artifacts."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import yaml


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a committed telemetry baseline from coverage.xml and "
            "slowest-tests.json, or from resilient CI diagnostics artifacts."
        )
    )
    parser.add_argument(
        "--coverage-xml",
        default="reports/coverage/coverage.xml",
        help="Path to coverage XML produced by coverage-verify.",
    )
    parser.add_argument(
        "--coverage-percent",
        type=float,
        default=None,
        help=(
            "Explicit coverage percentage fallback when coverage.xml is unavailable, "
            "for example when reconstructing the baseline from CI diagnostics."
        ),
    )
    parser.add_argument(
        "--coverage-log",
        default="",
        help=(
            "Optional log file containing a coverage report line such as "
            "'TOTAL ... 92.81%%'. Used when coverage.xml is unavailable."
        ),
    )
    parser.add_argument(
        "--slowest-json",
        default="reports/test-telemetry/slowest-tests.json",
        help="Path to slow-test telemetry JSON produced by duration-telemetry.",
    )
    parser.add_argument(
        "--junit",
        action="append",
        default=[],
        help=(
            "Optional JUnit XML path used to derive duration telemetry when "
            "slowest-tests.json is unavailable. May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--output-yaml",
        default="configs/quality/test_telemetry_baseline.yaml",
        help="Committed YAML baseline path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/05-engineering/test-telemetry-baseline.md",
        help="Committed Markdown baseline path.",
    )
    parser.add_argument(
        "--source-branch",
        default="main",
        help="Branch from which the telemetry baseline was captured.",
    )
    parser.add_argument(
        "--source-commit",
        default="",
        help="Commit SHA or revision label for the captured baseline.",
    )
    parser.add_argument(
        "--source-run-id",
        default="",
        help="CI run identifier associated with the captured baseline.",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=85.0,
        help="Canonical hard coverage threshold enforced in CI.",
    )
    return parser.parse_args()


def _read_coverage_percent(path: Path) -> float | None:
    if not path.exists():
        return None
    root = ET.parse(path).getroot()
    raw = root.attrib.get("line-rate")
    if raw is None:
        return None
    try:
        return round(float(raw) * 100.0, 2)
    except ValueError:
        return None


def _read_coverage_percent_from_log(path: Path) -> float | None:
    if not path.exists():
        return None
    pattern = re.compile(r"^TOTAL\s+.*?([0-9]+(?:\.[0-9]+)?)%$", re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8"))
    if match is None:
        return None
    try:
        return round(float(match.group(1)), 2)
    except ValueError:
        return None


def _read_slowest_summary(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"total_cases": None, "top_slowest": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    total_cases = payload.get("total_cases")
    top_slowest = payload.get("top_slowest")
    if not isinstance(top_slowest, list):
        top_slowest = []
    return {
        "total_cases": total_cases if isinstance(total_cases, int) else None,
        "top_slowest": top_slowest,
    }


def _derive_slowest_summary_from_junit_paths(
    junit_paths: list[Path],
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for junit_path in junit_paths:
        if not junit_path.exists():
            continue
        root = ET.parse(junit_path).getroot()
        for testcase in root.iter("testcase"):
            duration = float(testcase.attrib.get("time", "0") or 0.0)
            if duration <= 0:
                continue
            case_name = testcase.attrib.get("name", "")
            class_name = testcase.attrib.get("classname", "")
            full_name = f"{class_name}::{case_name}" if class_name else case_name
            rows.append(
                {
                    "source": junit_path.name,
                    "test": full_name or "<unknown>",
                    "duration_s": round(duration, 3),
                }
            )

    rows.sort(key=lambda row: float(row["duration_s"]), reverse=True)
    return {"total_cases": len(rows), "top_slowest": rows[:25]}


def build_baseline_payload(
    *,
    coverage_xml_path: Path,
    coverage_percent: float | None,
    coverage_log_path: Path,
    slowest_json_path: Path,
    junit_paths: list[Path],
    source_branch: str,
    source_commit: str,
    source_run_id: str,
    coverage_threshold: float,
) -> dict[str, object]:
    resolved_coverage_percent = (
        _read_coverage_percent(coverage_xml_path)
        if coverage_percent is None
        else round(float(coverage_percent), 2)
    )
    if resolved_coverage_percent is None:
        resolved_coverage_percent = _read_coverage_percent_from_log(coverage_log_path)

    slowest_summary = _read_slowest_summary(slowest_json_path)
    if slowest_summary["total_cases"] is None and junit_paths:
        slowest_summary = _derive_slowest_summary_from_junit_paths(junit_paths)
    status = (
        "captured"
        if resolved_coverage_percent is not None
        or slowest_summary["total_cases"] is not None
        else "pending_initial_refresh"
    )

    return {
        "version": 1,
        "policy_scope": "test_telemetry_baseline",
        "workflow_path": ".github/workflows/tests.yml",
        "source_branch": source_branch,
        "refreshed_at_utc": datetime.now(UTC).isoformat(),
        "refresh_status": status,
        "source_commit": source_commit or None,
        "source_run_id": source_run_id or None,
        "artifact_inputs": {
            "coverage_xml": str(coverage_xml_path),
            "coverage_log": str(coverage_log_path) if str(coverage_log_path) else None,
            "coverage_percent_fallback": resolved_coverage_percent
            if not coverage_xml_path.exists()
            else None,
            "slowest_tests_json": str(slowest_json_path),
            "junit_inputs": [str(path) for path in junit_paths],
        },
        "coverage": {
            "threshold_percent": coverage_threshold,
            "actual_percent": resolved_coverage_percent,
            "threshold_satisfied": (
                None
                if resolved_coverage_percent is None
                else resolved_coverage_percent >= coverage_threshold
            ),
        },
        "duration_telemetry": slowest_summary,
    }


def render_baseline_markdown(payload: dict[str, object]) -> str:
    coverage = payload["coverage"]
    duration = payload["duration_telemetry"]
    source_commit = payload.get("source_commit") or "pending"
    source_run_id = payload.get("source_run_id") or "pending"
    coverage_actual = coverage["actual_percent"]
    coverage_display = (
        "pending"
        if coverage_actual is None
        else f"{float(coverage_actual):.2f}%"
    )
    total_cases = duration["total_cases"]
    total_cases_display = "pending" if total_cases is None else str(total_cases)

    lines = [
        "______________________________________________________________________",
        "",
        "Version: 1.0.0",
        "Status: active",
        "Class: published",
        "Owner: BioETL Team",
        "Reviewers:",
        "",
        "- BioETL Team",
        f"  Last verified: '{datetime.now(UTC).date().isoformat()}'",
        "",
        "______________________________________________________________________",
        "",
        "# Test Telemetry Baseline",
        "",
        "Committed baseline for CI coverage and slow-test telemetry so engineering",
        "audits do not depend only on ephemeral GitHub artifact retention.",
        "This baseline is the committed evidence companion for the live CI hard gate",
        "`coverage-verify`; historical `test-health` rollups remain non-blocking",
        "trend evidence only.",
        "",
        "## Current Authoritative Baseline",
        "",
        "- Merge-blocking truth comes from live CI status and `coverage-verify`.",
        "- This document preserves the committed baseline snapshot so audits do not",
        "  rely only on expiring workflow artifacts.",
        "",
        "## Baseline Snapshot",
        "",
        f"- Source branch: `{payload['source_branch']}`",
        f"- Source commit: `{source_commit}`",
        f"- Source run id: `{source_run_id}`",
        f"- Refresh status: `{payload['refresh_status']}`",
        f"- Refreshed at (UTC): `{payload['refreshed_at_utc']}`",
        "",
        "## Coverage",
        "",
        f"- Hard threshold: `{float(coverage['threshold_percent']):.1f}%`",
        f"- Actual coverage: `{coverage_display}`",
        f"- Threshold satisfied: `{coverage['threshold_satisfied']}`",
        "",
        "## Duration Telemetry",
        "",
        f"- Total collected test cases: `{total_cases_display}`",
        "",
        "### Top Slowest Tests",
        "",
    ]

    top_slowest = duration["top_slowest"]
    if isinstance(top_slowest, list) and top_slowest:
        lines.extend(
            [
                "| Rank | Duration (s) | Test | Source |",
                "|---:|---:|---|---|",
            ]
        )
        for index, row in enumerate(top_slowest[:10], start=1):
            if not isinstance(row, dict):
                continue
            test_name = row.get("test", "unknown")
            source = row.get("source", "unknown")
            duration_s = row.get("duration_s", "unknown")
            lines.append(
                f"| {index} | `{duration_s}` | `{test_name}` | `{source}` |"
            )
    else:
        lines.append(
            "No committed slow-test baseline is present yet. Refresh from a main-branch "
            "CI run using `python -m scripts.engineering.ci.update_test_telemetry_baseline`."
        )

    lines.extend(
        [
            "",
            "## Refresh Procedure",
            "",
            "1. Preferred path: download `reports/coverage/coverage.xml` and "
            "`reports/test-telemetry/slowest-tests.json` from a main-branch CI run.",
            "2. Fallback path: use resilient CI diagnostics artifacts "
            "(`junit_parallel.xml`, `junit_serial.xml`, and the coverage `TOTAL` line "
            "from `parallel.log`) when the direct coverage artifact expired.",
            "3. Run `python -m scripts.engineering.ci.update_test_telemetry_baseline "
            "--source-commit <sha> --source-run-id <run-id> ...` with either direct "
            "artifacts or fallback diagnostics inputs.",
            "4. Commit the updated YAML and Markdown baseline together.",
            "",
        ]
    )
    return "\n".join(lines)


def write_baseline_outputs(
    *,
    payload: dict[str, object],
    output_yaml_path: Path,
    output_md_path: Path,
) -> None:
    output_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_yaml_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    output_md_path.write_text(
        render_baseline_markdown(payload),
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    payload = build_baseline_payload(
        coverage_xml_path=Path(args.coverage_xml),
        coverage_percent=args.coverage_percent,
        coverage_log_path=Path(args.coverage_log),
        slowest_json_path=Path(args.slowest_json),
        junit_paths=[Path(path) for path in args.junit],
        source_branch=args.source_branch,
        source_commit=args.source_commit,
        source_run_id=args.source_run_id,
        coverage_threshold=args.coverage_threshold,
    )
    write_baseline_outputs(
        payload=payload,
        output_yaml_path=Path(args.output_yaml),
        output_md_path=Path(args.output_md),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
