"""Standard-library JUnit record accounting shared by CI and baseline fallback."""

from __future__ import annotations

import argparse
import json
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

type Summary = dict[str, Any]


def _nonnegative_duration(raw: str | None, label: str, path: Path) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(
            f"Invalid JUnit {label} duration in {path}: {raw!r}"
        ) from error
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid JUnit {label} duration in {path}: {raw!r}")
    return value


def _validate_aggregate(
    node: ET.Element, field: str, allowed: set[int], path: Path
) -> None:
    declared = node.get(field)
    if declared is None:
        return
    try:
        count = int(declared)
    except ValueError as error:
        raise ValueError(f"Invalid JUnit {field} testcase count in {path}") from error
    if count < 0 or count not in allowed:
        raise ValueError(
            f"JUnit {field} testcase count disagrees with records in {path}: "
            f"declared {count}, allowed {sorted(allowed)}"
        )


def _aggregate_counts(node: ET.Element, cases: list[ET.Element]) -> dict[str, set[int]]:
    counts = {
        "tests": {len(cases)},
        "skipped": {sum(case.find("skipped") is not None for case in cases)},
    }
    for field in ("failures", "errors"):
        tag = field[:-1]
        suite_diagnostics = sum(
            len(suite.findall(tag))
            for suite in node.iter()
            if suite.tag in {"testsuite", "testsuites"}
        )
        # JUnit emitters differ: pytest counts diagnostic elements, while
        # other producers count affected testcase records.
        counts[field] = {
            sum(case.find(tag) is not None for case in cases) + suite_diagnostics,
            sum(len(case.findall(tag)) for case in cases) + suite_diagnostics,
        }
    return counts


def _validated_cases(path: Path) -> tuple[ET.Element, list[ET.Element]]:
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError(f"Unsupported JUnit root in {path}: {root.tag}")

    def check(node: ET.Element) -> list[ET.Element]:
        cases = list(node.findall("testcase"))
        for child in node:
            if child.tag in {"testsuite", "testsuites"}:
                cases.extend(check(child))
        for field, actual in _aggregate_counts(node, cases).items():
            _validate_aggregate(node, field, actual, path)
        return cases

    return root, check(root)


def _record_case(
    case: ET.Element, path: Path, rows: list[Summary]
) -> tuple[int, int, int, float]:
    skipped = case.find("skipped") is not None
    error = case.find("error") is not None
    failure = case.find("failure") is not None
    name = case.get("name", "")
    class_name = case.get("classname", "")
    full_name = f"{class_name}::{name}" if class_name else name
    duration = _nonnegative_duration(case.get("time"), "testcase", path)
    if not skipped and duration is not None and duration > 0:
        rows.append(
            {
                "source": path.name,
                "test": full_name or "<unknown>",
                "duration_s": round(duration, 3),
            }
        )
    return int(skipped), int(error), int(failure), duration or 0.0


def _outermost_suites(node: ET.Element) -> list[ET.Element]:
    """Select non-overlapping suite clocks beneath optional wrapper elements."""
    if node.tag == "testsuite":
        return [node]
    suites: list[ET.Element] = []
    for child in node:
        if child.tag in {"testsuite", "testsuites"}:
            suites.extend(_outermost_suites(child))
    return suites


def derive_summary(junit_paths: list[Path]) -> Summary:
    """Count each testcase record once; positive duration is a separate measure."""
    rows: list[Summary] = []
    observed = skipped = errors = failures = 0
    duration_sums: dict[str, float] = {}
    lane_wall: dict[str, float] = {}
    missing = [path for path in junit_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing JUnit telemetry input: {missing[0]}")
    if len({path.resolve() for path in junit_paths}) != len(junit_paths):
        raise ValueError("Duplicate JUnit telemetry input path")
    if len({path.name for path in junit_paths}) != len(junit_paths):
        raise ValueError("Ambiguous JUnit telemetry source name")
    existing = junit_paths
    for path in existing:
        root, cases = _validated_cases(path)
        suites = _outermost_suites(root)
        lane_wall[path.name] = round(
            sum(
                _nonnegative_duration(suite.get("time"), "testsuite", path) or 0
                for suite in suites
            ),
            3,
        )
        duration_sum = 0.0
        for case in cases:
            observed += 1
            case_skipped, case_errors, case_failures, duration = _record_case(
                case, path, rows
            )
            skipped += case_skipped
            errors += case_errors
            failures += case_failures
            duration_sum += duration
        duration_sums[path.name] = round(duration_sum, 3)
    rows.sort(key=lambda row: float(row["duration_s"]), reverse=True)
    executed = observed - skipped
    return {
        "total_cases": executed if existing else None,
        "top_slowest": rows[:25],
        "execution_context": {
            "count_semantics": "non_skipped_junit_records",
            "observed_count": observed,
            "skipped_count": skipped,
            "executed_count": executed,
            "error_record_count": errors,
            "failure_record_count": failures,
            "positive_duration_count": len(rows),
            "junit_source_count": len(existing),
            "junit_sources": [path.name for path in existing],
            "junit_testcase_duration_sum_s": duration_sums,
            "lane_wall_time_s": lane_wall,
            "lane_wall_time_source": "junit_testsuite_time",
        },
    }


def write_ci_summary() -> Summary:
    """Produce the workflow's JSON and Markdown from the same validated records."""
    raw_dir = Path("reports/test-telemetry/raw")
    output_dir = Path("reports/test-telemetry")
    summary = derive_summary(sorted(raw_dir.rglob("*.xml")))
    context = summary["execution_context"]
    context["worker_mode"] = (
        "mixed: xdist unit/integration; serial contracts/repo-backed/memory"
    )
    context["explicit_exclusions"] = [
        {
            "lane": "live-provider-contracts",
            "reason": "scheduled network-owned workflow",
        },
        {"lane": "performance", "reason": "benchmark-owned non-blocking workflow"},
        {"lane": "manual-e2e", "reason": "operator-triggered external-runtime lane"},
    ]
    summary.update(
        source_commit=os.getenv("GITHUB_SHA"),
        source_run_id=f"github-{os.getenv('GITHUB_RUN_ID', 'unknown')}-{os.getenv('GITHUB_RUN_ATTEMPT', '1')}",
    )
    lines = [
        "# Slowest Tests",
        "",
        f"Observed testcase records: `{context['observed_count']}`",
        f"Non-skipped testcase records: `{summary['total_cases']}`",
        "",
    ]
    if summary["top_slowest"]:
        lines.extend(["| Rank | Duration (s) | Test | Source |", "|---:|---:|---|---|"])
        for index, row in enumerate(summary["top_slowest"], 1):
            lines.append(
                f"| {index} | {row['duration_s']:.3f} | `{row['test']}` | `{row['source']}` |"
            )
    elif context["observed_count"]:
        lines.append(
            "JUnit testcase records are present; none has a non-skipped positive duration."
        )
    else:
        lines.append("No JUnit testcase records were collected.")
    markdown = "\n".join(lines) + "\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "slowest-tests.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "slowest-tests.md").write_text(markdown, encoding="utf-8")
    if step_summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(step_summary).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    write_ci_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
