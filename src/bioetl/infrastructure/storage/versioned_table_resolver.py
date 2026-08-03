"""Helpers for resolving versioned physical table names."""

from __future__ import annotations

from collections.abc import Sequence

__all__ = [
    "resolve_read_candidates",
    "resolve_versioned_table_name",
    "resolve_write_targets",
]

_SEMVER_PARTS_COUNT = 3


def _validate_logical_table_name(logical_table: str) -> str:
    normalized = logical_table.strip()
    if not normalized:
        raise ValueError("logical_table must be a non-empty string")
    return normalized


def _validate_semver(version: str) -> str:
    normalized = version.strip()
    parts = normalized.split(".")
    if len(parts) != _SEMVER_PARTS_COUNT or any(not part.isdigit() for part in parts):
        raise ValueError(f"contract version must be SemVer X.Y.Z, got {version!r}")
    return normalized


def resolve_versioned_table_name(logical_table: str, version: str) -> str:
    """Return the versioned logical table name for one contract version."""
    normalized_table = _validate_logical_table_name(logical_table)
    normalized_version = _validate_semver(version)
    return f"{normalized_table}__v{normalized_version.replace('.', '_')}"


def resolve_read_candidates(
    logical_table: str,
    read_order: Sequence[str],
) -> list[str]:
    """Resolve ordered fallback read candidates for a logical table."""
    return [
        resolve_versioned_table_name(logical_table, version) for version in read_order
    ]


def resolve_write_targets(
    logical_table: str,
    write_versions: Sequence[str],
) -> list[str]:
    """Resolve ordered physical write targets for a logical table."""
    return [
        resolve_versioned_table_name(logical_table, version)
        for version in write_versions
    ]
