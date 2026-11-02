"""Filesystem containment checks for evidence-location data roots (RF-003).

Rejects absolute escapes and symlink/junction walks that leave a trusted alias
base. Used when opening a resolved data root — never as a READY verdict source.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationInvalidError,
)

__all__ = [
    "EVIDENCE_LOCATION_CATALOG_PATH_FIELD",
    "assert_path_within_trusted_base",
    "reject_symlink_or_junction",
]

# Shared Sonar-safe field label for catalog containment checks.
EVIDENCE_LOCATION_CATALOG_PATH_FIELD = "evidence location catalog path"


def _normalize_resolved_path(path: Path) -> Path:
    """Normalize Win32 extended-length paths before containment comparison."""
    if os.name != "nt":
        return path
    text = str(path)
    if text.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + text[8:])
    if text.startswith("\\\\?\\"):
        return Path(text[4:])
    return path


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


def _require_absolute_pair(
    candidate: Path,
    trusted_base: Path,
    *,
    field_name: str,
) -> tuple[Path, Path]:
    base = Path(trusted_base)
    target = Path(candidate)
    if not base.is_absolute():
        raise EvidenceLocationInvalidError("trusted evidence base must be absolute")
    if not target.is_absolute():
        raise EvidenceLocationInvalidError(
            f"{field_name} must be absolute after alias resolution"
        )
    return base, target


def _resolve_trusted_base(base: Path) -> Path:
    try:
        return _normalize_resolved_path(base.resolve(strict=False))
    except OSError as exc:
        raise EvidenceLocationInvalidError(
            "trusted evidence base is not resolvable"
        ) from exc


def _relative_under_base(
    target: Path,
    base_resolved: Path,
    *,
    field_name: str,
) -> tuple[Path, Path]:
    """Return ``(relative, normalized_target)`` under ``base_resolved``."""
    try:
        return target.relative_to(base_resolved), target
    except ValueError:
        pass
    try:
        target_resolved = _normalize_resolved_path(target.resolve(strict=False))
    except OSError as exc:
        raise EvidenceLocationInvalidError(
            f"{field_name} is not resolvable within the trusted base"
        ) from exc
    if not target_resolved.is_relative_to(base_resolved):
        raise EvidenceLocationInvalidError(
            f"{field_name} escapes the trusted evidence alias base"
        )
    return target_resolved.relative_to(base_resolved), target_resolved


def _reject_link_chain(
    base_resolved: Path,
    relative: Path,
    *,
    field_name: str,
) -> None:
    cursor = base_resolved
    for part in relative.parts:
        cursor = cursor / part
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise EvidenceLocationInvalidError(
                f"{field_name} containment check failed"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or cursor.is_junction():
            raise EvidenceLocationInvalidError(
                f"{field_name} rejects symlink or junction escape"
            )


def _finalize_within_base(
    target: Path,
    base_resolved: Path,
    *,
    field_name: str,
) -> Path:
    try:
        final = _normalize_resolved_path(target.resolve(strict=False))
    except OSError as exc:
        raise EvidenceLocationInvalidError(
            f"{field_name} is not resolvable within the trusted base"
        ) from exc
    if not final.is_relative_to(base_resolved):
        raise EvidenceLocationInvalidError(
            f"{field_name} escapes the trusted evidence alias base"
        )
    return final


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
    base, target = _require_absolute_pair(
        candidate, trusted_base, field_name=field_name
    )
    base_resolved = _resolve_trusted_base(base)
    relative, target = _relative_under_base(
        target, base_resolved, field_name=field_name
    )
    _reject_link_chain(base_resolved, relative, field_name=field_name)
    return _finalize_within_base(target, base_resolved, field_name=field_name)
