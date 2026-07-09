#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/qa/vcr commands.

Usage:
    python -m scripts.engineering.qa.vcr <command> [args...]
    python -m scripts.engineering.qa.vcr --help

Commands:
    check-placement    Block VCR cassette anti-patterns
    check-naming       Enforce VCR filename policy
    check-secrets      Detect potential secret leaks in VCR cassettes
    check-metadata-age Enforce managed VCR metadata freshness
    check-replay-preflight  Fail fast on unresolved replay VCR pointers
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import dispatch_cli, python_command

COMMANDS: dict[str, str] = {
    "check-placement": "check_root_vcr_cassettes.py",
    "check-naming": "check_vcr_filename_policy.py",
    "check-secrets": "check_vcr_secrets.py",
    "check-metadata-age": "check_vcr_metadata_age.py",
    "check-replay-preflight": "check_replay_preflight.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMANDS.items()}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
