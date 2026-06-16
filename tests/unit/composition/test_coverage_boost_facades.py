"""Targeted unit coverage boosts for composition facades and runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest

from bioetl.composition import _services
from bioetl.composition import _workflow_services
from bioetl.composition.bootstrap import cli as cli_bootstrap
from bioetl.composition.factories import __getattr__ as factories_getattr
from bioetl.composition.factories.storage.maintenance_mixin import (
    StorageBundleMaintenanceMixin,
)
from bioetl.composition.runtime_builders import (
    _exact_replay_cached_bronze_context as replay_context,
)
from bioetl.composition.runtime_builders import (
    _run_manifest_data_roots as data_roots,
)


pytestmark = pytest.mark.unit


def test_factories_package_lazy_exports_and_unknown_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("fake_services")
    fake_module.BaseServicesFactory = object()
    fake_pipeline = ModuleType("fake_pipeline")
    fake_pipeline.create_pipeline_factory = mock.sentinel.pipeline_factory
    fake_registry = ModuleType("fake_registry")
    fake_registry.pubchem_compound_factory = mock.sentinel.pubchem_factory
    fake_pipeline.registry = fake_registry

    def _fake_import_module(name: str) -> ModuleType:
        mapping = {
            "bioetl.composition.factories.services.factory": fake_module,
        }
        return mapping[name]

    monkeypatch.setattr("bioetl.composition.factories.import_module", _fake_import_module)
    monkeypatch.setitem(__import__("sys").modules, "bioetl.composition.factories.pipeline", fake_pipeline)
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
        lambda name: fake_health if name == "bioetl.composition.bootstrap.cli.health" else (_ for _ in ()).throw(KeyError(name)),
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
        "bioetl.composition._registration.ensure_runtime_registrations",
        lambda registry=None, scope="pipelines": calls.append((registry, scope)),
    )
    monkeypatch.setattr(
        "bioetl.composition._services._invoke_bootstrap",
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


def test_maintenance_mixin_get_table_version_handles_missing_and_import_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = StorageBundleMaintenanceMixin.__new__(StorageBundleMaintenanceMixin)
    missing = bundle.get_table_version(str(tmp_path / "missing"))
    assert missing is None

    delta_root = tmp_path / "silver"
    (delta_root / "_delta_log").mkdir(parents=True)
    (delta_root / "_delta_log" / "0001.json").write_text("{}", encoding="utf-8")

    monkeypatch.setitem(__import__("sys").modules, "deltalake", None)
    assert bundle.get_table_version(str(delta_root)) is None
