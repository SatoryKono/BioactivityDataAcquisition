#!/usr/bin/env python3
"""Unified entry point for AI operational scripts.

Usage:
    python -m scripts.ai <surface> [args...]
    python -m scripts.ai --help

Surfaces:
    agent_tools  Optional AgentDebugX and ProofAgent adapters
    codex    Codex setup/check tooling
    mcp      MCP operational tooling
    vibe     Vibe launch tooling
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

_DIR = Path(__file__).parent
SURFACES = ("agent_tools", "codex", "mcp", "vibe")


def _codex_command(rest: list[str]) -> list[str]:
    if os.name == "nt":
        launcher = _DIR / "codex" / "run-codex.ps1"
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(launcher),
            *rest,
        ]
    return ["bash", str((_DIR / "codex" / "run-codex.sh").resolve()), *rest]


def _module_command(surface: str, rest: list[str]) -> list[str]:
    return [sys.executable, "-m", f"scripts.ai.{surface}", *rest]


def _vibe_command(rest: list[str]) -> list[str]:
    vibe_dir = _DIR / "vibe"
    helper_dir = vibe_dir / "helper"
    if os.name == "nt":
        if rest[:1] == ["check"]:
            return [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(helper_dir / "check-env.ps1"),
            ]
        if rest[:1] == ["setup"]:
            return [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(helper_dir / "setup-env.ps1"),
            ]
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(vibe_dir / "launch.ps1"),
            *rest,
        ]

    if rest[:1] == ["check"]:
        return ["bash", str(helper_dir / "check-env.sh")]
    if rest[:1] == ["setup"]:
        return ["bash", str(helper_dir / "setup-env.sh")]
    return ["bash", str(vibe_dir / "launch.sh"), *rest]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__ or "", end="")
        return 0

    surface, rest = args[0], args[1:]
    if surface not in SURFACES:
        available = ", ".join(sorted(SURFACES))
        print(f"Unknown surface: {surface}", file=sys.stderr)
        print(f"Available: {available}", file=sys.stderr)
        return 2

    if surface == "codex":
        command = _codex_command(rest)
    elif surface == "vibe":
        command = _vibe_command(rest)
    else:
        command = _module_command(surface, rest)

    return subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        ensure_safe_cli_argv([str(x) for x in command]), check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
