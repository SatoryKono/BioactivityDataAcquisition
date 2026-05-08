"""Internal event-family inference helpers for run-ledger entries."""

from __future__ import annotations

MANIFEST_CREATED_EVENT = "manifest_created"
RUN_STARTED_EVENT = "run_started"
RUN_FINISHED_EVENT = "run_finished"
RUN_FAILED_EVENT = "run_failed"
RUN_SHUTDOWN_EVENT = "run_shutdown"
STAGE_STARTED_EVENT = "stage_started"
STAGE_COMPLETED_EVENT = "stage_completed"
ARTIFACT_PUBLISHED_EVENT = "artifact_published"
INPUT_SNAPSHOT_PUBLISHED_EVENT = "input_snapshot_published"
_DIAGNOSTIC_FAMILY = "diagnostic"
_PIPELINE_LIFECYCLE_FAMILY = "pipeline.lifecycle"
_PIPELINE_PHASE_FAMILY = "pipeline.phase"

_LEDGER_EVENT_FAMILY_EXACT: dict[str, str] = {
    MANIFEST_CREATED_EVENT: _DIAGNOSTIC_FAMILY,
    RUN_STARTED_EVENT: _PIPELINE_LIFECYCLE_FAMILY,
    RUN_FINISHED_EVENT: _PIPELINE_LIFECYCLE_FAMILY,
    RUN_FAILED_EVENT: _PIPELINE_LIFECYCLE_FAMILY,
    RUN_SHUTDOWN_EVENT: _PIPELINE_LIFECYCLE_FAMILY,
    STAGE_STARTED_EVENT: _PIPELINE_PHASE_FAMILY,
    STAGE_COMPLETED_EVENT: _PIPELINE_PHASE_FAMILY,
    ARTIFACT_PUBLISHED_EVENT: "artifact",
    INPUT_SNAPSHOT_PUBLISHED_EVENT: "input_snapshot",
}
_LEDGER_EVENT_FAMILY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("dq_", "dq"),
    ("lineage_", "lineage"),
    ("checkpoint_", "checkpoint"),
    ("composite_", "composite"),
    ("artifact_", "artifact"),
)
_LEDGER_EVENT_FAMILY_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("_started", _PIPELINE_PHASE_FAMILY),
    ("_completed", _PIPELINE_PHASE_FAMILY),
)


def _match_ledger_event_family_by_suffix(event_type: str) -> str | None:
    for suffix, family in _LEDGER_EVENT_FAMILY_SUFFIXES:
        if event_type.endswith(suffix):
            return family
    return None


def _match_ledger_event_family_by_prefix(event_type: str) -> str | None:
    for prefix, family in _LEDGER_EVENT_FAMILY_PREFIXES:
        if event_type.startswith(prefix):
            return family
    return None


def infer_ledger_event_family(event_type: str) -> str:
    """Infer stable event-family taxonomy for ledger entries."""
    normalized_event_type = event_type.strip().lower()
    if not normalized_event_type:
        return _DIAGNOSTIC_FAMILY
    for family in (
        _LEDGER_EVENT_FAMILY_EXACT.get(normalized_event_type),
        _match_ledger_event_family_by_suffix(normalized_event_type),
        _match_ledger_event_family_by_prefix(normalized_event_type),
    ):
        if family is not None:
            return family
    return _DIAGNOSTIC_FAMILY
