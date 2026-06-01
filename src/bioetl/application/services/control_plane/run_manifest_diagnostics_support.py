"""Public facade for run-manifest diagnostics helpers owned by control_plane.

``manifest.diagnostics`` modules MUST import shared implementation symbols through
this module instead of ``control_plane._*`` private modules (RF-011.2).
"""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.artifact_payloads import (
    ARTIFACT_DETAIL_KEYS,
    ARTIFACT_TRACE_ORDERED_KEYS,
    build_artifact_ref_from_ledger_entry,
)
from bioetl.application.services.control_plane.manifest.diagnostics.ledger_processing import (
    _process_ledger_entries,
)
from bioetl.application.services.control_plane.manifest.diagnostics.main_helpers import (
    _build_unified_reproducibility_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence import (
    build_alert_signals,
    build_lineage_closure_boundary,
    build_next_steps,
    build_persistence_profile,
    claims_payload,
    missing_replay_ready_requirements,
    resolve_required_profile_requirements,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_helpers import (
    _build_replay_parentage,
    _collect_append_mode_semantic_sinks,
    _is_composite_execution_context,
    _resolve_applied_checkpoint_compatibility_policy,
    _resolve_exact_replay_support_boundary,
    _resolve_replay_family_contract,
    _resolve_reproducibility_profile,
    _resolve_requested_checkpoint_compatibility_policy,
    _resolve_required_persistence_profile,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_state import (
    _build_replay_state_projection,
    _resolve_broader_historical_exact_replay_state,
    _resolve_continuation_mode,
    _resolve_exact_replay_blockers,
    _resolve_historical_live_run_upgrade_state,
    _resolve_replay_capability_reason,
    _resolve_replay_mode,
    _resolve_replay_occurrence_kind,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary import (
    _build_exact_replay_anchors,
    _build_final_summary,
    _build_runtime_views,
    _FinalSummaryRequest,
    _RuntimeViewsRequest,
)
from bioetl.application.services.control_plane.manifest.replay_family_contract_payload import (
    build_replay_family_contract_payload,
)
from bioetl.application.services.control_plane.manifest.snapshot_payloads import (
    input_snapshot_payload,
    manifest_input_snapshot_trace_refs,
    serialize_snapshot_captured_at,
    source_ref_payload,
    source_refs_payload,
)

__all__ = [
    "ARTIFACT_DETAIL_KEYS",
    "ARTIFACT_TRACE_ORDERED_KEYS",
    "_FinalSummaryRequest",
    "_RuntimeViewsRequest",
    "_build_exact_replay_anchors",
    "_build_final_summary",
    "_build_replay_parentage",
    "_build_replay_state_projection",
    "_build_runtime_views",
    "_build_unified_reproducibility_diagnostics",
    "_collect_append_mode_semantic_sinks",
    "_is_composite_execution_context",
    "_process_ledger_entries",
    "_resolve_applied_checkpoint_compatibility_policy",
    "_resolve_broader_historical_exact_replay_state",
    "_resolve_continuation_mode",
    "_resolve_exact_replay_blockers",
    "_resolve_exact_replay_support_boundary",
    "_resolve_historical_live_run_upgrade_state",
    "_resolve_replay_capability_reason",
    "_resolve_replay_family_contract",
    "_resolve_replay_mode",
    "_resolve_replay_occurrence_kind",
    "_resolve_reproducibility_profile",
    "_resolve_requested_checkpoint_compatibility_policy",
    "_resolve_required_persistence_profile",
    "build_alert_signals",
    "build_artifact_ref_from_ledger_entry",
    "build_lineage_closure_boundary",
    "build_next_steps",
    "build_persistence_profile",
    "build_replay_family_contract_payload",
    "claims_payload",
    "input_snapshot_payload",
    "manifest_input_snapshot_trace_refs",
    "missing_replay_ready_requirements",
    "resolve_required_profile_requirements",
    "serialize_snapshot_captured_at",
    "source_ref_payload",
    "source_refs_payload",
]
