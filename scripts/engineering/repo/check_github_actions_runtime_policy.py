#!/usr/bin/env python3
"""Validate GitHub Actions references against runtime policy allowlist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = ROOT / ".github/workflows"
COMPOSITE_ACTIONS_DIR = ROOT / ".github/actions"

ALLOWED_USES: dict[str, set[str]] = {
    "actions/checkout": {"de0fac2e4500dabe0009e67214ff5f5447ce83dd"},  # v6.0.2
    "actions/setup-python": {"a309ff8b426b58ec0e2a45f0f869d46889d02405"},  # v6.2.0
    "actions/cache": {"27d5ce7f107fe9357f9df03efb73ab90386fccae"},  # v5.0.5
    "actions/upload-artifact": {"043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"},  # v7.0.1
    "actions/setup-node": {"48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e"},  # v6.4.0
    "actions/download-artifact": {"3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"},  # v8.0.1
}

USES_PATTERN = re.compile(r"^\s*uses:\s*([^\s#]+)")


def iter_yaml_files() -> list[Path]:
    return [
        *sorted(WORKFLOWS_DIR.glob("*.yml")),
        *sorted(COMPOSITE_ACTIONS_DIR.rglob("action.yml")),
    ]


def _parsed_uses_reference(line: str) -> tuple[str, str] | None:
    match = USES_PATTERN.match(line)
    if match is None:
        return None
    uses_ref = match.group(1)
    return uses_ref, uses_ref.partition("@")[0]


def _validate_allowed_uses_ref(uses_ref: str, action: str) -> str | None:
    allowed_refs = ALLOWED_USES.get(action)
    if allowed_refs is None:
        return None
    _, _, ref = uses_ref.partition("@")
    if ref and ref in allowed_refs:
        return None
    return f"disallowed {uses_ref}; expected one of {sorted(allowed_refs)}"


def _uses_violations_in_file(file_path: Path) -> list[str]:
    violations: list[str] = []
    rel_path = file_path.relative_to(ROOT)
    for line_no, line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        parsed = _parsed_uses_reference(line)
        if parsed is None:
            continue
        uses_ref, action = parsed
        violation = _validate_allowed_uses_ref(uses_ref, action)
        if violation is None:
            continue
        violations.append(f"{rel_path}:{line_no}: {violation}")
    return violations


def _collect_uses_violations() -> list[str]:
    violations: list[str] = []
    for file_path in iter_yaml_files():
        violations.extend(_uses_violations_in_file(file_path))
    return violations


def _report_violations(violations: list[str]) -> int:
    if not violations:
        print("GitHub Actions runtime policy check passed.")
        return 0
    sys.stderr.write("GitHub Actions runtime policy violations found:\n")
    for violation in violations:
        sys.stderr.write(f"- {violation}\n")
    return 1


def main() -> int:
    return _report_violations(_collect_uses_violations())


if __name__ == "__main__":
    raise SystemExit(main())
