"""Validate and interpret immutable Bronze evidence for exact replay."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath

from bioetl.domain.control_plane.snapshot_field_resolution import (
    coerce_optional_text as _coerce_optional_text,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest

# Explicit re-export for sibling runtime_builders importers (no_implicit_reexport).
_optional_text = _coerce_optional_text


def _validated_ledger_snapshot_uri(
    *,
    manifest: RunManifest,
    entry: RunLedgerEntry,
) -> str | None:
    """Validate one ledger snapshot event and return its immutable URI."""
    details = entry.details if isinstance(entry.details, Mapping) else {}
    provider = _optional_text(details.get("provider"))
    entity = _optional_text(details.get("entity"))
    if provider is not None and provider != manifest.provider:
        raise RuntimeError(
            "Exact replay parent snapshot provider mismatch between ledger "
            f"('{provider}') and manifest ('{manifest.provider}')"
        )
    if entity is not None and entity != manifest.entity:
        raise RuntimeError(
            "Exact replay parent snapshot entity mismatch between ledger "
            f"('{entity}') and manifest ('{manifest.entity}')"
        )
    return _optional_text(details.get("immutable_uri"))


def _extract_bronze_date(immutable_uri: str) -> str:
    prefix = "bronze://"
    if not immutable_uri.startswith(prefix):
        raise RuntimeError(
            "Exact replay parent snapshot immutable_uri must use bronze:// "
            f"for cached Bronze reconstruction, got '{immutable_uri}'"
        )
    relative = immutable_uri[len(prefix) :]
    normalized = PurePosixPath(relative)
    if not normalized.parts:
        raise RuntimeError(
            "Exact replay parent snapshot immutable_uri is missing Bronze date "
            f"segment: '{immutable_uri}'"
        )
    bronze_date = str(normalized.parts[0]).strip()
    if not bronze_date:
        raise RuntimeError(
            "Exact replay parent snapshot immutable_uri has an empty Bronze date "
            f"segment: '{immutable_uri}'"
        )
    return bronze_date
