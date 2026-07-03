"""Domain layer constants.

Centralized constants shared across domain modules.
This module contains only immutable values with no external dependencies.

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- REQ-ID-001 to REQ-ID-008: Content hash algorithm (meta-field exclusion)
"""

from __future__ import annotations

# =============================================================================
# Processing defaults
# =============================================================================

DEFAULT_BATCH_SIZE: int = 100
"""Default number of records per batch for pipeline processing."""

DEFAULT_CHECKPOINT_INTERVAL: int = 1000
"""Default interval (in records) between checkpoint saves."""

DEFAULT_LOCK_TTL_SECONDS: int = 3600
"""Default time-to-live for runtime locks (1 hour)."""

# =============================================================================
# Data Quality defaults
# =============================================================================

DEFAULT_DQ_QUALITY_SCORE_MIN: float = 0.80
"""Minimum data quality score threshold for pipeline pass."""

# =============================================================================
# Content hashing
# =============================================================================

# Meta-fields to exclude from hash calculation (RULES.md §2.8.1)
# These are system/ingestion fields that should not affect content identity.
META_FIELDS: frozenset[str] = frozenset(
    {
        "_ingestion_ts",
        "_run_id",
        "_run_type",
        "_dq_warn",
        "_dq_error",
        "_source_batch_id",
        "_index",
        "_lookup_method",
        "_original_id",
        "_source",
    }
)

# Persisted Delta rows must not carry occurrence-scoped runtime provenance.
# These anchors travel separately via explicit write kwargs, sidecars,
# lineage fragments, run manifests, and audit artifacts.
NONDETERMINISTIC_PERSISTED_FIELDS: frozenset[str] = frozenset(
    {
        "_ingestion_ts",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_composite_run_id",
        "_lineage_created_at",
    }
)

# Application transformer output must not carry occurrence-scoped provenance
# in canonical Silver/Gold row payloads. These anchors travel separately via
# explicit write kwargs, sidecars, audit records, and control-plane artifacts.
TRANSIENT_RUNTIME_PROVENANCE_SOURCE_FIELDS: frozenset[str] = frozenset(
    {
        "ingestion_ts",
        "run_id",
        "run_type",
        "source_batch_id",
    }
)
