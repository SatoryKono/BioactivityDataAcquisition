"""Unit tests for run-manifest support helpers around replay boundaries."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, call
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
)
from bioetl.composition.runtime_builders import (
    _run_manifest_creation_support_helpers as creation_helper_module,
)
from bioetl.composition.runtime_builders import (
    _run_manifest_replay_support as replay_helper_module,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support import (
    RunManifestCreateRequestInputs,
    build_manifest_create_request,
    emit_replay_reconstructability_metric,
)
from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
    build_planned_artifacts,
    build_launch_context_snapshot,
    build_run_source_refs,
    resolve_contract_identity,
    resolve_replay_capability,
    validate_reproducible_sink_modes,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_code_revision_for_manifest,
    validate_required_runtime_persistence_profile,
)
from bioetl.composition.services.versioning import CodeRevisionProvenance
from bioetl.domain.control_plane import ReplayCapability, RunInputSnapshotRef
from bioetl.domain.context import PipelineRunContext
from bioetl.infrastructure.config._base import Settings


def _make_settings(**overrides: object) -> Settings:
    return cast(Settings, SimpleNamespace(bronze_path=Path("/unused"), **overrides))


def _make_run_context(**overrides: object) -> PipelineRunContext:
    defaults = {
        "pipeline_name": "chembl_activity",
        "resume": False,
        "dry_run": False,
        "limit": None,
        "query": None,
        "start_offset": None,
        "log_level": "INFO",
        "ignore_yaml_filter": False,
        "skip_gold": False,
        "exact_replay": False,
        "vacuum": None,
        "input_filter": None,
        "cached_bronze": None,
    }
    defaults.update(overrides)
    return cast(PipelineRunContext, SimpleNamespace(**defaults))


def _make_manifest_request(
    *,
    exact_replay: bool = False,
    required_persistence_profile: str = "degraded_observable",
    replay_capability: ReplayCapability = ReplayCapability.REBUILD_ONLY,
) -> RunManifestCreateSpec:
    return RunManifestCreateSpec(
        run_id=deterministic_run_uuid_from_callsite("test_run_manifest_support"),
        run_type="incremental",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={
            "exact_replay": exact_replay,
            "required_persistence_profile": required_persistence_profile,
        },
        runtime_config={},
        resolved_config={},
        replay_capability=replay_capability,
    )


@pytest.mark.unit
def test_emit_replay_reconstructability_metric_is_owned_by_creation_support() -> None:
    assert emit_replay_reconstructability_metric.__module__.endswith(
        "_run_manifest_creation_support"
    )


@pytest.mark.unit
def test_build_manifest_create_request_uses_supplied_reproducibility_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_build_manifest_source_refs(**kwargs: object):
        captured["required_persistence_profile"] = kwargs[
            "required_persistence_profile"
        ]
        return ("source-ref",)

    def _fake_build_manifest_launch_context(
        *, reproducibility_context: object, **_: object
    ):
        captured["launch_context_context"] = reproducibility_context
        return {
            "configured_required_persistence_profile": "degraded_observable",
            "required_persistence_profile": "forensic_grade",
            "exact_replay": False,
        }

    def _fake_build_replay_assessment(**_: object):
        return SimpleNamespace(
            replay_readiness_verdict=SimpleNamespace(value="rebuild_only"),
            blocking_gaps=(),
        )

    def _fake_assemble_manifest_create_spec(**kwargs: object):
        captured["assemble_request_inputs"] = kwargs["request_inputs"]
        return RunManifestCreateSpec(
            run_id=deterministic_run_uuid_from_callsite("test_run_manifest_support"),
            run_type="incremental",
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context=kwargs["launch_context"],
            runtime_config={},
            resolved_config={},
            replay_capability=ReplayCapability.REBUILD_ONLY,
        )

    def _fake_validate_required_runtime_persistence_profile(**kwargs: object):
        captured["validated_required_profile"] = kwargs["required_persistence_profile"]

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._build_manifest_source_refs",
        _fake_build_manifest_source_refs,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._build_manifest_launch_context",
        _fake_build_manifest_launch_context,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._build_replay_assessment",
        _fake_build_replay_assessment,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._assemble_manifest_create_spec",
        _fake_assemble_manifest_create_spec,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support.validate_required_runtime_persistence_profile",
        _fake_validate_required_runtime_persistence_profile,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support.resolve_code_revision_for_manifest",
        lambda **_: "rev-1",
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._manifest_support.resolve_replay_parentage",
        lambda **_: (None, None),
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_creation_support._manifest_support.resolve_replay_capability",
        lambda **_: ReplayCapability.REBUILD_ONLY,
    )

    reproducibility_context = SimpleNamespace(
        configured_required_persistence_profile="degraded_observable",
        required_persistence_profile="forensic_grade",
        strict_exact_replay_supported=False,
        family="strict",
        replay_family_contract="strict",
        strict_replay_runtime_verdict="rebuild_only",
        support_scope="supported",
        reason="fixture",
    )
    request = build_manifest_create_request(
        RunManifestCreateRequestInputs(
            ctx=_make_run_context(),
            inputs=SimpleNamespace(
                cached_bronze=None,
                runtime_config=SimpleNamespace(),
                settings=SimpleNamespace(test_mode=False, debug=False),
            ),
            provider="chembl",
            entity="activity",
            reproducibility_context=reproducibility_context,
            run_type_value="incremental",
            execution_context_value="isolated",
            config_hash="resolved-hash",
            resolved_config_hash="resolved-hash",
            effective_config_hash="effective-hash",
            source_fingerprint="source-fingerprint-1",
            contract_identity=RunManifestContractIdentity(
                contract_ref="chembl.activity",
                contract_version="1.2.3",
                contract_schema_hash="schema-deadbeef",
                dq_policy_ref="chembl.activity.policy",
                rule_bundle_version="2026.04",
                normalization_profile_ref="chembl.activity.norm",
                normalization_profile_version="1.0.0",
                normalization_profile_hash="f" * 64,
            ),
            dq_contract_compatibility_hash="dq-hash",
            effective_config_artifact_id="artifact-1",
        )
    )

    assert request.launch_context["required_persistence_profile"] == "forensic_grade"
    assert (
        request.launch_context["configured_required_persistence_profile"]
        == "degraded_observable"
    )
    assert captured["required_persistence_profile"] == "forensic_grade"
    assert captured["validated_required_profile"] == "forensic_grade"
    assert captured["launch_context_context"] is reproducibility_context
    assert captured["assemble_request_inputs"].source_fingerprint == (
        "source-fingerprint-1"
    )


@pytest.mark.unit
def test_creation_helper_build_manifest_source_refs_forwards_runtime_profile() -> None:
    manifest_support = MagicMock()
    manifest_support.build_run_source_refs.return_value = ("source-ref",)
    ctx = _make_run_context()
    inputs = SimpleNamespace(
        cached_bronze="cached-bronze",
        settings=SimpleNamespace(test_mode=False, debug=False),
    )

    result = creation_helper_module.build_manifest_source_refs(
        manifest_support=manifest_support,
        ctx=ctx,
        inputs=inputs,
        provider="chembl",
        entity="activity",
        required_persistence_profile="replay_ready",
    )

    assert result == ("source-ref",)
    manifest_support.build_run_source_refs.assert_called_once_with(
        ctx=ctx,
        cached_bronze="cached-bronze",
        settings=inputs.settings,
        provider="chembl",
        entity="activity",
        required_persistence_profile="replay_ready",
    )


@pytest.mark.unit
def test_creation_helper_assemble_manifest_create_spec_populates_contract_and_debug_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        creation_helper_module,
        "current_silver_filter_compatibility_mode",
        lambda: "compat-mode-test",
    )
    ctx = cast(
        PipelineRunContext,
        SimpleNamespace(
            run_id=deterministic_run_uuid_from_callsite("manifest_create_spec"),
            run_type="incremental",
            pipeline_name="chembl_activity",
            workflow_id="wf-123",
            workflow_run_id="workflow-run-123",
            workflow_name="chembl_baseline",
            workflow_step_id="run_chembl_activity",
            debug_export_enabled=True,
            debug_export_dir="artifacts/debug_exports",
        ),
    )
    inputs = SimpleNamespace(
        runtime_config={"existing": "value"},
        yaml_config={"version": "9.9.9"},
        settings=_make_settings(data_dir=Path("/tmp/bioetl-data")),
    )
    request_inputs = creation_helper_module.RunManifestCreateRequestInputs(
        ctx=ctx,
        inputs=inputs,
        provider="chembl",
        entity="activity",
        reproducibility_context=SimpleNamespace(),
        run_type_value="incremental",
        execution_context_value="isolated",
        config_hash="config-hash",
        resolved_config_hash="resolved-config-hash",
        effective_config_hash="effective-config-hash",
        source_fingerprint="source-fingerprint",
        contract_identity=RunManifestContractIdentity(
            contract_ref="chembl.activity",
            contract_version="1.2.3",
            contract_schema_hash="schema-hash",
            dq_policy_ref="chembl.activity.policy",
            rule_bundle_version="2026.06",
            normalization_profile_ref="chembl.activity.norm",
            normalization_profile_version="1.0.0",
            normalization_profile_hash="f" * 64,
        ),
        dq_contract_compatibility_hash="dq-compat-hash",
        effective_config_artifact_id="artifact-123",
    )
    code_revision = CodeRevisionProvenance(
        git_commit="a" * 40,
        source_revision_state="clean",
        dependency_lock_hash="sha256:test-lock",
    )

    request = creation_helper_module.assemble_manifest_create_spec(
        request_inputs=request_inputs,
        source_refs=("source-ref",),
        replay_of_run_id="parent-run",
        replay_of_manifest_id="parent-manifest",
        code_revision=code_revision,
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        launch_context={"exact_replay": True},
    )

    assert request.runtime_config["existing"] == "value"
    assert request.runtime_config["silver_filter_compatibility_mode"] == (
        "compat-mode-test"
    )
    assert request.pipeline_version == "9.9.9"
    assert request.contract_ref == "chembl.activity"
    assert request.contract_schema_hash == "schema-hash"
    assert request.effective_config_artifact_id == "artifact-123"
    assert request.replay_capability is ReplayCapability.EXACT_REPLAY_SUPPORTED
    assert request.workflow_run_id == "workflow-run-123"
    assert request.workflow_name == "chembl_baseline"
    assert request.workflow_step_id == "run_chembl_activity"
    debug_export = next(
        artifact
        for artifact in request.planned_artifacts
        if artifact.layer == "debug_export"
    )
    assert debug_export.path.endswith(
        f"artifacts/debug_exports/wf-123/chembl_activity/{ctx.run_id}"
    )


@pytest.mark.unit
def test_creation_helper_create_ledger_service_uses_runtime_factories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_store = object()
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.control_plane_store_builders.create_run_ledger_store",
        lambda **kwargs: sentinel_store,
    )
    monkeypatch.setattr(
        "bioetl.composition.occurrence_identity.create_runtime_occurrence_id",
        lambda prefix: f"{prefix}-001",
    )
    inputs = SimpleNamespace(
        settings=_make_settings(),
        observability=SimpleNamespace(metrics="metrics-service"),
    )
    ctx = cast(
        PipelineRunContext,
        SimpleNamespace(run_id=deterministic_run_uuid_from_callsite("ledger_service")),
    )

    service = creation_helper_module.create_ledger_service(inputs, ctx)

    assert service is not None
    assert service.ledger_port is sentinel_store
    assert service.run_id == ctx.run_id
    assert service.manifest_id == "pending"
    assert service._entry_id_factory() == "run_ledger_entry-001"


@pytest.mark.unit
def test_replay_support_helpers_cover_boundary_launch_context_and_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay_helper_module.validate_exact_replay_boundary(
        SimpleNamespace(exact_replay=False),
        SimpleNamespace(strict_exact_replay_supported=False),
    )

    with pytest.raises(RuntimeError, match="strict exact-replay support boundary"):
        replay_helper_module.validate_exact_replay_boundary(
            SimpleNamespace(exact_replay=True),
            SimpleNamespace(strict_exact_replay_supported=False),
        )

    manifest_support = MagicMock()
    manifest_support.build_launch_context_snapshot.return_value = {"seed": "value"}
    request_inputs = SimpleNamespace(
        ctx=SimpleNamespace(),
        run_type_value="incremental",
        execution_context_value="isolated",
        inputs=SimpleNamespace(settings=SimpleNamespace(debug=True)),
    )
    reproducibility_context = SimpleNamespace(
        configured_required_persistence_profile="degraded_observable",
        required_persistence_profile="replay_ready",
        required_persistence_profile_opt_down=True,
        strict_exact_replay_supported=True,
        family="strict",
        replay_family_contract="strict",
        strict_replay_runtime_verdict="exact_replay_ready",
        support_scope="supported",
        reason="fixture",
    )
    launch_context = replay_helper_module.build_manifest_launch_context(
        manifest_support=manifest_support,
        request_inputs=request_inputs,
        reproducibility_context=reproducibility_context,
    )

    manifest_support.build_launch_context_snapshot.assert_called_once()
    assert launch_context == {"seed": "value"}

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        replay_helper_module,
        "assess_reproducibility_policy",
        lambda **kwargs: captured.setdefault("kwargs", kwargs) or SimpleNamespace(),
    )
    replay_helper_module.build_replay_assessment(
        request_inputs=SimpleNamespace(
            ctx=SimpleNamespace(exact_replay=True, resume=False),
            inputs=SimpleNamespace(settings=SimpleNamespace(debug=True)),
            run_type_value="incremental",
        ),
        reproducibility_context=reproducibility_context,
        source_refs=("source-ref",),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )

    assert captured["kwargs"] == {
        "source_refs": ("source-ref",),
        "required_persistence_profile": "replay_ready",
        "strict_exact_replay_supported": True,
        "exact_replay_requested": True,
        "resume_requested": False,
        "replay_capability": ReplayCapability.EXACT_REPLAY_SUPPORTED,
        "run_type": "incremental",
        "debug_only": True,
    }

    replay_context: dict[str, object] = {}
    replay_helper_module.apply_replay_assessment(
        replay_context,
        SimpleNamespace(
            replay_readiness_verdict=SimpleNamespace(value="exact_replay_ready"),
            blocking_gaps=("missing_snapshot",),
        ),
    )
    assert replay_context == {
        "replay_readiness_verdict": "exact_replay_ready",
        "exact_replay_ready": True,
        "replay_blockers": ["missing_snapshot"],
    }


@pytest.mark.unit
def test_build_planned_artifacts_includes_debug_export_root_when_enabled() -> None:
    settings = _make_settings(data_dir=Path("/tmp/bioetl-data"))

    artifacts = build_planned_artifacts(
        settings=settings,
        provider="chembl",
        entity="activity",
        run_id="00000000-0000-0000-0000-000000000123",
        pipeline_name="chembl_activity",
        workflow_id="chembl_baseline",
        debug_export_root="artifacts/debug_exports",
    )

    debug_export = next(
        artifact for artifact in artifacts if artifact.layer == "debug_export"
    )
    expected_suffix = Path(
        "artifacts/debug_exports/chembl_baseline/chembl_activity/"
        "00000000-0000-0000-0000-000000000123"
    )
    assert Path(debug_export.path).as_posix().endswith(expected_suffix.as_posix())


@pytest.mark.unit
def test_resolve_code_revision_for_manifest_keeps_clean_provenance_in_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        lambda: CodeRevisionProvenance(
            git_commit="a" * 40,
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock",
        ),
    )

    provenance = resolve_code_revision_for_manifest(
        resolved_config_hash="b" * 64,
        test_mode=True,
    )

    assert provenance.git_commit == "a" * 40
    assert provenance.source_revision_state == "clean"
    assert provenance.dependency_lock_hash == "sha256:test-lock"


@pytest.mark.unit
def test_resolve_code_revision_for_manifest_uses_deterministic_fallback_for_dirty_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        lambda: CodeRevisionProvenance(
            git_commit="c" * 40,
            source_revision_state="dirty",
            dependency_lock_hash="sha256:test-lock",
        ),
    )

    provenance = resolve_code_revision_for_manifest(
        resolved_config_hash="deadbeef" * 8,
        test_mode=True,
    )

    assert provenance.git_commit == "test-deadbeefdead"
    assert provenance.source_revision_state == "clean"
    assert provenance.dependency_lock_hash == "sha256:test-lock-deadbeefdead"


@pytest.mark.unit
def test_cached_bronze_snapshot_refs_keep_stable_identity_when_mtime_changes(
    tmp_path: Path,
) -> None:
    bronze_root = tmp_path / "bronze"
    bronze_day = bronze_root / "2026-04-12"
    bronze_day.mkdir(parents=True)
    batch_file = bronze_day / "batch_demo.jsonl.zst"
    batch_file.write_bytes(b"stable-snapshot-bytes")

    first = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )
    current_mtime = batch_file.stat().st_mtime
    os.utime(batch_file, (current_mtime + 10, current_mtime + 10))
    second = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].snapshot_id == second[0].snapshot_id
    assert first[0].content_hash == second[0].content_hash
    assert first[0].immutable_uri == second[0].immutable_uri
    assert first[0].immutable_uri == "bronze://2026-04-12/batch_demo.jsonl.zst"
    assert first[0].captured_at is None
    assert second[0].captured_at is None


@pytest.mark.unit
def test_cached_bronze_snapshot_identity_is_content_addressed_not_locator(
    tmp_path: Path,
) -> None:
    bronze_root = tmp_path / "bronze"
    first_day = bronze_root / "2026-04-12"
    second_day = bronze_root / "2026-04-13"
    first_day.mkdir(parents=True)
    second_day.mkdir(parents=True)
    (first_day / "batch_demo.jsonl.zst").write_bytes(b"same-payload")
    (second_day / "batch_renamed.jsonl.zst").write_bytes(b"same-payload")

    first = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )
    second = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-13",
    )

    assert first[0].snapshot_id == second[0].snapshot_id
    assert first[0].snapshot_id == f"sha256:{first[0].content_hash}"
    assert first[0].immutable_uri == "bronze://2026-04-12/batch_demo.jsonl.zst"
    assert second[0].immutable_uri == "bronze://2026-04-13/batch_renamed.jsonl.zst"


@pytest.mark.unit
def test_cached_bronze_snapshot_refs_are_sorted_by_snapshot_identity(
    tmp_path: Path,
) -> None:
    bronze_root = tmp_path / "bronze"
    bronze_day = bronze_root / "2026-04-12"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_b.jsonl.zst").write_bytes(b"batch-b")
    (bronze_day / "batch_a.jsonl.zst").write_bytes(b"batch-a")

    refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date="2026-04-12",
    )

    snapshot_ids = [ref.snapshot_id for ref in refs]
    assert snapshot_ids == sorted(snapshot_ids)


@pytest.mark.unit
def test_build_run_source_refs_fails_closed_for_exact_replay_without_snapshots() -> (
    None
):
    settings = _make_settings()
    ctx = _make_run_context(query=None, exact_replay=True)
    cached_bronze = SimpleNamespace(
        enabled=True,
        bronze_path="test-output/does-not-exist",
        bronze_date="2026-04-12",
    )

    with pytest.raises(
        RuntimeError,
        match="Cached Bronze execution requires at least one persisted batch file",
    ):
        build_run_source_refs(
            ctx=ctx,
            cached_bronze=cached_bronze,
            settings=settings,
            provider="chembl",
            entity="activity",
        )


@pytest.mark.unit
def test_build_run_source_refs_rejects_strict_profile_without_snapshots() -> None:
    settings = _make_settings()
    ctx = _make_run_context(query=None, exact_replay=False)

    with pytest.raises(
        RuntimeError,
        match="strict persistence profiles require immutable input snapshots",
    ):
        build_run_source_refs(
            ctx=ctx,
            cached_bronze=None,
            settings=settings,
            provider="chembl",
            entity="activity",
            required_persistence_profile="replay_ready",
        )


@pytest.mark.unit
def test_validate_required_runtime_persistence_profile_rejects_bounded_live_capture() -> (
    None
):
    request = _make_manifest_request(
        exact_replay=False,
        required_persistence_profile="replay_ready",
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )
    request = replace(
        request,
        launch_context={
            **request.launch_context,
            "execution_context": "pipeline",
        },
        source_refs=(),
    )

    with pytest.raises(
        RuntimeError,
        match="cannot satisfy required persistence profile 'replay_ready'",
    ):
        validate_required_runtime_persistence_profile(
            request=request,
            required_persistence_profile="replay_ready",
            strict_exact_replay_supported=True,
        )


@pytest.mark.unit
def test_build_run_source_refs_accepts_manifest_backed_snapshot_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    ctx = _make_run_context(query=None, exact_replay=True)
    manifest_snapshot = RunInputSnapshotRef(
        snapshot_id="sha256:manifest-snapshot",
        content_hash="manifest-snapshot",
        immutable_uri="bronze://chembl/activity/manifest.jsonl.zst",
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.run_manifest_support.resolve_pipeline_input_snapshot_refs",
        lambda **_: (manifest_snapshot,),
    )

    source_refs = build_run_source_refs(
        ctx=ctx,
        cached_bronze=None,
        settings=settings,
        provider="chembl",
        entity="activity",
        required_persistence_profile="replay_ready",
    )

    assert len(source_refs) == 1
    assert source_refs[0].input_snapshots == (manifest_snapshot,)


@pytest.mark.unit
def test_resolve_replay_capability_requires_persisted_snapshots_for_exact_replay() -> (
    None
):
    no_snapshot_refs = (
        SimpleNamespace(provider="chembl", entity="activity", input_snapshots=()),
    )
    snapshot_refs = (
        SimpleNamespace(
            provider="chembl",
            entity="activity",
            input_snapshots=(SimpleNamespace(snapshot_id="snap-1"),),
        ),
    )

    assert (
        resolve_replay_capability(
            source_refs=no_snapshot_refs,
            resume_requested=False,
        )
        is ReplayCapability.REBUILD_ONLY
    )
    assert (
        resolve_replay_capability(
            source_refs=no_snapshot_refs,
            resume_requested=True,
        )
        is ReplayCapability.RESUME_ONLY
    )
    assert (
        resolve_replay_capability(
            source_refs=snapshot_refs,
            resume_requested=False,
        )
        is ReplayCapability.EXACT_REPLAY_SUPPORTED
    )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_append_without_contract() -> None:
    with pytest.raises(RuntimeError, match="idempotency_contract"):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(enabled=True, mode="append"),
                    "gold": SimpleNamespace(enabled=False, mode="scd2"),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_allows_non_strict_append_with_contract() -> (
    None
):
    validate_reproducible_sink_modes(
        yaml_config=SimpleNamespace(
            sink={
                "silver": SimpleNamespace(
                    enabled=True,
                    mode="append",
                    idempotency_contract="append_log",
                    idempotency_evidence={
                        "occurrence_identity_fields": ["activity_id", "run_id"]
                    },
                ),
                "gold": SimpleNamespace(
                    enabled=False,
                    mode="scd2",
                    idempotency_contract="scd2",
                ),
            }
        ),
        strict_replay_requested=False,
    )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_append_without_evidence() -> None:
    with pytest.raises(
        RuntimeError,
        match="requires machine-readable idempotency evidence",
    ):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="append_log",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_allows_partition_append_evidence() -> None:
    validate_reproducible_sink_modes(
        yaml_config=SimpleNamespace(
            sink={
                "silver": SimpleNamespace(
                    enabled=False,
                    mode="merge",
                    idempotency_contract="merge_upsert",
                ),
                "gold": SimpleNamespace(
                    enabled=True,
                    mode="append",
                    idempotency_contract="partition_append_with_stable_partition_key",
                    idempotency_evidence={"stable_partition_keys": ["run_date"]},
                ),
            }
        ),
        strict_replay_requested=False,
    )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_disallowed_append_contract() -> None:
    with pytest.raises(RuntimeError, match="idempotency_contract=disallowed"):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="disallowed",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_incompatible_append_contract() -> (
    None
):
    with pytest.raises(
        RuntimeError,
        match=r"sink\.silver\.mode=append is incompatible with "
        r"sink\.silver\.idempotency_contract=merge_upsert",
    ):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="merge_upsert",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=False,
        )


@pytest.mark.unit
def test_validate_reproducible_sink_modes_rejects_append_in_strict_replay_context() -> (
    None
):
    with pytest.raises(
        RuntimeError,
        match="Strict reproducibility contexts cannot use append-mode Silver/Gold",
    ):
        validate_reproducible_sink_modes(
            yaml_config=SimpleNamespace(
                sink={
                    "silver": SimpleNamespace(
                        enabled=True,
                        mode="append",
                        idempotency_contract="occurrence_only",
                    ),
                    "gold": SimpleNamespace(
                        enabled=False,
                        mode="scd2",
                        idempotency_contract="scd2",
                    ),
                }
            ),
            strict_replay_requested=True,
        )


@pytest.mark.unit
def test_build_launch_context_snapshot_marks_ordinary_source_boundary() -> None:
    ctx = _make_run_context(
        limit=10,
        query="assay_type=B",
        exact_replay=True,
        cached_bronze=SimpleNamespace(enabled=True),
    )

    launch_context = build_launch_context_snapshot(
        ctx,
        run_type_value="incremental",
        execution_context_value="pipeline",
        required_persistence_profile="replay_ready",
    )

    assert launch_context["execution_context"] == "pipeline"
    assert launch_context["required_persistence_profile"] == "replay_ready"
    assert launch_context["configured_required_persistence_profile"] == "replay_ready"
    assert (
        launch_context["exact_replay_support_boundary"]
        == "snapshot_backed_source_runs_only"
    )


@pytest.mark.unit
def test_build_launch_context_snapshot_marks_source_run_exact_replay_boundary_for_composite() -> (
    None
):
    ctx = _make_run_context(limit=10)

    launch_context = build_launch_context_snapshot(
        ctx,
        run_type_value="incremental",
        execution_context_value="composite",
        required_persistence_profile="degraded_observable",
    )

    assert launch_context["execution_context"] == "composite"
    assert launch_context["required_persistence_profile"] == "degraded_observable"
    assert (
        launch_context["configured_required_persistence_profile"]
        == "degraded_observable"
    )
    assert (
        launch_context["exact_replay_support_boundary"]
        == "snapshot_backed_source_runs_only"
    )


@pytest.mark.unit
def test_resolve_contract_identity_reads_registry_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text(
        """
entries:
  chembl.activity:
    dq_policy_ref: chembl.activity.policy
    rule_bundle_version: "2026.04"
    identity:
      contract_version: "1.2.3"
      schema_hash: deadbeef
      normalization_profile_ref: "chembl.activity"
      normalization_profile_version: "1.0.0"
      normalization_profile_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = resolve_contract_identity(provider="chembl", entity="activity")

    assert result.contract_ref == "chembl.activity"
    assert result.contract_version == "1.2.3"
    assert result.contract_schema_hash == "deadbeef"
    assert result.dq_policy_ref == "chembl.activity.policy"
    assert result.rule_bundle_version == "2026.04"
    assert result.normalization_profile_ref == "chembl.activity"
    assert result.normalization_profile_version == "1.0.0"
    assert (
        result.normalization_profile_hash
        == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


@pytest.mark.unit
def test_resolve_contract_identity_falls_back_when_registry_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text("entries: [invalid", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = resolve_contract_identity(provider="chembl", entity="activity")

    assert result.contract_ref == "chembl.activity"
    assert result.contract_version is None
    assert result.contract_schema_hash is None
    assert result.dq_policy_ref is None
    assert result.rule_bundle_version is None
    assert result.normalization_profile_ref is None
    assert result.normalization_profile_version is None
    assert result.normalization_profile_hash is None


@pytest.mark.unit
def test_resolve_contract_identity_fails_closed_for_strict_context_when_registry_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text("entries: [invalid", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="Strict reproducibility contexts require"):
        resolve_contract_identity(
            provider="chembl",
            entity="activity",
            strict=True,
        )


@pytest.mark.unit
def test_resolve_contract_identity_fails_closed_when_strict_identity_incomplete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "configs" / "base"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "contract_registry.yaml"
    registry_path.write_text(
        """
entries:
  chembl.activity:
    identity:
      contract_version: "1.2.3"
      schema_hash: deadbeef
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(
        RuntimeError,
        match=(
            "missing: dq_policy_ref, rule_bundle_version, "
            "normalization_profile_ref, normalization_profile_version, "
            "normalization_profile_hash"
        ),
    ):
        resolve_contract_identity(
            provider="chembl",
            entity="activity",
            strict=True,
        )


@pytest.mark.unit
def test_replay_reconstructability_metric_is_reconstructable_for_non_strict_runs() -> (
    None
):
    metrics = MagicMock()

    emit_replay_reconstructability_metric(
        request=_make_manifest_request(
            exact_replay=False,
            required_persistence_profile="degraded_observable",
            replay_capability=ReplayCapability.REBUILD_ONLY,
        ),
        strict_exact_replay_supported=False,
        metrics=metrics,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": "chembl_activity",
            "replay_capability": "rebuild_only",
            "strict_requirement": "false",
            "status": "reconstructable",
        },
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_replay_lag_seconds",
        value=0.0,
        labels={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "replay_capability": "rebuild_only",
            "status": "not_requested",
        },
    )


@pytest.mark.unit
def test_replay_reconstructability_metric_marks_strict_runs_not_reconstructable() -> (
    None
):
    metrics = MagicMock()

    emit_replay_reconstructability_metric(
        request=_make_manifest_request(
            exact_replay=True,
            required_persistence_profile="forensic_grade",
            replay_capability=ReplayCapability.RESUME_ONLY,
        ),
        strict_exact_replay_supported=False,
        metrics=metrics,
    )

    metrics.increment_counter.assert_has_calls(
        [
            call(
                "bioetl_replay_reconstructability_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "replay_capability": "resume_only",
                    "strict_requirement": "true",
                    "status": "not_reconstructable",
                },
            ),
            call(
                "bioetl_replay_drift_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "replay_capability": "resume_only",
                    "drift_type": "strict_replay_not_reconstructable",
                    "status": "detected",
                },
            ),
        ]
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_replay_lag_seconds",
        value=0.0,
        labels={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "replay_capability": "resume_only",
            "status": "blocked",
        },
    )


@pytest.mark.unit
def test_replay_reconstructability_metric_marks_strict_runs_reconstructable_when_supported() -> (
    None
):
    metrics = MagicMock()

    emit_replay_reconstructability_metric(
        request=_make_manifest_request(
            exact_replay=False,
            required_persistence_profile="replay_ready",
            replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        ),
        strict_exact_replay_supported=True,
        metrics=metrics,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_replay_reconstructability_events_total",
        value=1,
        labels={
            "pipeline": "chembl_activity",
            "replay_capability": "exact_replay_supported",
            "strict_requirement": "true",
            "status": "reconstructable",
        },
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_replay_lag_seconds",
        value=0.0,
        labels={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "replay_capability": "exact_replay_supported",
            "status": "not_requested",
        },
    )
