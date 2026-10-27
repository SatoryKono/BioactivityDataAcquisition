"""Diagnostic ratchet to prevent regression in type debt."""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Any


def _parse_line(line: str) -> tuple[str, str, str] | None:
    if ": error:" not in line:
        return None
    parts = line.split(":", 3)
    if len(parts) < 4:
        return None
    file_path = parts[0].strip()
    msg_and_code = parts[3].strip()
    code_start = msg_and_code.rfind("[")
    code_end = msg_and_code.rfind("]")
    if code_start != -1 and code_end != -1 and code_end > code_start:
        code = msg_and_code[code_start + 1 : code_end]
        msg = msg_and_code[:code_start].strip()
    else:
        code = "unknown"
        msg = msg_and_code
    return file_path, msg, code


def _parse_mypy_output(log_path: Path) -> dict[str, dict[str, dict[str, int]]]:
    """Parse mypy log output into a dict of module -> message -> code -> count."""
    diagnostics: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    if not log_path.exists():
        raise FileNotFoundError(
            f"mypy log file not found at {log_path}. Ensure mypy runs before this script."
        )

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_line(line)
            if parsed:
                file_path, msg, code = parsed
                diagnostics[file_path][msg][code] += 1

    return diagnostics


def _compare_diagnostics(
    current_diagnostics: dict[str, dict[str, dict[str, int]]], baseline: dict[str, Any]
) -> list[str]:
    errors = []
    for file_path, messages in current_diagnostics.items():
        for msg, codes in messages.items():
            for code, count in codes.items():
                baseline_count = baseline.get(file_path, {}).get(msg, {}).get(code, 0)
                if count > baseline_count:
                    errors.append(
                        f"{file_path}: count for '{msg}' [{code}] increased from {baseline_count} to {count}"
                    )
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    log_path = repo_root / "reports" / "mypy_strict.log"
    baseline_path = repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json"

    current_diagnostics = _parse_mypy_output(log_path)

    if baseline_path.exists():
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)
        except json.JSONDecodeError:
            print("::error::Invalid JSON in mypy_diagnostic_baseline.json")
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
