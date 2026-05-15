"""Compatibility re-export for composite runner control-plane support seams."""

from __future__ import annotations

from bioetl.application.composite.runner_pkg.runner_control_plane_lifecycle import (
    CompositeRunnerControlPlaneHostProtocol,
    record_dependencies_stage_started,
    record_enrichment_stage_started,
    record_merge_stage_started,
    record_run_failed,
    record_run_metrics_event,
    record_run_shutdown,
    record_run_started,
    record_seed_stage_started,
    record_stage_completed,
    record_stage_started,
    record_with_ledger_service,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_phase_completion import (
    record_dependencies_stage_completed,
    record_run_finished,
    record_seed_stage_completed,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_phase_followup import (
    record_enrichment_stage_completed,
    record_merge_stage_completed,
)


__all__ = [
    "CompositeRunnerControlPlaneHostProtocol",
    "record_dependencies_stage_completed",
    "record_dependencies_stage_started",
    "record_enrichment_stage_completed",
    "record_enrichment_stage_started",
    "record_merge_stage_completed",
    "record_merge_stage_started",
    "record_run_failed",
    "record_run_finished",
    "record_run_metrics_event",
    "record_run_shutdown",
    "record_run_started",
    "record_seed_stage_completed",
    "record_seed_stage_started",
    "record_stage_completed",
    "record_stage_started",
    "record_with_ledger_service",
]
