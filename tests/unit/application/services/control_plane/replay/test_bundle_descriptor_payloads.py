# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestInspectionResult,
)
from bioetl.application.services.control_plane.replay._bundle_descriptor_payloads import (
    ReplayClaimSnapshot,
    build_replay_bundle,
    dict_or_empty,
    optional_string,
    resolve_identity_graph,
    resolve_replay_claims,
)
from bioetl.domain.control_plane import ReplayCapability
from tests.unit.application.services.run_manifest_test_support import (
    RunManifestOverrides,
    make_run_manifest,
)


@pytest.mark.unit
def test_identity_graph_prefers_resolved_result_over_diagnostic_fallback() -> None:
    manifest = make_run_manifest()
    result = RunManifestInspectionResult(
        manifest=manifest,
        diagnostics={"identity_graph": {"source": "diagnostics"}},
        identity_graph={"source": "resolved"},
    )

    assert resolve_identity_graph(result, result.diagnostics) == {"source": "resolved"}


@pytest.mark.unit
def test_identity_graph_uses_diagnostic_mapping_when_result_has_no_graph() -> None:
    manifest = make_run_manifest()
    result = RunManifestInspectionResult(
        manifest=manifest,
        diagnostics={"identity_graph": {"source": "diagnostics"}},
    )

    assert resolve_identity_graph(result, result.diagnostics) == {
        "source": "diagnostics"
    }


@pytest.mark.unit
def test_replay_claims_merge_diagnostics_identity_graph_and_manifest_defaults() -> None:
    claims = resolve_replay_claims(
        diagnostics={
            "replay_readiness_verdict": "exact_replay_ready",
            "exact_replay_eligible": True,
            "required_persistence_profile": "diagnostic-profile",
        },
        identity_graph={
            "replay_family_contract": {"contract": "snapshot_backed_exact_replay"},
            "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        },
        persistence_profile={},
        replay_capability_default=ReplayCapability.EXACT_REPLAY_SUPPORTED.value,
        requested_exact_replay_default=True,
    )

    assert claims.replay_capability == "exact_replay_supported"
    assert claims.replay_readiness_verdict == "exact_replay_ready"
    assert claims.exact_replay_eligible is True
    assert claims.exact_replay_support_boundary == "snapshot_backed_source_runs_only"
    assert claims.replay_family_contract == {"contract": "snapshot_backed_exact_replay"}
    assert claims.required_profile == "diagnostic-profile"


@pytest.mark.unit
def test_replay_claims_prefer_persistence_profile_over_diagnostic_profile() -> None:
    claims = resolve_replay_claims(
        diagnostics={"required_persistence_profile": "diagnostic-profile"},
        identity_graph={},
        persistence_profile={"required_profile": "profile-from-persistence"},
        replay_capability_default=ReplayCapability.REBUILD_ONLY.value,
        requested_exact_replay_default=False,
    )

    assert claims.required_profile == "profile-from-persistence"


@pytest.mark.unit
def test_replay_bundle_payload_is_json_safe_and_filters_malformed_collections() -> None:
    manifest = make_run_manifest(
        manifest_id="manifest-replay-bundle",
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        overrides=RunManifestOverrides(
            launch_context={"exact_replay": True, "limit": 10},
            dependency_lock_hash=None,
            effective_config_artifact_id="eca-123",
        ),
    )
    result = RunManifestInspectionResult(
        manifest=manifest,
        ledger_entries=(object(), object()),  # type: ignore[arg-type]
    )
    diagnostics = {
        "event_family_counts": {"artifact": 2},
        "event_type_counts": "not-a-mapping",
        "replay_parentage": {"parent_run_id": "run-parent"},
        "input_snapshots": [{"snapshot_id": "snapshot-1"}, "bad"],
        "artifact_refs": [{"artifact_id": "silver:1"}, 42],
        "lineage_fragment_ids": ["fragment-1", 2],
        "historical_live_run_upgrade_state": "not_supported",
        "broader_historical_exact_replay_state": "bounded",
    }
    claims = ReplayClaimSnapshot(
        replay_capability="exact_replay_supported",
        replay_readiness_verdict="exact_replay_ready",
        exact_replay_support_boundary="snapshot_backed_source_runs_only",
        replay_family_contract={"contract": "snapshot_backed_exact_replay"},
        exact_replay_eligible=True,
        required_profile="replay_ready",
    )

    bundle = build_replay_bundle(
        result,
        diagnostics,
        identity_graph={"manifest_id": manifest.manifest_id},
        claims=claims,
        produced_artifact_trace={"missing_requirements": []},
    )

    assert bundle["control_plane"] == {
        "manifest_id": "manifest-replay-bundle",
        "run_id": str(manifest.run_id),
        "schema_version": "1.0",
        "execution_fingerprint": "fingerprint-manifest-replay-bundle",
        "ledger_event_count": 2,
        "event_family_counts": {"artifact": 2},
        "event_type_counts": {},
    }
    assert bundle["code_provenance"] == {
        "pipeline_version": "1.0.0",
        "git_commit": "abc1234",
        "config_hash": "a" * 64,
        "resolved_config_hash": "b" * 64,
        "effective_config_hash": "c" * 64,
        "effective_config_artifact_id": "eca-123",
        "contract_ref": "chembl.activity",
        "contract_version": "1.2.0",
        "dq_policy_ref": "chembl_activity.gold",
        "rule_bundle_version": "2026.03",
        "dq_contract_compatibility_hash": "compat-hash-1",
    }
    assert bundle["input_snapshots"] == [{"snapshot_id": "snapshot-1"}]
    assert bundle["artifact_refs"] == [{"artifact_id": "silver:1"}]
    assert bundle["lineage_fragment_ids"] == ["fragment-1", "2"]
    assert bundle["replay_claims"] == {
        "replay_capability": "exact_replay_supported",
        "replay_readiness_verdict": "exact_replay_ready",
        "exact_replay_eligible": True,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "replay_family_contract": {"contract": "snapshot_backed_exact_replay"},
        "historical_live_run_upgrade_state": "not_supported",
        "broader_historical_exact_replay_state": "bounded",
    }
    assert bundle["required_persistence_profile"] == "replay_ready"


@pytest.mark.unit
def test_payload_scalar_helpers_are_type_stable() -> None:
    assert dict_or_empty({"a": 1}) == {"a": 1}
    assert dict_or_empty([("not", "a mapping")]) == {}
    assert optional_string(None) is None
    assert optional_string(42) == "42"
