"""Diagnostic ratchet that blocks growth of mypy error identities."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_ERROR_LINE_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?:(?P<column>\d+):)? error: (?P<message>.*)$"
)
DiagnosticCounts = dict[str, dict[str, dict[str, int]]]


def _parse_line(line: str) -> tuple[str, str, str] | None:
    match = _ERROR_LINE_RE.match(line.rstrip("\r\n"))
    if match is None:
        return None
    message_and_code = match.group("message").strip()
    code_start = message_and_code.rfind("[")
    code_end = message_and_code.rfind("]")
    if code_start != -1 and code_end > code_start:
        code = message_and_code[code_start + 1 : code_end]
        message = message_and_code[:code_start].strip()
    else:
        code = "unknown"
        message = message_and_code
    return match.group("path").strip(), message, code


def _parse_mypy_output(log_path: Path) -> DiagnosticCounts:
    """Parse mypy log output into module -> message -> code -> count."""
    diagnostics: DiagnosticCounts = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    if not log_path.exists():
        raise FileNotFoundError(
            f"mypy log file not found at {log_path}. Ensure mypy runs before this script."
        )

    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            parsed = _parse_line(line)
            if parsed is None:
                continue
            file_path, message, code = parsed
            diagnostics[file_path][message][code] += 1

    return diagnostics


def _baseline_count(
    baseline: dict[str, Any], file_path: str, message: str, code: str
) -> int:
    file_entry = baseline.get(file_path, {})
    if not isinstance(file_entry, dict):
        return 0
    message_entry = file_entry.get(message, {})
    if not isinstance(message_entry, dict):
        return 0
    count = message_entry.get(code, 0)
    if isinstance(count, bool) or not isinstance(count, int):
        return 0
    return count


def _compare_diagnostics(
    current_diagnostics: DiagnosticCounts, baseline: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    for file_path, messages in current_diagnostics.items():
        for message, codes in messages.items():
            for code, count in codes.items():
                baseline_count = _baseline_count(baseline, file_path, message, code)
                if count > baseline_count:
                    errors.append(
                        f"{file_path}: count for '{message}' [{code}] increased "
                        f"from {baseline_count} to {count}"
                    )
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    log_path = repo_root / "reports" / "mypy_strict.log"
    baseline_path = repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json"

    try:
        current_diagnostics = _parse_mypy_output(log_path)
    except FileNotFoundError as exc:
        print(f"::error::{exc}")
        return 1

    if baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("::error::Invalid JSON in mypy_diagnostic_baseline.json")
            return 1
        if not isinstance(baseline, dict):
            print("::error::mypy_diagnostic_baseline.json must be an object")
            return 1
    else:
        baseline = {}

    errors = _compare_diagnostics(current_diagnostics, baseline)
    if errors:
        print("::error::Mypy diagnostic ratchet failed. New type errors introduced:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("::notice::Mypy diagnostic ratchet passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
