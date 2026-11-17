"""Shared row indexing and hashing helpers for target migration validation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import cast

from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.schemas.base import ISO8601_TIMESTAMP_REGEX
from bioetl.domain.transformations import generate_content_hash

META = frozenset({"entity_id", "content_hash"})
GOLD_SCD_COLUMNS = frozenset({"_valid_from", "_valid_to", "_is_current", "_version"})


def business_fields(row: Mapping[str, object]) -> dict[str, object]:
    """Return business fields without storage metadata or technical columns."""
    return {
        key: value
        for key, value in row.items()
        if not key.startswith("_") and key not in META
    }


def hash_input(row: Mapping[str, object]) -> dict[str, object]:
    """Map legacy descriptions into the canonical target hash input."""
    record = business_fields(row)
    if "description" in record and "target_description" not in record:
        record["target_description"] = record["description"]
    return record


def scd_timestamp(value: object) -> bool:
    """Accept datetimes or complete ISO8601 timestamps for SCD bounds."""
    if isinstance(value, datetime):
        return True
    if (
        not isinstance(value, str)
        or re.fullmatch(ISO8601_TIMESTAMP_REGEX, value) is None
    ):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_scd_types(row: Mapping[str, object]) -> None:
    """Reject malformed temporal bounds, current flags, and SCD versions."""
    if not scd_timestamp(row["_valid_from"]):
        raise ValueError("Gold SCD _valid_from requires datetime or valid ISO8601 text")
    valid_to = row["_valid_to"]
    if valid_to is not None and not scd_timestamp(valid_to):
        raise ValueError(
            "Gold SCD _valid_to requires nullable datetime or valid ISO8601 text"
        )
    if type(row["_is_current"]) is not bool:
        raise ValueError("Gold SCD _is_current must retain its boolean type")
    version = row["_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("Gold SCD _version must retain its positive integer type")


def _row_version(
    row: Mapping[str, object], scd: bool, identity: str, current_ids: set[str]
) -> int | None:
    """Validate an optional SCD envelope and enforce one current version per target."""
    version: int | None = None
    if scd:
        if not GOLD_SCD_COLUMNS.issubset(row):
            raise ValueError(
                "invalid legacy technical field: incomplete target SCD history envelope"
            )
        try:
            validate_scd_types(row)
        except ValueError as error:
            raise ValueError(f"invalid legacy technical field: {error}") from error
        version = cast(int, row["_version"])
        if row["_is_current"]:
            if identity in current_ids:
                raise ValueError("target migration needs unique current target IDs")
            current_ids.add(identity)
    return version


def by_id(
    rows: Sequence[Mapping[str, object]],
) -> dict[tuple[str, int | None], Mapping[str, object]]:
    """Index rows by target and SCD version while rejecting duplicate identities."""
    indexed: dict[tuple[str, int | None], Mapping[str, object]] = {}
    current_ids: set[str] = set()
    scd = any(GOLD_SCD_COLUMNS.intersection(row) for row in rows)
    for row in rows:
        identity = row.get("target_id")
        if not isinstance(identity, str) or not identity:
            raise ValueError("target migration needs unique, nonempty target IDs")
        version = _row_version(row, scd, identity, current_ids)
        key = identity, version
        if key in indexed:
            raise ValueError("target migration needs unique target ID/version pairs")
        indexed[key] = row
    if not indexed:
        raise ValueError("empty target cohort cannot replace a canonical table")
    return indexed


def scoped_target_hash(
    row: Mapping[str, object],
    include_fields: tuple[str, ...],
    profile: NormalizationProfile,
) -> str:
    """Recompute the runtime hash of an already normalized persisted row."""
    record = hash_input(row)
    taxonomy_id = record.get("taxonomy_id")
    if isinstance(taxonomy_id, float) and taxonomy_id.is_integer():
        record["taxonomy_id"] = int(taxonomy_id)
    return str(
        generate_content_hash(
            record,
            "chembl",
            exclude_none=True,
            include_fields=set(include_fields),
            set_like_fields=set(profile.set_like_fields),
            datetime_policy="v2_datetime_utc",
        )
    )


def read_delta(path: Path) -> list[dict[str, object]]:
    """Read all persisted Delta rows for cohort validation."""
    from deltalake import DeltaTable

    from bioetl.infrastructure.storage.delta.table_ops import read_delta_records

    return cast(
        "list[dict[str, object]]",
        read_delta_records(DeltaTable(str(path))),
    )


__all__ = [
    "GOLD_SCD_COLUMNS",
    "META",
    "business_fields",
    "by_id",
    "hash_input",
    "read_delta",
    "scd_timestamp",
    "scoped_target_hash",
    "validate_scd_types",
]
