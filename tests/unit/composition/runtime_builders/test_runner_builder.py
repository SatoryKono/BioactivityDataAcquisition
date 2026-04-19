"""Unit tests for runtime runner builder leaf module."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.ports.noop import NoOpTracing
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.composition.runtime_builders import observability_builder
from bioetl.composition.runtime_builders import runner_builder

SILVER_OUTPUT_PATH = "test-output/silver/chembl/activity"
SILVER_METADATA_PATH = "test-output/silver/chembl/activity/_metadata.yaml"


class _FakeRunner:
    def __init__(self) -> None:
        self.attached_run_ledger_service: object | None = None
        self.services = SimpleNamespace(metadata_writer=None, storage=None)

    def attach_run_ledger_service(self, service: object) -> None:
        self.attached_run_ledger_service = service

    def __eq__(self, other: object) -> bool:
        return other == "runner-instance" or other is self


class _FakeFactory:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None
        self.runner = _FakeRunner()

    def create_runner(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return self.runner


class _RecorderAwareMetadataWriter:
    def __init__(self) -> None:
        self.recorder = None

    def attach_artifact_recorder(self, recorder) -> None:
        self.recorder = recorder


class _FakeRegistry:
    def __init__(self, factory: _FakeFactory) -> None:
        self._factory = factory

    def get(self, pipeline_name: str) -> SimpleNamespace:
        return SimpleNamespace(factory=self._factory, pipeline_name=pipeline_name)


def _namespace_observability(logger: object | None = None) -> SimpleNamespace:
    effective_logger = (
        logger if logger is not None else SimpleNamespace(info=lambda *_, **__: None)
    )
    return SimpleNamespace(logger=effective_logger, metrics=MagicMock())


def _runtime_config_stub() -> dict[str, object]:
    return {"runtime_profile": "stub"}


def _build_factory_registry() -> tuple[_FakeFactory, _FakeRegistry]:
    fake_factory = _FakeFactory()
    return fake_factory, _FakeRegistry(factory=fake_factory)


def _build_context(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "pipeline_name": "chembl_activity",
        "run_id": uuid4(),
        "log_level": "INFO",
        "vacuum": None,
        "run_type": "incremental",
        "resume": False,
        "limit": None,
        "query": None,
        "dry_run": False,
        "skip_gold": False,
        "start_offset": None,
        "input_filter": SimpleNamespace(enabled=False),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _build_settings(
    *,
    data_dir: str | None = None,
    heartbeat_interval: int = 30,
    health_check_mode: str | None = None,
    control_plane: object | None = None,
    test_mode: bool = False,
) -> SimpleNamespace:
    pipeline_values: dict[str, object] = {
        "heartbeat_interval": heartbeat_interval,
    }
    if health_check_mode is not None:
        pipeline_values["health_check_mode"] = health_check_mode
    if control_plane is not None:
        pipeline_values["control_plane"] = control_plane

    settings_values: dict[str, object] = {
        "pipeline": SimpleNamespace(**pipeline_values),
        "test_mode": test_mode,
    }
    if data_dir is not None:
        settings_values["data_dir"] = data_dir
    return SimpleNamespace(**settings_values)


def _build_pipeline_config(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "provider": "chembl",
        "entity_type": "activity",
        "version": "2.0.0",
        "maintenance": None,
        "input_filter": SimpleNamespace(),
        "business_primary_keys": ["activity_id"],
        "technical_primary_key": "entity_id",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _default_build_observability_bundle_fn(**_: object) -> SimpleNamespace:
    return _namespace_observability(SimpleNamespace(info=lambda *_, **__: None))


def _default_cached_bronze_context(_: object) -> SimpleNamespace:
    return SimpleNamespace(enabled=False)


def _call_build_pipeline_runner(
    context: SimpleNamespace | None = None,
    *,
    registry: _FakeRegistry | None = None,
    create_registry_fn: object | None = None,
    ensure_providers_loaded_fn: object | None = None,
    register_all_pipelines_fn: object | None = None,
    settings: object | None = None,
    pipeline_config: object | None = None,
    build_observability_bundle_fn: object | None = None,
    assemble_vacuum_settings_fn: object | None = None,
    assemble_runtime_config_fn: object | None = None,
    assemble_filter_config_fn: object | None = None,
    assemble_cached_bronze_context_fn: object | None = None,
) -> object:
    kwargs: dict[str, object] = {
        "ensure_providers_loaded_fn": ensure_providers_loaded_fn
        if ensure_providers_loaded_fn is not None
        else (lambda: None),
        "register_all_pipelines_fn": register_all_pipelines_fn
        if register_all_pipelines_fn is not None
        else (lambda registry=None: None),
        "get_settings_fn": lambda: (
            settings if settings is not None else _build_settings()
        ),
        "load_pipeline_config_fn": lambda _: (
            pipeline_config if pipeline_config is not None else _build_pipeline_config()
        ),
        "build_observability_bundle_fn": build_observability_bundle_fn
        if build_observability_bundle_fn is not None
        else _default_build_observability_bundle_fn,
        "assemble_vacuum_settings_fn": assemble_vacuum_settings_fn
        if assemble_vacuum_settings_fn is not None
        else (lambda **_: None),
        "assemble_runtime_config_fn": assemble_runtime_config_fn
        if assemble_runtime_config_fn is not None
        else (lambda **_: _runtime_config_stub()),
        "assemble_filter_config_fn": assemble_filter_config_fn
        if assemble_filter_config_fn is not None
        else (lambda **_: None),
        "assemble_cached_bronze_context_fn": assemble_cached_bronze_context_fn
        if assemble_cached_bronze_context_fn is not None
        else _default_cached_bronze_context,
    }
    if registry is not None:
        kwargs["registry"] = registry
    if create_registry_fn is not None:
        kwargs["create_registry_fn"] = create_registry_fn
    return runner_builder.build_pipeline_runner(
        context if context is not None else _build_context(),
        **kwargs,
    )


def test_build_pipeline_runner_defaults_to_provider_registry_bootstrap() -> None:
    """Default provider bootstrap should come from the named loader helper."""
    default_fn = runner_builder.build_pipeline_runner.__kwdefaults__[
        "ensure_providers_loaded_fn"
    ]

    assert default_fn is runner_builder.ensure_providers_loaded


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
        run_id=uuid4(),
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
    )

    result = runner_builder.build_pipeline_runner(
        context,
        registry=fake_registry,
        ensure_providers_loaded_fn=lambda: calls.setdefault("providers", True),
        register_all_pipelines_fn=lambda registry=None: calls.setdefault(
            "pipelines_registry", registry
        ),
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_observability_bundle_fn,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=assemble_filter_config_fn,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
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
        str(bronze_day / "batch_2026-01-01_demo.jsonl.zst"),
        str(bronze_day / "batch_2026-01-01_extra.jsonl.zst"),
    ]
    assert all(snapshot["content_hash"] for snapshot in snapshots)
    assert [snapshot["snapshot_id"] for snapshot in snapshots] == sorted(
        snapshot["snapshot_id"] for snapshot in snapshots
    )
    events = [event for event, _ in logger_calls]
    assert events[:2] == [
        "input_filter_enabled",
        "cached_bronze_mode_enabled",
    ]
    assert "effective_config_artifact_persisted" in events


def test_build_pipeline_runner_creates_registry_when_not_provided() -> None:
    """Builder should create a fresh registry when no explicit registry is provided."""
    fake_factory, created_registry = _build_factory_registry()

    result = _call_build_pipeline_runner(
        _build_context(),
        create_registry_fn=lambda: created_registry,
        settings=_build_settings(heartbeat_interval=15, test_mode=True),
        pipeline_config=_build_pipeline_config(
            maintenance=None,
            input_filter=None,
        ),
    )

    assert result == "runner-instance"
    assert fake_factory.kwargs is not None
    assert fake_factory.kwargs["runtime"] == _runtime_config_stub()


def test_build_pipeline_runner_registers_pipelines_into_created_registry() -> None:
    """Builder should register pipelines against the created runtime registry."""
    fake_factory, created_registry = _build_factory_registry()
    calls: dict[str, object] = {}

    result = _call_build_pipeline_runner(
        _build_context(),
        create_registry_fn=lambda: created_registry,
        ensure_providers_loaded_fn=lambda: calls.setdefault("providers", True),
        register_all_pipelines_fn=lambda registry=None: calls.setdefault(
            "pipelines_registry", registry
        ),
        settings=_build_settings(heartbeat_interval=15, test_mode=True),
        pipeline_config=_build_pipeline_config(
            maintenance=None,
            input_filter=None,
        ),
    )

    assert result == "runner-instance"
    assert calls["providers"] is True
    assert calls["pipelines_registry"] is created_registry


def test_build_pipeline_runner_uses_canonical_runtime_subservices_by_default() -> None:
    """Builder should resolve canonical subservices when no overrides are passed."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
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
        run_id=uuid4(),
        log_level="INFO",
    )

    with patch.object(
        runner_builder, "prepare_runner_inputs", return_value=expected_inputs
    ) as mock_prepare_inputs:
        result = runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            ensure_providers_loaded_fn=lambda: None,
            register_all_pipelines_fn=lambda registry=None: None,
            get_settings_fn=lambda: MagicMock(),
            load_pipeline_config_fn=lambda _: MagicMock(),
        )

    assert result == "runner-instance"
    kwargs = mock_prepare_inputs.call_args.kwargs
    assert (
        kwargs["build_observability_bundle_fn"]
        is runner_builder.build_observability_bundle
    )
    assert (
        kwargs["assemble_vacuum_settings_fn"] is runner_builder.assemble_vacuum_settings
    )
    assert (
        kwargs["assemble_runtime_config_fn"] is runner_builder.assemble_runtime_config
    )
    assert kwargs["assemble_filter_config_fn"] is runner_builder.assemble_filter_config
    assert (
        kwargs["assemble_cached_bronze_context_fn"]
        is runner_builder.assemble_cached_bronze_context
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
    assert "occurrence_envelope" in effective_payload

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
    assert fake_factory.runner.attached_run_ledger_service is not None

    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    assert ledger_path.exists()
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert ledger_payload["manifest_id"] == manifest_id
    assert ledger_payload["event_type"] == "manifest_created"


def test_build_pipeline_runner_rejects_exact_replay_without_materialized_cached_bronze_batches(
    tmp_path: Path,
) -> None:
    """Exact replay must fail closed when cached-Bronze snapshots are missing."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    empty_bronze_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    empty_bronze_root.mkdir(parents=True)

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=25,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        exact_replay=True,
        input_filter=SimpleNamespace(enabled=False),
    )

    with pytest.raises(
        RuntimeError,
        match="Cached Bronze execution requires at least one persisted batch file for snapshot provenance",
    ):
        runner_builder.build_pipeline_runner(
            context,
            registry=fake_registry,
            ensure_providers_loaded_fn=lambda: None,
            register_all_pipelines_fn=lambda registry=None: None,
            get_settings_fn=lambda: SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(heartbeat_interval=30),
                test_mode=False,
            ),
            load_pipeline_config_fn=lambda _: SimpleNamespace(
                provider="chembl",
                entity_type="activity",
                version="2.0.0",
                maintenance=SimpleNamespace(
                    auto_vacuum=False,
                    vacuum_retention_days=7,
                ),
                input_filter=SimpleNamespace(),
                business_primary_keys=["activity_id"],
                technical_primary_key="entity_id",
            ),
            build_observability_bundle_fn=lambda **_: _namespace_observability(
                SimpleNamespace(info=lambda *_, **__: None),
            ),
            assemble_vacuum_settings_fn=lambda **_: "vacuum",
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental",
                limit=25,
                exact_replay=True,
            ),
            assemble_filter_config_fn=lambda **_: None,
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(empty_bronze_root),
                bronze_date="2026-01-01",
            ),
        )

    assert fake_factory.kwargs is None


def test_build_pipeline_runner_keeps_snapshot_backed_execution_identity_stable_across_repeated_exact_replays(
    tmp_path: Path,
) -> None:
    """Repeated exact replays over the same snapshots should keep one canonical identity."""
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")
    (bronze_day / "batch_2026-01-01_extra.jsonl.zst").write_bytes(b"snapshot-bytes-2")

    def _build_context() -> SimpleNamespace:
        return SimpleNamespace(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            log_level="INFO",
            vacuum=None,
            run_type="incremental",
            resume=False,
            limit=100,
            query=None,
            dry_run=False,
            skip_gold=False,
            start_offset=None,
            exact_replay=True,
            input_filter=SimpleNamespace(enabled=False),
        )

    def _build_runner_once() -> dict[str, object]:
        fake_factory = _FakeFactory()
        fake_registry = _FakeRegistry(factory=fake_factory)
        runner_builder.build_pipeline_runner(
            _build_context(),
            registry=fake_registry,
            ensure_providers_loaded_fn=lambda: None,
            register_all_pipelines_fn=lambda registry=None: None,
            get_settings_fn=lambda: SimpleNamespace(
                data_dir=str(tmp_path),
                pipeline=SimpleNamespace(heartbeat_interval=30),
                test_mode=False,
            ),
            load_pipeline_config_fn=lambda _: SimpleNamespace(
                provider="chembl",
                entity_type="activity",
                version="2.0.0",
                maintenance={"retain_days": 7},
                input_filter=SimpleNamespace(),
                business_primary_keys=["activity_id"],
                technical_primary_key="entity_id",
            ),
            build_observability_bundle_fn=lambda **_: _namespace_observability(
                SimpleNamespace(info=lambda *_, **__: None),
            ),
            assemble_vacuum_settings_fn=lambda **_: "vacuum",
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental",
                limit=100,
                exact_replay=True,
            ),
            assemble_filter_config_fn=lambda **_: None,
            assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
                enabled=True,
                bronze_path=str(bronze_root),
                bronze_date="2026-01-01",
            ),
        )
        manifest_id = fake_factory.kwargs["manifest_id"]
        manifest_path = (
            tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
        )
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    first_manifest = _build_runner_once()
    second_manifest = _build_runner_once()

    assert first_manifest["manifest_id"] != second_manifest["manifest_id"]
    assert first_manifest["run_id"] != second_manifest["run_id"]
    assert (
        first_manifest["execution_fingerprint"]
        == second_manifest["execution_fingerprint"]
    )
    assert first_manifest["replay_capability"] == "exact_replay_supported"
    assert second_manifest["replay_capability"] == "exact_replay_supported"
    assert first_manifest["source_refs"] == second_manifest["source_refs"]


def test_build_pipeline_runner_persists_resume_launch_context_when_resume_enabled(
    tmp_path: Path,
) -> None:
    """Resume requests should still persist manifest + ledger control-plane state."""
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(resume=True, limit=25, query="status=active")

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
    launch_context = payload["launch_context"]
    assert isinstance(launch_context, dict)
    assert launch_context["resume"] is True
    assert payload["replay_capability"] == "resume_only"
    assert launch_context["query"] == "status=active"
    assert launch_context["pipeline_name"] == "chembl_activity"

    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    assert ledger_path.exists()
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert ledger_payload["manifest_id"] == manifest_id
    assert ledger_payload["event_type"] == "manifest_created"


def test_build_pipeline_runner_aborts_before_factory_create_when_manifest_persistence_fails(
    tmp_path: Path,
) -> None:
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(limit=25)

    with (
        patch(
            "bioetl.composition.runtime_builders.run_manifest_builder.FileRunManifestStore.save",
            side_effect=OSError("manifest write failed"),
        ),
        pytest.raises(OSError, match="manifest write failed"),
    ):
        _call_build_pipeline_runner(
            context,
            registry=fake_registry,
            settings=_build_settings(data_dir=str(tmp_path)),
            pipeline_config=_build_pipeline_config(
                maintenance=SimpleNamespace(
                    auto_vacuum=False,
                    vacuum_retention_days=7,
                ),
            ),
            assemble_vacuum_settings_fn=lambda **_: "vacuum",
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental",
                limit=25,
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_pipeline_runner_binds_manifest_id_into_observability_bundle(
    tmp_path: Path,
) -> None:
    """Builder should enrich bundle logger context once manifest_id exists."""
    fake_factory, fake_registry = _build_factory_registry()
    base_logger = MagicMock()
    bound_logger = MagicMock()
    base_logger.bind.return_value = bound_logger
    bundle = ObservabilityBundle(
        logger=base_logger,
        metrics=MagicMock(),
        tracer=NoOpTracing(),
    )

    context = _build_context(limit=25)

    _call_build_pipeline_runner(
        context,
        registry=fake_registry,
        settings=_build_settings(data_dir=str(tmp_path)),
        pipeline_config=_build_pipeline_config(),
        build_observability_bundle_fn=lambda **_: bundle,
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
    )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    base_logger.bind.assert_called_once_with(manifest_id=manifest_id)
    assert fake_factory.kwargs["observability"].logger is bound_logger


def test_build_pipeline_runner_binds_manifest_id_into_namespace_logger(
    tmp_path: Path,
) -> None:
    """Builder should support lightweight namespace observability doubles."""
    fake_factory, fake_registry = _build_factory_registry()
    base_logger = MagicMock()
    bound_logger = MagicMock()
    base_logger.bind.return_value = bound_logger
    observability = _namespace_observability(base_logger)

    context = _build_context(limit=25)

    _call_build_pipeline_runner(
        context,
        registry=fake_registry,
        settings=_build_settings(data_dir=str(tmp_path)),
        pipeline_config=_build_pipeline_config(),
        build_observability_bundle_fn=lambda **_: observability,
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
    )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    base_logger.bind.assert_called_once_with(manifest_id=manifest_id)
    assert fake_factory.kwargs["observability"].logger is bound_logger


def test_build_pipeline_runner_requires_manifest_control_plane_when_manifest_disabled(
    tmp_path: Path,
) -> None:
    """Builder should fail closed when manifest rollout is disabled."""
    fake_factory, fake_registry = _build_factory_registry()
    context = _build_context(limit=25)

    with pytest.raises(
        RuntimeError,
        match="Pipeline execution requires run manifests",
    ):
        _call_build_pipeline_runner(
            context,
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=False,
                    run_ledger_enabled=False,
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_pipeline_runner_can_disable_ledger_while_keeping_manifest(
    tmp_path: Path,
) -> None:
    """Manifest should still persist when ledger rollout is explicitly disabled."""
    fake_factory, fake_registry = _build_factory_registry()

    _call_build_pipeline_runner(
        _build_context(limit=25),
        registry=fake_registry,
        settings=_build_settings(
            data_dir=str(tmp_path),
            control_plane=SimpleNamespace(
                run_manifest_enabled=True,
                run_ledger_enabled=False,
            ),
        ),
        pipeline_config=_build_pipeline_config(),
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
    )

    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    assert fake_factory.runner.attached_run_ledger_service is None
    assert (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    ).exists()
    assert not (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    ).exists()


def test_build_pipeline_runner_requires_ledger_for_forensic_grade_profile(
    tmp_path: Path,
) -> None:
    """Forensic-grade runtime profile must fail closed when ledger is disabled."""
    _, fake_registry = _build_factory_registry()

    with pytest.raises(
        RuntimeError,
        match="required persistence profile 'forensic_grade'",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=False,
                    required_persistence_profile="forensic_grade",
                ),
            ),
            pipeline_config=_build_pipeline_config(),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )


def test_build_pipeline_runner_requires_lineage_sidecars_for_forensic_grade_profile(
    tmp_path: Path,
) -> None:
    """Forensic-grade profile must fail when active sink layers skip metadata."""
    _, fake_registry = _build_factory_registry()

    with pytest.raises(
        RuntimeError,
        match="metadata sidecars / lineage persistence for active layers",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="forensic_grade",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=False),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=False),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )


def test_build_pipeline_runner_requires_exact_replay_capability_for_replay_ready_profile(
    tmp_path: Path,
) -> None:
    """Replay-ready profile must fail when the run has no immutable snapshots."""
    fake_factory, fake_registry = _build_factory_registry()

    with pytest.raises(
        RuntimeError,
        match="immutable input snapshots and exact replay capability are not available",
    ):
        _call_build_pipeline_runner(
            _build_context(limit=25, exact_replay=False),
            registry=fake_registry,
            settings=_build_settings(
                data_dir=str(tmp_path),
                control_plane=SimpleNamespace(
                    run_manifest_enabled=True,
                    run_ledger_enabled=True,
                    required_persistence_profile="replay_ready",
                ),
            ),
            pipeline_config=_build_pipeline_config(
                sink={
                    "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                    "silver": SimpleNamespace(enabled=True, save_metadata=True),
                    "gold": SimpleNamespace(enabled=True, save_metadata=True),
                },
            ),
            assemble_runtime_config_fn=lambda **_: SimpleNamespace(
                run_type="incremental"
            ),
        )

    assert fake_factory.kwargs is None
    assert not (tmp_path / "output" / "control" / "run_manifest").exists()
    assert not (tmp_path / "output" / "control" / "run_ledger").exists()


def test_build_pipeline_runner_allows_forensic_grade_with_exact_replay_and_sidecars(
    tmp_path: Path,
) -> None:
    """Forensic-grade profile should succeed when replay and sidecar surfaces exist."""
    fake_factory, fake_registry = _build_factory_registry()
    bronze_root = tmp_path / "bronze-cache"
    bronze_day = bronze_root / "2026-01-01"
    bronze_day.mkdir(parents=True)
    (bronze_day / "batch_2026-01-01_demo.jsonl.zst").write_bytes(b"snapshot-bytes")

    result = _call_build_pipeline_runner(
        _build_context(limit=25, exact_replay=True),
        registry=fake_registry,
        settings=_build_settings(
            data_dir=str(tmp_path),
            control_plane=SimpleNamespace(
                run_manifest_enabled=True,
                run_ledger_enabled=True,
                required_persistence_profile="forensic_grade",
            ),
        ),
        pipeline_config=_build_pipeline_config(
            sink={
                "bronze": SimpleNamespace(enabled=True, save_metadata=True),
                "silver": SimpleNamespace(enabled=True, save_metadata=True),
                "gold": SimpleNamespace(enabled=True, save_metadata=True),
            },
        ),
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(
            enabled=True,
            bronze_path=str(bronze_root),
            bronze_date="2026-01-01",
        ),
    )

    assert result == "runner-instance"
    assert isinstance(fake_factory.kwargs, dict)
    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    assert fake_factory.runner.attached_run_ledger_service is not None

    manifest_path = (
        tmp_path / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["launch_context"]["required_persistence_profile"] == (
        "forensic_grade"
    )
    assert payload["replay_capability"] == "exact_replay_supported"


def test_build_pipeline_runner_attaches_artifact_recorder_to_metadata_writers(
    tmp_path: Path,
) -> None:
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    top_writer = _RecorderAwareMetadataWriter()
    bronze_writer = _RecorderAwareMetadataWriter()
    silver_writer = _RecorderAwareMetadataWriter()
    gold_writer = _RecorderAwareMetadataWriter()
    fake_factory.runner.services = SimpleNamespace(
        metadata_writer=top_writer,
        storage=SimpleNamespace(
            bronze=SimpleNamespace(_metadata_writer=bronze_writer),
            silver=SimpleNamespace(_metadata_writer=silver_writer),
            gold=SimpleNamespace(_metadata_writer=gold_writer),
        ),
    )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=25,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        input_filter=SimpleNamespace(enabled=False),
    )

    runner_builder.build_pipeline_runner(
        context,
        registry=fake_registry,
        ensure_providers_loaded_fn=lambda: None,
        register_all_pipelines_fn=lambda registry=None: None,
        get_settings_fn=lambda: SimpleNamespace(
            data_dir=str(tmp_path),
            pipeline=SimpleNamespace(heartbeat_interval=30),
            test_mode=False,
        ),
        load_pipeline_config_fn=lambda _: SimpleNamespace(
            provider="chembl",
            entity_type="activity",
            version="2.0.0",
            maintenance=None,
            input_filter=SimpleNamespace(),
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
        ),
        build_observability_bundle_fn=lambda **_: _namespace_observability(
            SimpleNamespace(info=lambda *_, **__: None),
        ),
        assemble_vacuum_settings_fn=lambda **_: None,
        assemble_runtime_config_fn=lambda **_: SimpleNamespace(run_type="incremental"),
        assemble_filter_config_fn=lambda **_: None,
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(enabled=False),
    )

    for writer in (top_writer, bronze_writer, silver_writer, gold_writer):
        assert writer.recorder is not None

    manifest_id = fake_factory.kwargs["manifest_id"]
    assert isinstance(manifest_id, str)
    silver_writer.recorder(
        "silver",
        SILVER_OUTPUT_PATH,
        {
            "metadata_path": SILVER_METADATA_PATH,
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-1",
        },
    )
    ledger_path = (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
    )
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    ledger_payload = json.loads(lines[1])
    assert ledger_payload["event_type"] == "artifact_published"
    assert ledger_payload["stage"] == "silver"
    assert ledger_payload["dataset_ref"] == "silver:chembl.activity@1"
    assert ledger_payload["lineage_fragment_id"] == "silver:fragment-1"


def test_runner_builder_uses_runtime_config_access_seam() -> None:
    """runner_builder should route runtime config access through the local seam."""
    source = Path(
        "src/bioetl/composition/runtime_builders/runner_builder.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.composition.runtime_builders.config_access" in imported_modules, (
        "runner_builder must use the runtime config_access seam."
    )
    assert "bioetl.infrastructure.config.pipeline_config_api" not in imported_modules, (
        "runner_builder must not import pipeline_config_api directly."
    )
    assert (
        "bioetl.infrastructure.config.source_config_loader" not in imported_modules
    ), "runner_builder must not import source_config_loader directly."


def test_runner_builder_does_not_expose_legacy_wrapper_patch_points() -> None:
    """Legacy monkeypatch wrappers should stay removed from runner_builder."""
    for attr_name in (
        "VacuumSettings",
        "_assemble_vacuum_settings",
        "_assemble_runtime_config",
        "_assemble_filter_config",
        "_assemble_cached_bronze_context",
        "_build_observability_bundle",
        "_validate_pk_contract",
        "_resolve_health_check_mode",
        "_resolve_filter_batch_size",
    ):
        assert not hasattr(runner_builder, attr_name)


def test_inputs_resolver_uses_explicit_resolved_vacuumsettings_name() -> None:
    """Runtime builder helpers should not expose the old VacuumSettings alias."""
    assert hasattr(inputs_resolver, "ResolvedVacuumSettings")
    assert not hasattr(inputs_resolver, "VacuumSettings")


def test_build_pipeline_runner_forces_probe_mode_in_test_mode() -> None:
    """Builder must pass probe health mode when settings.test_mode is enabled."""
    _, fake_registry = _build_factory_registry()
    captured: dict[str, object] = {}

    def assemble_runtime_config_fn(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return _runtime_config_stub()

    _call_build_pipeline_runner(
        _build_context(vacuum=SimpleNamespace(enabled=None, retention_days=7)),
        registry=fake_registry,
        settings=_build_settings(health_check_mode="strict", test_mode=True),
        pipeline_config=_build_pipeline_config(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            batch_size=100,
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=assemble_runtime_config_fn,
    )

    assert captured["health_check_mode"] == "probe"


def test_build_pipeline_runner_uses_configured_mode_outside_test_mode() -> None:
    """Builder must pass configured health mode when test_mode is disabled."""
    _, fake_registry = _build_factory_registry()
    captured: dict[str, object] = {}

    def assemble_runtime_config_fn(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return _runtime_config_stub()

    _call_build_pipeline_runner(
        _build_context(vacuum=SimpleNamespace(enabled=None, retention_days=7)),
        registry=fake_registry,
        settings=_build_settings(health_check_mode="probe", test_mode=False),
        pipeline_config=_build_pipeline_config(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            batch_size=100,
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=assemble_runtime_config_fn,
    )

    assert captured["health_check_mode"] == "probe"


def test_build_pipeline_runner_forces_skip_gold_when_sink_disabled() -> None:
    """Builder should disable Gold writes when pipeline YAML disables Gold sink."""
    fake_factory, fake_registry = _build_factory_registry()

    _call_build_pipeline_runner(
        _build_context(vacuum=SimpleNamespace(enabled=None, retention_days=7)),
        registry=fake_registry,
        settings=_build_settings(health_check_mode="strict"),
        pipeline_config=_build_pipeline_config(
            pipeline_name="chembl_activity",
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            batch_size=100,
            sink={"gold": SimpleNamespace(enabled=False)},
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=runner_builder.assemble_runtime_config,
    )

    assert fake_factory.kwargs is not None
    runtime = fake_factory.kwargs["runtime"]
    assert runtime.skip_gold is True


def test_assemble_filter_config_passes_cli_overrides_when_enabled() -> None:
    ctx = SimpleNamespace(
        ignore_yaml_filter=False,
        input_filter=SimpleNamespace(
            enabled=True,
            source_path="ids.csv",
            column_name="compound_id",
            filter_field="compound_id",
            fallback_column="legacy_id",
            filter_ids=["1", "2"],
            fallback_mapping={"1": "A"},
            multi_filter_ids={"compound_id": ["1"]},
            valid_combinations=[{"compound_id": "1"}],
        ),
    )
    sentinel = object()

    with patch.object(
        inputs_resolver.FilterConfigBuilder, "build", return_value=sentinel
    ) as mock_build:
        result = inputs_resolver.assemble_filter_config(
            yaml_filter=SimpleNamespace(),
            ctx=ctx,
            test_mode=False,
        )

    assert result is sentinel
    assert mock_build.call_args.kwargs["cli_csv"] == "ids.csv"
    assert mock_build.call_args.kwargs["test_mode"] is False


@pytest.mark.unit
def test_canonical_observability_builder_uses_noop_when_disabled() -> None:
    logger = MagicMock()
    tracer = MagicMock()
    metrics = MagicMock()
    logger_factory = MagicMock(return_value=logger)
    noop_tracing_factory = MagicMock(return_value=tracer)
    noop_metrics_factory = MagicMock(return_value=metrics)

    result = observability_builder.build_observability_bundle(
        pipeline="chembl_activity",
        run_id=uuid4(),
        settings=SimpleNamespace(
            env="dev",
            observability=SimpleNamespace(
                tracing_enabled=False,
                metrics_enabled=False,
                dq_monitor_enabled=False,
                allow_noop_observability_in_prod=False,
            ),
        ),
        logger_factory=logger_factory,
        noop_tracing_factory=noop_tracing_factory,
        noop_metrics_factory=noop_metrics_factory,
    )

    assert result.logger is logger
    assert result.tracer is tracer
    assert result.metrics is metrics
    assert result.dq_monitor is None
    noop_metrics_factory.assert_called_once_with(warn_on_use=False)


@pytest.mark.unit
def test_canonical_observability_builder_configures_dq_monitor_thresholds() -> None:
    logger = MagicMock()
    tracer = MagicMock()
    metrics = MagicMock()
    dq_monitor = MagicMock()
    logger_factory = MagicMock(return_value=logger)
    tracer_factory = MagicMock(return_value=tracer)
    metrics_factory = MagicMock(return_value=metrics)
    dq_monitor_factory = MagicMock(return_value=dq_monitor)

    settings = SimpleNamespace(
        env="dev",
        observability=SimpleNamespace(
            tracing_enabled=True,
            metrics_enabled=True,
            dq_monitor_enabled=True,
            dq_baseline_window=20,
            dq_z_score_threshold=2.5,
            dq_min_baseline_samples=12,
            dq_error_rate_max=0.3,
            dq_quality_score_min=0.7,
            allow_noop_observability_in_prod=False,
        ),
    )

    result = observability_builder.build_observability_bundle(
        pipeline="chembl_activity",
        run_id=uuid4(),
        settings=settings,
        logger_factory=logger_factory,
        tracer_factory=tracer_factory,
        metrics_factory=metrics_factory,
        dq_monitor_factory=dq_monitor_factory,
    )

    assert result.logger is logger
    assert result.tracer is tracer
    assert result.metrics is metrics
    assert result.dq_monitor is dq_monitor
    assert dq_monitor.detector.min_baseline_samples == 12
    assert dq_monitor.detector.set_threshold.call_count == 2


def test_validate_pk_contract_requires_business_primary_keys() -> None:
    config = SimpleNamespace(
        business_primary_keys=[],
        technical_primary_key="entity_id",
    )

    with pytest.raises(ValueError, match="business_primary_keys must be non-empty"):
        inputs_resolver.validate_pk_contract(config)


def test_validate_pk_contract_ignores_legacy_attribute_when_present() -> None:
    config = SimpleNamespace(
        business_primary_keys=["entity_id"],
        primary_keys=["legacy_id"],
        technical_primary_key="entity_id",
    )

    inputs_resolver.validate_pk_contract(config)


def test_validate_pk_contract_requires_technical_primary_key() -> None:
    config = SimpleNamespace(
        business_primary_keys=["entity_id"],
        technical_primary_key="",
    )

    with pytest.raises(ValueError, match="technical_primary_key must be non-empty"):
        inputs_resolver.validate_pk_contract(config)
