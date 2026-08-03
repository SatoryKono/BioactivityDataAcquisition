"""Pipeline lifecycle bounded vocabularies for Prometheus metric labels."""

from __future__ import annotations

__all__ = [
    "_ALLOWED_BATCH_LIFECYCLE_EVENT_LABELS",
    "_ALLOWED_COMPOSITE_PHASE_ERROR_KIND_LABELS",
    "_ALLOWED_COMPOSITE_PHASE_LOSS_KIND_LABELS",
    "_ALLOWED_COMPOSITE_PHASE_RECORD_OUTCOME_LABELS",
    "_ALLOWED_COMPOSITE_PHASE_RETRY_KIND_LABELS",
    "_ALLOWED_PHASE_LABELS",
    "_ALLOWED_POSTRUN_PHASE_LABELS",
    "_ALLOWED_STAGE_MODEL_OUTCOME_LABELS",
    "_ALLOWED_STAGE_MODEL_STAGE_LABELS",
]

_ALLOWED_STAGE_MODEL_STAGE_LABELS = frozenset(
    {
        "input",
        "ingestion",
        "transform",
        "validation",
        "storage",
        "output",
        "bronze",
        "silver",
        "gold",
        "other",
    }
)
_ALLOWED_STAGE_MODEL_OUTCOME_LABELS = frozenset(
    {
        "fetched",
        "bronze_written",
        "records",
        "silver_ready",
        "valid",
        "gold_ready",
        "filtered_out",
        "evaluated",
        "quarantined",
        "skipped",
        "deduplicated",
        "silver_written",
        "gold_written",
        "written",
        "excluded_by_contract",
        "ready",
        "other",
    }
)
_ALLOWED_BATCH_LIFECYCLE_EVENT_LABELS = frozenset(
    {"created", "written", "failed", "other"}
)
_ALLOWED_COMPOSITE_PHASE_RECORD_OUTCOME_LABELS = frozenset(
    {"extracted", "silver", "input", "enriched", "merged", "fully_enriched", "other"}
)
_ALLOWED_COMPOSITE_PHASE_ERROR_KIND_LABELS = frozenset(
    {"failed", "timeout", "record_error", "other"}
)
_ALLOWED_COMPOSITE_PHASE_LOSS_KIND_LABELS = frozenset(
    {"unwritten", "not_found", "partially_enriched", "quarantined", "other"}
)
_ALLOWED_COMPOSITE_PHASE_RETRY_KIND_LABELS = frozenset({"resume", "other"})
_ALLOWED_PHASE_LABELS = frozenset(
    {
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "preflight_validation",
        "seed",
        "dependencies",
        "enrichment",
        "merge",
        "cross_validation",
        "gold_write",
        "other",
    }
)
_ALLOWED_POSTRUN_PHASE_LABELS = frozenset(
    {
        "dq_evaluation",
        "dq_reports",
        "compaction",
        "vacuum",
        "final_metadata",
        "other",
    }
)
