"""Extraction helpers for SubcellularFractionDataSource."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bioetl.application.core.entity_id import compute_subcellular_fraction_entity_id
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_governed_vocabulary,
    normalize_profile_title,
)
from bioetl.domain.schemas.constants import SUBCELLULAR_FRACTIONS
from bioetl.domain.types import JsonDict


def normalize_fraction(raw_fraction: object) -> str | None:
    """Normalize a raw subcellular fraction string."""
    if raw_fraction is None:
        return None
    normalized = normalize_profile_governed_vocabulary(
        normalize_profile_title(str(raw_fraction)),
        allowed_values=SUBCELLULAR_FRACTIONS,
        preserve_unknown=True,
    )
    return normalized if isinstance(normalized, str) and normalized else None


def compute_entity_id(subcellular_fraction: str) -> str:
    """Compute a deterministic entity ID for a subcellular fraction."""
    return compute_subcellular_fraction_entity_id(subcellular_fraction)


def create_fraction_record(
    assay: JsonDict,
    fraction: str,
) -> JsonDict:
    """Create the initial output record for a unique fraction."""
    assay_id = assay.get("assay_id") or assay.get("assay_chembl_id")
    return {
        "entity_id": compute_entity_id(fraction),
        "subcellular_fraction": fraction,
        "example_assay_id": str(assay_id).strip() if assay_id else None,
        "assay_count": 1,
    }


def update_fraction_record(
    record: JsonDict,
    assay: JsonDict,
) -> None:
    """Merge another assay observation into an existing fraction record."""
    record["assay_count"] = int(record["assay_count"]) + 1
    if record["example_assay_id"] is not None:
        return
    assay_id = assay.get("assay_id") or assay.get("assay_chembl_id")
    record["example_assay_id"] = str(assay_id).strip() if assay_id else None


async def extract_unique_fraction_records(
    assays: AsyncIterator[JsonDict],
    limit: int | None,
    seen_fractions: set[str],
) -> AsyncIterator[JsonDict]:
    """Collect unique subcellular fraction records from an assay stream.

    Always consumes the full ``assays`` stream so ``assay_count`` and
    ``example_assay_id`` are fully aggregated for collected fractions before any
    record is yielded (#7787). When ``limit`` is set, only that many unique
    fractions are *tracked*, but later assays that map to already-tracked
    fractions still update counts.
    """
    seen_fractions.clear()
    records: dict[str, JsonDict] = {}
    try:
        async for assay in assays:
            fraction = normalize_fraction(assay.get("assay_subcellular_fraction"))
            if not fraction:
                continue
            key = fraction.lower()
            record = records.get(key)
            if record is None:
                # Cap unique fractions, but keep consuming the stream for updates.
                if limit is not None and len(records) >= limit:
                    continue
                record = create_fraction_record(assay, fraction)
                records[key] = record
                seen_fractions.add(key)
                continue
            update_fraction_record(record, assay)
    finally:
        aclose = getattr(assays, "aclose", None)
        if callable(aclose):
            from collections.abc import Awaitable, Callable
            from typing import cast

            aclose_fn = cast(Callable[[], Awaitable[object]], aclose)
            await aclose_fn()
    for record in records.values():
        yield record
