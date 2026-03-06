#!/usr/bin/env python3
"""Validate E2E matrix smoke health from pytest JUnit XML.

Checks:
- expected number of matrix smoke test cases
- skip-rate SLO (absolute and percentage)
- deterministic classification labels (infra_flaky vs code_regression)
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_SKIP_CODE_RE = re.compile(r"E2E_SKIP\[([A-Z0-9_]+)\]")
_FAIL_CODE_RE = re.compile(r"E2E_FAIL\[([A-Z0-9_]+)\]")
_SMOKE_TEST_PREFIX = "test_pipeline_matrix_smoke["


@dataclass(frozen=True, slots=True)
class MatrixHealthSummary:
    total: int
    passed: int
    skipped: int
    failed: int
    skip_rate: float
    skip_labels: Counter[str]
    failure_labels: Counter[str]

    @property
    def infra_flaky_total(self) -> int:
        return int(self.skip_labels.get("infra_flaky", 0)) + int(
            self.failure_labels.get("infra_flaky", 0)
        )

    @property
    def code_regression_total(self) -> int:
        return int(self.failure_labels.get("code_regression", 0))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate E2E matrix smoke skip-rate and failure labels from JUnit XML.",
    )
    parser.add_argument(
        "--junit",
        type=Path,
        required=True,
        help="Path to pytest JUnit XML.",
    )
    parser.add_argument(
        "--expected-total",
        type=int,
        default=0,
        help="Expected number of matrix smoke cases (0 disables fixed-total check).",
    )
    parser.add_argument(
        "--expected-total-from-configs",
        action="store_true",
        help="Derive expected total from configs/entities/*.yaml count.",
    )
    parser.add_argument(
        "--configs-root",
        type=Path,
        default=Path("configs/entities"),
        help="Path used with --expected-total-from-configs.",
    )
    parser.add_argument(
        "--max-skips",
        type=int,
        default=1,
        help="Maximum allowed skipped matrix smoke cases.",
    )
    parser.add_argument(
        "--max-skip-rate",
        type=float,
        default=0.05,
        help="Maximum allowed skip rate in range [0, 1].",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional path to write markdown summary.",
    )
    parser.add_argument(
        "--allow-unknown-labels",
        action="store_true",
        help="Do not fail when unknown skip/failure labels are found.",
    )
    parser.add_argument(
        "--ignore-failures",
        action="store_true",
        help="Ignore failed testcases when used with rerun-stability gating.",
    )
    return parser.parse_args()


def _extract_code(payload: str, *, pattern: re.Pattern[str]) -> str:
    match = pattern.search(payload)
    if match is None:
        return "UNCLASSIFIED"
    return match.group(1)


def _classify_skip(code: str) -> str:
    if code.startswith("INFRA_FLAKY") or code.startswith("CASSETTE"):
        return "infra_flaky"
    return "unknown"


def _classify_failure(code: str) -> str:
    if code == "CODE_REGRESSION":
        return "code_regression"
    if code.startswith("INFRA_FLAKY"):
        return "infra_flaky"
    return "unknown"


def _build_summary(junit_path: Path) -> MatrixHealthSummary:
    root = ET.parse(junit_path).getroot()
    smoke_cases = [
        case
        for case in root.iter("testcase")
        if str(case.attrib.get("name", "")).startswith(_SMOKE_TEST_PREFIX)
    ]

    skip_labels: Counter[str] = Counter()
    failure_labels: Counter[str] = Counter()
    skipped = 0
    failed = 0

    for case in smoke_cases:
        skipped_node = case.find("skipped")
        failure_node = case.find("failure")
        error_node = case.find("error")

        if skipped_node is not None:
            skipped += 1
            payload = (
                f"{skipped_node.attrib.get('message', '')}\n{skipped_node.text or ''}"
            )
            code = _extract_code(payload, pattern=_SKIP_CODE_RE)
            skip_labels[_classify_skip(code)] += 1
            continue

        if failure_node is not None or error_node is not None:
            failed += 1
            node = failure_node if failure_node is not None else error_node
            assert node is not None
            payload = f"{node.attrib.get('message', '')}\n{node.text or ''}"
            code = _extract_code(payload, pattern=_FAIL_CODE_RE)
            failure_labels[_classify_failure(code)] += 1

    total = len(smoke_cases)
    passed = total - skipped - failed
    skip_rate = (skipped / total) if total else 0.0
    return MatrixHealthSummary(
        total=total,
        passed=passed,
        skipped=skipped,
        failed=failed,
        skip_rate=skip_rate,
        skip_labels=skip_labels,
        failure_labels=failure_labels,
    )


def _render_markdown(summary: MatrixHealthSummary, violations: list[str]) -> str:
    lines = [
        "# E2E Matrix Smoke Health",
        "",
        f"- total: `{summary.total}`",
        f"- passed: `{summary.passed}`",
        f"- skipped: `{summary.skipped}`",
        f"- failed: `{summary.failed}`",
        f"- skip_rate: `{summary.skip_rate:.4f}`",
        f"- skip_labels: `{dict(summary.skip_labels)}`",
        f"- failure_labels: `{dict(summary.failure_labels)}`",
        f"- infra_flaky_total: `{summary.infra_flaky_total}`",
        f"- code_regression_total: `{summary.code_regression_total}`",
        "",
    ]
    if violations:
        lines.append("## Violations")
        lines.extend(f"- {item}" for item in violations)
    else:
        lines.append("## Result")
        lines.append("- PASS")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    if not args.junit.exists():
        print(f"[e2e-matrix-health] JUnit file not found: {args.junit}")
        return 1
    if args.max_skip_rate < 0 or args.max_skip_rate > 1:
        print("[e2e-matrix-health] --max-skip-rate must be in [0, 1]")
        return 1

    summary = _build_summary(args.junit)
    expected_total = args.expected_total
    if args.expected_total_from_configs:
        expected_total = len(sorted(args.configs_root.rglob("*.yaml")))

    violations: list[str] = []

    if summary.total == 0:
        violations.append("No matrix smoke test cases found in JUnit report")
    if expected_total > 0 and summary.total != expected_total:
        violations.append(
            f"expected total={expected_total}, observed total={summary.total}"
        )
    if summary.skipped > args.max_skips:
        violations.append(
            f"skip count {summary.skipped} exceeds budget {args.max_skips}"
        )
    if summary.skip_rate > args.max_skip_rate:
        violations.append(
            f"skip rate {summary.skip_rate:.4f} exceeds budget {args.max_skip_rate:.4f}"
        )
    if summary.failed > 0 and not args.ignore_failures:
        violations.append(f"matrix smoke has {summary.failed} failing test(s)")

    unknown_skip = summary.skip_labels.get("unknown", 0)
    unknown_failure = summary.failure_labels.get("unknown", 0)
    if not args.allow_unknown_labels:
        if unknown_skip:
            violations.append(f"unknown skip labels detected: {unknown_skip}")
        if unknown_failure:
            violations.append(f"unknown failure labels detected: {unknown_failure}")

    print("[e2e-matrix-health] summary")
    print(
        f"  total={summary.total} passed={summary.passed} skipped={summary.skipped} failed={summary.failed}"
    )
    print(f"  skip_rate={summary.skip_rate:.4f}")
    print(f"  skip_labels={dict(summary.skip_labels)}")
    print(f"  failure_labels={dict(summary.failure_labels)}")
    print(f"  infra_flaky_total={summary.infra_flaky_total}")
    print(f"  code_regression_total={summary.code_regression_total}")

    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(
            _render_markdown(summary, violations),
            encoding="utf-8",
        )
        print(f"[e2e-matrix-health] wrote markdown summary: {args.markdown_out}")

    if violations:
        print("[e2e-matrix-health] violations detected:")
        for item in violations:
            print(f"  - {item}")
        return 1

    print("[e2e-matrix-health] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
