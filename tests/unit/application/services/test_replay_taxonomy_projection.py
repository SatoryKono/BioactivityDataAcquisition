from __future__ import annotations

import pytest

from bioetl.application.services._observability_workflow_checkpoint_support import (
    _replay_context,
)
from bioetl.application.services.control_plane._run_manifest_identity_graph_builder import (
    RunManifestIdentityGraphAssembler,
)
from bioetl.application.services.control_plane._run_manifest_replay_taxonomy import (
    resolve_replay_resume_rebuild_verdict,
)
from bioetl.application.services.control_plane.replay_bundle_descriptor_service import (
    build_run_replay_bundle_descriptor,
)
from bioetl.application.services.control_plane.run_manifest_inspection_models import (
    RunManifestInspectionResult,
)
from bioetl.domain.control_plane import ReplayCapability
from tests.unit.application.services.run_manifest_test_support import (
    RunManifestOverrides,
    make_run_manifest,
)


def _build_result_with_conflicting_identity_graph() -> RunManifestInspectionResult:
    manifest = make_run_manifest(
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        overrides=RunManifestOverrides(
            launch_context={"exact_replay": True, "limit": 25},
            effective_config_hash="c" * 64,
            effective_config_artifact_id="eca-123",
            dq_contract_compatibility_hash="compat-hash-1",
        ),
    )
    diagnostics = {
        "replay_capability": "exact_replay_supported",
        "requested_exact_replay": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": {"contract": "snapshot_backed_exact_replay"},
        "replay_mode": "exact_replay",
        "continuation_mode": "exact_replay",
        "operator_replay_mode": "Exact Replay",
        "replay_readiness_verdict": "exact_replay_ready",
        "replay_resume_rebuild_verdict": "exact_replay_ready",
        "replay_next_action": (
            "Use exact replay with manifest, execution fingerprint, and input snapshots."
        ),
        "exact_replay_eligible": True,
        "exact_replay_blockers": [],
        "append_mode_semantic_sinks": [],
        "replay_capability_reason": "full_immutable_input_snapshot_envelope_present",
        "source_posture": "immutable_snapshot_envelope",
        "input_snapshot_missing_source_refs": [],
        "resume_contract": {"continuation_mode": "exact_replay"},
        "resume_diagnostics": None,
        "lineage_closure_boundary": {"supported": True},
        "produced_artifact_trace": {"missing_requirements": []},
        "persistence_profile": {"required_profile": "replay_ready"},
    }
    stale_identity_graph = {
        "replay_capability": "resume_only",
        "replay_mode": "resume",
        "continuation_mode": "checkpoint_snapshot_only_resume",
        "operator_replay_mode": "Resume",
        "replay_readiness_verdict": "lifecycle_projection_only",
        "replay_resume_rebuild_verdict": "resume_only",
        "replay_next_action": (
            "Use checkpoint resume only; do not treat this as exact replay."
        ),
        "exact_replay_support_boundary": "stale-boundary",
        "replay_family_contract": {"contract": "stale"},
        "exact_replay_eligible": False,
    }
    return RunManifestInspectionResult(
        manifest=manifest,
        diagnostics=diagnostics,
        identity_graph=stale_identity_graph,
    )


@pytest.mark.unit
def test_identity_graph_replay_section_uses_canonical_diagnostics_projection() -> None:
    result = _build_result_with_conflicting_identity_graph()

    replay_section = (
        RunManifestIdentityGraphAssembler._build_identity_graph_replay_section(  # type: ignore[attr-defined]
            result.manifest,
            result.diagnostics,
        )
    )

    assert replay_section["replay_mode"] == "exact_replay"
    assert replay_section["continuation_mode"] == "exact_replay"
    assert replay_section["operator_replay_mode"] == "Exact Replay"
    assert replay_section["replay_readiness_verdict"] == "exact_replay_ready"
    assert replay_section["replay_resume_rebuild_verdict"] == "exact_replay_ready"
    assert replay_section["exact_replay_eligible"] is True


@pytest.mark.unit
def test_replay_bundle_descriptor_prefers_canonical_diagnostics_projection() -> None:
    result = _build_result_with_conflicting_identity_graph()

    bundle = build_run_replay_bundle_descriptor(result)

    assert bundle.replay_capability == "exact_replay_supported"
    assert bundle.replay_readiness_verdict == "exact_replay_ready"
    assert bundle.exact_replay_support_boundary == "snapshot_backed_source_runs_only"
    assert bundle.exact_replay_eligible is True


@pytest.mark.unit
def test_checkpoint_replay_context_prefers_canonical_diagnostics_projection() -> None:
    result = _build_result_with_conflicting_identity_graph()

    replay_context = _replay_context(result)

    assert replay_context == {
        "replay_capability": "exact_replay_supported",
        "replay_mode": "exact_replay",
        "continuation_mode": "exact_replay",
        "operator_replay_mode": "Exact Replay",
        "replay_readiness_verdict": "exact_replay_ready",
        "replay_resume_rebuild_verdict": "exact_replay_ready",
        "replay_next_action": (
            "Use exact replay with manifest, execution fingerprint, and input snapshots."
        ),
        "exact_replay_eligible": True,
    }


@pytest.mark.unit
def test_replay_resume_rebuild_verdict_requires_exact_replay_capability_for_exact_ready() -> (
    None
):
    verdict = resolve_replay_resume_rebuild_verdict(
        replay_capability="rebuild_only",
        replay_mode="exact_replay",
        continuation_mode="exact_replay",
        replay_readiness_verdict="exact_replay_ready",
    )

    assert verdict == "rebuild_only"


@pytest.mark.unit
def test_replay_resume_rebuild_verdict_keeps_resume_separate_from_exact_replay() -> (
    None
):
    verdict = resolve_replay_resume_rebuild_verdict(
        replay_capability="resume_only",
        replay_mode="resume",
        continuation_mode="checkpoint_snapshot_only_resume",
        replay_readiness_verdict="resume_only_ready",
    )

    assert verdict == "resume_only"
