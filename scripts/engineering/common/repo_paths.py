#!/usr/bin/env python3
"""Shared path helpers for BioETL scripts."""

from __future__ import annotations

from pathlib import Path


def resolve_repo_root() -> Path:
    """Resolve the repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[0]


REPO_ROOT = resolve_repo_root()


def ensure_path_within_root(path: Path, root: Path) -> Path:
    """Resolve ``path`` and refuse values that escape ``root``.

    Used at filesystem write/read sinks so static path-injection analyzers can
    see an explicit containment check before I/O.

    Callers that intentionally write outside the repository (CLI ``--root``,
    unit-test fixtures) must pass that directory as ``root``.
    """
    resolved_root = root.resolve()
    resolved_path = path.expanduser().resolve(strict=False)
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(
            f"refusing path outside {resolved_root.as_posix()}: {resolved_path.as_posix()}"
        )
    return resolved_path


def ensure_repo_path(path: Path, *, root: Path | None = None) -> Path:
    """Resolve ``path`` and require it to stay under the repository root."""
    return ensure_path_within_root(path, root or REPO_ROOT)


def resolve_cli_path(
    path: str | Path,
    *,
    root: Path | None = None,
) -> Path:
    """Resolve a CLI path argument relative to ``root`` and confine it.

    Relative values are joined under ``root`` (default: repository root) before
    the containment check. Use this as the standard sink-side guard for
    Sonar pythonsecurity:S8707 (CLI path taint / filesystem escape).
    """
    base = (root or REPO_ROOT).expanduser().resolve(strict=False)
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return ensure_path_within_root(candidate, base)


def argparse_repo_path(value: str) -> Path:
    """``argparse`` ``type=`` callback that confines paths to the repo root."""
    return resolve_cli_path(value)
