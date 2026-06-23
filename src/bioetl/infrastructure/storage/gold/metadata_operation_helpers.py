"""Passive helpers for Gold metadata write operations."""

from __future__ import annotations

from bioetl.domain.models.metadata import GoldMetadata


def normalize_delta_version_value(version_value: object) -> int | None:
    """Normalize a DeltaTable.version() result to an integer version."""
    if isinstance(version_value, int):
        return version_value
    if isinstance(version_value, str) and version_value.strip().isdigit():
        return int(version_value.strip())
    return None


def extract_delta_table_version(table: object) -> int | None:
    """Extract a normalized version from a DeltaTable-like object."""
    version_fn = getattr(table, "version", None)
    if not callable(version_fn):
        return None
    return normalize_delta_version_value(version_fn())


def raise_missing_gold_metadata_bundle(
    *,
    table_path: str,
    table_name: str,
) -> GoldMetadata:
    """Fail closed when canonical Gold metadata bundle construction is unavailable."""
    raise RuntimeError(
        "MetadataCoordinator with create_gold_metadata_bundle is required "
        f"for Gold metadata publication: table_name={table_name}, "
        f"table_path={table_path}"
    )
