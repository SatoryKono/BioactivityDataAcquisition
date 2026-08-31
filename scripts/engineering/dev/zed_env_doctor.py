#!/usr/bin/env python3
"""Zed environment doctor (stdlib-only).

Validates the native-Windows project interpreter (``.venv-win``) and the
import surface required by tracked Zed tasks. Emits actionable recovery
guidance instead of raw ``ModuleNotFoundError`` traces.

Does not install or upgrade dependencies.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VENV_DIRNAME = ".venv-win"
VENV_PYTHON_REL = Path(VENV_DIRNAME) / "Scripts" / "python.exe"

# Supported product Python floor for BioETL local Zed work.
MIN_PYTHON = (3, 12)

# Modules required by tracked `.zed/tasks.json` quality/test surfaces.
DEFAULT_REQUIRED_MODULES: tuple[str, ...] = (
    "pytest",
    "pytest_cov",
    "ruff",
    "mypy",
    "importlinter",
    "grimp",
    "bandit",
    "pip_audit",
    "vulture",
    "xenon",
    "jsonschema",
)

# Friendly names for recovery messages when import name differs from tool brand.
MODULE_LABELS: dict[str, str] = {
    "importlinter": "import-linter",
    "pip_audit": "pip-audit",
}

SETUP_HINT = r".\scripts\engineering\dev\setup_env_windows.ps1"


@dataclass(frozen=True, slots=True)
class Finding:
    """Single doctor finding with a stable machine-readable code."""

    code: str
    message: str
    recovery: str


def _module_label(module: str) -> str:
    return MODULE_LABELS.get(module, module)


def expected_venv_python(repo_root: Path | None = None) -> Path:
    """Return the canonical Windows venv interpreter path."""
    root = REPO_ROOT if repo_root is None else repo_root
    return (root / VENV_PYTHON_REL).resolve(strict=False)


def _is_under_venv(executable: Path, venv_python: Path) -> bool:
    try:
        exe = executable.resolve(strict=False)
        venv = venv_python.resolve(strict=False)
    except OSError:
        return False
    return exe == venv or venv.parent in exe.parents


def check_interpreter(
    *,
    repo_root: Path | None = None,
    executable: str | None = None,
) -> list[Finding]:
    """Validate `.venv-win` presence and a supported Python version."""
    root = REPO_ROOT if repo_root is None else repo_root
    venv_python = expected_venv_python(root)
    findings: list[Finding] = []

    if not venv_python.is_file():
        findings.append(
            Finding(
                code="missing_venv",
                message=f"Missing Windows project interpreter: {venv_python}",
                recovery=f"Create it with: {SETUP_HINT}",
            )
        )
        return findings

    exe = Path(sys.executable if executable is None else executable)
    if not _is_under_venv(exe, venv_python):
        findings.append(
            Finding(
                code="wrong_interpreter",
                message=(f"Running under {exe}, but Zed tasks expect {venv_python}."),
                recovery=(
                    "Select the `.venv-win` toolchain in Zed, or re-run tasks "
                    f"from the project venv. Refresh with: {SETUP_HINT}"
                ),
            )
        )

    version = sys.version_info[:2]
    if version < MIN_PYTHON:
        findings.append(
            Finding(
                code="python_version",
                message=(
                    f"Python {version[0]}.{version[1]} is below the supported "
                    f"floor {MIN_PYTHON[0]}.{MIN_PYTHON[1]}."
                ),
                recovery=f"Recreate `.venv-win` with Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}: {SETUP_HINT}",
            )
        )

    return findings


def check_modules(modules: Iterable[str]) -> list[Finding]:
    """Validate that required import targets are present (no side effects)."""
    findings: list[Finding] = []
    for module in modules:
        if importlib.util.find_spec(module) is None:
            label = _module_label(module)
            findings.append(
                Finding(
                    code="missing_module",
                    message=f"Required package is not importable: {label} ({module})",
                    recovery=(
                        "This is an environment/bootstrap gap, not a product "
                        f"failure. Refresh the editable install: {SETUP_HINT}"
                    ),
                )
            )
    return findings


def check_workdir(
    *, repo_root: Path | None = None, cwd: Path | None = None
) -> list[Finding]:
    """Ensure the process is running from the repository root (or a child)."""
    root = (REPO_ROOT if repo_root is None else repo_root).resolve(strict=False)
    current = (Path.cwd() if cwd is None else cwd).resolve(strict=False)
    try:
        current.relative_to(root)
    except ValueError:
        return [
            Finding(
                code="wrong_cwd",
                message=f"Working directory {current} is outside the repo root {root}.",
                recovery="Open the BioETL worktree root in Zed, then re-run the task.",
            )
        ]
    return []


def diagnose(
    *,
    modules: Sequence[str] | None = None,
    repo_root: Path | None = None,
    executable: str | None = None,
    cwd: Path | None = None,
    skip_interpreter: bool = False,
) -> list[Finding]:
    """Run all doctor checks and return findings (empty means healthy)."""
    required = tuple(DEFAULT_REQUIRED_MODULES if modules is None else modules)
    findings: list[Finding] = []
    if not skip_interpreter:
        findings.extend(check_interpreter(repo_root=repo_root, executable=executable))
    findings.extend(check_workdir(repo_root=repo_root, cwd=cwd))
    findings.extend(check_modules(required))
    return findings


def format_report(findings: Sequence[Finding]) -> str:
    """Render a concise multi-line diagnostic for stderr."""
    if not findings:
        return (
            "[zed_env_doctor] ok: .venv-win interpreter and required "
            "task imports are available\n"
        )

    lines = [
        "[zed_env_doctor] environment is not ready for Zed quality tasks",
        "",
    ]
    for index, finding in enumerate(findings, start=1):
        lines.append(f"{index}. [{finding.code}] {finding.message}")
        lines.append(f"   recovery: {finding.recovery}")
    lines.append("")
    lines.append(
        "Hint: Zed tasks do not auto-install dependencies. "
        f"Use {SETUP_HINT} once, then re-run Environment: verify."
    )
    lines.append("")
    return "\n".join(lines)


def ensure_ready(
    *,
    modules: Sequence[str] | None = None,
    repo_root: Path | None = None,
) -> None:
    """Exit with a non-zero status and no traceback when the env is incomplete.

    Safe to call from other Zed helpers. Does not install packages.
    """
    root = REPO_ROOT if repo_root is None else repo_root
    # Helpers already chdir to REPO_ROOT in most cases; still normalize here.
    try:
        os.chdir(root)
    except OSError as exc:
        sys.stderr.write(f"[zed_env_doctor] cannot chdir to repo root {root}: {exc}\n")
        raise SystemExit(2) from None

    findings = diagnose(modules=modules, repo_root=root)
    if findings:
        sys.stderr.write(format_report(findings))
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the Zed Environment: verify task."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help", "help"}:
        sys.stdout.write(
            "Usage: python scripts/engineering/dev/zed_env_doctor.py "
            "[--require MODULE ...]\n"
            "Validates .venv-win and imports used by Zed tasks. "
            "Does not install packages.\n"
        )
        return 0

    modules: list[str] | None = None
    if args:
        if args[0] != "--require" or len(args) < 2:
            sys.stderr.write(
                "Usage: python scripts/engineering/dev/zed_env_doctor.py "
                "[--require MODULE ...]\n"
            )
            return 2
        modules = args[1:]

    findings = diagnose(modules=modules)
    sys.stderr.write(format_report(findings))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
