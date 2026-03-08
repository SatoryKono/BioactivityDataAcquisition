#!/usr/bin/env python3
"""Enforce Ruff C901 complexity governance against a committed baseline.

Policy:
- New C901 violations are forbidden.
- Existing baseline violations may remain temporarily.
- Complexity of baseline violations must not increase.
- Optional folder budgets cap allowed C901 counts per path prefix.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = PROJECT_ROOT / "scripts" / "baselines" / "c901_baseline.json"
FUNCTION_RE = re.compile(r"`([^`]+)`")
COMPLEXITY_RE = re.compile(r"\((\d+)\s*>\s*(\d+)\)")


@dataclass(frozen=True, slots=True)
class Violation:
    """Normalized representation of a Ruff C901 violation."""

    file: str
    function: str
    complexity: int
    threshold: int
    row: int

    @property
    def key(self) -> str:
        return f"{self.file}::{self.function}"


def _normalize_file_path(filename: str) -> str:
    """Normalize Ruff filename to project-relative POSIX path."""
    normalized = filename.replace("\\", "/")

    marker = "/src/bioetl/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        return f"src/bioetl/{suffix}".strip("/")

    if normalized.startswith("src/"):
        return normalized

    # As fallback keep path with normalized separators.
    return normalized


def _parse_violation(item: dict[str, Any]) -> Violation | None:
    """Parse one Ruff JSON item into Violation, skipping malformed entries."""
    message = str(item.get("message", ""))
    function_match = FUNCTION_RE.search(message)
    complexity_match = COMPLEXITY_RE.search(message)

    if not function_match or not complexity_match:
        return None

    return Violation(
        file=_normalize_file_path(str(item.get("filename", ""))),
        function=function_match.group(1),
        complexity=int(complexity_match.group(1)),
        threshold=int(complexity_match.group(2)),
        row=int(item.get("location", {}).get("row", 0)),
    )


def _run_ruff_c901(target: str) -> list[Violation]:
    """Run Ruff C901 check and return normalized violations list."""
    cmd = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        target,
        "--select",
        "C901",
        "--output-format",
        "json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = proc.stdout.strip()
    if not stdout:
        return []

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        print("[ERROR] Failed to parse Ruff JSON output", file=sys.stderr)
        print(exc, file=sys.stderr)
        print(stdout[:1000], file=sys.stderr)
        raise SystemExit(2) from exc

    violations: list[Violation] = []
    for item in payload:
        violation = _parse_violation(item)
        if violation is not None:
            violations.append(violation)
    return violations


def _load_baseline(path: Path) -> tuple[dict[str, Violation], dict[str, int]]:
    """Load baseline violations and folder budgets from JSON file."""
    if not path.exists():
        print(f"[ERROR] Missing baseline file: {path}", file=sys.stderr)
        raise SystemExit(2)

    data = json.loads(path.read_text(encoding="utf-8"))
    entries_raw = data.get("entries", [])
    folder_budgets = data.get("folder_budgets", {})

    baseline: dict[str, Violation] = {}
    for entry in entries_raw:
        violation = Violation(
            file=str(entry["file"]),
            function=str(entry["function"]),
            complexity=int(entry["complexity"]),
            threshold=int(entry.get("threshold", 10)),
            row=int(entry.get("row", 0)),
        )
        baseline[violation.key] = violation

    budgets: dict[str, int] = {
        str(prefix): int(limit) for prefix, limit in folder_budgets.items()
    }
    return baseline, budgets


def _count_by_prefix(violations: list[Violation], prefix: str) -> int:
    """Count violations with file path under given prefix."""
    norm_prefix = prefix.rstrip("/")
    return sum(
        1
        for violation in violations
        if violation.file == norm_prefix or violation.file.startswith(f"{norm_prefix}/")
    )


def _print_violation_list(title: str, violations: list[Violation]) -> None:
    """Pretty-print a list of violations."""
    if not violations:
        return
    print(title)
    for item in sorted(violations, key=lambda x: (x.file, x.function)):
        print(
            f"  - {item.file}:{item.row} :: {item.function} "
            f"(complexity {item.complexity} > {item.threshold})"
        )


def _evaluate_policy(
    current: list[Violation],
    baseline_map: dict[str, Violation],
    folder_budgets: dict[str, int],
) -> int:
    """Evaluate governance policy and return process exit code."""
    current_map = {violation.key: violation for violation in current}

    new_keys = sorted(set(current_map) - set(baseline_map))
    resolved_keys = sorted(set(baseline_map) - set(current_map))

    regressions: list[tuple[Violation, Violation]] = []
    for key in sorted(set(current_map) & set(baseline_map)):
        cur = current_map[key]
        base = baseline_map[key]
        if cur.complexity > base.complexity:
            regressions.append((base, cur))

    budget_violations: list[tuple[str, int, int]] = []
    for prefix, limit in sorted(folder_budgets.items()):
        count = _count_by_prefix(current, prefix)
        if count > limit:
            budget_violations.append((prefix, count, limit))

    new_violations = [current_map[key] for key in new_keys]
    resolved_violations = [baseline_map[key] for key in resolved_keys]

    print("C901 Governance Report")
    print(f"  Current violations: {len(current)}")
    print(f"  Baseline violations: {len(baseline_map)}")
    print(f"  New violations: {len(new_violations)}")
    print(f"  Resolved vs baseline: {len(resolved_violations)}")

    if folder_budgets:
        print("  Folder budgets:")
        for prefix, limit in sorted(folder_budgets.items()):
            count = _count_by_prefix(current, prefix)
            print(f"    - {prefix}: {count}/{limit}")

    _print_violation_list("\n[BLOCKER] New C901 violations:", new_violations)

    if regressions:
        print("\n[BLOCKER] Complexity regression in baseline violations:")
        for base, cur in regressions:
            print(
                f"  - {cur.file}:{cur.row} :: {cur.function} "
                f"({base.complexity} -> {cur.complexity})"
            )

    if budget_violations:
        print("\n[BLOCKER] Folder budget exceeded:")
        for prefix, count, limit in budget_violations:
            print(f"  - {prefix}: {count} > {limit}")

    if resolved_violations:
        _print_violation_list(
            "\n[INFO] Resolved baseline violations:", resolved_violations
        )

    has_blockers = bool(new_violations or regressions or budget_violations)
    if has_blockers:
        print("\nResult: FAILED (C901 governance violation)")
        return 1

    print("\nResult: OK (no new C901 structural debt)")
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Enforce Ruff C901 baseline and folder budgets.",
    )
    parser.add_argument(
        "--target",
        default="src/bioetl",
        help="Path to run Ruff C901 check on (default: src/bioetl).",
    )
    parser.add_argument(
        "--baseline-file",
        default=str(DEFAULT_BASELINE.relative_to(PROJECT_ROOT)),
        help="Baseline JSON path relative to project root.",
    )
    parser.add_argument(
        "--mode",
        choices=("block", "warn"),
        default="block",
        help=(
            "Governance mode: 'block' fails CI on violations, "
            "'warn' reports violations but exits 0."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    baseline_path = (PROJECT_ROOT / args.baseline_file).resolve()

    baseline_map, folder_budgets = _load_baseline(baseline_path)
    current = _run_ruff_c901(args.target)

    exit_code = _evaluate_policy(current, baseline_map, folder_budgets)
    if exit_code == 0 or args.mode == "block":
        return exit_code

    print("\nMode: WARN (non-blocking rollout enabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
