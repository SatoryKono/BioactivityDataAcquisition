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
"""Split baseline and wiring tests for runtime runner builder."""

from __future__ import annotations

import json
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.composition.runtime_builders.runner_builder_wiring import (
    LegacyRunnerBuilderOverrides,
    resolve_runner_builder_wiring,
    resolve_runner_factory_wiring,
)
from bioetl.composition.runtime_builders import (
    inputs_resolver,
    runner_control_plane_assembly,
)

from tests.unit.composition.runtime_builders.runner_builder_test_support import *


pytestmark = pytest.mark.unit


def test_handle_control_plane_setup_returns_effective_manifest_profile(
    monkeypatch,
) -> None:
    """Attachment closure must follow the manifest-resolved strict profile."""
    logger = MagicMock()
    ctx = SimpleNamespace(skip_gold=False, exact_replay=True)
    inputs = SimpleNamespace(
        settings=SimpleNamespace(data_dir="/tmp/bioetl-test-data"),
        yaml_config=SimpleNamespace(),
        observability=SimpleNamespace(logger=logger),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        runner_control_plane_assembly,
        "_resolve_runner_control_plane_policy",
        lambda *_, **__: SimpleNamespace(
            manifest_enabled=True,
            ledger_enabled=True,
            required_profile="degraded_observable",
        ),
    )
    monkeypatch.setattr(
        runner_control_plane_assembly,
        "create_run_manifest_with_effective_config",
        lambda **_: (
            SimpleNamespace(
                manifest_id="manifest-1",
                required_persistence_profile="replay_ready",
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        runner_control_plane_assembly,
        "attach_manifest_id",
        lambda effective_ctx, **_: effective_ctx,
    )
    monkeypatch.setattr(
        runner_control_plane_assembly,
        "_bind_manifest_logger_context",
        lambda effective_inputs, manifest_id: (
            captured.setdefault("manifest_id", manifest_id),
            effective_inputs,
        )[1],
    )

    result = runner_control_plane_assembly.assemble_runner_control_plane(ctx, inputs)

    assert captured["manifest_id"] == "manifest-1"
    assert result.required_profile == "replay_ready"
    logger.info.assert_called_once_with(
        "control_plane_profile_resolved",
        stage="bootstrap",
        configured_required_persistence_profile="degraded_observable",
        required_persistence_profile="replay_ready",
        run_manifest_enabled=True,
        run_ledger_enabled=True,
        exact_replay=True,
    )


def test_build_pipeline_runner_defaults_to_provider_registry_bootstrap() -> None:
    """Default factory wiring should use the named provider loader helper."""
    wiring = resolve_runner_factory_wiring()

    assert wiring.ensure_providers_loaded is runner_builder.ensure_providers_loaded


def test_build_pipeline_runner_wires_dependencies(tmp_path: Path) -> None:
    """Builder should assemble dependencies and pass them to pipeline factory."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")
    (bronze_day / "batch_2026-01-01_extra.jsonl.zst").write_bytes(b"snapshot-bytes-2")

    calls: dict[str, object] = {}

    def get_settings_fn() -> SimpleNamespace:
        return SimpleNamespace(
            data_dir=str(tmp_path),
            pipeline=SimpleNamespace(heartbeat_interval=30),
            test_mode=False,
        )

    def load_pipeline_config_fn(_: str) -> SimpleNamespace:
        return SimpleNamespace(
            maintenance={"retain_days": 7},
            input_filter=SimpleNamespace(),
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
        )

    logger_calls: list[tuple[str, dict[str, object]]] = []
    logger = SimpleNamespace(
        info=lambda event, **kwargs: logger_calls.append((event, kwargs)),
    )

    def build_observability_bundle_fn(**_: object) -> SimpleNamespace:
        return _namespace_observability(logger)

    def assemble_vacuum_settings_fn(**_: object) -> str:
        return "vacuum"

    def assemble_runtime_config_fn(**_: object) -> dict[str, object]:
        return _runtime_config_stub()

    def assemble_filter_config_fn(**_: object) -> SimpleNamespace:
        return SimpleNamespace(
            source_path="ids.csv",
            column_name="molecule_id",
            filter_field="molecule_id",
        )

    def assemble_cached_bronze_context_fn(_: object) -> SimpleNamespace:
        return SimpleNamespace(
            enabled=True,
            bronze_path=str(bronze_root),
            bronze_date="2026-01-01",
        )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=deterministic_uuid_from_callsite("test_runner_builder_basics"),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=100,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        input_filter=SimpleNamespace(enabled=False),
        workflow_run_id=None,
        workflow_name=None,
        workflow_step_id=None,
        workflow_id="standalone",
        debug_export_enabled=False,
        debug_export_dir=None,
    )

    with patch(
        "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
        return_value=SimpleNamespace(
            git_commit="deadbeef" * 5,
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock",
        ),
    ):
        result = runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            wiring=resolve_runner_builder_wiring(
                legacy_overrides=LegacyRunnerBuilderOverrides(
                    ensure_providers_loaded_fn=lambda: calls.setdefault(
                        "providers", True
                    ),
                    register_all_pipelines_fn=lambda registry=None: calls.setdefault(
                        "pipelines_registry", registry
                    ),
                    get_settings_fn=get_settings_fn,
                    load_pipeline_config_fn=load_pipeline_config_fn,
                    build_observability_bundle_fn=build_observability_bundle_fn,
                    assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
                    assemble_runtime_config_fn=assemble_runtime_config_fn,
                    assemble_filter_config_fn=assemble_filter_config_fn,
                    assemble_cached_bronze_context_fn=(
                        assemble_cached_bronze_context_fn
                    ),
                )
            ),
        )

    assert result == "runner-instance"
    assert calls["providers"] is True
    assert calls["pipelines_registry"] is fake_registry
    assert fake_factory.kwargs is not None
    assert fake_factory.kwargs["runtime"] == _runtime_config_stub()
    assert fake_factory.kwargs["cached_bronze"].enabled is True
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_refs = payload["source_refs"]
    assert isinstance(source_refs, list)
    assert len(source_refs) == 1
    assert payload["replay_capability"] == "exact_replay_supported"
    snapshots = source_refs[0]["input_snapshots"]
    assert len(snapshots) == 2
    assert sorted(snapshot["immutable_uri"] for snapshot in snapshots) == [
        "bronze://2026-01-01/batch_2026-01-01_demo.jsonl.zst",
        "bronze://2026-01-01/batch_2026-01-01_extra.jsonl.zst",
    ]
    assert all(snapshot["content_hash"] for snapshot in snapshots)
    assert all(
        snapshot["snapshot_id"] == f"sha256:{snapshot['content_hash']}"
        for snapshot in snapshots
    )
    assert [snapshot["snapshot_id"] for snapshot in snapshots] == sorted(
        snapshot["snapshot_id"] for snapshot in snapshots
    )
    events = [event for event, _ in logger_calls]
    assert events[:2] == [
        "input_filter_enabled",
        "cached_bronze_mode_enabled",
    ]
    assert "effective_config_artifact_persisted" in events


def test_build_pipeline_runner_creates_registry_when_not_provided(
    tmp_path: Path,
) -> None:
    """Builder should create a fresh registry when no explicit registry is provided."""
    fake_factory, created_registry = _build_factory_registry()

    result = _call_build_pipeline_runner(
        _build_context(),
        create_registry_fn=lambda: created_registry,
        settings=_build_settings(
            data_dir=str(tmp_path),
            heartbeat_interval=15,
            test_mode=True,
        ),
        pipeline_config=_build_pipeline_config(
            maintenance=None,
            input_filter=None,
        ),
    )

    assert result == "runner-instance"
    assert fake_factory.kwargs is not None
    assert fake_factory.kwargs["runtime"] == _runtime_config_stub()


def test_build_pipeline_runner_registers_pipelines_into_created_registry(
    tmp_path: Path,
) -> None:
    """Builder should register pipelines against the created runtime registry."""
    created_registry = _build_factory_registry()[1]
    calls: dict[str, object] = {}

    result = _call_build_pipeline_runner(
        _build_context(),
        create_registry_fn=lambda: created_registry,
        ensure_providers_loaded_fn=lambda: calls.setdefault("providers", True),
        register_all_pipelines_fn=lambda registry=None: calls.setdefault(
            "pipelines_registry", registry
        ),
        settings=_build_settings(
            data_dir=str(tmp_path),
            heartbeat_interval=15,
            test_mode=True,
        ),
        pipeline_config=_build_pipeline_config(
            maintenance=None,
            input_filter=None,
        ),
    )

    assert result == "runner-instance"
    assert calls["providers"] is True
    assert calls["pipelines_registry"] is created_registry


def test_build_pipeline_runner_uses_canonical_subservices_with_observability_seam() -> (
    None
):
    """Builder should resolve canonical subservices without importing observability bootstrap."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    build_observability_bundle_fn = MagicMock(name="build_observability_bundle")
    expected_inputs = SimpleNamespace(
        settings="settings",
        yaml_config="yaml-config",
        observability=_namespace_observability(
            SimpleNamespace(
                info=lambda *_, **__: None,
                error=lambda *_, **__: None,
            ),
        ),
        runtime_config="runtime",
        filter_config=None,
        cached_bronze=SimpleNamespace(enabled=False),
    )
    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=deterministic_uuid_from_callsite("test_runner_builder_basics"),
        log_level="INFO",
    )

    with (
        patch.object(
            runner_builder, "prepare_runner_inputs", return_value=expected_inputs
        ) as mock_prepare_inputs,
        patch.object(
            runner_builder,
            "_assemble_runner_control_plane",
            return_value=runner_control_plane_assembly.ControlPlaneSetupResult(
                ctx=context,
                inputs=expected_inputs,
                run_ledger_service=None,
                required_profile="degraded_observable",
            ),
        ),
    ):
        result = runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            wiring=resolve_runner_builder_wiring(
                legacy_overrides=LegacyRunnerBuilderOverrides(
                    ensure_providers_loaded_fn=lambda: None,
                    register_all_pipelines_fn=lambda registry=None: None,
                    get_settings_fn=lambda: _build_settings(),
                    load_pipeline_config_fn=lambda _: MagicMock(),
                    build_observability_bundle_fn=build_observability_bundle_fn,
                )
            ),
        )

    assert result == "runner-instance"
    kwargs = mock_prepare_inputs.call_args.kwargs
    assert kwargs["build_observability_bundle_fn"] is build_observability_bundle_fn
    assert (
        kwargs["assemble_vacuum_settings_fn"]
        is inputs_resolver.assemble_vacuum_settings
    )
    assert (
        kwargs["assemble_runtime_config_fn"] is inputs_resolver.assemble_runtime_config
    )
    assert kwargs["assemble_filter_config_fn"] is inputs_resolver.assemble_filter_config
    assert (
        kwargs["assemble_cached_bronze_context_fn"]
        is inputs_resolver.assemble_cached_bronze_context
    )
    assert kwargs["load_source_config_fn"] is runner_builder.load_source_config


def test_build_pipeline_runner_persists_manifest_before_factory_create(
    tmp_path: Path,
) -> None:
    """Builder should persist a manifest and pass manifest_id to the factory."""
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(limit=25, query="assay_type=B")

    result = _call_build_pipeline_runner(
        context,
        registry=fake_registry,
        settings=_build_settings(data_dir=str(tmp_path)),
        pipeline_config=_build_pipeline_config(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
        ),
        assemble_vacuum_settings_fn=lambda **_: "vacuum",
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(
            run_type="incremental",
            limit=25,
        ),
    )

    assert result == "runner-instance"
    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)

    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["manifest_id"] == manifest_id
    assert (
        payload["execution_fingerprint"] == fake_factory.kwargs["execution_fingerprint"]
    )
    assert payload["pipeline_name"] == "chembl_activity"
    code_provenance = payload["code_provenance"]
    assert isinstance(code_provenance, dict)
    effective_config_artifact_id = code_provenance["effective_config_artifact_id"]
    assert isinstance(effective_config_artifact_id, str)
    assert code_provenance["config_hash"] == fake_factory.kwargs["config_hash"]
    assert code_provenance["contract_ref"] == "chembl.activity"
    assert isinstance(code_provenance.get("contract_version"), str)
    assert isinstance(code_provenance.get("contract_schema_hash"), str)
    assert isinstance(code_provenance.get("dq_policy_ref"), str)
    assert isinstance(code_provenance.get("rule_bundle_version"), str)
    assert (
        code_provenance["dq_contract_compatibility_hash"]
        == fake_factory.kwargs["dq_contract_compatibility_hash"]
    )
    assert (
        effective_config_artifact_id
        == fake_factory.kwargs["effective_config_artifact_id"]
    )

    effective_config_path = (
        tmp_path
        / "output"
        / "control"
        / "effective_config"
        / f"{effective_config_artifact_id}.json"
    )
    assert effective_config_path.exists()
    effective_payload = json.loads(effective_config_path.read_text(encoding="utf-8"))
    assert isinstance(effective_payload, dict)
    assert effective_payload["artifact_id"] == effective_config_artifact_id
    assert effective_payload["semantic_artifact"]["artifact_id"] == (
        effective_config_artifact_id
    )
    assert (
        effective_payload["semantic_artifact"]["resolution_policy"]["strict_validation"]
        is False
    )
    assert "occurrence_envelope" not in effective_payload

    effective_index_path = (
        tmp_path
        / "output"
        / "control"
        / "effective_config"
        / "_by_run_id"
        / f"{context.run_id}.txt"
    )
    assert effective_index_path.exists()
    assert effective_index_path.read_text(encoding="utf-8").strip() == (
        effective_config_artifact_id
    )
    occurrence_path = (
        tmp_path
        / "output"
        / "control"
        / "effective_config"
        / "_occurrences"
        / f"{context.run_id}.json"
    )
    assert occurrence_path.exists()
    occurrence_payload = json.loads(occurrence_path.read_text(encoding="utf-8"))
    assert occurrence_payload["artifact_id"] == effective_config_artifact_id
    assert occurrence_payload["run_id"] == str(context.run_id)
    assert "occurrence_envelope" in occurrence_payload
    assert fake_factory.runner.attached_run_ledger_service is not None

    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    assert ledger_path.exists()
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert ledger_payload["manifest_id"] == manifest_id
    assert ledger_payload["event_type"] == "manifest_created"
