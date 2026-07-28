#!/usr/bin/env python3
"""Write a committed test-telemetry baseline from CI artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import yaml

BRANCH_TELEMETRY_DIR = Path("reports/test-telemetry")
TELEMETRY_FRESHNESS_MAX_AGE_DAYS = 45


def compute_test_telemetry_source_tree_sha256(repo_root: Path = Path(".")) -> str:
    """Hash maintained test sources and lane policy, excluding generated evidence."""
    paths = list((repo_root / "tests").rglob("*.py"))
    paths.extend(
        repo_root / path
        for path in (
            "pyproject.toml",
            "configs/quality/test_matrix.yaml",
            ".github/workflows/tests.yml",
        )
    )
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        if not path.exists():
            continue
        digest.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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
    pattern = re.compile(r"^TOTAL\s+.*?(\d+(?:\.\d+)?)%$", re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8"))
    if match is None:
        return None
    try:
        return round(float(match.group(1)), 2)
    except ValueError:
        return None


def _read_slowest_summary(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"total_cases": None, "top_slowest": [], "execution_context": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    total_cases = payload.get("total_cases")
    top_slowest = payload.get("top_slowest")
    if top_slowest is None:
        top_slowest = payload.get("top_slowest_tests")
    if not isinstance(top_slowest, list):
        top_slowest = []
    return {
        "total_cases": total_cases if isinstance(total_cases, int) else None,
        "top_slowest": top_slowest,
        "execution_context": payload.get("execution_context", {}),
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
    return {
        "total_cases": len(rows),
        "top_slowest": rows[:25],
        "execution_context": {
            "junit_source_count": len([path for path in junit_paths if path.exists()]),
            "junit_sources": [path.name for path in junit_paths if path.exists()],
            "executed_count": len(rows),
            "worker_mode": "caller-declared; see source run metadata",
            "junit_testcase_duration_sum_s": {},
            "explicit_exclusions": [],
        },
    }


def _extract_slowest_zone(test_name: object) -> str:
    """Collapse a pytest node id into a module-level hotspot identifier."""
    if not isinstance(test_name, str) or not test_name.strip():
        return "<unknown>"
    return test_name.split("::", 1)[0] or "<unknown>"


def _summarize_slowest_zones(
    rows: list[dict[str, object]],
    *,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Summarize slow-test hotspots so audits can reason about zones, not only cases."""
    zone_totals: dict[str, dict[str, object]] = {}
    for row in rows:
        zone = _extract_slowest_zone(row.get("test"))
        try:
            duration_s = round(float(row.get("duration_s", 0.0) or 0.0), 3)
        except (TypeError, ValueError):
            duration_s = 0.0

        current = zone_totals.setdefault(
            zone,
            {
                "zone": zone,
                "test_count": 0,
                "total_duration_s": 0.0,
                "max_duration_s": 0.0,
            },
        )
        current["test_count"] = int(current["test_count"]) + 1
        current["total_duration_s"] = round(
            float(current["total_duration_s"]) + duration_s,
            3,
        )
        current["max_duration_s"] = round(
            max(float(current["max_duration_s"]), duration_s),
            3,
        )

    return sorted(
        zone_totals.values(),
        key=lambda row: (
            -float(row["total_duration_s"]),
            -float(row["max_duration_s"]),
            str(row["zone"]),
        ),
    )[:limit]


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
    source_tree_sha256: str | None = None,
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
    top_slowest = slowest_summary["top_slowest"]
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
        "source_tree_sha256": source_tree_sha256,
        "freshness_guard": {
            "timestamp_field": "refreshed_at_utc",
            "max_age_days": TELEMETRY_FRESHNESS_MAX_AGE_DAYS,
        },
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
        "duration_telemetry": {
            "total_cases": slowest_summary["total_cases"],
            "top_slowest": top_slowest,
            "top_slowest_zones": _summarize_slowest_zones(top_slowest),
            "execution_context": slowest_summary.get("execution_context", {}),
        },
    }


def render_baseline_markdown(payload: dict[str, object]) -> str:
    coverage = payload["coverage"]
    duration = payload["duration_telemetry"]
    source_commit = payload.get("source_commit") or "pending"
    source_run_id = payload.get("source_run_id") or "pending"
    coverage_actual = coverage["actual_percent"]
    coverage_display = (
        "pending" if coverage_actual is None else f"{float(coverage_actual):.2f}%"
    )
    total_cases = duration["total_cases"]
    total_cases_display = "pending" if total_cases is None else str(total_cases)
    freshness_guard = payload["freshness_guard"]

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
        f"- Freshness guard: `<={int(freshness_guard['max_age_days'])} days` via "
        f"`{freshness_guard['timestamp_field']}`",
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
            lines.append(f"| {index} | `{duration_s}` | `{test_name}` | `{source}` |")
    else:
        lines.append(
            "No committed slow-test baseline is present yet. Refresh from a main-branch "
            "CI run using `python -m scripts.engineering.ci.update_test_telemetry_baseline`."
        )

    lines.extend(
        [
            "",
            "### Top Slow Zones",
            "",
        ]
    )

    zone_rows = duration.get("top_slowest_zones")
    if isinstance(zone_rows, list) and zone_rows:
        lines.extend(
            [
                "| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |",
                "|---:|---|---:|---:|---:|",
            ]
        )
        for index, row in enumerate(zone_rows[:10], start=1):
            if not isinstance(row, dict):
                continue
            lines.append(
                f"| {index} | `{row.get('zone', '<unknown>')}` | "
                f"{row.get('test_count', 'unknown')} | "
                f"{row.get('total_duration_s', 'unknown')} | "
                f"{row.get('max_duration_s', 'unknown')} |"
            )
    else:
        lines.append("No committed slow-zone summary is available yet.")

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
            "4. Commit the updated baseline and branch-consumable telemetry "
            "summary layer together.",
            "",
        ]
    )
    return "\n".join(lines)


def render_branch_telemetry_markdown(payload: dict[str, object]) -> str:
    """Render committed slow-test summary as a lightweight branch-readable report."""
    duration = payload["duration_telemetry"]
    total_cases = duration["total_cases"]
    rows = duration["top_slowest"]
    zones = duration.get("top_slowest_zones")
    total_cases_display = "pending" if total_cases is None else str(total_cases)

    lines = [
        "# Slowest Tests",
        "",
        f"Source commit: `{payload.get('source_commit') or 'pending'}`",
        f"Source run id: `{payload.get('source_run_id') or 'pending'}`",
        f"Refresh status: `{payload['refresh_status']}`",
        f"Collected test cases: `{total_cases_display}`",
        f"Freshness guard: `<={int(payload['freshness_guard']['max_age_days'])} days`",
        "",
    ]
    if isinstance(rows, list) and rows:
        lines.extend(
            [
                "| Rank | Duration (s) | Test | Source |",
                "|---:|---:|---|---|",
            ]
        )
        for index, row in enumerate(rows[:25], start=1):
            if not isinstance(row, dict):
                continue
            lines.append(
                f"| {index} | {row.get('duration_s', 'unknown')} | "
                f"`{row.get('test', 'unknown')}` | `{row.get('source', 'unknown')}` |"
            )
    else:
        lines.append("No committed slow-test telemetry is available yet.")
    lines.extend(["", "## Top Slow Zones", ""])
    if isinstance(zones, list) and zones:
        lines.extend(
            [
                "| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |",
                "|---:|---|---:|---:|---:|",
            ]
        )
        for index, row in enumerate(zones[:10], start=1):
            if not isinstance(row, dict):
                continue
            lines.append(
                f"| {index} | `{row.get('zone', '<unknown>')}` | "
                f"{row.get('test_count', 'unknown')} | "
                f"{row.get('total_duration_s', 'unknown')} | "
                f"{row.get('max_duration_s', 'unknown')} |"
            )
    else:
        lines.append("No committed slow-zone summary is available yet.")
    lines.append("")
    return "\n".join(lines)


def build_branch_telemetry_reports(payload: dict[str, object]) -> dict[str, str]:
    """Build committed branch-readable telemetry report payloads."""
    coverage = payload["coverage"]
    duration = payload["duration_telemetry"]
    coverage_percent = (
        coverage.get("actual_percent") if isinstance(coverage, dict) else None
    )
    top_slowest = duration["top_slowest"]
    return {
        "coverage-summary.json": json.dumps(
            {
                "source_branch": payload["source_branch"],
                "source_commit": payload.get("source_commit"),
                "source_run_id": payload.get("source_run_id"),
                "source_tree_sha256": payload.get("source_tree_sha256"),
                "refreshed_at_utc": payload["refreshed_at_utc"],
                "refresh_status": payload["refresh_status"],
                "coverage_percent": coverage_percent,
                "coverage": coverage,
            },
            indent=2,
        )
        + "\n",
        "slowest-tests.json": json.dumps(
            {
                "source_branch": payload["source_branch"],
                "source_commit": payload.get("source_commit"),
                "source_run_id": payload.get("source_run_id"),
                "source_tree_sha256": payload.get("source_tree_sha256"),
                "refreshed_at_utc": payload["refreshed_at_utc"],
                "refresh_status": payload["refresh_status"],
                "total_cases": duration["total_cases"],
                "top_slowest": top_slowest,
                "top_slowest_tests": top_slowest,
                "top_slowest_zones": duration["top_slowest_zones"],
                "execution_context": duration.get("execution_context", {}),
            },
            indent=2,
        )
        + "\n",
        "slowest-tests.md": render_branch_telemetry_markdown(payload) + "\n",
    }


def merge_existing_baseline_supplemental_fields(
    payload: dict[str, object],
    *,
    existing_yaml_path: Path,
) -> dict[str, object]:
    """Preserve non-generated governance fields that live beside the baseline."""
    if not existing_yaml_path.exists():
        return payload

    existing_payload = yaml.safe_load(existing_yaml_path.read_text(encoding="utf-8"))
    if not isinstance(existing_payload, dict):
        return payload

    merged = dict(payload)
    for field_name in ("slow_governance_cache_probe",):
        if field_name not in merged and field_name in existing_payload:
            merged[field_name] = existing_payload[field_name]
    return merged


def write_branch_telemetry_reports(
    *,
    payload: dict[str, object],
    output_dir: Path = BRANCH_TELEMETRY_DIR,
) -> None:
    """Write committed branch-readable telemetry summaries under reports/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative_name, text in build_branch_telemetry_reports(payload).items():
        (output_dir / relative_name).write_text(text, encoding="utf-8")


def write_baseline_outputs(
    *,
    payload: dict[str, object],
    output_yaml_path: Path,
    output_md_path: Path,
    branch_reports_dir: Path = BRANCH_TELEMETRY_DIR,
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
    write_branch_telemetry_reports(payload=payload, output_dir=branch_reports_dir)


def main() -> int:
    from scripts.engineering.common.repo_paths import resolve_output_path

    args = _parse_args()
    coverage_xml_path = resolve_output_path(args.coverage_xml)
    coverage_log_path = resolve_output_path(args.coverage_log)
    slowest_json_path = resolve_output_path(args.slowest_json)
    junit_paths = [resolve_output_path(path) for path in args.junit]
    output_yaml_path = resolve_output_path(args.output_yaml)
    output_md_path = resolve_output_path(args.output_md)
    payload = build_baseline_payload(
        coverage_xml_path=coverage_xml_path,
        coverage_percent=args.coverage_percent,
        coverage_log_path=coverage_log_path,
        slowest_json_path=slowest_json_path,
        junit_paths=junit_paths,
        source_branch=args.source_branch,
        source_commit=args.source_commit,
        source_run_id=args.source_run_id,
        coverage_threshold=args.coverage_threshold,
        source_tree_sha256=compute_test_telemetry_source_tree_sha256(),
    )
    payload = merge_existing_baseline_supplemental_fields(
        payload,
        existing_yaml_path=output_yaml_path,
    )
    write_baseline_outputs(
        payload=payload,
        output_yaml_path=output_yaml_path,
        output_md_path=output_md_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
