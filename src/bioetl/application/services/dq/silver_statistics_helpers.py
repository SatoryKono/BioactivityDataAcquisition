"""Helper functions for Silver statistics calculator."""

from __future__ import annotations

from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    ValueDistributionResult,
)


def detect_type_changes(
    current: dict[str, str], previous: dict[str, str]
) -> list[dict[str, str]]:
    """Find fields whose types differ between current and previous schema."""
    return [
        {"field": f, "from": previous[f], "to": current[f]}
        for f in current
        if f in previous and current[f] != previous[f]
    ]


def check_deduplication_stats(
    df_len: int,
    input_count: int,
    content_hash_unique_count: int | None,
) -> DeduplicationStatsResult:
    """Calculate deduplication statistics from input/output counts."""
    output_count = df_len
    dedupe_count = input_count - output_count

    content_hash_dupes = 0
    if content_hash_unique_count is not None:
        content_hash_dupes = output_count - content_hash_unique_count

    return DeduplicationStatsResult(
        input_before_dedupe=input_count,
        duplicates_by_content_hash=content_hash_dupes,
        duplicates_by_business_key=dedupe_count - content_hash_dupes,
        output_after_dedupe=output_count,
        status=DQCheckStatus.PASS,
    )


def check_content_hash_integrity_stats(
    df_len: int,
    hash_collision_count: int | None,
) -> ContentHashIntegrityResult:
    """Calculate content-hash collision metrics."""
    if hash_collision_count is None:
        return ContentHashIntegrityResult(
            records_checked=0,
            hash_collisions=0,
            rehash_mismatches=0,
            status=DQCheckStatus.PASS,
        )

    status = DQCheckStatus.PASS if hash_collision_count == 0 else DQCheckStatus.WARN
    return ContentHashIntegrityResult(
        records_checked=df_len,
        hash_collisions=hash_collision_count,
        rehash_mismatches=0,
        status=status,
    )


def value_distribution_to_dict(
    result: ValueDistributionResult,
) -> JsonDict:  # Any: DQ check values vary by check type
    """Convert value-distribution result to serializable dictionary."""
    output: JsonDict = {  # Any: DQ check values vary by check type
        "numeric_columns": {},
        "categorical_columns": {},
        "status": result.status.value,
    }

    for col, numeric_dist in result.numeric_columns.items():
        output["numeric_columns"][col] = to_dict(numeric_dist)

    for col, categorical_dist in result.categorical_columns.items():
        output["categorical_columns"][col] = {
            "top_values": list(categorical_dist.top_values),
            "cardinality": categorical_dist.cardinality,
        }

    return output
