"""Data quality helper transformations (no I/O, deterministic, side-effect free).

Implements RULES.md §2.8 — Data Quality Scoring and Threshold Checks.
"""

from __future__ import annotations

from ..types import ContentHash


def calculate_dq_score(valid_count: int, total_count: int) -> float:
    """Calculate data quality score (0.0 to 1.0).

    Args:
        valid_count: Number of records that passed validation.
        total_count: Total number of records processed.

    Returns:
        Quality score ratio between 0.0 and 1.0 (1.0 if total is zero).
    """
    if valid_count < 0 or total_count < 0:
        raise ValueError("valid_count and total_count must be non-negative")
    if valid_count > total_count:
        raise ValueError("valid_count cannot exceed total_count")
    if total_count == 0:
        return 1.0
    return valid_count / total_count


def exceeds_threshold(
    error_count: int,
    total_count: int,
    soft_threshold: float = 0.05,
    hard_threshold: float = 0.20,
) -> tuple[bool, bool]:
    """Check if error rate exceeds thresholds.

    Args:
        error_count: Number of records with errors.
        total_count: Total number of records processed.
        soft_threshold: Warning threshold ratio (default 5%).
        hard_threshold: Failure threshold ratio (default 20%).

    Returns:
        Tuple of (exceeds_soft, exceeds_hard) booleans.
    """
    if total_count == 0:
        return False, False
    error_rate = error_count / total_count
    return error_rate > soft_threshold, error_rate > hard_threshold


def detect_hash_collision(
    _: ContentHash,
    source_record_id: str,
    existing_source_id: str | None,
) -> bool:
    """Detect content hash collision.

    Args:
        _: Content hash (unused, kept for API compatibility).
        source_record_id: ID of the incoming record.
        existing_source_id: ID of the record already stored with the same hash.

    Returns:
        True if a collision is detected (same hash, different source IDs).
    """
    return existing_source_id is not None and source_record_id != existing_source_id
