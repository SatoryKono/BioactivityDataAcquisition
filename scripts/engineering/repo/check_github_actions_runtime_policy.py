#!/usr/bin/env python3
"""Validate GitHub Actions references against runtime policy allowlist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = ROOT / ".github/workflows"
COMPOSITE_ACTIONS_DIR = ROOT / ".github/actions"

# Canonical policy: pin to vetted SHAs for runtime-sensitive official actions.
ALLOWED_USES: dict[str, set[str]] = {
    "actions/checkout": {"de0fac2e4500dabe0009e67214ff5f5447ce83dd"},  # v6
    "actions/setup-python": {"a26af69be951a213d495a4c3e4e4022e16d87065"},  # v5
    "actions/cache": {"0057852bfaa89a56745cba8c7296529d2fc39830"},  # v4
    "actions/upload-artifact": {"ea165f8d65b6e75b540449e92b4886f43607fa02"},  # v4
}

USES_PATTERN = re.compile(r"^\s*uses:\s*([^\s#]+)")


def iter_yaml_files() -> list[Path]:
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    composite_files = sorted(COMPOSITE_ACTIONS_DIR.rglob("action.yml"))
    return [*workflow_files, *composite_files]


def main() -> int:
    violations: list[str] = []

    for file_path in iter_yaml_files():
        rel_path = file_path.relative_to(ROOT)
        for line_no, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES_PATTERN.match(line)
            if match is None:
                continue
            uses_ref = match.group(1)
            action, _, ref = uses_ref.partition("@")
            if action not in ALLOWED_USES:
                continue
            if not ref:
                violations.append(f"{rel_path}:{line_no}: missing ref for {action}")
                continue
            if ref in ALLOWED_USES[action]:
                continue
            violations.append(
                f"{rel_path}:{line_no}: disallowed {uses_ref}; expected one of {sorted(ALLOWED_USES[action])}"
            )

    if violations:
        sys.stderr.write("GitHub Actions runtime policy violations found:\n")
        for violation in violations:
            sys.stderr.write(f"- {violation}\n")
        return 1

    print("GitHub Actions runtime policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
