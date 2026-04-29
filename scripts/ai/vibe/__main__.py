#!/usr/bin/env python3
"""Compatibility entry point for Vibe launch tooling.

Usage:
    python -m scripts.ai vibe [check|setup|args...]
    python -m scripts.ai.vibe [check|setup|args...]
    python -m scripts.ai vibe --help
    python -m scripts.ai.vibe --help

The canonical public Python surface is ``python -m scripts.ai vibe``.
This direct module path remains only as a compatibility entrypoint.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).parent


def _posix_command(args: list[str]) -> list[str]:
    mistral_dir = _DIR.parent / "mistrallvibe" / "helper"
    if args[:1] == ["check"]:
        return ["bash", str(mistral_dir / "check-env.sh")]
    if args[:1] == ["setup"]:
        return ["bash", str(mistral_dir / "setup-env.sh")]
    return ["bash", str(_DIR / "launch.sh"), *args]


def _windows_command(args: list[str]) -> list[str]:
    mistral_dir = _DIR.parent / "mistrallvibe" / "helper"
    if args[:1] == ["check"]:
        target = mistral_dir / "check-env.ps1"
    elif args[:1] == ["setup"]:
        target = mistral_dir / "setup-env.ps1"
    else:
        target = _DIR / "launch.ps1"
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(target),
            *args,
        ]
    return [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(target),
    ]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args and args[0] in {"-h", "--help"}:
        print(__doc__ or "", end="")
        return 0
    command = _windows_command(args) if os.name == "nt" else _posix_command(args)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
