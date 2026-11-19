#!/usr/bin/env python3
"""Zed environment doctor (stdlib-only).

Validates the native-Windows project interpreter (``.venv-win``) and the
import surface used by local Zed helpers. Emits actionable recovery
guidance instead of raw ``ModuleNotFoundError`` traces.

Does not install or upgrade dependencies.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[3]
VENV_DIRNAME = ".venv-win"
VENV_PYTHON_REL = Path(VENV_DIRNAME) / "Scripts" / "python.exe"

# Supported product Python floor for BioETL local Zed work.
MIN_PYTHON = (3, 12)

# Modules required by the local Zed quality/test helpers.
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

# Explicit scope avoids requiring unrelated optional tools for a single-tool task.
LOCKED_TOOLS: tuple[str, ...] = (
    "ruff",
    "mypy",
    "basedpyright",
    "pyrefly",
    "ty",
    "pytest",
)


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


def _locked_package_version(packages: Sequence[dict[str, object]], tool: str) -> str:
    """Return the single uv.lock version recorded for one tool."""
    matches: set[str] = set()
    for package in packages:
        if package.get("name") == tool:
            version = package.get("version")
            if not isinstance(version, str):
                raise ValueError(f"expected a locked version for {tool}")
            matches.add(version)
    if len(matches) != 1:
        raise ValueError(f"expected one locked version for {tool}")
    return matches.pop()


def _locked_tool_versions(lock_path: Path, tools: Sequence[str]) -> dict[str, str]:
    with lock_path.open("rb") as stream:
        document = cast(dict[str, object], tomllib.load(stream))
    raw_packages = document.get("package", [])
    if not isinstance(raw_packages, list):
        raise ValueError("expected uv.lock package tables")
    packages: list[dict[str, object]] = []
    for package in cast(list[object], raw_packages):
        if not isinstance(package, dict):
            raise ValueError("expected uv.lock package tables")
        packages.append(cast(dict[str, object], package))
    versions: dict[str, str] = {}
    for tool in tools:
        versions[tool] = _locked_package_version(packages, tool)
    return versions


def check_locked_versions(
    modules: Iterable[str] = LOCKED_TOOLS,
    *,
    repo_root: Path | None = None,
) -> list[Finding]:
    """Compare selected tool distributions to uv.lock without importing tools."""
    tools = tuple(dict.fromkeys(module for module in modules if module in LOCKED_TOOLS))
    if not tools:
        return []
    root = REPO_ROOT if repo_root is None else repo_root
    try:
        expected_versions = _locked_tool_versions(root / "uv.lock", tools)
    except (OSError, UnicodeError, ValueError) as exc:
        return [
            Finding(
                code="invalid_lockfile",
                message=f"Cannot verify tool versions from uv.lock: {exc}",
                recovery="Restore or explicitly regenerate uv.lock, then run "
                + SETUP_HINT,
            )
        ]

    findings: list[Finding] = []
    for tool, expected in expected_versions.items():
        try:
            installed = metadata.version(tool)
        except metadata.PackageNotFoundError:
            findings.append(
                Finding(
                    code="missing_distribution",
                    message=f"Required tool distribution is missing: {tool}",
                    recovery=f"Install locked project tools with: {SETUP_HINT}",
                )
            )
            continue
        if installed != expected:
            findings.append(
                Finding(
                    code="locked_version_mismatch",
                    message=f"{tool} {installed} is installed; uv.lock requires {expected}.",
                    recovery=f"Sync the existing project environment with: {SETUP_HINT}",
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
    findings.extend(
        check_locked_versions(
            LOCKED_TOOLS if modules is None else required, repo_root=repo_root
        )
    )
    return findings


def format_report(findings: Sequence[Finding]) -> str:
    """Render a concise multi-line diagnostic for stderr."""
    if not findings:
        return (
            "[zed_env_doctor] ok: .venv-win interpreter and required "
            "task imports and locked tool versions are available\n"
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
            "Validates .venv-win, task imports, and tool versions from uv.lock. "
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
