"""Static event-policy tables for run-ledger replay projection."""

from __future__ import annotations

from typing import TypedDict

from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane._run_ledger_runtime import (
    ARTIFACT_PUBLISHED_EVENT,
    DQ_POLICY_APPLIED_EVENT,
    MANIFEST_CREATED_EVENT,
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    RUN_STARTED_EVENT,
    STAGE_STARTED_EVENT,
)


class StageCompletionUpdate(TypedDict, total=False):
    """State updates produced by a completed composite stage."""

    state: CompositePipelineState
    seed_completed: bool
    merge_completed: bool


STAGE_COMPLETION_UPDATES: dict[str, StageCompletionUpdate] = {
    "seed": {
        "state": CompositePipelineState.SEED_COMPLETED,
        "seed_completed": True,
    },
    "dependencies": {
        "state": CompositePipelineState.DEPENDENCIES_COMPLETED,
    },
    "enrichment": {
        "state": CompositePipelineState.ENRICHMENT_COMPLETED,
    },
    "merge": {
        "state": CompositePipelineState.MERGING,
        "merge_completed": True,
    },
}

PASS_THROUGH_EVENT_TYPES = frozenset(
    {
        MANIFEST_CREATED_EVENT,
        RUN_STARTED_EVENT,
        RUN_SHUTDOWN_EVENT,
        STAGE_STARTED_EVENT,
        ARTIFACT_PUBLISHED_EVENT,
        DQ_POLICY_APPLIED_EVENT,
    }
)

TERMINAL_STATES = {
    RUN_FINISHED_EVENT: CompositePipelineState.COMPLETED,
    RUN_FAILED_EVENT: CompositePipelineState.FAILED,
}

__all__ = [
    "PASS_THROUGH_EVENT_TYPES",
    "STAGE_COMPLETION_UPDATES",
    "TERMINAL_STATES",
    "StageCompletionUpdate",
]
