#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/qa/vcr commands.

Usage:
    python -m scripts.engineering.qa.vcr <command> [args...]
    python -m scripts.engineering.qa.vcr --help

Commands:
    check-placement    Block VCR cassette anti-patterns
    check-naming       Enforce VCR filename policy
    check-secrets      Detect potential secret leaks in VCR cassettes
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "check-placement": "check_root_vcr_cassettes.py",
    "check-naming": "check_vcr_filename_policy.py",
    "check-secrets": "check_vcr_secrets.py",
}

_DIR = Path(__file__).parent


def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run([sys.executable, str(script), *argv], check=False)
    return result.returncode


def _print_help() -> None:
    print(__doc__ or "", end="")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2

    return _run_script(COMMANDS[cmd], rest)


if __name__ == "__main__":
    raise SystemExit(main())
