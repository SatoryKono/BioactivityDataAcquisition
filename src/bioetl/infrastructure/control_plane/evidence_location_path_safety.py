"""Filesystem containment checks for evidence-location data roots (RF-003).

Rejects absolute escapes and symlink/junction walks that leave a trusted alias
base. Used when opening a resolved data root — never as a READY verdict source.
"""

from __future__ import annotations

import stat
from pathlib import Path

from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationInvalidError,
)

__all__ = [
    "assert_path_within_trusted_base",
    "reject_symlink_or_junction",
]


def reject_symlink_or_junction(path: Path, *, field_name: str = "path") -> None:
    """Raise when ``path`` itself is a symlink or Windows junction."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise EvidenceLocationInvalidError(
            f"{field_name} is not readable for containment checks"
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or path.is_junction():
        raise EvidenceLocationInvalidError(
            f"{field_name} rejects symlink or junction escape"
        )


def assert_path_within_trusted_base(
    candidate: Path,
    *,
    trusted_base: Path,
    field_name: str = "data_root",
) -> Path:
    """Return a resolved ``candidate`` that stays under ``trusted_base``.

    Every existing component from the trusted base down to ``candidate`` is
    inspected with ``lstat`` so a symlink/junction cannot walk outside the
    alias base. Missing leaf directories are allowed (empty roots may still be
    opened for read-only lookup).
    """
    base = Path(trusted_base)
    target = Path(candidate)
    if not base.is_absolute():
        raise EvidenceLocationInvalidError("trusted evidence base must be absolute")
    if not target.is_absolute():
        raise EvidenceLocationInvalidError(
            f"{field_name} must be absolute after alias resolution"
        )

    try:
        base_resolved = base.resolve(strict=False)
    except OSError as exc:
        raise EvidenceLocationInvalidError(
            "trusted evidence base is not resolvable"
        ) from exc

    try:
        relative = target.relative_to(base_resolved)
    except ValueError:
        relative = None

    if relative is None:
        try:
            target_resolved = target.resolve(strict=False)
        except OSError as exc:
            raise EvidenceLocationInvalidError(
                f"{field_name} is not resolvable within the trusted base"
            ) from exc
        if not target_resolved.is_relative_to(base_resolved):
            raise EvidenceLocationInvalidError(
                f"{field_name} escapes the trusted evidence alias base"
            )
        relative = target_resolved.relative_to(base_resolved)
        target = target_resolved

    cursor = base_resolved
    for part in relative.parts:
        cursor = cursor / part
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise EvidenceLocationInvalidError(
                f"{field_name} containment check failed"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or cursor.is_junction():
            raise EvidenceLocationInvalidError(
                f"{field_name} rejects symlink or junction escape"
            )

    try:
        final = target.resolve(strict=False)
    except OSError as exc:
        raise EvidenceLocationInvalidError(
            f"{field_name} is not resolvable within the trusted base"
        ) from exc
    if not final.is_relative_to(base_resolved):
        raise EvidenceLocationInvalidError(
            f"{field_name} escapes the trusted evidence alias base"
        )
    return final
