"""Unit tests for runtime control-plane helpers."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from bioetl.composition.runtime_builders import control_plane
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
)


def test_create_run_manifest_with_effective_config_uses_yaml_provider_entity(
    monkeypatch,
) -> None:
    """Control-plane artifact inputs must use canonical provider/entity resolution."""
    captured: dict[str, object] = {}
    reproducibility_context = SimpleNamespace(
        required_persistence_profile="degraded_observable",
        strict_exact_replay_supported=False,
    )
    contract_identity = RunManifestContractIdentity(
        contract_ref="chembl.activity",
        contract_version="1.2.3",
        contract_schema_hash="schema-deadbeef",
        dq_policy_ref="chembl.activity.policy",
        rule_bundle_version="2026.04",
        normalization_profile_ref="chembl.activity.norm",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="f" * 64,
    )

    def _fake_create_and_persist_effective_config_artifact(**kwargs: object):
        captured["provider"] = kwargs["provider"]
        captured["entity"] = kwargs["entity"]
        return (
            "artifact-1",
            "resolved-hash",
            "effective-hash",
            "source-hash",
            "dq-hash",
        )

    def _fake_create_run_manifest(**kwargs: object):
        captured["manifest_provider"] = kwargs["inputs"].yaml_config.provider
        captured["manifest_entity"] = kwargs["inputs"].yaml_config.entity_type
        return ("control-plane-refs", None)

    monkeypatch.setattr(
        control_plane,
        "create_and_persist_effective_config_artifact",
        _fake_create_and_persist_effective_config_artifact,
    )
    monkeypatch.setattr(
        control_plane,
        "resolve_manifest_reproducibility_context",
        lambda **_: reproducibility_context,
    )
    monkeypatch.setattr(
        control_plane._manifest_support,
        "resolve_contract_identity",
        lambda **_: contract_identity,
    )
    monkeypatch.setattr(
        control_plane,
        "create_run_manifest",
        _fake_create_run_manifest,
    )

    ctx = SimpleNamespace(
        pipeline_name="custom_runtime_name",
        run_id=uuid4(),
    )
    inputs = SimpleNamespace(
        yaml_config=SimpleNamespace(provider="chembl", entity_type="activity"),
    )

    result = control_plane.create_run_manifest_with_effective_config(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=False,
    )

    assert result == ("control-plane-refs", None)
    assert captured["provider"] == "chembl"
    assert captured["entity"] == "activity"
    assert captured["manifest_provider"] == "chembl"
    assert captured["manifest_entity"] == "activity"


def test_create_run_manifest_with_effective_config_reuses_publication_context(
    monkeypatch,
) -> None:
    """Control-plane orchestration must share one resolved publication context."""
    captured: dict[str, object] = {}
    reproducibility_context = SimpleNamespace(
        required_persistence_profile="forensic_grade",
        strict_exact_replay_supported=False,
    )
    contract_identity = RunManifestContractIdentity(
        contract_ref="chembl.activity",
        contract_version="1.2.3",
        contract_schema_hash="schema-deadbeef",
        dq_policy_ref="chembl.activity.policy",
        rule_bundle_version="2026.04",
        normalization_profile_ref="chembl.activity.norm",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="f" * 64,
    )

    monkeypatch.setattr(
        control_plane,
        "resolve_manifest_reproducibility_context",
        lambda **_: reproducibility_context,
    )
    monkeypatch.setattr(
        control_plane._manifest_support,
        "resolve_contract_identity",
        lambda **_: contract_identity,
    )

    def _fake_create_and_persist_effective_config_artifact(**kwargs: object):
        captured["effective_context"] = kwargs["reproducibility_context"]
        captured["effective_identity"] = kwargs["contract_identity"]
        return (
            "artifact-1",
            "resolved-hash",
            "effective-hash",
            "source-hash",
            "dq-hash",
        )

    def _fake_create_run_manifest(**kwargs: object):
        captured["manifest_context"] = kwargs["reproducibility_context"]
        captured["manifest_identity"] = kwargs["contract_identity"]
        return ("control-plane-refs", None)

    monkeypatch.setattr(
        control_plane,
        "create_and_persist_effective_config_artifact",
        _fake_create_and_persist_effective_config_artifact,
    )
    monkeypatch.setattr(
        control_plane,
        "create_run_manifest",
        _fake_create_run_manifest,
    )

    ctx = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        exact_replay=False,
    )
    inputs = SimpleNamespace(
        yaml_config=SimpleNamespace(provider="chembl", entity_type="activity"),
    )

    result = control_plane.create_run_manifest_with_effective_config(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=False,
    )

    assert result == ("control-plane-refs", None)
    assert captured["effective_context"] is reproducibility_context
    assert captured["manifest_context"] is reproducibility_context
    assert captured["effective_identity"] is contract_identity
    assert captured["manifest_identity"] is contract_identity


def test_attach_manifest_id_accepts_control_plane_refs_object() -> None:
    """Context attachment should accept one refs object without manual unpacking."""
    ctx = SimpleNamespace(manifest_id=None)
    control_plane_refs = control_plane._ManifestControlPlaneRefs(
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        config_hash="a" * 64,
        resolved_config_hash="a" * 64,
        effective_config_hash="b" * 64,
        source_fingerprint="c" * 64,
        dq_contract_compatibility_hash="d" * 64,
        effective_config_artifact_id="artifact-1",
        contract_ref="chembl.activity",
        contract_version="1.2.3",
        contract_schema_hash="deadbeef",
        dq_policy_ref="chembl.activity.policy",
        rule_bundle_version="2026.04",
        normalization_profile_ref="chembl.activity.norm",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="d" * 64,
        required_persistence_profile="replay_ready",
    )

    updated = control_plane.attach_manifest_id(
        ctx,
        control_plane_refs=control_plane_refs,
    )

    assert updated is ctx
    assert ctx.manifest_id == "manifest-1"
    assert ctx.execution_fingerprint == "fingerprint-1"
    assert ctx.contract_ref == "chembl.activity"
    assert ctx.normalization_profile_ref == "chembl.activity.norm"
    assert ctx.source_fingerprint == "c" * 64


def test_attach_manifest_id_accepts_legacy_refs_without_source_fingerprint() -> None:
    """Legacy mock-like refs may omit newly added optional provenance fields."""
    ctx = SimpleNamespace(manifest_id=None)
    control_plane_refs = SimpleNamespace(
        manifest_id="manifest-legacy",
        execution_fingerprint="fingerprint-legacy",
        config_hash="a" * 64,
        resolved_config_hash="b" * 64,
        effective_config_hash="c" * 64,
        dq_contract_compatibility_hash="d" * 64,
        effective_config_artifact_id="artifact-legacy",
        contract_ref="chembl.activity",
        contract_version="1.2.3",
        contract_schema_hash="deadbeef",
        dq_policy_ref="chembl.activity.policy",
        rule_bundle_version="2026.04",
        normalization_profile_ref=None,
        normalization_profile_version=None,
        normalization_profile_hash=None,
    )

    updated = control_plane.attach_manifest_id(
        ctx,
        control_plane_refs=control_plane_refs,
    )

    assert updated is ctx
    assert ctx.manifest_id == "manifest-legacy"
    assert ctx.execution_fingerprint == "fingerprint-legacy"
    assert ctx.contract_ref == "chembl.activity"
    assert getattr(ctx, "source_fingerprint", None) is None
