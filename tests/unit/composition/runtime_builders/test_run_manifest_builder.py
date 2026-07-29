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
"""Focused unit tests for run-manifest builder identity wiring."""

from __future__ import annotations

import pytest
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

from types import SimpleNamespace

from bioetl.composition.runtime_builders import run_manifest_builder
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestProvenanceBundle,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
)
from bioetl.domain.models.metadata import InputSnapshotRef
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint


pytestmark = pytest.mark.unit


def _make_provenance_bundle() -> RunManifestProvenanceBundle:
    return RunManifestProvenanceBundle(
        effective_config_artifact_id="artifact-1",
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        source_fingerprint="source-fingerprint-1",
        dq_contract_compatibility_hash="dq-hash",
    )


def _make_contract_identity() -> RunManifestContractIdentity:
    return RunManifestContractIdentity(
        contract_ref="chembl.activity",
        contract_version="1.2.3",
        contract_schema_hash="schema-deadbeef",
        dq_policy_ref="chembl.activity.policy",
        rule_bundle_version="2026.04",
        normalization_profile_ref="chembl.activity.norm",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="f" * 64,
    )


def test_build_manifest_create_request_uses_named_contract_identity_fields(
    monkeypatch,
) -> None:
    """Manifest request inputs must be populated from named identity fields."""
    captured: dict[str, object] = {}

    def _fake_build_manifest_create_request(request_inputs):
        captured["request_inputs"] = request_inputs
        return request_inputs

    monkeypatch.setattr(
        run_manifest_builder,
        "build_manifest_create_request",
        _fake_build_manifest_create_request,
    )

    identity = _make_contract_identity()
    result = run_manifest_builder._build_manifest_create_request(
        ctx=SimpleNamespace(
            run_id=deterministic_uuid_from_callsite("test_run_manifest_builder"),
            pipeline_name="chembl_activity",
        ),
        inputs=SimpleNamespace(),
        provider="chembl",
        entity="activity",
        reproducibility_context=SimpleNamespace(
            required_persistence_profile="replay_ready",
            strict_exact_replay_supported=True,
        ),
        run_type_value="incremental",
        execution_context_value="isolated",
        provenance=_make_provenance_bundle(),
        contract_identity=identity,
    )

    request_inputs = captured["request_inputs"]
    assert result is request_inputs
    assert request_inputs.contract_identity is identity
    assert request_inputs.contract_identity.contract_ref == identity.contract_ref
    assert (
        request_inputs.contract_identity.contract_version == identity.contract_version
    )
    assert (
        request_inputs.contract_identity.contract_schema_hash
        == identity.contract_schema_hash
    )
    assert request_inputs.contract_identity.dq_policy_ref == identity.dq_policy_ref
    assert (
        request_inputs.contract_identity.rule_bundle_version
        == identity.rule_bundle_version
    )
    assert (
        request_inputs.contract_identity.normalization_profile_ref
        == identity.normalization_profile_ref
    )
    assert (
        request_inputs.contract_identity.normalization_profile_version
        == identity.normalization_profile_version
    )
    assert (
        request_inputs.contract_identity.normalization_profile_hash
        == identity.normalization_profile_hash
    )
    assert request_inputs.reproducibility_context.required_persistence_profile == (
        "replay_ready"
    )
    assert request_inputs.source_fingerprint == "source-fingerprint-1"


def test_create_control_plane_refs_uses_named_contract_identity_fields() -> None:
    """Manifest refs must stay aligned with named contract identity fields."""
    identity = _make_contract_identity()
    snapshot = InputSnapshotRef(
        snapshot_id="snapshot-1",
        content_hash="sha256:snapshot-1",
        immutable_uri="file:///immutable/snapshot-1.json",
    )

    refs = run_manifest_builder._create_control_plane_refs(
        manifest=SimpleNamespace(
            manifest_id="manifest-1",
            execution_fingerprint="fingerprint-1",
            replay_of_run_id="run-parent-1",
            replay_of_manifest_id="manifest-parent-1",
            source_refs=[SimpleNamespace(input_snapshots=[snapshot])],
        ),
        provenance=_make_provenance_bundle(),
        contract_identity=identity,
        required_persistence_profile="replay_ready",
    )

    assert refs.contract_ref == identity.contract_ref
    assert refs.contract_version == identity.contract_version
    assert refs.contract_schema_hash == identity.contract_schema_hash
    assert refs.dq_policy_ref == identity.dq_policy_ref
    assert refs.rule_bundle_version == identity.rule_bundle_version
    assert refs.normalization_profile_ref == identity.normalization_profile_ref
    assert refs.normalization_profile_version == identity.normalization_profile_version
    assert refs.normalization_profile_hash == identity.normalization_profile_hash
    assert refs.required_persistence_profile == "replay_ready"
    assert refs.source_fingerprint == "source-fingerprint-1"
    assert refs.replay_of_run_id == "run-parent-1"
    assert refs.replay_of_manifest_id == "manifest-parent-1"
    assert refs.input_snapshot_fingerprint == (
        compute_input_snapshot_identity_fingerprint([snapshot])
    )


def test_build_manifest_create_request_passes_through_reproducibility_context(
    monkeypatch,
) -> None:
    """Builder must reuse the already-resolved reproducibility context."""
    captured: dict[str, object] = {}

    def _fake_build_manifest_create_request(request_inputs):
        captured["reproducibility_context"] = request_inputs.reproducibility_context
        return request_inputs

    monkeypatch.setattr(
        run_manifest_builder,
        "build_manifest_create_request",
        _fake_build_manifest_create_request,
    )

    reproducibility_context = SimpleNamespace(
        required_persistence_profile="forensic_grade",
        strict_exact_replay_supported=False,
    )
    result = run_manifest_builder._build_manifest_create_request(
        ctx=SimpleNamespace(
            run_id=deterministic_uuid_from_callsite("test_run_manifest_builder"),
            pipeline_name="chembl_activity",
        ),
        inputs=SimpleNamespace(),
        provider="chembl",
        entity="activity",
        reproducibility_context=reproducibility_context,
        run_type_value="incremental",
        execution_context_value="isolated",
        provenance=_make_provenance_bundle(),
        contract_identity=_make_contract_identity(),
    )

    assert result.reproducibility_context is reproducibility_context
    assert captured["reproducibility_context"] is reproducibility_context


def test_resolve_manifest_publication_context_uses_supplied_publication_context(
    monkeypatch,
) -> None:
    """Context resolution must reuse supplied publication inputs when provided."""
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._manifest_publication_context_support.resolve_manifest_reproducibility_context",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("reproducibility resolver should not run")
        ),
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._manifest_publication_context_support.resolve_contract_identity",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("contract identity resolver should not run")
        ),
    )

    reproducibility_context = SimpleNamespace(
        required_persistence_profile="forensic_grade",
        strict_exact_replay_supported=False,
    )
    contract_identity = _make_contract_identity()
    result = run_manifest_builder.resolve_manifest_publication_context(
        ctx=SimpleNamespace(
            run_id=deterministic_uuid_from_callsite("test_run_manifest_builder"),
            pipeline_name="custom_runtime_name",
            exact_replay=False,
        ),
        inputs=SimpleNamespace(
            yaml_config=SimpleNamespace(provider="chembl", entity_type="activity"),
        ),
        reproducibility_context=reproducibility_context,
        contract_identity=contract_identity,
    )

    assert result.provider == "chembl"
    assert result.entity == "activity"
    assert result.reproducibility_context is reproducibility_context
    assert result.contract_identity is contract_identity
