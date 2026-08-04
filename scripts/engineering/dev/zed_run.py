#!/usr/bin/env python3
"""Guarded Zed task launcher.

Runs the environment doctor, then either:

* ``-m <module> [args...]`` — ``python -m <module> ...``
* ``<script.py> [args...]`` — execute a repo-relative Python script

Does not install dependencies. Recovery points at
``scripts/engineering/dev/setup_env_windows.ps1``.
"""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.dev.zed_env_doctor import DEFAULT_REQUIRED_MODULES, ensure_ready

# Map ``python -m`` targets used by `.zed/tasks.json` to importable packages.
MODULE_IMPORT_MAP: dict[str, tuple[str, ...]] = {
    "ruff": ("ruff",),
    "mypy": ("mypy",),
    "bandit": ("bandit",),
    "pip_audit": ("pip_audit",),
    "pytest": ("pytest",),
    "vulture": ("vulture",),
    "xenon": ("xenon",),
}


def _usage() -> str:
    return (
        "Usage:\n"
        "  python scripts/engineering/dev/zed_run.py -m <module> [args...]\n"
        "  python scripts/engineering/dev/zed_run.py <script.py> [args...]\n"
        "  python scripts/engineering/dev/zed_run.py --doctor [--require MODULE ...]\n"
    )


def _required_for_module(module: str) -> tuple[str, ...]:
    return MODULE_IMPORT_MAP.get(module, (module,))


def _required_for_script(script: Path) -> tuple[str, ...]:
    name = script.name
    if name == "zed_pytest_lane.py":
        return ("pytest",)
    if name == "zed_lint_imports.py":
        return ("importlinter", "grimp")
    if name == "zed_vulture.py":
        return ("vulture",)
    if name == "zed_xenon.py":
        return ("xenon",)
    if name == "zed_mypy.py":
        return ("mypy",)
    if name == "setup_mcp.py":
        # Generator is stdlib + repo code; full doctor is still useful for parity.
        return DEFAULT_REQUIRED_MODULES
    return DEFAULT_REQUIRED_MODULES


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        sys.stderr.write(_usage())
        return 2

    os.chdir(REPO_ROOT)

    if args[0] == "--doctor":
        from scripts.engineering.dev.zed_env_doctor import main as doctor_main

        return int(doctor_main(args[1:]))

    if args[0] == "-m":
        if len(args) < 2:
            sys.stderr.write(_usage())
            return 2
        module = args[1]
        module_args = args[2:]
        ensure_ready(modules=_required_for_module(module))
        completed = subprocess.run(
            [sys.executable, "-m", module, *module_args],
            cwd=REPO_ROOT,
            check=False,
        )
        return int(completed.returncode)

    script_arg = args[0]
    script_path = Path(script_arg)
    if not script_path.is_absolute():
        script_path = (REPO_ROOT / script_path).resolve(strict=False)
    if not script_path.is_file():
        sys.stderr.write(f"[zed_run] script not found: {script_path}\n")
        return 2

    ensure_ready(modules=_required_for_script(script_path))
    # Mirror ``python script.py args`` semantics for helpers that read sys.argv.
    sys.argv = [str(script_path), *args[1:]]
    try:
        runpy.run_path(str(script_path), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
