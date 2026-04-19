#!/usr/bin/env python3
"""Validate E2E matrix stability across repeated smoke reruns.

A matrix case is considered recurrently unstable when it does not pass
in any rerun. Classification is deterministic:
- infra_flaky: all non-pass outcomes are infra_flaky
- code_regression: at least one non-pass outcome is code_regression/unknown
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_SMOKE_TEST_PREFIX = "test_pipeline_matrix_smoke["
_SKIP_CODE_RE = re.compile(r"E2E_SKIP\[([A-Z0-9_]+)\]")
_FAIL_CODE_RE = re.compile(r"E2E_FAIL\[([A-Z0-9_]+)\]")


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    status: str
    classification: str


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


def _smoke_test_name(name: str) -> bool:
    """Return True when testcase name belongs to matrix smoke suite."""
    return name.startswith(_SMOKE_TEST_PREFIX)


def _node_payload(node: ET.Element) -> str:
    """Build message payload used for code extraction."""
    return f"{node.attrib.get('message', '')}\n{node.text or ''}"


def _case_outcome(case: ET.Element) -> CaseOutcome:
    """Parse one testcase node into normalized outcome."""
    skipped_node = case.find("skipped")
    failure_node = case.find("failure")
    error_node = case.find("error")
    if skipped_node is not None:
        code = _extract_code(_node_payload(skipped_node), pattern=_SKIP_CODE_RE)
        return CaseOutcome("skipped", _classify_skip(code))
    if failure_node is not None or error_node is not None:
        node = failure_node if failure_node is not None else error_node
        assert node is not None
        code = _extract_code(_node_payload(node), pattern=_FAIL_CODE_RE)
        return CaseOutcome("failed", _classify_failure(code))
    return CaseOutcome("passed", "passed")


def _parse_junit(path: Path) -> dict[str, CaseOutcome]:
    root = ET.parse(path).getroot()
    result: dict[str, CaseOutcome] = {}
    for case in root.iter("testcase"):
        name = str(case.attrib.get("name", ""))
        if not _smoke_test_name(name):
            continue
        result[name] = _case_outcome(case)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate E2E smoke stability across N reruns.",
    )
    parser.add_argument(
        "--junit-glob",
        required=True,
        help="Glob for JUnit files (e.g. reports/e2e/matrix-smoke-run*.xml).",
    )
    parser.add_argument(
        "--required-runs",
        type=int,
        default=3,
        help="Required number of rerun reports.",
    )
    parser.add_argument(
        "--max-recurrent-infra-flaky",
        type=int,
        default=0,
        help="Allowed recurrent infra_flaky cases.",
    )
    parser.add_argument(
        "--max-recurrent-code-regression",
        type=int,
        default=0,
        help="Allowed recurrent code_regression cases.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional markdown report path.",
    )
    return parser.parse_args()


def _build_markdown(
    *,
    runs: list[Path],
    recurrent_counters: Counter[str],
    recurrent_cases: list[tuple[str, str]],
    violations: list[str],
) -> str:
    lines = [
        "# E2E Rerun Stability",
        "",
        f"- runs: `{len(runs)}`",
        f"- reports: `{[str(path) for path in runs]}`",
        f"- recurrent_infra_flaky: `{recurrent_counters.get('infra_flaky', 0)}`",
        f"- recurrent_code_regression: `{recurrent_counters.get('code_regression', 0)}`",
        "",
    ]
    if recurrent_cases:
        lines.append("## Recurrent Cases")
        lines.extend(
            f"- `{name}`: `{classification}`"
            for name, classification in recurrent_cases
        )
        lines.append("")
    if violations:
        lines.append("## Violations")
        lines.extend(f"- {item}" for item in violations)
    else:
        lines.append("## Result")
        lines.append("- PASS")
    lines.append("")
    return "\n".join(lines)


def _selected_runs(paths: list[Path], required_runs: int) -> tuple[list[Path], list[str]]:
    """Select rerun reports and emit count violation when incomplete."""
    violations: list[str] = []
    if len(paths) < required_runs:
        violations.append(
            f"expected at least {required_runs} rerun reports, got {len(paths)}"
        )
    return paths[:required_runs], violations


def _recurrent_cases(
    run_outcomes: list[dict[str, CaseOutcome]],
) -> tuple[Counter[str], list[tuple[str, str]]]:
    """Collect recurrently unstable cases across reruns."""
    recurrent_counters: Counter[str] = Counter()
    recurrent_cases: list[tuple[str, str]] = []
    case_names = sorted({name for report in run_outcomes for name in report})
    for name in case_names:
        outcomes = [
            report.get(name, CaseOutcome("missing", "unknown"))
            for report in run_outcomes
        ]
        if any(item.status == "passed" for item in outcomes):
            continue
        classifications = [item.classification for item in outcomes]
        classification = (
            "infra_flaky"
            if all(item == "infra_flaky" for item in classifications)
            else "code_regression"
        )
        recurrent_counters[classification] += 1
        recurrent_cases.append((name, classification))
    return recurrent_counters, recurrent_cases


def _budget_violations(
    *,
    recurrent_counters: Counter[str],
    max_recurrent_infra_flaky: int,
    max_recurrent_code_regression: int,
) -> list[str]:
    """Return budget violations for recurrent instability counters."""
    violations: list[str] = []
    recurrent_infra = recurrent_counters.get("infra_flaky", 0)
    recurrent_code = recurrent_counters.get("code_regression", 0)
    if recurrent_infra > max_recurrent_infra_flaky:
        violations.append(
            "recurrent infra_flaky cases "
            f"{recurrent_infra} exceed budget {max_recurrent_infra_flaky}"
        )
    if recurrent_code > max_recurrent_code_regression:
        violations.append(
            "recurrent code_regression cases "
            f"{recurrent_code} exceed budget {max_recurrent_code_regression}"
        )
    return violations


def _print_summary(runs: list[Path], recurrent_counters: Counter[str]) -> None:
    """Print compact rerun stability summary."""
    print("[e2e-rerun-stability] summary")
    print(f"  runs={len(runs)} reports={[str(path) for path in runs]}")
    print(f"  recurrent_infra_flaky={recurrent_counters.get('infra_flaky', 0)}")
    print(
        f"  recurrent_code_regression={recurrent_counters.get('code_regression', 0)}"
    )


def main() -> int:
    args = _parse_args()
    paths = sorted(Path().glob(args.junit_glob))
    runs, violations = _selected_runs(paths, args.required_runs)
    run_outcomes = [_parse_junit(path) for path in runs]
    recurrent_counters, recurrent_cases = _recurrent_cases(run_outcomes)
    violations.extend(
        _budget_violations(
            recurrent_counters=recurrent_counters,
            max_recurrent_infra_flaky=args.max_recurrent_infra_flaky,
            max_recurrent_code_regression=args.max_recurrent_code_regression,
        )
    )
    _print_summary(runs, recurrent_counters)

    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(
            _build_markdown(
                runs=runs,
                recurrent_counters=recurrent_counters,
                recurrent_cases=recurrent_cases,
                violations=violations,
            ),
            encoding="utf-8",
        )
        print(f"[e2e-rerun-stability] wrote markdown report: {args.markdown_out}")

    if violations:
        print("[e2e-rerun-stability] violations detected:")
        for item in violations:
            print(f"  - {item}")
        return 1

    print("[e2e-rerun-stability] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
