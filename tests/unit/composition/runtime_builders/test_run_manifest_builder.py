"""Focused unit tests for run-manifest builder identity wiring."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from bioetl.composition.runtime_builders import run_manifest_builder
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
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
        ctx=SimpleNamespace(run_id=uuid4(), pipeline_name="chembl_activity"),
        inputs=SimpleNamespace(),
        provider="chembl",
        entity="activity",
        reproducibility_context=SimpleNamespace(
            required_persistence_profile="replay_ready",
            strict_exact_replay_supported=True,
        ),
        run_type_value="incremental",
        execution_context_value="isolated",
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
        contract_identity=identity,
    )

    request_inputs = captured["request_inputs"]
    assert result is request_inputs
    assert request_inputs.contract_ref == identity.contract_ref
    assert request_inputs.contract_version == identity.contract_version
    assert request_inputs.contract_schema_hash == identity.contract_schema_hash
    assert request_inputs.dq_policy_ref == identity.dq_policy_ref
    assert request_inputs.rule_bundle_version == identity.rule_bundle_version
    assert (
        request_inputs.normalization_profile_ref
        == identity.normalization_profile_ref
    )
    assert (
        request_inputs.normalization_profile_version
        == identity.normalization_profile_version
    )
    assert (
        request_inputs.normalization_profile_hash
        == identity.normalization_profile_hash
    )
    assert request_inputs.reproducibility_context.required_persistence_profile == (
        "replay_ready"
    )


def test_create_control_plane_refs_uses_named_contract_identity_fields() -> None:
    """Manifest refs must stay aligned with named contract identity fields."""
    identity = _make_contract_identity()

    refs = run_manifest_builder._create_control_plane_refs(
        manifest=SimpleNamespace(
            manifest_id="manifest-1",
            execution_fingerprint="fingerprint-1",
        ),
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
        contract_identity=identity,
        required_persistence_profile="replay_ready",
    )

    assert refs.contract_ref == identity.contract_ref
    assert refs.contract_version == identity.contract_version
    assert refs.contract_schema_hash == identity.contract_schema_hash
    assert refs.dq_policy_ref == identity.dq_policy_ref
    assert refs.rule_bundle_version == identity.rule_bundle_version
    assert refs.normalization_profile_ref == identity.normalization_profile_ref
    assert (
        refs.normalization_profile_version
        == identity.normalization_profile_version
    )
    assert refs.normalization_profile_hash == identity.normalization_profile_hash
    assert refs.required_persistence_profile == "replay_ready"


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
        ctx=SimpleNamespace(run_id=uuid4(), pipeline_name="chembl_activity"),
        inputs=SimpleNamespace(),
        provider="chembl",
        entity="activity",
        reproducibility_context=reproducibility_context,
        run_type_value="incremental",
        execution_context_value="isolated",
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
        contract_identity=_make_contract_identity(),
    )

    assert result.reproducibility_context is reproducibility_context
    assert captured["reproducibility_context"] is reproducibility_context


def test_resolve_manifest_context_uses_supplied_publication_context(
    monkeypatch,
) -> None:
    """Context resolution must reuse supplied publication inputs when provided."""
    monkeypatch.setattr(
        run_manifest_builder,
        "resolve_manifest_reproducibility_context",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("reproducibility resolver should not run")
        ),
    )
    monkeypatch.setattr(
        run_manifest_builder,
        "_resolve_manifest_contract_identity",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("contract identity resolver should not run")
        ),
    )

    reproducibility_context = SimpleNamespace(
        required_persistence_profile="forensic_grade",
        strict_exact_replay_supported=False,
    )
    contract_identity = _make_contract_identity()
    result = run_manifest_builder._resolve_manifest_context(
        ctx=SimpleNamespace(
            run_id=uuid4(),
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
