#!/usr/bin/env python3
"""Sync scripts inventory manifest through the canonical inventory checker."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync or validate the scripts inventory manifest."
    )
    parser.add_argument(
        "--manifest",
        default="configs/quality/scripts_inventory_manifest.json",
        help="Path to the scripts inventory manifest.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        action="store_true",
        help="Refresh the manifest in place.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the manifest without rewriting it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    script_path = Path(__file__).with_name("check_scripts_inventory.py")
    command = [sys.executable, str(script_path)]

    if args.write or not args.check:
        command.append("--update")
    else:
        command.append("--check")

    command.extend(["--manifest", args.manifest])
    result = subprocess.run(command, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
