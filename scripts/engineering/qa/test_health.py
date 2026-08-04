#!/usr/bin/env python3
"""Test-health lane wrapper, JUnit aggregation, and history rollup."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import yaml

ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
CLASSIFIERS_PATH = ROOT / "configs" / "quality" / "test_health_classifiers.yaml"
BASELINE_PATH = ROOT / "configs" / "quality" / "test_telemetry_baseline.yaml"
DEFAULT_REPORTS_DIR = ROOT / "reports" / "quality" / "test-runs"


@dataclass(frozen=True)
class RunPlan:
    """Concrete command and artifact paths for one logical test-health run."""

    suite: str
    run_id: str
    backend: str
    command: list[str]
    junit_paths: list[Path]
    junit_dir: Path | None
    summary_path: Path


def _load_lanes(matrix_path: Path = MATRIX_PATH) -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load(matrix_path.read_text(encoding="utf-8")) or {}
    return payload.get("test_lanes", {}).get("lanes", {})


@lru_cache(maxsize=8)
def _load_failure_classifiers(
    config_path: Path = CLASSIFIERS_PATH,
) -> tuple[tuple[tuple[str, re.Pattern[str]], ...], str, str, str]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    classifiers = payload.get("classifiers", [])
    if not isinstance(classifiers, list) or not classifiers:
        raise ValueError(f"{config_path}: classifiers must be a non-empty list")

    compiled: list[tuple[str, re.Pattern[str]]] = []
    for item in classifiers:
        if not isinstance(item, dict):
            raise ValueError(f"{config_path}: classifier entries must be mappings")
        category = item.get("category")
        pattern = item.get("pattern")
        if not isinstance(category, str) or not category:
            raise ValueError(f"{config_path}: classifier category is required")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError(f"{config_path}: classifier pattern is required")
        compiled.append((category, re.compile(pattern, re.I)))

    return (
        tuple(compiled),
        str(payload.get("default_error_classification", "setup_error")),
        str(payload.get("default_failure_classification", "assertion")),
        str(payload.get("default_unknown_classification", "unknown")),
    )


def _split_passthrough(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    separator = argv.index("--")
    return argv[:separator], argv[separator + 1 :]


def _default_run_id(suite: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{suite}-{stamp}"


def _unique_run_id(reports_dir: Path, run_id: str) -> str:
    """Return a run ID that preserves existing local history artifacts."""
    if not (reports_dir / f"{run_id}.json").exists():
        return run_id

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = f"{run_id}-{timestamp}"
    index = 2
    while (reports_dir / f"{candidate}.json").exists():
        candidate = f"{run_id}-{timestamp}-{index}"
        index += 1
    return candidate


def _relative_to_root(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _git_sha() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _with_pythonpath_src(env: Mapping[str, str]) -> dict[str, str]:
    updated = dict(env)
    src = str(ROOT / "src")
    parts = (
        [] if not updated.get("PYTHONPATH") else updated["PYTHONPATH"].split(os.pathsep)
    )
    if src not in parts:
        parts.insert(0, src)
    updated["PYTHONPATH"] = os.pathsep.join(parts)
    return updated


def _strip_lane_paths(pytest_args: list[str], paths: list[str]) -> list[str]:
    path_set = {path.rstrip("/") for path in paths}
    return [arg for arg in pytest_args if str(arg).rstrip("/") not in path_set]


def build_run_plan(
    *,
    suite: str,
    run_id: str,
    reports_dir: Path,
    runner_args: list[str],
    pytest_extra: list[str],
    skip_preflight: bool,
    lanes: dict[str, dict[str, Any]] | None = None,
) -> RunPlan:
    """Build the backend command for a logical test-health lane."""
    lane_map = lanes if lanes is not None else _load_lanes()
    if suite not in lane_map:
        available = ", ".join(sorted(lane_map))
        raise ValueError(f"Unknown test-health suite '{suite}'. Available: {available}")

    lane = lane_map[suite]
    backend = str(lane["runner_backend"])
    runner = str(lane["runner"])
    summary_path = reports_dir / f"{run_id}.json"
    junit_root = reports_dir / "junit"

    command = ["bash", runner]
    if skip_preflight:
        command.append("--skip-preflight")

    if backend == "run_pytest_sharded":
        junit_dir = junit_root / run_id
        junit_paths: list[Path] = []
        command.extend(str(arg) for arg in lane.get("runner_options", []))
        command.extend(runner_args)
        command.extend(["--junit-dir", _relative_to_root(junit_dir), "--"])
        pytest_args = _strip_lane_paths(
            [str(arg) for arg in lane.get("pytest_args", [])],
            [str(path) for path in lane.get("paths", [])],
        )
        command.extend([*pytest_args, *pytest_extra])
    else:
        junit_dir = None
        junit_path = junit_root / f"{run_id}.xml"
        junit_paths = [junit_path]
        command.extend(runner_args)
        command.extend(str(arg) for arg in lane.get("pytest_args", []))
        command.extend(pytest_extra)
        command.append(f"--junitxml={_relative_to_root(junit_path)}")

    return RunPlan(
        suite=suite,
        run_id=run_id,
        backend=backend,
        command=command,
        junit_paths=junit_paths,
        junit_dir=junit_dir,
        summary_path=summary_path,
    )


def _iter_testcases(xml_path: Path) -> list[ElementTree.Element]:
    root = ElementTree.parse(xml_path).getroot()
    if root.tag == "testcase":
        return [root]
    return list(root.iter("testcase"))


def _case_nodeid(case: ElementTree.Element) -> str:
    file_attr = case.attrib.get("file")
    name = case.attrib.get("name", "")
    classname = case.attrib.get("classname", "")
    if file_attr:
        return f"{file_attr}::{name}" if name else file_attr
    if classname and name:
        return f"{classname}::{name}"
    return name or classname or "<unknown>"


def _failure_entry(
    *,
    case: ElementTree.Element,
    child: ElementTree.Element,
    xml_path: Path,
    classifier_config_path: Path,
) -> dict[str, str]:
    message = child.attrib.get("message") or (child.text or "").strip()
    first_line = message.splitlines()[0] if message else ""
    return {
        "nodeid": _case_nodeid(case),
        "file": case.attrib.get("file", ""),
        "phase": child.tag,
        "message": first_line,
        "classification": classify_failure(
            phase=child.tag,
            message=first_line,
            file=case.attrib.get("file", ""),
            classifier_config_path=classifier_config_path,
        ),
        "junit_xml": _relative_to_root(xml_path),
    }


def classify_failure(
    *,
    phase: str,
    message: str,
    file: str = "",
    classifier_config_path: Path = CLASSIFIERS_PATH,
) -> str:
    """Classify test failures using conservative, overrideable heuristics."""
    classifiers, default_error, default_failure, default_unknown = (
        _load_failure_classifiers(classifier_config_path)
    )
    haystack = f"{phase}\n{file}\n{message}"
    phase_lower = phase.lower()
    if phase_lower in {"error", "setup", "teardown"}:
        for category, pattern in classifiers:
            if pattern.search(haystack):
                return category
        return default_error
    for category, pattern in classifiers:
        if pattern.search(haystack):
            return category
    return default_failure if phase_lower == "failure" else default_unknown


def _is_xfail(skipped: ElementTree.Element) -> bool:
    marker = " ".join(
        str(value)
        for value in (
            skipped.attrib.get("type"),
            skipped.attrib.get("message"),
            skipped.text,
        )
        if value
    ).lower()
    return "xfail" in marker


def aggregate_junit(
    *,
    xml_paths: list[Path],
    run_id: str,
    suite: str,
    shards: list[str],
    started_at: str,
    duration_seconds: float,
    command: list[str],
    exit_code: int,
    classifier_config_path: Path = CLASSIFIERS_PATH,
) -> dict[str, Any]:
    """Aggregate one or more pytest JUnit XML files into a run summary."""
    counts = {
        "collected": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    failures: list[dict[str, str]] = []
    cases: list[dict[str, str]] = []

    for xml_path in xml_paths:
        for case in _iter_testcases(xml_path):
            counts["collected"] += 1
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")
            nodeid = _case_nodeid(case)
            file_attr = case.attrib.get("file", "")
            if error is not None:
                counts["errors"] += 1
                cases.append({"nodeid": nodeid, "file": file_attr, "status": "error"})
                failures.append(
                    _failure_entry(
                        case=case,
                        child=error,
                        xml_path=xml_path,
                        classifier_config_path=classifier_config_path,
                    )
                )
            elif failure is not None:
                counts["failed"] += 1
                cases.append({"nodeid": nodeid, "file": file_attr, "status": "failed"})
                failures.append(
                    _failure_entry(
                        case=case,
                        child=failure,
                        xml_path=xml_path,
                        classifier_config_path=classifier_config_path,
                    )
                )
            elif skipped is not None:
                if _is_xfail(skipped):
                    counts["xfailed"] += 1
                    cases.append(
                        {"nodeid": nodeid, "file": file_attr, "status": "xfailed"}
                    )
                else:
                    counts["skipped"] += 1
                    cases.append(
                        {"nodeid": nodeid, "file": file_attr, "status": "skipped"}
                    )
            else:
                counts["passed"] += 1
                cases.append({"nodeid": nodeid, "file": file_attr, "status": "passed"})

    return {
        "run_id": run_id,
        "suite": suite,
        "shards": shards,
        "started_at": started_at,
        "duration_seconds": round(duration_seconds, 3),
        "command": shlex.join(command),
        "git_sha": _git_sha(),
        "ci_job": os.environ.get("GITHUB_JOB") or os.environ.get("CI_JOB_NAME"),
        "exit_code": exit_code,
        "counts": counts,
        "cases": cases,
        "failures": failures,
    }


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _resolve_junit_inputs(junit_paths: list[str], junit_globs: list[str]) -> list[Path]:
    paths = [Path(path) for path in junit_paths]
    for pattern in junit_globs:
        matches = sorted(glob.glob(pattern, recursive=True))
        paths.extend(Path(match) for match in matches)
    return sorted({path for path in paths if path.exists()})


def _junit_duration_seconds(xml_paths: list[Path]) -> float:
    total = 0.0
    for xml_path in xml_paths:
        root = ElementTree.parse(xml_path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        for suite in suites:
            try:
                total += float(suite.attrib.get("time", "0") or 0)
            except ValueError:
                continue
    return total


def _write_junit_summary(
    *,
    suite: str,
    run_id: str,
    reports_dir: Path,
    junit_paths: list[str],
    junit_globs: list[str],
    command: str,
    exit_code: int,
    classifier_config_path: Path,
) -> Path | None:
    xml_paths = _resolve_junit_inputs(junit_paths, junit_globs)
    if not xml_paths:
        print("[test-health] no JUnit XML inputs found", file=sys.stderr)
        return None

    rendered_command = shlex.split(command) if command else ["pytest"]
    payload = aggregate_junit(
        xml_paths=xml_paths,
        run_id=run_id,
        suite=suite,
        shards=[path.stem for path in xml_paths],
        started_at=datetime.now(UTC).isoformat(),
        duration_seconds=_junit_duration_seconds(xml_paths),
        command=rendered_command,
        exit_code=exit_code,
        classifier_config_path=classifier_config_path,
    )
    summary_path = reports_dir / f"{run_id}.json"
    _write_summary(summary_path, payload)
    print(f"[test-health] summary: {_relative_to_root(summary_path)}")
    return summary_path


def _discover_junit_paths(plan: RunPlan) -> tuple[list[Path], list[str]]:
    if plan.junit_dir is not None:
        paths = sorted(plan.junit_dir.glob("*.xml"))
        return paths, [path.stem for path in paths]
    return [path for path in plan.junit_paths if path.exists()], []


def _run_tests(argv: list[str]) -> int:
    wrapper_args, pytest_extra = _split_passthrough(argv)
    parser = argparse.ArgumentParser(description="Run a named test-health lane.")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument(
        "--classifier-config",
        type=Path,
        default=CLASSIFIERS_PATH,
        help="YAML failure-classifier rules.",
    )
    args, runner_args = parser.parse_known_args(wrapper_args)

    run_id = _unique_run_id(
        args.reports_dir,
        args.run_id or _default_run_id(args.suite),
    )
    plan = build_run_plan(
        suite=args.suite,
        run_id=run_id,
        reports_dir=args.reports_dir,
        runner_args=runner_args,
        pytest_extra=pytest_extra,
        skip_preflight=args.skip_preflight,
    )

    print(f"[test-health] suite={plan.suite} run_id={plan.run_id}")
    print(f"[test-health] command: {shlex.join(plan.command)}")
    if args.dry_run:
        return 0

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "junit").mkdir(parents=True, exist_ok=True)
    if plan.junit_dir is not None:
        plan.junit_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(UTC)
    start_time = time.monotonic()
    completed = subprocess.run(
        plan.command,
        cwd=ROOT,
        env={
            **_with_pythonpath_src(os.environ),
            "BIOETL_TEST_HEALTH_WRAPPER": "1",
        },
        check=False,
    )
    duration = time.monotonic() - start_time
    xml_paths, shards = _discover_junit_paths(plan)
    if xml_paths:
        payload = aggregate_junit(
            xml_paths=xml_paths,
            run_id=plan.run_id,
            suite=plan.suite,
            shards=shards,
            started_at=started.isoformat(),
            duration_seconds=duration,
            command=plan.command,
            exit_code=completed.returncode,
            classifier_config_path=args.classifier_config,
        )
    else:
        payload = {
            "run_id": plan.run_id,
            "suite": plan.suite,
            "shards": shards,
            "started_at": started.isoformat(),
            "duration_seconds": round(duration, 3),
            "command": shlex.join(plan.command),
            "git_sha": _git_sha(),
            "ci_job": os.environ.get("GITHUB_JOB") or os.environ.get("CI_JOB_NAME"),
            "exit_code": completed.returncode,
            "counts": {
                "collected": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "xfailed": 0,
                "xpassed": 0,
            },
            "failures": [],
            "warnings": ["No JUnit XML files were found for this run."],
        }
    _write_summary(plan.summary_path, payload)
    print(f"[test-health] summary: {_relative_to_root(plan.summary_path)}")
    return completed.returncode


def _summarize_junit(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate existing pytest JUnit XML into a test-health summary."
    )
    parser.add_argument("--suite", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--junit", action="append", default=[])
    parser.add_argument("--junit-glob", action="append", default=[])
    parser.add_argument("--command", default="")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument(
        "--classifier-config",
        type=Path,
        default=CLASSIFIERS_PATH,
        help="YAML failure-classifier rules.",
    )
    args = parser.parse_args(argv)

    run_id = _unique_run_id(
        args.reports_dir,
        args.run_id or _default_run_id(args.suite),
    )
    summary_path = _write_junit_summary(
        suite=args.suite,
        run_id=run_id,
        reports_dir=args.reports_dir,
        junit_paths=args.junit,
        junit_globs=args.junit_glob,
        command=args.command,
        exit_code=args.exit_code,
        classifier_config_path=args.classifier_config,
    )
    if summary_path is None:
        return 2
    return 0


def _read_run_summaries(reports_dir: Path, limit: int) -> list[dict[str, Any]]:
    files = sorted(
        (path for path in reports_dir.glob("*.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:limit]
    return [json.loads(path.read_text(encoding="utf-8")) for path in files]


def _green_run(run: dict[str, Any]) -> bool:
    counts = run.get("counts", {})
    failed_tests = int(counts.get("failed", 0)) + int(counts.get("errors", 0))
    return failed_tests == 0 and int(run.get("exit_code", 0)) == 0


def _case_outcomes(runs: list[dict[str, Any]]) -> dict[str, set[str]]:
    outcomes: dict[str, set[str]] = {}
    for run in runs:
        failures = {
            str(failure.get("nodeid", "<unknown>"))
            for failure in run.get("failures", [])
        }
        for nodeid in failures:
            outcomes.setdefault(nodeid, set()).add("failed")
        for case in run.get("cases", []):
            nodeid = str(case.get("nodeid", "<unknown>"))
            status = str(case.get("status", "unknown"))
            if status in {"passed", "failed", "error"}:
                outcomes.setdefault(nodeid, set()).add(status)
    return outcomes


def build_rollup(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate test-health history metrics from run summaries."""
    suites: dict[str, dict[str, Any]] = {}
    failing_nodeids: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    latest_green_failures_by_suite: dict[str, set[str]] = {}
    newest_failures_by_suite: dict[str, set[str]] = {}

    for run in reversed(runs):
        suite = str(run.get("suite", "unknown"))
        failures = {
            str(failure.get("nodeid", "<unknown>"))
            for failure in run.get("failures", [])
        }
        if _green_run(run):
            latest_green_failures_by_suite[suite] = set()
        else:
            newest_failures_by_suite[suite] = failures

    for run in runs:
        suite = str(run.get("suite", "unknown"))
        counts = run.get("counts", {})
        bucket = suites.setdefault(
            suite,
            {
                "run_count": 0,
                "failure_count": 0,
                "test_failure_count": 0,
                "unique_failing_tests": set(),
                "skipped": 0,
                "green_count": 0,
            },
        )
        bucket["run_count"] += 1
        failed_tests = int(counts.get("failed", 0)) + int(counts.get("errors", 0))
        bucket["test_failure_count"] += failed_tests
        bucket["skipped"] += int(counts.get("skipped", 0))
        if _green_run(run):
            bucket["green_count"] += 1
        else:
            bucket["failure_count"] += 1
        for failure in run.get("failures", []):
            nodeid = str(failure.get("nodeid", "<unknown>"))
            bucket["unique_failing_tests"].add(nodeid)
            failing_nodeids[nodeid] = failing_nodeids.get(nodeid, 0) + 1
            classification = str(failure.get("classification", "unknown"))
            classification_counts[classification] = (
                classification_counts.get(classification, 0) + 1
            )

    rendered_suites: dict[str, dict[str, Any]] = {}
    for suite, stats in suites.items():
        run_count = int(stats["run_count"])
        rendered_suites[suite] = {
            "run_count": run_count,
            "failure_count": stats["failure_count"],
            "pass_rate": round(stats["green_count"] / run_count, 4)
            if run_count
            else 0.0,
            "test_failure_count": stats["test_failure_count"],
            "unique_failing_tests": len(stats["unique_failing_tests"]),
            "skipped": stats["skipped"],
        }

    outcomes = _case_outcomes(runs)
    flaky_candidates = sorted(
        nodeid
        for nodeid, statuses in outcomes.items()
        if "failed" in statuses and "passed" in statuses
    )
    new_failures: dict[str, list[str]] = {}
    for suite, failures in newest_failures_by_suite.items():
        baseline_failures = latest_green_failures_by_suite.get(suite, set())
        new_failures[suite] = sorted(failures - baseline_failures)

    return {
        "run_count": len(runs),
        "suites": rendered_suites,
        "top_failing_nodeids": dict(
            sorted(failing_nodeids.items(), key=lambda item: (-item[1], item[0]))[:10]
        ),
        "classification_counts": dict(sorted(classification_counts.items())),
        "flaky_candidates": flaky_candidates,
        "new_failures": new_failures,
    }


def _append_suite_table(lines: list[str], suites: dict[str, dict[str, Any]]) -> None:
    if not suites:
        lines.extend(["No test-health runs found.", ""])
        return
    lines.extend(
        [
            "## Suites",
            "",
            "| Suite | Runs | Non-green | Pass rate | Test failures | Unique failing tests | Skipped |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for suite, stats in sorted(suites.items()):
        lines.append(
            f"| {suite} | {stats['run_count']} | {stats['failure_count']} | "
            f"{stats['pass_rate']:.1%} | {stats['test_failure_count']} | "
            f"{stats['unique_failing_tests']} | {stats['skipped']} |"
        )
    lines.append("")


def _append_count_section(
    *,
    lines: list[str],
    title: str,
    counts: dict[str, int],
    formatter: Any,
) -> None:
    if not counts:
        return
    lines.extend([title, ""])
    for key, count in counts.items():
        lines.append(formatter(key, count))
    lines.append("")


def _append_simple_list_section(
    *,
    lines: list[str],
    title: str,
    items: list[str],
) -> None:
    if not items:
        return
    lines.extend([title, ""])
    for item in items[:10]:
        lines.append(f"- `{item}`")
    lines.append("")


def _append_new_failures_section(
    lines: list[str],
    new_failures: dict[str, list[str]],
) -> None:
    if not new_failures:
        return
    lines.extend(["## New Failures", ""])
    for suite, nodeids in sorted(new_failures.items()):
        for nodeid in nodeids[:10]:
            lines.append(f"- `{suite}`: `{nodeid}`")
    lines.append("")


def _load_committed_baseline(
    baseline_path: Path = BASELINE_PATH,
) -> dict[str, Any] | None:
    if not baseline_path.exists():
        return None
    payload = yaml.safe_load(baseline_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else None


def _append_baseline_section(
    lines: list[str],
    baseline: dict[str, Any] | None,
) -> None:
    lines.extend(
        [
            "## Current Authoritative Baseline",
            "",
            "- Current merge-blocking truth comes from live CI status and the "
            "`coverage-verify` hard coverage gate.",
            "- This rollup is historical evidence only and must not be read as the "
            "current pass/fail baseline.",
            "- Committed baseline artifact: "
            "`configs/quality/test_telemetry_baseline.yaml`",
        ]
    )
    if not baseline:
        lines.extend(
            [
                "- Committed baseline payload: `missing`",
                "",
            ]
        )
        return

    coverage = baseline.get("coverage", {})
    duration = baseline.get("duration_telemetry", {})
    actual_percent = coverage.get("actual_percent")
    threshold_percent = coverage.get("threshold_percent")
    total_cases = duration.get("total_cases")
    coverage_display = (
        "pending" if actual_percent is None else f"{float(actual_percent):.2f}%"
    )
    threshold_display = (
        "pending" if threshold_percent is None else f"{float(threshold_percent):.1f}%"
    )
    total_cases_display = "pending" if total_cases is None else str(total_cases)
    lines.extend(
        [
            f"- Source branch: `{baseline.get('source_branch') or 'pending'}`",
            f"- Source commit: `{baseline.get('source_commit') or 'pending'}`",
            f"- Source run id: `{baseline.get('source_run_id') or 'pending'}`",
            f"- Refresh status: `{baseline.get('refresh_status') or 'pending'}`",
            f"- Coverage baseline: `{coverage_display}` "
            f"(threshold `{threshold_display}`)",
            f"- Duration telemetry cases: `{total_cases_display}`",
            "",
        ]
    )


def format_rollup_markdown(
    rollup: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
) -> str:
    """Render a test-health rollup as GitHub job-summary friendly Markdown."""
    lines = [
        "# Test Health Rollup",
        "",
        "Historical test-health evidence for recent recorded lane runs.",
        "",
        f"Runs analyzed: {rollup['run_count']}",
        "",
    ]
    _append_baseline_section(lines, baseline)
    _append_suite_table(lines, rollup.get("suites", {}))
    _append_count_section(
        lines=lines,
        title="## Failure Classifications",
        counts=rollup.get("classification_counts", {}),
        formatter=lambda classification, count: f"- `{classification}`: {count}",
    )
    _append_new_failures_section(lines, rollup.get("new_failures", {}))
    _append_simple_list_section(
        lines=lines,
        title="## Flaky Candidates",
        items=rollup.get("flaky_candidates", []),
    )
    _append_count_section(
        lines=lines,
        title="## Top Failing Nodeids",
        counts=rollup.get("top_failing_nodeids", {}),
        formatter=lambda nodeid, count: f"- {count}x `{nodeid}`",
    )

    return "\n".join(lines).rstrip() + "\n"


def _maybe_ingest_rollup_junit(
    *,
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int | None:
    if not (args.junit or args.junit_glob):
        return None
    if not args.suite:
        parser.error("--suite is required when --junit or --junit-glob is used")
    run_id = _unique_run_id(
        args.reports_dir,
        args.run_id or _default_run_id(args.suite),
    )
    summary_path = _write_junit_summary(
        suite=args.suite,
        run_id=run_id,
        reports_dir=args.reports_dir,
        junit_paths=args.junit,
        junit_globs=args.junit_glob,
        command=args.command,
        exit_code=args.exit_code,
        classifier_config_path=args.classifier_config,
    )
    return None if summary_path is not None else 2


def _print_rollup_console_summary(rollup: dict[str, Any]) -> None:
    print(f"Test health rollup: last {rollup['run_count']} runs")
    _print_rollup_suite_stats(rollup["suites"])
    _print_named_count_section(
        heading="Failure classifications:",
        counts=rollup["classification_counts"],
        formatter=lambda classification, count: f"- {classification}: {count}",
    )
    _print_named_list_section(
        heading="Flaky candidates:",
        items=rollup["flaky_candidates"][:10],
    )
    _print_new_failures_section(rollup["new_failures"])
    _print_named_count_section(
        heading="Top failing nodeids:",
        counts=rollup["top_failing_nodeids"],
        formatter=lambda nodeid, count: f"- {count}x {nodeid}",
    )


def _print_rollup_suite_stats(suites: dict[str, dict[str, Any]]) -> None:
    for suite, stats in sorted(suites.items()):
        print(
            f"- {suite}: runs={stats['run_count']} "
            f"non_green={stats['failure_count']} "
            f"pass_rate={stats['pass_rate']:.1%} "
            f"test_failures={stats['test_failure_count']} "
            f"unique_failing_tests={stats['unique_failing_tests']} "
            f"skipped={stats['skipped']}"
        )


def _print_named_count_section(
    *,
    heading: str,
    counts: dict[str, int],
    formatter: Callable[[str, int], str],
) -> None:
    if not counts:
        return
    print(heading)
    for name, count in counts.items():
        print(formatter(name, count))


def _print_named_list_section(*, heading: str, items: list[str]) -> None:
    if not items:
        return
    print(heading)
    for item in items:
        print(f"- {item}")


def _print_new_failures_section(new_failures: dict[str, list[str]]) -> None:
    if not new_failures:
        return
    print("New failures:")
    for suite, nodeids in sorted(new_failures.items()):
        for nodeid in nodeids[:10]:
            print(f"- {suite}: {nodeid}")


def _write_rollup_markdown_outputs(
    *,
    args: argparse.Namespace,
    rollup: dict[str, Any],
) -> None:
    if not (args.markdown_out or args.github_step_summary):
        return
    markdown = format_rollup_markdown(
        rollup,
        baseline=_load_committed_baseline(),
    )
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
        print(f"Markdown rollup: {_relative_to_root(args.markdown_out)}")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.github_step_summary and step_summary:
        Path(step_summary).parent.mkdir(parents=True, exist_ok=True)
        with Path(step_summary).open("a", encoding="utf-8") as handle:
            handle.write(markdown)


def _rollup(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Summarize test-health history.")
    parser.add_argument("--last", type=int, default=30)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument(
        "--suite",
        help="Optionally aggregate matching JUnit XML into this suite before rollup.",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--junit", action="append", default=[])
    parser.add_argument("--junit-glob", action="append", default=[])
    parser.add_argument("--command", default="")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument(
        "--classifier-config",
        type=Path,
        default=CLASSIFIERS_PATH,
        help="YAML failure-classifier rules.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="Write a Markdown rollup artifact for CI summaries.",
    )
    parser.add_argument(
        "--github-step-summary",
        action="store_true",
        help="Append Markdown rollup to $GITHUB_STEP_SUMMARY when available.",
    )
    args = parser.parse_args(argv)

    ingest_exit_code = _maybe_ingest_rollup_junit(parser=parser, args=args)
    if ingest_exit_code is not None:
        return ingest_exit_code
    rollup = build_rollup(_read_run_summaries(args.reports_dir, args.last))
    _print_rollup_console_summary(rollup)
    _write_rollup_markdown_outputs(args=args, rollup=rollup)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--help", "-h"}:
        print(
            "Usage:\n"
            "  python -m scripts.engineering.qa run-tests --suite SUITE [-- pytest args]\n"
            "  python -m scripts.engineering.qa summarize-junit --suite SUITE --junit-glob 'reports/**/*.xml'\n"
            "  python -m scripts.engineering.qa test-health --last 30 [--suite SUITE --junit-glob 'reports/**/*.xml']"
        )
        return 0
    command, rest = args[0], args[1:]
    if command == "run-tests":
        return _run_tests(rest)
    if command == "summarize-junit":
        return _summarize_junit(rest)
    if command == "test-health":
        return _rollup(rest)
    print(f"Unknown test-health command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
