"""Tests for centralized reproducibility policy evaluation."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane import (
    ReplayCapability,
    ReplayReadinessVerdict,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
    is_degraded_observable_profile_requested,
    resolve_effective_required_persistence_profile,
    resolve_replay_capability,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    build_replay_family_contract,
    published_reproducibility_family_inventory,
)


pytestmark = pytest.mark.unit

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
    assert (
        assessment.replay_readiness_verdict
        == ReplayReadinessVerdict.EXACT_REPLAY_BLOCKED
    )


def test_replay_readiness_verdicts_keep_resume_rebuild_and_incremental_distinct() -> (
    None
):
    resume_assessment = assess_reproducibility_policy(
        source_refs=(_source_ref(),),
        required_persistence_profile="degraded_observable",
        strict_exact_replay_supported=True,
        resume_requested=True,
        run_type="incremental",
    )
    incremental_assessment = assess_reproducibility_policy(
        source_refs=(_source_ref(),),
        required_persistence_profile="degraded_observable",
        strict_exact_replay_supported=True,
        run_type="incremental",
    )
    rebuild_assessment = assess_reproducibility_policy(
        source_refs=(_source_ref(),),
        required_persistence_profile="degraded_observable",
        strict_exact_replay_supported=True,
        run_type="full",
    )

    assert (
        resume_assessment.replay_readiness_verdict
        == ReplayReadinessVerdict.RESUME_COMPATIBLE
    )
    assert (
        incremental_assessment.replay_readiness_verdict
        == ReplayReadinessVerdict.INCREMENTAL_NEW_RUN
    )
    assert (
        rebuild_assessment.replay_readiness_verdict
        == ReplayReadinessVerdict.REBUILD_ONLY
    )


def test_unsupported_family_verdict_is_debug_only_when_strict_replay_not_claimed() -> (
    None
):
    assessment = assess_reproducibility_policy(
        source_refs=(_source_ref(),),
        required_persistence_profile="degraded_observable",
        strict_exact_replay_supported=False,
        run_type="incremental",
    )

    assert assessment.replay_readiness_verdict == ReplayReadinessVerdict.DEBUG_ONLY


def test_supported_family_contract_publishes_replay_ready_default() -> None:
    contract = build_replay_family_contract(
        provider="chembl",
        entity="activity",
        contract_ref="chembl.activity",
        execution_context="source",
    )

    assert contract["strict_exact_replay_supported"] is True
    assert contract["default_required_persistence_profile"] == "replay_ready"
    assert (
        contract["strict_replay_runtime_verdict"]
        == "allowed_with_snapshot_backed_source_refs"
    )


def test_published_source_family_contract_publishes_strict_profile_support() -> None:
    contract = build_replay_family_contract(
        provider="openalex",
        entity="publication",
        contract_ref="openalex.publication",
        execution_context="source",
    )

    assert contract["strict_exact_replay_supported"] is True
    assert contract["contract"] == "snapshot_backed_exact_replay"
    assert contract["default_required_persistence_profile"] == "replay_ready"
    assert (
        contract["strict_replay_runtime_verdict"]
        == "allowed_with_snapshot_backed_source_refs"
    )


def test_published_reproducibility_inventory_declares_runtime_verdicts() -> None:
    inventory = published_reproducibility_family_inventory()
    valid_verdicts = {
        "allowed_with_snapshot_backed_source_refs",
        "requires_full_composite_snapshot_envelope",
        "blocked_outside_supported_boundary",
    }

    assert inventory
    assert {
        str(item["strict_replay_runtime_verdict"]) for item in inventory
    } <= valid_verdicts
    assert all("strict_replay_runtime_verdict" in item for item in inventory)
    assert any(
        str(item["family"]) == "composite.publication"
        and item["lineage_closure_supported"] is True
        for item in inventory
    )


def test_exact_replay_launch_inherits_supported_family_default_profile() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            exact_replay_requested=True,
        )
        == "replay_ready"
    )


def test_public_profile_resolver_accepts_explicit_strict_profile_set() -> None:
    """Public wrapper must accept the low-level strict-profile keyword."""
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="custom_strict",
            strict_persistence_profiles=frozenset({"custom_strict"}),
            exact_replay_requested=True,
        )
        == "custom_strict"
    )


def test_critical_runtime_inherits_supported_family_default_profile() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            critical_runtime=True,
        )
        == "replay_ready"
    )


def test_supported_family_launch_promotes_degraded_override_to_strict_floor() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            exact_replay_requested=False,
        )
        == "replay_ready"
    )


def test_explicit_local_opt_down_preserves_degraded_profile_for_supported_family() -> (
    None
):
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            exact_replay_requested=False,
            allow_degraded_opt_down=True,
        )
        == "degraded_observable"
    )


def test_exact_replay_ignores_local_degraded_opt_down() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="replay_ready",
            exact_replay_requested=True,
            allow_degraded_opt_down=True,
        )
        == "replay_ready"
    )


def test_unsupported_family_launch_preserves_degraded_override() -> None:
    assert (
        resolve_effective_required_persistence_profile(
            configured_required_profile="degraded_observable",
            family_default_profile="degraded_observable",
            exact_replay_requested=False,
        )
        == "degraded_observable"
    )


def test_degraded_observable_profile_request_is_domain_policy() -> None:
    """Composition should consume this pure profile decision from domain."""
    assert is_degraded_observable_profile_requested("degraded-observable") is True
    assert is_degraded_observable_profile_requested("replay_ready") is False
    assert is_degraded_observable_profile_requested(None) is False
