#!/usr/bin/env python3
"""Write telemetry from CI artifacts or a verified complete local measurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.common.repo_paths import REPO_ROOT
from scripts.engineering.ci.junit_duration_summary import (
    derive_summary as _derive_slowest_summary_from_junit_paths,
)

BRANCH_TELEMETRY_DIR = Path("reports/test-telemetry")
CANONICAL_COVERAGE_XML = "reports/coverage/coverage.xml"
CANONICAL_SLOWEST_TESTS_JSON = "reports/test-telemetry/slowest-tests.json"
DEFAULT_COVERAGE_THRESHOLD = 85.0
TELEMETRY_FRESHNESS_MAX_AGE_DAYS = 45
UNKNOWN_LABEL = "<unknown>"
SUPPORTED_SOURCE_EVENTS = (
    "pull_request",
    "push",
    "workflow_dispatch",
    "schedule",
    "local_coverage_verify",
)

# Coverage, JUnit, YAML, and JSON inputs are heterogeneous external artifacts.
# Keep their dynamic values confined to this report-materialization boundary.
type TelemetryPayload = dict[str, Any]


def compute_test_telemetry_source_tree_sha256(repo_root: Path = REPO_ROOT) -> str:
    """Hash maintained test sources and lane policy, excluding generated evidence.

    Newlines are normalized to LF so Windows working trees with CRLF smudge
    match Linux CI checkouts (eol=lf in .gitattributes).
    """
    paths = list((repo_root / "tests").rglob("*.py"))
    paths.extend(
        repo_root / path
        for path in (
            "pyproject.toml",
            "configs/quality/test_matrix.yaml",
            ".github/workflows/tests.yml",
            "scripts/engineering/ci/junit_duration_summary.py",
        )
    )
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        if not path.exists():
            continue
        digest.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        payload = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(payload)
        digest.update(b"\0")
    source_tree_sha256 = digest.hexdigest()
    print(f"[test-telemetry] source_tree_sha256={source_tree_sha256}")
    return source_tree_sha256


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a committed telemetry baseline from coverage.xml and "
            "slowest-tests.json, or from resilient CI diagnostics artifacts."
        )
    )
    parser.add_argument(
        "--local-manifest",
        type=Path,
        help="Complete canonical 17-shard manifest; derives local identity and all inputs.",
    )
    parser.add_argument(
        "--rebind-current-tree",
        action="store_true",
        help="Rehash current audited test inputs while preserving a verified captured run.",
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
        "--source-event",
        choices=SUPPORTED_SOURCE_EVENTS,
        default="push",
        help="GitHub Actions event that produced the captured artifacts.",
    )
    parser.add_argument(
        "--source-run-url",
        default="",
        help="Canonical GitHub Actions URL for the captured source run.",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=None,
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


def _read_coverage_percent_from_log(path: Path | None) -> float | None:
    if path is None or not path.is_file():
        return None
    # Linear TOTAL coverage line (S8786: avoid reluctant .*?).
    pattern = re.compile(r"^TOTAL(?:\s+\S+)+\s+(\d+(?:\.\d+)?)%$", re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8"))
    if match is None:
        return None
    try:
        return round(float(match.group(1)), 2)
    except ValueError:
        return None


def _normalized_execution_context(payload: TelemetryPayload) -> TelemetryPayload:
    execution_context = payload.get("execution_context", {})
    if not isinstance(execution_context, dict):
        return {}
    execution_context = dict(execution_context)
    duration_sums = execution_context.get("junit_testcase_duration_sum_s")
    if (
        not execution_context.get("lane_wall_time_s")
        and isinstance(duration_sums, dict)
        and duration_sums
    ):
        execution_context["lane_wall_time_s"] = dict(duration_sums)
        execution_context["lane_wall_time_source"] = (
            "junit_testcase_duration_sum_fallback"
        )
    return execution_context


def _canonical_local_count(
    payload: TelemetryPayload, execution_context: TelemetryPayload, total_cases: object
) -> bool:
    # The canonical local 17-shard producer already counted non-skipped JUnit
    # records before CI gained this marker. Its provenance distinguishes it
    # from the old inline CI producer's positive-duration-row total.
    local_capture = payload.get("measurement_provenance", {})
    local_skipped_count = execution_context.get("skipped_count")
    return (
        execution_context.get("count_semantics") is None
        and isinstance(total_cases, int)
        and not isinstance(total_cases, bool)
        and total_cases >= 0
        and isinstance(local_skipped_count, int)
        and not isinstance(local_skipped_count, bool)
        and local_skipped_count >= 0
        and payload.get("source_event") == "local_coverage_verify"
        and isinstance(local_capture, dict)
        and local_capture.get("producer") == "run_local_coverage_verify.py"
        and local_capture.get("complete") is True
        and execution_context.get("executed_count") == total_cases
    )


def _validate_non_skipped_counts(
    path: Path, total_cases: object, execution_context: TelemetryPayload
) -> None:
    observed = execution_context.get("observed_count")
    skipped = execution_context.get("skipped_count")
    executed = execution_context.get("executed_count")
    sources = execution_context.get("junit_source_count")
    if not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in (observed, skipped, executed, sources)
    ):
        raise ValueError(f"Inconsistent non-skipped JUnit counts in {path}")
    assert isinstance(observed, int) and isinstance(skipped, int)
    assert isinstance(executed, int) and isinstance(sources, int)
    if (
        skipped > observed
        or observed - skipped != executed
        or (sources == 0 and (total_cases is not None or observed != 0))
        or (
            sources > 0
            and (
                not isinstance(total_cases, int)
                or isinstance(total_cases, bool)
                or total_cases < 0
                or total_cases != executed
            )
        )
    ):
        raise ValueError(f"Inconsistent non-skipped JUnit counts in {path}")


def _read_slowest_summary(path: Path) -> TelemetryPayload:
    if not path.exists():
        return {"total_cases": None, "top_slowest": [], "execution_context": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    total_cases = payload.get("total_cases")
    top_slowest = payload.get("top_slowest")
    if top_slowest is None:
        top_slowest = payload.get("top_slowest_tests")
    if not isinstance(top_slowest, list):
        top_slowest = []
    execution_context = _normalized_execution_context(payload)
    if execution_context.get("count_semantics") == "non_skipped_junit_records":
        _validate_non_skipped_counts(path, total_cases, execution_context)
    elif _canonical_local_count(payload, execution_context, total_cases):
        execution_context["count_semantics"] = "non_skipped_junit_records"
    else:
        # Pre-parity CI JSON used total_cases for timed rows only.
        execution_context["count_semantics"] = "legacy_positive_duration_rows"
        execution_context.pop("executed_count", None)
    return {
        "total_cases": total_cases
        if isinstance(total_cases, int) and not isinstance(total_cases, bool)
        else None,
        "top_slowest": top_slowest,
        "execution_context": execution_context,
    }


def _extract_slowest_zone(test_name: object) -> str:
    """Collapse a pytest node id into a module-level hotspot identifier."""
    if not isinstance(test_name, str) or not test_name.strip():
        return UNKNOWN_LABEL
    return test_name.split("::", 1)[0] or UNKNOWN_LABEL


def _summarize_slowest_zones(
    rows: list[TelemetryPayload],
    *,
    limit: int = 10,
) -> list[TelemetryPayload]:
    """Summarize slow-test hotspots so audits can reason about zones, not only cases."""
    zone_totals: dict[str, TelemetryPayload] = {}
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


def _portable_artifact_path(
    path: Path | None,
    *,
    repo_root: Path = REPO_ROOT,
) -> str | None:
    """Render telemetry inputs without machine-local absolute prefixes.

    Prefer paths relative to the repository root. When the input lives outside
    the repo (for example a tmp checkout used by unit tests that chdir), fall
    back to a path relative to the current working directory before emitting an
    absolute string.
    """
    if path is None:
        return None
    resolved_path = path.resolve(strict=False)
    resolved_root = repo_root.resolve(strict=False)
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        pass
    try:
        return resolved_path.relative_to(Path.cwd().resolve(strict=False)).as_posix()
    except ValueError:
        return str(path)


def _validated_junit_override(
    slowest_summary: TelemetryPayload, junit_paths: list[Path]
) -> TelemetryPayload:
    derived_summary = _derive_slowest_summary_from_junit_paths(junit_paths)
    if slowest_summary["total_cases"] is None:
        return derived_summary

    previous_sources = slowest_summary["execution_context"].get("junit_sources")
    previous_source_count = slowest_summary["execution_context"].get(
        "junit_source_count"
    )
    derived_sources = derived_summary["execution_context"]["junit_sources"]
    if (
        not isinstance(previous_sources, list)
        or not all(isinstance(source, str) for source in previous_sources)
        or len(set(previous_sources)) != len(previous_sources)
        or len(set(derived_sources)) != len(derived_sources)
        or (
            previous_source_count is not None
            and previous_source_count != len(previous_sources)
        )
        or sorted(previous_sources) != sorted(derived_sources)
    ):
        raise ValueError(
            "JUnit inputs do not match the source inventory of the "
            "existing slowest-tests.json; refusing a partial refresh"
        )
    # JUnit determines counts and durations, but it cannot reconstruct the
    # capture's worker configuration or its declared out-of-scope lanes.
    previous_context = slowest_summary["execution_context"]
    derived_context = derived_summary["execution_context"]
    for key in ("worker_mode", "explicit_exclusions"):
        if key in previous_context:
            derived_context[key] = previous_context[key]
    return derived_summary


def build_baseline_payload(
    *,
    coverage_xml_path: Path,
    coverage_percent: float | None,
    coverage_log_path: Path | None,
    slowest_json_path: Path,
    junit_paths: list[Path],
    source_branch: str,
    source_commit: str,
    source_run_id: str,
    coverage_threshold: float,
    source_tree_sha256: str | None = None,
    source_event: str = "push",
    source_run_url: str = "",
    prefer_junit: bool = False,
) -> TelemetryPayload:
    resolved_coverage_percent = (
        _read_coverage_percent(coverage_xml_path)
        if coverage_percent is None
        else round(float(coverage_percent), 2)
    )
    if resolved_coverage_percent is None:
        resolved_coverage_percent = _read_coverage_percent_from_log(coverage_log_path)

    slowest_summary = _read_slowest_summary(slowest_json_path)
    if prefer_junit or (
        junit_paths
        and (
            slowest_summary["total_cases"] is None
            or slowest_summary["execution_context"].get("count_semantics")
            == "legacy_positive_duration_rows"
        )
    ):
        slowest_summary = _validated_junit_override(slowest_summary, junit_paths)
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
        "source_event": source_event,
        "source_run_url": source_run_url or None,
        "source_tree_sha256": source_tree_sha256,
        "freshness_guard": {
            "timestamp_field": "refreshed_at_utc",
            "max_age_days": TELEMETRY_FRESHNESS_MAX_AGE_DAYS,
        },
        "artifact_inputs": {
            "coverage_xml": CANONICAL_COVERAGE_XML,
            "coverage_log": _portable_artifact_path(coverage_log_path),
            "coverage_percent_fallback": resolved_coverage_percent
            if not coverage_xml_path.exists()
            else None,
            "slowest_tests_json": CANONICAL_SLOWEST_TESTS_JSON,
            "junit_inputs": [_portable_artifact_path(path) for path in junit_paths],
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
            "count_semantics": slowest_summary.get("execution_context", {}).get(
                "count_semantics", "unknown"
            ),
            "top_slowest": top_slowest,
            "top_slowest_zones": _summarize_slowest_zones(top_slowest),
            "execution_context": slowest_summary.get("execution_context", {}),
        },
    }


def _format_slowest_test_table_rows(
    rows: object,
    *,
    limit: int,
    duration_backticks: bool,
) -> list[str]:
    if not isinstance(rows, list) or not rows:
        return []
    lines = [
        "| Rank | Duration (s) | Test | Source |",
        "|---:|---:|---|---|",
    ]
    for index, row in enumerate(rows[:limit], start=1):
        if not isinstance(row, dict):
            continue
        duration_s = row.get("duration_s", "unknown")
        duration_cell = f"`{duration_s}`" if duration_backticks else str(duration_s)
        lines.append(
            f"| {index} | {duration_cell} | "
            f"`{row.get('test', 'unknown')}` | `{row.get('source', 'unknown')}` |"
        )
    return lines


def _format_slowest_zone_table_rows(rows: object, *, limit: int = 10) -> list[str]:
    if not isinstance(rows, list) or not rows:
        return []
    lines = [
        "| Rank | Zone | Tests | Total Duration (s) | Max Duration (s) |",
        "|---:|---|---:|---:|---:|",
    ]
    for index, row in enumerate(rows[:limit], start=1):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| {index} | `{row.get('zone', UNKNOWN_LABEL)}` | "
            f"{row.get('test_count', 'unknown')} | "
            f"{row.get('total_duration_s', 'unknown')} | "
            f"{row.get('max_duration_s', 'unknown')} |"
        )
    return lines


def _no_duration_message(duration: TelemetryPayload) -> str:
    context = duration.get("execution_context", {})
    if context.get("junit_source_count") == 0:
        return "No JUnit telemetry sources are available."
    if "observed_count" in context:
        if context["observed_count"] > 0:
            return "JUnit testcase records are present; none has a non-skipped positive duration."
        return "JUnit sources contain no testcase records."
    if duration.get("total_cases") is not None:
        return "No non-skipped positive testcase durations were measured."
    return "No committed slow-test telemetry is available yet."


def render_baseline_markdown(payload: TelemetryPayload) -> str:
    coverage = payload["coverage"]
    duration = payload["duration_telemetry"]
    source_commit = payload.get("source_commit") or "pending"
    source_run_id = payload.get("source_run_id") or "pending"
    source_event = payload.get("source_event") or "pending"
    source_run_url = payload.get("source_run_url") or "pending"
    coverage_actual = coverage["actual_percent"]
    coverage_display = (
        "pending" if coverage_actual is None else f"{float(coverage_actual):.2f}%"
    )
    total_cases = duration["total_cases"]
    total_cases_display = "pending" if total_cases is None else str(total_cases)
    legacy_count = duration.get("count_semantics") == "legacy_positive_duration_rows"
    count_label = (
        "Legacy positive-duration testcase rows"
        if legacy_count
        else "Total executed test cases"
    )
    count_explanation = (
        ["- Legacy timed-row count cannot establish non-skipped testcase records."]
        if legacy_count
        else [
            "- Executed means observed non-skipped JUnit testcase records, not",
            "  collection count or distinct logical tests. Error records can describe",
            "  setup or collection failures rather than a test body run.",
        ]
    )
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
        f"- Source event: `{source_event}`",
        f"- Source run URL: `{source_run_url}`",
        f"- Source tree sha256: `{payload.get('source_tree_sha256') or 'pending'}`",
        f"- Refresh status: `{payload['refresh_status']}`",
        f"- Refreshed at (UTC): `{payload['refreshed_at_utc']}`",
        "",
        "## Branch-accurate provenance (#5729)",
        "",
        "- Continuous identity is `source_tree_sha256` over `tests/**/*.py`,",
        "  `pyproject.toml`, `configs/quality/test_matrix.yaml`,",
        "  `.github/workflows/tests.yml`, and the live JUnit producer",
        "  `scripts/engineering/ci/junit_duration_summary.py`.",
        "- `measurement_provenance.head` and `test_tree_sha256` retain the captured",
        "  run identity when the current audited test tree advances later.",
        "- Freshness uses live UTC (injectable via `BIOETL_TELEMETRY_REFERENCE_NOW`)",
        "  and rejects future/stale `refreshed_at_utc` values.",
        "- `source_commit` must remain an ancestor of HEAD or have a reviewed squash",
        "  bridge in `reports/test-telemetry/squash-provenance.json`. A bridge keeps",
        "  the real captured source/run and requires equal PR/merge trees, source",
        "  ancestry in the PR, merge ancestry in HEAD and unchanged runtime/test inputs.",
        "- Reviewed squash receipts retain hash-verified Git commit/tree objects",
        "  for offline validation when old PR commits are absent from a fresh clone.",
        "  If a shallow checkout's HEAD is newer than the squash merge, unshallow",
        "  it first so merge ancestry and the merged tree can be verified locally.",
        "- To produce a receipt for an existing local capture, run",
        "  `python -m scripts.engineering.ci.test_telemetry_provenance --measurement-repo-root",
        "  <original-worktree> --local-manifest <manifest.json> --pull-request <merged-PR>`.",
        "  The generator validates the complete 17-shard capture and reads the merged",
        "  PR mapping before writing the bridge. Keep the original capture available.",
        "- For a reviewed local coverage capture, run",
        "  `python -m scripts.engineering.ci.update_test_telemetry_baseline",
        "  --rebind-current-tree`, then the coupled `refresh-ci-drift-families`",
        "  update/check for test-gov, flaky-fingerprint, telemetry and evidence.",
        "  Non-local captures require regeneration from their source artifacts.",
        "- New captures use `verification_mode: live_github`: resolve the recorded",
        "  PR's actual merge with read-only GitHub GETs after squash. Never stamp a",
        "  future merge SHA. API failure, unmerged PRs, changed inputs and incomplete",
        "  compare responses fail closed; the live fingerprint/freshness guards remain.",
        "- Reviewed snapshots retain `local_single_host` trust; they are not signed",
        "  vendor attestations or CI execution receipts. Exact `source_commit == HEAD`",
        "  remains opt-in via `BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD=1`.",
        "- GitHub evidence from a non-main branch requires `pull_request`;",
        "  its run URL and id remain independently auditable.",
        "- `--local-manifest <path>` accepts only a complete canonical 17-shard run",
        "  with matching source/test hashes, reachable commit, XML/JUnit digests,",
        "  zero failures/errors and both 85% gates passed. Identity and inputs",
        "  are derived from that manifest; cached CI summaries are never reused.",
        "- Local captures use `source_event: local_coverage_verify`, a `local-` run",
        "  id and no GitHub run URL. Trust remains `local_single_host`;",
        "  `CI=BLOCKED_EXTERNAL_PERMANENT` never becomes CI PASS or lifecycle ADMIT.",
        "- Refresh command:",
        "  `python -m scripts.engineering.ci.update_test_telemetry_baseline`",
        "  `--source-commit <sha> --source-run-id <run-id>`",
        "  `--source-event <event> --source-run-url <url>`.",
        "",
        "## Coverage",
        "",
        f"- Hard threshold: `{float(coverage['threshold_percent']):.1f}%`",
        f"- Actual coverage: `{coverage_display}`",
        f"- Threshold satisfied: `{coverage['threshold_satisfied']}`",
        "",
        "## Duration Telemetry",
        "",
        f"- {count_label}: `{total_cases_display}`",
        *count_explanation,
        "- Only measured positive durations enter the slowest-test ranking.",
        "  Older CI timed-row totals are not directly comparable with this count.",
        f"- Freshness guard: `<={int(freshness_guard['max_age_days'])} days` via "
        f"`{freshness_guard['timestamp_field']}`",
        "",
        "### Top Slowest Tests",
        "",
    ]

    top_slowest_lines = _format_slowest_test_table_rows(
        duration["top_slowest"],
        limit=10,
        duration_backticks=True,
    )
    if top_slowest_lines:
        lines.extend(top_slowest_lines)
    else:
        lines.append(_no_duration_message(duration))

    lines.extend(["", "### Top Slow Zones", ""])
    zone_lines = _format_slowest_zone_table_rows(duration.get("top_slowest_zones"))
    if zone_lines:
        lines.extend(zone_lines)
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
            "4. A legacy JSON timed-row count requires raw `--junit` inputs for "
            "the complete recorded source inventory; the updater rejects a "
            "partial or legacy-only refresh before writing outputs.",
            "5. Commit the updated baseline and branch-consumable telemetry "
            "summary layer together.",
            "",
        ]
    )
    return "\n".join(lines)


def render_branch_telemetry_markdown(payload: TelemetryPayload) -> str:
    """Render committed slow-test summary as a lightweight branch-readable report."""
    duration = payload["duration_telemetry"]
    total_cases = duration["total_cases"]
    total_cases_display = "pending" if total_cases is None else str(total_cases)
    legacy_count = duration.get("count_semantics") == "legacy_positive_duration_rows"
    count_label = (
        "Legacy positive-duration testcase rows"
        if legacy_count
        else "Executed test cases"
    )
    count_explanation = (
        ["Legacy timed-row count cannot establish non-skipped testcase records."]
        if legacy_count
        else [
            "Executed counts non-skipped JUnit records, including zero or missing",
            "duration; duplicate identities remain separate records. This is not a",
            "collection count. Older CI timed-row totals are not directly comparable.",
        ]
    )

    lines = [
        "# Slowest Tests",
        "",
        f"Source commit: `{payload.get('source_commit') or 'pending'}`",
        f"Source run id: `{payload.get('source_run_id') or 'pending'}`",
        f"Source event: `{payload.get('source_event') or 'pending'}`",
        f"Source run URL: `{payload.get('source_run_url') or 'pending'}`",
        f"Refresh status: `{payload['refresh_status']}`",
        f"{count_label}: `{total_cases_display}`",
        *count_explanation,
        f"Freshness guard: `<={int(payload['freshness_guard']['max_age_days'])} days`",
        "",
    ]
    top_slowest_lines = _format_slowest_test_table_rows(
        duration["top_slowest"],
        limit=25,
        duration_backticks=False,
    )
    if top_slowest_lines:
        lines.extend(top_slowest_lines)
    else:
        lines.append(_no_duration_message(duration))
    lines.extend(["", "## Top Slow Zones", ""])
    zone_lines = _format_slowest_zone_table_rows(duration.get("top_slowest_zones"))
    if zone_lines:
        lines.extend(zone_lines)
    else:
        lines.append("No committed slow-zone summary is available yet.")
    lines.append("")
    return "\n".join(lines)


def build_branch_telemetry_reports(payload: TelemetryPayload) -> dict[str, str]:
    """Build committed branch-readable telemetry report payloads."""
    coverage = payload["coverage"]
    duration = payload["duration_telemetry"]
    coverage_percent = (
        coverage.get("actual_percent") if isinstance(coverage, dict) else None
    )
    top_slowest = duration["top_slowest"]
    provenance = (
        {"measurement_provenance": payload["measurement_provenance"]}
        if "measurement_provenance" in payload
        else {}
    )
    return {
        "coverage-summary.json": json.dumps(
            {
                "source_branch": payload["source_branch"],
                "source_commit": payload.get("source_commit"),
                "source_run_id": payload.get("source_run_id"),
                "source_event": payload.get("source_event"),
                "source_run_url": payload.get("source_run_url"),
                "source_tree_sha256": payload.get("source_tree_sha256"),
                "refreshed_at_utc": payload["refreshed_at_utc"],
                "refresh_status": payload["refresh_status"],
                "coverage_percent": coverage_percent,
                "coverage": coverage,
                **provenance,
            },
            indent=2,
        )
        + "\n",
        "slowest-tests.json": json.dumps(
            {
                "source_branch": payload["source_branch"],
                "source_commit": payload.get("source_commit"),
                "source_run_id": payload.get("source_run_id"),
                "source_event": payload.get("source_event"),
                "source_run_url": payload.get("source_run_url"),
                "source_tree_sha256": payload.get("source_tree_sha256"),
                "refreshed_at_utc": payload["refreshed_at_utc"],
                "refresh_status": payload["refresh_status"],
                "total_cases": duration["total_cases"],
                **(
                    {"count_semantics": duration["count_semantics"]}
                    if "count_semantics" in duration
                    else {}
                ),
                "top_slowest": top_slowest,
                "top_slowest_tests": top_slowest,
                "top_slowest_zones": duration["top_slowest_zones"],
                "execution_context": duration.get("execution_context", {}),
                **provenance,
            },
            indent=2,
        )
        + "\n",
        "slowest-tests.md": render_branch_telemetry_markdown(payload) + "\n",
    }


def merge_existing_baseline_supplemental_fields(
    payload: TelemetryPayload,
    *,
    existing_yaml_path: Path,
) -> TelemetryPayload:
    """Preserve non-generated governance fields that live beside the baseline."""
    if not existing_yaml_path.exists():
        return payload

    existing_payload = yaml.safe_load(existing_yaml_path.read_text(encoding="utf-8"))
    if not isinstance(existing_payload, dict):
        return payload

    merged: TelemetryPayload = dict(payload)
    for field_name in (
        "slow_governance_cache_probe",
        "branch_accurate_guard",
        "historical_snapshots",
    ):
        if field_name not in merged and field_name in existing_payload:
            merged[field_name] = existing_payload[field_name]
    if payload.get("source_event") == "local_coverage_verify" and (
        existing_payload.get("source_event") != "local_coverage_verify"
    ):
        historical = dict(existing_payload)
        historical.pop("historical_snapshots", None)
        merged["historical_snapshots"] = [
            *merged.get("historical_snapshots", []),
            {
                "provenance_status": "historical_unverified_ci_binding",
                "baseline": historical,
            },
        ]
    return merged


def write_branch_telemetry_reports(
    *,
    payload: TelemetryPayload,
    output_dir: Path = BRANCH_TELEMETRY_DIR,
) -> None:
    """Write committed branch-readable telemetry summaries under reports/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative_name, text in build_branch_telemetry_reports(payload).items():
        (output_dir / relative_name).write_text(text, encoding="utf-8")


def write_baseline_outputs(
    *,
    payload: TelemetryPayload,
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


def _rebind_current_tree(args: argparse.Namespace) -> int:
    """Preserve only metrics bound to the reviewed capture while rehashing tests."""
    import subprocess

    from scripts.engineering.ci.test_telemetry_provenance import (
        capture_metrics_are_bound,
        source_commit_is_reachable,
    )
    from scripts.engineering.common.repo_paths import resolve_output_path

    if any(
        (
            args.local_manifest,
            args.source_commit,
            args.source_run_id,
            args.source_run_url,
            args.source_branch != "main",
            args.source_event != "push",
            args.coverage_percent is not None,
            args.coverage_xml != CANONICAL_COVERAGE_XML,
            args.coverage_log,
            args.slowest_json != CANONICAL_SLOWEST_TESTS_JSON,
            args.junit,
            args.coverage_threshold is not None,
        )
    ):
        raise ValueError("Rebind uses only the existing verified capture")
    output_yaml_path = resolve_output_path(args.output_yaml)
    output_md_path = resolve_output_path(args.output_md)
    payload = yaml.safe_load(output_yaml_path.read_text(encoding="utf-8"))
    if payload.get("source_event") != "local_coverage_verify":
        raise ValueError(
            "Rebind requires a reviewed local coverage capture; "
            "rebuild non-local telemetry from its source artifacts"
        )
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    if not source_commit_is_reachable(payload, REPO_ROOT, head):
        raise ValueError("Captured run lacks proven ancestry or reviewed squash bridge")
    if not capture_metrics_are_bound(payload, REPO_ROOT):
        raise ValueError("Captured telemetry metrics lack a reviewed binding")
    payload["source_tree_sha256"] = compute_test_telemetry_source_tree_sha256()
    write_baseline_outputs(
        payload=payload,
        output_yaml_path=output_yaml_path,
        output_md_path=output_md_path,
    )
    return 0


def main() -> int:
    from scripts.engineering.common.repo_paths import resolve_output_path

    args = _parse_args()
    if args.rebind_current_tree:
        return _rebind_current_tree(args)
    if args.source_event == "local_coverage_verify" and not args.local_manifest:
        raise ValueError("local_coverage_verify requires --local-manifest")
    coverage_xml_path = resolve_output_path(args.coverage_xml)
    coverage_log_path = (
        resolve_output_path(args.coverage_log) if args.coverage_log else None
    )
    slowest_json_path = resolve_output_path(args.slowest_json)
    junit_paths = [resolve_output_path(path) for path in args.junit]
    output_yaml_path = resolve_output_path(args.output_yaml)
    output_md_path = resolve_output_path(args.output_md)
    if args.local_manifest:
        from scripts.engineering.ci.local_test_telemetry import build_local_baseline

        if any(
            (
                args.source_commit,
                args.source_run_id,
                args.source_run_url,
                args.coverage_percent is not None,
                args.coverage_log,
                args.junit,
            )
        ):
            raise ValueError(
                "Local telemetry identity and inputs must come from the manifest"
            )
        payload = build_local_baseline(
            resolve_output_path(str(args.local_manifest)), repo_root=REPO_ROOT
        )
    else:
        payload = build_baseline_payload(
            coverage_xml_path=coverage_xml_path,
            coverage_percent=args.coverage_percent,
            coverage_log_path=coverage_log_path,
            slowest_json_path=slowest_json_path,
            junit_paths=junit_paths,
            source_branch=args.source_branch,
            source_commit=args.source_commit,
            source_run_id=args.source_run_id,
            source_event=args.source_event,
            source_run_url=args.source_run_url,
            coverage_threshold=(
                args.coverage_threshold
                if args.coverage_threshold is not None
                else DEFAULT_COVERAGE_THRESHOLD
            ),
            source_tree_sha256=compute_test_telemetry_source_tree_sha256(),
        )
        if (
            payload["duration_telemetry"]["count_semantics"]
            == "legacy_positive_duration_rows"
        ):
            raise ValueError(
                "Legacy slowest-tests.json requires --junit inputs before "
                "refreshing a captured baseline"
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
