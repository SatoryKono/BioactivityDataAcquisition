"""Dataset-level semantic content identity helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from bioetl.domain.transformations.hashing import (
    canonical_json_dumps,
    normalize_for_hash,
)

DATASET_CONTENT_HASH_OCCURRENCE_ONLY_FIELDS = frozenset(
    {
        "content_hash",
        "run_id",
        "manifest_id",
        "composite_run_id",
        "lineage_created_at",
        "write_started_at",
        "write_completed_at",
        "created_at",
        "updated_at",
    }
)


def build_dataset_content_hash(
    *,
    provider: str,
    records: Sequence[Mapping[str, object]] | None,
) -> str | None:
    """Build an order-insensitive dataset-level content hash for one sidecar."""
    if not records:
        return None
    normalized_rows = [
        canonical_json_dumps(
            normalize_for_hash(
                {str(key): value for key, value in record.items()},
                exclude_fields=set(DATASET_CONTENT_HASH_OCCURRENCE_ONLY_FIELDS),
            )
        )
        for record in records
    ]
    normalized_rows.sort()
    canonical_payload = canonical_json_dumps(
        {
            "provider": provider,
            "rows": normalized_rows,
        }
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


__all__ = [
    "DATASET_CONTENT_HASH_OCCURRENCE_ONLY_FIELDS",
    "build_dataset_content_hash",
]
