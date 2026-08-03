#!/usr/bin/env python3
"""Zed-safe mypy gate matching CI type-checking scope.

CI (``.github/workflows/type-checking.yml``) runs::

    mypy --config-file pyproject.toml --strict --no-incremental src/bioetl

``src/memory/**`` is a separate package with a large historical graph-sync core.
Prefer this wrapper from Zed Type check so results match the merge gate.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_DEV_DIR = Path(__file__).resolve().parent
if str(_DEV_DIR) not in sys.path:
    sys.path.insert(0, str(_DEV_DIR))

from zed_env_doctor import ensure_ready  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    del argv
    os.chdir(REPO_ROOT)
    ensure_ready(modules=("mypy",))
    # Match CI type-checking.yml product gate. Never pass bare ``src`` — that
    # pulls the memory sidecar graph tooling (hundreds of historical errors).
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--config-file",
        "pyproject.toml",
        "--no-pretty",
        "src/bioetl",
    ]
    print("[zed_mypy] CI-aligned type gate:", " ".join(cmd), flush=True)
    print(
        "[zed_mypy] scope=src/bioetl only "
        "(memory.* is ignore_errors in pyproject.toml)",
        flush=True,
    )
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
