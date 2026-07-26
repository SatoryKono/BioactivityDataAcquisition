#!/usr/bin/env python3
"""Run a module or script with the preferred BioETL project Python."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

REPO_ROOT = Path(__file__).resolve().parents[3]


def _preferred_python() -> str:
    if os.name == "nt":
        win_python = REPO_ROOT / ".venv-win" / "Scripts" / "python.exe"
        if win_python.exists():
            return str(win_python)

    wsl_venv_dir = Path(
        os.environ.get("BIOETL_WSL_VENV_DIR", str(Path.home() / ".venvs" / "bioetl"))
    )
    wsl_python = wsl_venv_dir / "bin" / "python"
    if wsl_python.exists():
        return str(wsl_python)

    repo_python = REPO_ROOT / ".venv" / "bin" / "python"
    if repo_python.exists():
        return str(repo_python)

    return sys.executable


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(
            "Usage: python scripts/engineering/dev/run_project_python.py <script.py | -m module> [args...]\n"
        )
        return 2

    target_python = _preferred_python()
    command = [target_python, *sys.argv[1:]]
    completed = subprocess.run(
        ensure_safe_cli_argv(command), cwd=REPO_ROOT, check=False
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
