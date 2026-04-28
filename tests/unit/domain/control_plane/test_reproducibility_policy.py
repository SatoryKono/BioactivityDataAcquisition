"""Tests for centralized reproducibility policy evaluation."""

from __future__ import annotations

from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
    legacy_config_hash_from_resolved_config_hash,
    resolve_effective_required_persistence_profile,
    resolve_replay_capability,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    build_replay_family_contract,
)


def _source_ref(
    *,
    snapshots: tuple[RunInputSnapshotRef, ...] = (),
) -> RunSourceRef:
    return RunSourceRef(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        input_snapshots=snapshots,
    )


def test_source_run_exact_replay_requires_at_least_one_snapshot_ref() -> None:
    snapshot = RunInputSnapshotRef(snapshot_id="snapshot-1", content_hash="hash-1")

    assert (
        resolve_replay_capability(
            source_refs=(_source_ref(snapshots=(snapshot,)),),
            resume_requested=False,
        )
        == ReplayCapability.EXACT_REPLAY_SUPPORTED
    )
    assert (
        resolve_replay_capability(
            source_refs=(_source_ref(),),
            resume_requested=True,
        )
        == ReplayCapability.RESUME_ONLY
    )


def test_full_snapshot_envelope_requires_every_source_to_be_snapshot_backed() -> None:
    snapshot = RunInputSnapshotRef(snapshot_id="snapshot-1", content_hash="hash-1")

    assert (
        resolve_replay_capability(
            source_refs=(_source_ref(snapshots=(snapshot,)), _source_ref()),
            resume_requested=False,
            require_full_snapshot_envelope=True,
        )
        == ReplayCapability.REBUILD_ONLY
    )


def test_replay_ready_assessment_reports_snapshot_gate_gaps() -> None:
    assessment = assess_reproducibility_policy(
        source_refs=(_source_ref(),),
        required_persistence_profile="replay_ready",
        strict_exact_replay_supported=True,
    )

    assert assessment.required_persistence_profile == "replay_ready"
    assert assessment.required_profile_satisfied is False
    assert assessment.blocking_gaps == (
        "immutable_input_snapshots",
        "exact_replay_capability",
    )


def test_supported_family_contract_publishes_replay_ready_default() -> None:
    contract = build_replay_family_contract(
        provider="chembl",
        entity="activity",
        contract_ref="chembl.activity",
        execution_context="source",
    )

    assert contract["strict_exact_replay_supported"] is True
    assert contract["default_required_persistence_profile"] == "replay_ready"


def test_exact_replay_launch_inherits_supported_family_default_profile() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            exact_replay_requested=True,
        )
        == "replay_ready"
    )


def test_non_exact_launch_preserves_configured_default_profile() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            exact_replay_requested=False,
        )
        == "degraded_observable"
    )


def test_legacy_config_hash_alias_is_resolved_config_hash() -> None:
    assert legacy_config_hash_from_resolved_config_hash("resolved-hash") == (
        "resolved-hash"
    )
