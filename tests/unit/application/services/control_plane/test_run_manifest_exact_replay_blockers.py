"""Unit tests for exact-replay blocker helper policy."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.control_plane.run_manifest_exact_replay_blockers import (
    append_mode_exact_replay_blockers,
    dependency_lock_exact_replay_blockers,
    profile_exact_replay_blockers,
    requires_dependency_lock_provenance,
    snapshot_exact_replay_blockers,
)
from bioetl.domain.control_plane import ReplayCapability

pytestmark = pytest.mark.unit


def test_profile_exact_replay_blockers_reports_unsupported_profile() -> None:
    profile = SimpleNamespace(strict_exact_replay_supported=False)

    assert profile_exact_replay_blockers(profile) == [
        "family_outside_supported_exact_replay_boundary"
    ]


def test_append_mode_exact_replay_blockers_reports_semantic_outputs() -> None:
    assert append_mode_exact_replay_blockers(["silver.activity"]) == [
        "append_mode_semantic_outputs"
    ]
    assert append_mode_exact_replay_blockers([]) == []


def test_snapshot_exact_replay_blockers_reports_missing_snapshot_envelope() -> None:
    manifest = SimpleNamespace(
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )
    policy_assessment = SimpleNamespace(
        snapshot_envelope=SimpleNamespace(any_input_snapshots=False),
    )

    assert snapshot_exact_replay_blockers(
        manifest=manifest,
        policy_assessment=policy_assessment,
    ) == ["immutable_input_snapshots_missing"]


def test_snapshot_exact_replay_blockers_reports_partial_snapshot_sources() -> None:
    manifest = SimpleNamespace(
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )
    policy_assessment = SimpleNamespace(
        snapshot_envelope=SimpleNamespace(
            any_input_snapshots=True,
            full_snapshot_envelope=False,
            missing_snapshot_source_refs=["chembl.activity"],
        ),
    )

    assert snapshot_exact_replay_blockers(
        manifest=manifest,
        policy_assessment=policy_assessment,
    ) == [
        "partial_input_snapshot_envelope",
        "input_snapshot_missing:chembl.activity",
    ]


def test_dependency_lock_blocker_requires_strict_exact_replay_provenance() -> None:
    manifest = SimpleNamespace(
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        code_provenance=SimpleNamespace(dependency_lock_hash=None),
    )
    profile = SimpleNamespace(strict_exact_replay_supported=True)
    policy_assessment = SimpleNamespace(strict_requirement_requested=True)

    assert (
        requires_dependency_lock_provenance(
            manifest=manifest,
            profile=profile,
            policy_assessment=policy_assessment,
        )
        is True
    )
    assert dependency_lock_exact_replay_blockers(
        manifest=manifest,
        profile=profile,
        policy_assessment=policy_assessment,
    ) == ["dependency_lock_provenance_missing"]
