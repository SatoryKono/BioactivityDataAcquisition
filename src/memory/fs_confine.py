"""Fail-closed filesystem confinement for memory artifacts."""

from __future__ import annotations

from pathlib import Path


def canonicalize_memory_path(
    path: Path,
    *,
    root: Path | None = None,
    must_exist: bool = False,
) -> Path:
    """Resolve ``path`` and reject ``..`` / symlink escape outside ``root``.

    Sonar pythonsecurity:S8707 / S2083: validate constructed paths before I/O.
    """
    candidate = Path(path).expanduser()
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"refusing path traversal: {candidate}")
    resolved = candidate.resolve(strict=must_exist)
    if root is None:
        return resolved
    root_resolved = Path(root).expanduser().resolve(strict=False)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError(
            f"refusing path outside {root_resolved.as_posix()}: {resolved.as_posix()}"
        )
    return resolved
