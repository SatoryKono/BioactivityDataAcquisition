#!/usr/bin/env python3
"""Zed-safe import-linter runner (Windows PowerShell argv/cwd-safe).

The architecture contracts live in ``.importlinter`` (not ``pyproject.toml``).
Zed GUI PowerShell may also drop task args or run with a non-repo cwd, so this
helper always ``chdir``s to the repository root and invokes import-linter there.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_DEV_DIR = Path(__file__).resolve().parent
if str(_DEV_DIR) not in sys.path:
    sys.path.insert(0, str(_DEV_DIR))

from scripts.engineering.dev.zed_env_doctor import ensure_ready


def main() -> int:
    os.chdir(REPO_ROOT)
    # Fail with an actionable bootstrap diagnostic instead of ModuleNotFoundError.
    ensure_ready(modules=("importlinter", "grimp"))

    # Prefer the tracked contracts file explicitly so a wrong --config from an
    # old task definition cannot point at pyproject.toml.
    config_path = REPO_ROOT / ".importlinter"
    if not config_path.is_file():
        sys.stderr.write(f"[zed_lint_imports] missing contracts file: {config_path}\n")
        return 2

    from importlinter.cli import lint_imports

    # On Windows, the committed cache_dir (/tmp/...) is not usable; disable
    # cache so the check remains deterministic without a Unix temp mount.
    return int(
        lint_imports(
            config_filename=str(config_path),
            no_cache=True,
            verbose=False,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
