"""Targeted unit coverage boosts for composition facades and runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest

from bioetl.composition import _services
from bioetl.composition import _workflow_services
from bioetl.composition import factories as factories_pkg
from bioetl.composition.bootstrap import cli as cli_bootstrap
from bioetl.composition.factories import __getattr__ as factories_getattr
from bioetl.composition.runtime_builders import (
    _exact_replay_cached_bronze_context as replay_context,
)
from bioetl.composition.runtime_builders import (
    _run_manifest_data_roots as data_roots,
)


pytestmark = pytest.mark.repo_backed


def _install_workflow_runner_service_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tmp_path: Path,
    created: dict[str, object],
) -> None:
    workflow_runner_module = ModuleType("workflow_runner_service")

    class _WorkflowRunnerService:
        def __init__(self, **kwargs):
            created["workflow_runner_service"] = kwargs

    workflow_runner_module.WorkflowRunnerService = _WorkflowRunnerService
    monkeypatch.setitem(
        sys.modules,
        "bioetl.application.services.workflow_runner_service",
        workflow_runner_module,
    )

    transform_service_module = ModuleType("workflow_transform_service")

    class _WorkflowTransformService:
        def __init__(self, **kwargs):
            created["transform_service"] = kwargs

    transform_service_module.WorkflowTransformService = _WorkflowTransformService
    monkeypatch.setitem(
        sys.modules,
        "bioetl.application.services.workflow_transform_service",
        transform_service_module,
    )

    transforms_module = ModuleType("workflow_transforms")
    transforms_module.WorkflowTransformRegistry = lambda: "transform_registry"
    monkeypatch.setitem(
        sys.modules,
        "bioetl.application.workflow.transforms",
        transforms_module,
    )

    builtins_module = ModuleType("workflow_transforms_builtins")
    builtins_module.register_builtin_workflow_transforms = (
        lambda registry, foreign_key_reconciliation_port: (
            "registered_registry",
            registry,
            foreign_key_reconciliation_port,
        )
    )
    monkeypatch.setitem(
        sys.modules,
        "bioetl.application.workflow.transforms.builtins",
        builtins_module,
    )

    observability_module = ModuleType("observability")
    observability_module.bootstrap_logger = (
        lambda name: SimpleNamespace(bind=lambda **kwargs: ("logger", name, kwargs))
    )
    monkeypatch.setitem(
        sys.modules,
        "bioetl.composition.bootstrap.runtime.observability",
        observability_module,
    )

    noop_module = ModuleType("noop")
    noop_module.create_noop_logger = lambda: "noop-logger"
    monkeypatch.setitem(
        sys.modules,
        "bioetl.composition.bootstrap.cli.noop",
        noop_module,
    )

    port_factories = ModuleType("port_factories")
    port_factories.create_metrics = lambda settings: "metrics"
    monkeypatch.setitem(
        sys.modules,
        "bioetl.composition.factories.services.port_factories",
        port_factories,
    )

    silver_writer_module = ModuleType("silver_writer")

    class _SilverWriter:
        def __init__(self, **kwargs):
            created["silver_writer"] = kwargs

    silver_writer_module.SilverWriter = _SilverWriter
    monkeypatch.setitem(
        sys.modules,
        "bioetl.infrastructure.storage.silver_writer",
        silver_writer_module,
    )

    quarantine_module = ModuleType("quarantine")
    quarantine_module.UnifiedQuarantineAdapter = lambda **kwargs: ("quarantine", kwargs)
    monkeypatch.setitem(
        sys.modules,
        "bioetl.infrastructure.quarantine",
        quarantine_module,
    )

    reconciliation_module = ModuleType("reconciliation")
    reconciliation_module.SilverForeignKeyReconciliationAdapter = (
        lambda **kwargs: ("reconciliation", kwargs)
    )
    monkeypatch.setitem(
        sys.modules,
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation",
        reconciliation_module,
    )

    monkeypatch.setattr(
        _workflow_services,
        "get_settings",
        lambda: SimpleNamespace(
            silver_path=tmp_path / "silver",
            quarantine_path=tmp_path / "quarantine",
            data_dir=tmp_path,
        ),
    )


def _install_workflow_execution_service_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    created: dict[str, object],
) -> None:
    execution_module = ModuleType("execution_service")

    class _WorkflowExecutionService:
        def __init__(self, **kwargs):
            created["execution_service"] = kwargs

    execution_module.WorkflowExecutionService = _WorkflowExecutionService
    monkeypatch.setitem(
        sys.modules,
        "bioetl.application.services.control_plane.workflow.execution_service",
        execution_module,
    )

    manifest_service_module = ModuleType("manifest_service")
    manifest_service_module.WorkflowManifestService = lambda **kwargs: (
        "manifest_service",
        kwargs,
    )
    monkeypatch.setitem(
        sys.modules,
        "bioetl.application.services.control_plane.workflow.manifest_service",
        manifest_service_module,
    )

    control_plane_module = ModuleType("control_plane")
    control_plane_module.FileWorkflowManifestStore = lambda **kwargs: (
        "manifest_store",
        kwargs,
    )
    control_plane_module.FileWorkflowLedgerStore = lambda **kwargs: (
        "ledger_store",
        kwargs,
    )
    control_plane_module.FileWorkflowExecutionStateStore = lambda **kwargs: (
        "state_store",
        kwargs,
    )
    monkeypatch.setitem(
        sys.modules,
        "bioetl.infrastructure.control_plane",
        control_plane_module,
    )

    time_module = ModuleType("time")
    time_module.SystemClock = lambda: "clock"
    monkeypatch.setitem(sys.modules, "bioetl.infrastructure.time", time_module)
    monkeypatch.setattr(
        _workflow_services,
        "get_workflow_runner_service",
        lambda registry=None: ("workflow_runner", registry),
    )
    monkeypatch.setattr(
        _workflow_services,
        "_get_workflow_memory_lock",
        lambda: "memory-lock",
    )


def test_factories_package_lazy_exports_and_unknown_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("fake_services")
    fake_module.BaseServicesFactory = object()
    fake_pipeline = ModuleType("fake_pipeline")
    fake_pipeline.__path__ = []  # type: ignore[attr-defined]
    fake_pipeline.create_pipeline_factory = mock.sentinel.pipeline_factory
    fake_assembler = ModuleType("fake_assembler")
    fake_assembler.create_pipeline_factory = mock.sentinel.pipeline_factory
    fake_registry = ModuleType("fake_registry")
    fake_registry.pubchem_compound_factory = mock.sentinel.pubchem_factory
    fake_pipeline.registry = fake_registry

    def _fake_import_module(name: str) -> ModuleType:
        mapping = {
            "bioetl.composition.factories.services.factory": fake_module,
        }
        return mapping[name]

    monkeypatch.setattr("bioetl.composition.factories.import_module", _fake_import_module)
    monkeypatch.setattr(factories_pkg, "pipeline", fake_pipeline, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "bioetl.composition.factories.pipeline", fake_pipeline)
    monkeypatch.setitem(
        __import__("sys").modules,
        "bioetl.composition.factories.pipeline.assembler",
        fake_assembler,
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "bioetl.composition.factories.pipeline.registry",
        fake_registry,
    )

    assert factories_getattr("BaseServicesFactory") is fake_module.BaseServicesFactory
    assert factories_getattr("create_pipeline_factory") is mock.sentinel.pipeline_factory
    assert factories_getattr("pubchem_compound_factory") is mock.sentinel.pubchem_factory
    with pytest.raises(AttributeError):
        factories_getattr("missing_export")


def test_cli_bootstrap_lazy_exports_and_unknown_attribute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_health = ModuleType("fake_health")
    fake_health.bootstrap_health_service = mock.sentinel.health_service

    monkeypatch.setattr(
        cli_bootstrap,
        "import_module",
        lambda name: fake_health
        if name == "bioetl.composition.bootstrap.cli.health"
        else (_ for _ in ()).throw(KeyError(name)),
    )

    assert cli_bootstrap.__getattr__("bootstrap_health_service") is mock.sentinel.health_service
    with pytest.raises(AttributeError):
        cli_bootstrap.__getattr__("missing")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.config_access.get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path),
    )
    store = cli_bootstrap.bootstrap_control_plane_lifecycle_store()
    assert store.base_path == tmp_path / "output" / "control"


def test_cli_bootstrap_adr_service_uses_filesystem_catalog() -> None:
    service = cli_bootstrap.bootstrap_adr_service()
    assert service.__class__.__name__ == "FilesystemAdrCatalog"


def test_services_facade_helpers_cover_lazy_resolution_and_workflow_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("fake_bootstrap")
    fake_module.bootstrap_metrics_service = lambda: mock.sentinel.metrics
    fake_module.bootstrap_checkpoint_service = lambda: mock.sentinel.checkpoint
    monkeypatch.setattr(_services, "import_module", lambda _: fake_module)

    assert _services.resolve_bootstrap_attr("bootstrap_metrics_service") is fake_module.bootstrap_metrics_service
    assert _services._invoke_bootstrap("bootstrap_checkpoint_service") is mock.sentinel.checkpoint
    with pytest.raises(AttributeError):
        _services.resolve_bootstrap_attr("missing_export")

    calls: list[tuple[object | None, str]] = []
    monkeypatch.setattr(
        _services,
        "_ensure_registrations",
        lambda registry=None, scope="pipelines": calls.append((registry, scope)),
    )
    monkeypatch.setattr(
        _services,
        "_invoke_bootstrap",
        lambda name, *args, **kwargs: (name, args, kwargs),
    )
    result = _services.get_metrics_service()
    assert result == ("bootstrap_metrics_service", (), {})
    assert calls[-1] == (None, "providers")

    monkeypatch.setattr(
        "bioetl.composition._workflow_services.get_workflow_runner_service",
        lambda registry=None: ("workflow_runner", registry),
    )
    assert _services.get_workflow_runner_service(registry="registry-1") == (
        "workflow_runner",
        "registry-1",
    )


def test_services_facade_wrappers_cover_provider_and_pipeline_entrypoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []
    pipeline_calls: list[object | None] = []
    bootstrap_calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(
        _services,
        "_ensure_provider_registrations",
        lambda: provider_calls.append("providers"),
    )
    monkeypatch.setattr(
        _services,
        "_ensure_pipeline_registrations",
        lambda registry=None: pipeline_calls.append(registry),
    )
    monkeypatch.setattr(
        _services,
        "_invoke_bootstrap",
        lambda name, *args, **kwargs: bootstrap_calls.append((name, args, kwargs))
        or (name, args, kwargs),
    )

    assert _services.get_checkpoint_service()[0] == "bootstrap_checkpoint_service"
    assert _services.get_audit_service()[0] == "bootstrap_audit_inspection_service"
    assert _services.get_quarantine_service()[0] == "bootstrap_quarantine_service"
    assert _services.get_bronze_cleanup_service()[0] == "bootstrap_bronze_cleanup_service"
    assert _services.get_vacuum_service()[0] == "bootstrap_vacuum_service"
    assert _services.get_export_service()[0] == "bootstrap_export_service"
    assert _services.get_lock_service()[0] == "bootstrap_lock_service"
    assert _services.get_pipeline_runner_service(registry="registry-2")[2] == {
        "registry": "registry-2"
    }
    assert _services.get_config_service()[0] == "bootstrap_config_service"
    assert (
        _services.get_contract_migration_service()[0]
        == "bootstrap_contract_migration_service"
    )
    assert _services.get_run_manifest_service()[0] == "bootstrap_run_manifest_service"
    assert (
        _services.get_forensic_run_diff_service()[0]
        == "bootstrap_forensic_run_diff_service"
    )
    assert (
        _services.get_historical_replay_corpus_service()[0]
        == "bootstrap_historical_replay_corpus_service"
    )
    assert (
        _services.get_historical_replay_closure_service()[0]
        == "bootstrap_historical_replay_closure_service"
    )
    assert (
        _services.get_historical_replay_universe_service()[0]
        == "bootstrap_historical_replay_universe_service"
    )
    assert _services.get_lineage_service()[0] == "bootstrap_lineage_service"
    assert _services.get_health_service()[0] == "bootstrap_health_service"
    assert (
        _services.get_observability_workflow_service()[0]
        == "bootstrap_observability_workflow_service"
    )
    assert (
        _services.get_health_server_dependencies()[0]
        == "bootstrap_health_server_dependencies"
    )
    assert _services.get_metrics_service()[0] == "bootstrap_metrics_service"
    assert _services.get_adr_service()[0] == "bootstrap_adr_service"
    assert _services.get_quarantine_port()[0] == "bootstrap_quarantine_adapter"
    assert provider_calls
    assert pipeline_calls == ["registry-2"]
    assert any(name == "bootstrap_metrics_service" for name, _, _ in bootstrap_calls)


def test_cleanup_bronze_awaits_protocol_service(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, bool]] = []

    class _CleanupService:
        async def cleanup(self, *, retention_days: int, dry_run: bool) -> dict[str, int]:
            calls.append((retention_days, dry_run))
            return {"removed": 3}

    monkeypatch.setattr(
        _services,
        "get_bronze_cleanup_service",
        lambda: _CleanupService(),
    )
    result = __import__("asyncio").run(
        _services.cleanup_bronze(retention_days=30, dry_run=True)
    )
    assert result == {"removed": 3}
    assert calls == [(30, True)]


def test_workflow_services_helpers_cover_loading_and_singleton_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.config.workflow_config_api.load_workflow_config",
        lambda name, configs_root: {"name": name, "configs_root": str(configs_root)},
    )
    monkeypatch.setattr(
        _workflow_services,
        "resolve_configs_root",
        lambda: tmp_path / "configs",
    )
    assert _workflow_services.load_workflow_config("chembl_baseline") == {
        "name": "chembl_baseline",
        "configs_root": str(tmp_path / "configs"),
    }

    fake_lock = object()
    monkeypatch.setattr(
        "bioetl.infrastructure.locking.MemoryLock",
        lambda: fake_lock,
    )
    _workflow_services._WORKFLOW_MEMORY_LOCK = None
    assert _workflow_services._get_workflow_memory_lock() is fake_lock
    assert _workflow_services._get_workflow_memory_lock() is fake_lock


def test_workflow_services_cover_default_factory_and_runner_service_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_runtime_runner = ModuleType("fake_runtime_runner")
    fake_runtime_runner.bootstrap_pipeline_runner_service = (
        lambda registry=None: ("pipeline_runner", registry)
    )
    monkeypatch.setitem(
        sys.modules,
        "bioetl.composition.bootstrap.runtime.runner",
        fake_runtime_runner,
    )
    assert _workflow_services._default_pipeline_runner_service_factory("registry-x") == (
        "pipeline_runner",
        "registry-x",
    )

    created: dict[str, object] = {}
    _install_workflow_runner_service_dependencies(
        monkeypatch,
        tmp_path=tmp_path,
        created=created,
    )

    _workflow_services.get_workflow_runner_service(registry="registry-y")
    assert created["workflow_runner_service"]["pipeline_runner"] == (
        "pipeline_runner",
        "registry-y",
    )
    assert created["transform_service"]["metrics"] == "metrics"
    assert created["silver_writer"]["pipeline_name"] == "workflow_transforms"


def test_workflow_services_cover_execution_service_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created: dict[str, object] = {}
    _install_workflow_runner_service_dependencies(
        monkeypatch,
        tmp_path=tmp_path,
        created=created,
    )
    _install_workflow_execution_service_dependencies(
        monkeypatch,
        created=created,
    )

    _workflow_services.get_workflow_execution_service(registry="registry-z")
    assert created["execution_service"]["workflow_runner"] == (
        "workflow_runner",
        "registry-z",
    )
    assert created["execution_service"]["workflow_lock_port"] == "memory-lock"


def test_workflow_inspection_service_uses_control_plane_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        _workflow_services,
        "get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path),
    )
    monkeypatch.setattr(
        "bioetl.composition.factories.services.port_factories.create_metrics",
        lambda settings: mock.sentinel.metrics,
    )

    service = _workflow_services.get_workflow_inspection_service()

    assert service.manifest_port.base_path == tmp_path / "output" / "control" / "workflow_manifest"
    assert service.ledger_port.base_path == tmp_path / "output" / "control" / "workflow_ledger"
    assert service.state_port.base_path == tmp_path / "output" / "control" / "workflow_state"


def test_run_manifest_data_root_helpers_cover_explicit_and_fallback_modes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert data_roots.is_explicit_data_root_configured(
        SimpleNamespace(data_dir="/var/bioetl")
    )
    assert data_roots.resolve_data_root_mode(SimpleNamespace(data_dir="/var/bioetl")) == "explicit"

    monkeypatch.setattr(data_roots.Path, "mkdir", lambda self, parents=True, exist_ok=True: None)
    monkeypatch.setattr(data_roots.os, "access", lambda path, mode: True)
    assert data_roots.resolve_data_root_mode(SimpleNamespace(data_dir=None)) == "repo_default"

    monkeypatch.setattr(
        data_roots,
        "_prepare_private_runtime_dir",
        lambda path: (_ for _ in ()).throw(OSError("no-cache")) if "bioetl-data" in str(path) else path,
    )
    assert data_roots._private_fallback_data_root_mode() == "tmp"
    assert data_roots._artifact_path_string(Path("a\\b")) == "a\\b"

    monkeypatch.setattr(
        data_roots.Path,
        "mkdir",
        lambda self, parents=True, exist_ok=True: (_ for _ in ()).throw(OSError("readonly")),
    )
    monkeypatch.setattr(data_roots, "_private_fallback_data_root_mode", lambda: "private_cache")
    assert data_roots.resolve_data_root_mode(SimpleNamespace(data_dir=None)) == "private_cache"

    monkeypatch.setattr(data_roots.Path, "mkdir", lambda self, parents=True, exist_ok=True: None)
    monkeypatch.setattr(data_roots.os, "access", lambda path, mode: False)
    monkeypatch.setattr(data_roots, "_private_fallback_data_root_mode", lambda: "tmp")
    assert data_roots.resolve_data_root_mode(SimpleNamespace(data_dir=None)) == "tmp"


def test_run_manifest_data_root_helpers_cover_planned_artifacts_and_private_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared: list[Path] = []
    monkeypatch.setattr(
        data_roots,
        "_prepare_private_runtime_dir",
        lambda path: prepared.append(path) or path,
    )
    result = data_roots._private_fallback_data_root()
    assert prepared
    assert result == prepared[0]

    artifacts = data_roots.build_planned_artifacts(
        settings=SimpleNamespace(data_dir=tmp_path),
        provider="chembl",
        entity="activity",
        run_id="run-1",
        pipeline_name="chembl_activity",
        workflow_id="wf-1",
        debug_export_root="exports/debug",
    )
    assert any(artifact.layer == "debug_export" for artifact in artifacts)
    assert data_roots.control_plane_root(SimpleNamespace(data_dir=tmp_path), "run_manifest") == (
        tmp_path / "output" / "control" / "run_manifest"
    )
    relative_artifacts = data_roots.build_planned_artifacts(
        settings=SimpleNamespace(data_dir=None),
        provider="chembl",
        entity="activity",
        run_id=None,
        pipeline_name=None,
        debug_export_root="exports/debug",
    )
    assert all(artifact.layer != "debug_export" for artifact in relative_artifacts)


def test_run_manifest_data_root_helpers_cover_resolve_and_private_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_private_fallback = data_roots._private_fallback_data_root
    original_prepare_private_runtime_dir = data_roots._prepare_private_runtime_dir
    assert data_roots._resolve_data_root(SimpleNamespace(data_dir="/explicit")) == Path(
        "/explicit"
    )

    monkeypatch.setattr(
        data_roots.Path,
        "mkdir",
        lambda self, parents=True, exist_ok=True: (_ for _ in ()).throw(OSError("readonly")),
    )
    monkeypatch.setattr(data_roots, "_private_fallback_data_root", lambda: Path("/tmp/private"))
    assert data_roots._resolve_data_root(SimpleNamespace(data_dir=None)) == Path("/tmp/private")

    monkeypatch.setattr(data_roots.Path, "mkdir", lambda self, parents=True, exist_ok=True: None)
    monkeypatch.setattr(data_roots.os, "access", lambda path, mode: False)
    assert data_roots._resolve_data_root(SimpleNamespace(data_dir=None)) == Path("/tmp/private")

    monkeypatch.setattr(data_roots, "_private_fallback_data_root", original_private_fallback)
    prepared: list[Path] = []
    monkeypatch.setattr(
        data_roots,
        "_prepare_private_runtime_dir",
        lambda path: prepared.append(path) or path,
    )
    resolved = data_roots._private_fallback_data_root()
    assert resolved == prepared[0]
    assert ".cache" in str(prepared[0])

    monkeypatch.setattr(
        data_roots,
        "_prepare_private_runtime_dir",
        lambda path: (_ for _ in ()).throw(OSError("fallback"))
        if ".cache" in str(path)
        else path,
    )
    tmp_fallback = data_roots._private_fallback_data_root()
    assert "bioetl-data-" in str(tmp_fallback)

    chmod_calls: list[tuple[Path, int]] = []
    monkeypatch.setattr(
        data_roots,
        "_prepare_private_runtime_dir",
        original_prepare_private_runtime_dir,
    )
    monkeypatch.setattr(data_roots.Path, "mkdir", lambda self, parents=True, exist_ok=True, mode=0o700: None)
    monkeypatch.setattr(
        data_roots.Path,
        "chmod",
        lambda self, mode: chmod_calls.append((self, mode)),
    )
    prepared_path = data_roots._prepare_private_runtime_dir(Path("/tmp/private-cache"))
    assert prepared_path == Path("/tmp/private-cache")
    assert chmod_calls == [(Path("/tmp/private-cache"), 0o700)]


@dataclass
class _ContextDataclass:
    cached_bronze: object | None = None


def test_exact_replay_helper_functions_cover_binding_and_uri_validation() -> None:
    cached = SimpleNamespace(enabled=True)
    dataclass_ctx = _ContextDataclass()
    updated = replay_context.bind_cached_bronze_context(dataclass_ctx, cached)
    assert updated.cached_bronze is cached

    namespace_ctx = SimpleNamespace(cached_bronze=None, pipeline_name="chembl_activity")
    rebound = replay_context.bind_cached_bronze_context(namespace_ctx, cached)
    assert rebound.cached_bronze is cached

    assert replay_context._optional_text("  value  ") == "value"
    assert replay_context._optional_text("   ") is None
    assert replay_context._extract_bronze_date("bronze://2026-01-01/batch.json") == "2026-01-01"
    with pytest.raises(RuntimeError, match="must use bronze://"):
        replay_context._extract_bronze_date("file:///tmp/batch.json")
    with pytest.raises(RuntimeError, match="missing Bronze date"):
        replay_context._extract_bronze_date("bronze://")


def test_exact_replay_collect_ledger_bronze_dates_covers_mismatch_and_source_refs() -> None:
    manifest = SimpleNamespace(
        provider="chembl",
        entity="activity",
        source_refs=(
            SimpleNamespace(
                provider="chembl",
                entity="activity",
                input_snapshots=(
                    SimpleNamespace(immutable_uri="bronze://2026-02-01/batch.json"),
                ),
            ),
        ),
    )
    entries = (
        SimpleNamespace(
            event_type="unrelated_event",
            details={},
        ),
    )
    assert replay_context._collect_ledger_bronze_dates(
        manifest=manifest,
        ledger_entries=entries,
    ) == ("2026-02-01",)

    mismatch_entries = (
        SimpleNamespace(
            event_type=replay_context.INPUT_SNAPSHOT_PUBLISHED_EVENT,
            details={"provider": "pubchem", "entity": "activity"},
        ),
    )
    with pytest.raises(RuntimeError, match="provider mismatch"):
        replay_context._collect_ledger_bronze_dates(
            manifest=manifest,
            ledger_entries=mismatch_entries,
        )
    entity_mismatch_entries = (
        SimpleNamespace(
            event_type=replay_context.INPUT_SNAPSHOT_PUBLISHED_EVENT,
            details={"provider": "chembl", "entity": "assay"},
        ),
    )
    with pytest.raises(RuntimeError, match="entity mismatch"):
        replay_context._collect_ledger_bronze_dates(
            manifest=manifest,
            ledger_entries=entity_mismatch_entries,
        )
    mixed_source_ref_manifest = SimpleNamespace(
        provider="chembl",
        entity="activity",
        source_refs=(
            SimpleNamespace(
                provider="pubchem",
                entity="activity",
                input_snapshots=(
                    SimpleNamespace(immutable_uri="bronze://2026-02-01/batch.json"),
                ),
            ),
        ),
    )
    with pytest.raises(RuntimeError, match="mixed provider/entity"):
        replay_context._collect_ledger_bronze_dates(
            manifest=mixed_source_ref_manifest,
            ledger_entries=(),
        )


def test_exact_replay_resolution_helpers_cover_parent_lookup_and_date_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_resolve_parent_manifest = replay_context._resolve_replay_parent_manifest
    original_resolve_parent_bronze_date = replay_context._resolve_parent_bronze_date
    settings = SimpleNamespace(
        bronze_path="/tmp/bronze",
        data_dir="/tmp/data",
    )
    manifest = SimpleNamespace(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        manifest_id="manifest-1",
        source_refs=(),
        run_id="run-1",
    )

    monkeypatch.setattr(
        replay_context,
        "_resolve_replay_parent_manifest",
        lambda ctx, settings: manifest,
    )
    monkeypatch.setattr(
        replay_context,
        "_resolve_parent_bronze_date",
        lambda manifest, settings: "2026-02-01",
    )
    resolved = replay_context.resolve_exact_replay_cached_bronze_context(
        ctx=SimpleNamespace(
            exact_replay=True,
            pipeline_name="chembl_activity",
        ),
        settings=settings,
        cached_bronze=SimpleNamespace(enabled=False),
    )
    assert resolved.bronze_path.endswith("/chembl/activity")
    assert resolved.bronze_date == "2026-02-01"

    unchanged = replay_context.resolve_exact_replay_cached_bronze_context(
        ctx=SimpleNamespace(exact_replay=False, pipeline_name="chembl_activity"),
        settings=settings,
        cached_bronze=SimpleNamespace(enabled=False),
    )
    assert unchanged.enabled is False

    with pytest.raises(RuntimeError, match="pipeline mismatch"):
        replay_context.resolve_exact_replay_cached_bronze_context(
            ctx=SimpleNamespace(exact_replay=True, pipeline_name="pubchem_activity"),
            settings=settings,
            cached_bronze=SimpleNamespace(enabled=False),
        )

    monkeypatch.setattr(
        replay_context,
        "FileRunManifestStore",
        lambda base_path: SimpleNamespace(
            get=lambda manifest_id: None,
            get_by_run_id=lambda run_id: None,
        ),
    )
    monkeypatch.setattr(replay_context, "control_plane_root", lambda settings, leaf: Path("/tmp") / leaf)
    with pytest.raises(RuntimeError, match="manifest_id 'manifest-404'"):
        original_resolve_parent_manifest(
            ctx=SimpleNamespace(
                replay_of_manifest_id="manifest-404",
                replay_of_run_id=None,
            ),
            settings=settings,
        )
    with pytest.raises(RuntimeError, match="requires replay_of_run_id"):
        original_resolve_parent_manifest(
            ctx=SimpleNamespace(
                replay_of_manifest_id=None,
                replay_of_run_id=None,
            ),
            settings=settings,
        )
    with pytest.raises(RuntimeError, match="valid UUID"):
        original_resolve_parent_manifest(
            ctx=SimpleNamespace(
                replay_of_manifest_id=None,
                replay_of_run_id="bad-uuid",
            ),
            settings=settings,
        )
    with pytest.raises(RuntimeError, match="run_id '00000000-0000-0000-0000-000000000001'"):
        original_resolve_parent_manifest(
            ctx=SimpleNamespace(
                replay_of_manifest_id=None,
                replay_of_run_id="00000000-0000-0000-0000-000000000001",
            ),
            settings=settings,
        )

    monkeypatch.setattr(
        replay_context,
        "FileRunLedgerStore",
        lambda base_path: SimpleNamespace(
            list_entries=lambda manifest_id: [],
        ),
    )
    with pytest.raises(RuntimeError, match="missing published Bronze input snapshot"):
        original_resolve_parent_bronze_date(manifest=manifest, settings=settings)
    monkeypatch.setattr(
        replay_context,
        "_collect_ledger_bronze_dates",
        lambda manifest, ledger_entries: ("2026-01-01", "2026-01-02"),
    )
    with pytest.raises(RuntimeError, match="multiple Bronze snapshot dates"):
        original_resolve_parent_bronze_date(manifest=manifest, settings=settings)


def test_maintenance_mixin_get_table_version_handles_missing_and_import_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "storage"
        / "maintenance_mixin.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_maintenance_mixin_isolated",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    StorageBundleMaintenanceMixin = module.StorageBundleMaintenanceMixin

    bundle = StorageBundleMaintenanceMixin.__new__(StorageBundleMaintenanceMixin)
    missing = bundle.get_table_version(str(tmp_path / "missing"))
    assert missing is None

    delta_root = tmp_path / "silver"
    (delta_root / "_delta_log").mkdir(parents=True)
    (delta_root / "_delta_log" / "0001.json").write_text("{}", encoding="utf-8")

    monkeypatch.setitem(__import__("sys").modules, "deltalake", None)
    assert bundle.get_table_version(str(delta_root)) is None
