"""Stream B CMP: remaining composition wrappers and private helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.cli import metrics as cli_metrics
from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
    create_metrics_service,
    maybe_start_metrics_server,
)
from bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases import (
    create_pipeline_config_loader,
    create_registry,
    create_source_config_loader,
    get_settings as phases_get_settings,
)
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    RunOptions,
    _build_input_filter_context,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.composition.factories.datasource.pubchem import (
    _create_executor_runner,
    _resolve_circuit_breaker,
    _resolve_rate_limit,
)
from bioetl.composition.factories.dq._context_resolver_support import (
    _trim_relaxed_silver_checks,
    extract_dq_output_paths_impl,
    get_layer_path_impl,
    has_flat_structure_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_output_paths,
    get_layer_path,
    has_flat_structure,
)
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    _extract_bronze_date,
    _optional_text,
    bind_cached_bronze_context,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support import (
    _launch_context_value,
    _resolve_replay_reconstructability_status,
)
from bioetl.composition.runtime_builders._run_manifest_creation_support_helpers import (
    resolve_replay_lag_seconds,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    resolve_provider_entity,
)
from bioetl.composition.runtime_builders._runner_control_plane_policy import (
    requires_artifact_publication_closure,
)
from bioetl.domain.control_plane.artifact_lineage_layers import (
    _has_lineage_sidecar_persistence,
    _is_sink_layer_enabled,
    _resolve_sink_layer_config,
)
from bioetl.domain.config.effective_config_serializer import (
    _dataclass_to_dict,
    _to_jsonable,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.types.dq_contracts import DQDisposition

pytestmark = pytest.mark.unit


def test_metrics_refresh_disabled_and_logged_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disabled = SimpleNamespace(observability=SimpleNamespace(metrics_enabled=False))
    cli_metrics.refresh_control_plane_integrity_metrics(disabled)  # type: ignore[arg-type]

    class _Boom:
        def __init__(self, **_kwargs: object) -> None:
            raise RuntimeError("refresh boom")

    monkeypatch.setattr(cli_metrics, "ControlPlaneIntegrityMetricsService", _Boom)
    logger = MagicMock()
    enabled = SimpleNamespace(observability=SimpleNamespace(metrics_enabled=True))
    cli_metrics.refresh_control_plane_integrity_metrics(enabled, logger=logger)  # type: ignore[arg-type]
    logger.warning.assert_called()

    off = SimpleNamespace(observability=SimpleNamespace(metrics_enabled=False))
    assert maybe_start_metrics_server(off) is False  # type: ignore[arg-type]
    no_obs = SimpleNamespace(observability=None)
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.metrics_bootstrap._metrics_enabled",
        lambda _settings: True,
    )
    assert maybe_start_metrics_server(no_obs) is False  # type: ignore[arg-type]


def test_pipeline_execution_and_services_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.composition import _pipeline_execution as pe
    from bioetl.composition import _services as services

    monkeypatch.setattr(pe, "get_settings", lambda: object())
    monkeypatch.setattr(pe, "maybe_start_metrics_server", lambda _settings: True)
    assert pe.ensure_metrics_server_started() is True
    pe._ensure_registrations(MagicMock())
    runner = object()
    monkeypatch.setattr(pe, "bootstrap_pipeline_runner", lambda _ctx: runner)
    monkeypatch.setattr(pe, "_require_execution_metrics_runner", lambda value: value)
    assert pe._create_pipeline_runner_from_context(object()) is runner  # type: ignore[arg-type]
    assert services._workflow_services_module() is not None
    monkeypatch.setattr(
        services,
        "_workflow_services_module",
        lambda: SimpleNamespace(
            get_workflow_execution_service=lambda **_k: "exec",
            load_workflow_config=lambda _name: "cfg",
        ),
    )
    assert services.get_workflow_execution_service() == "exec"
    assert services.load_workflow_config("wf") == "cfg"


def test_exact_replay_bind_and_uri_helpers() -> None:
    @dataclass
    class _Ctx:
        cached_bronze: object

    ctx = _Ctx("old")
    bound = bind_cached_bronze_context(ctx, "new")  # type: ignore[arg-type]
    assert bound.cached_bronze == "new"
    same = bind_cached_bronze_context(bound, "new")  # type: ignore[arg-type]
    assert same is bound

    class _NoSlots:
        __slots__ = ()

    with pytest.raises(TypeError, match="does not support cached_bronze"):
        bind_cached_bronze_context(_NoSlots(), "x")  # type: ignore[arg-type]
    assert _optional_text("  ") is None
    assert _extract_bronze_date("bronze://2026-01-01/part") == "2026-01-01"
    with pytest.raises(RuntimeError, match="bronze://"):
        _extract_bronze_date("file://x")
    with pytest.raises(RuntimeError, match="missing Bronze date"):
        _extract_bronze_date("bronze://")


def test_serializer_snapshot_and_reconstructability() -> None:
    @dataclass
    class _Item:
        value: int

    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    payload = _to_jsonable(
        {
            "when": stamp,
            "disp": DQDisposition("pass") if False else next(iter(DQDisposition)),
            "item": _Item(1),
            "seq": (1, 2),
        }
    )
    assert isinstance(payload, dict)
    assert _dataclass_to_dict("x") is None
    assert resolve_provider_entity(
        pipeline_name="chembl", yaml_config=SimpleNamespace()
    ) == (
        "chembl",
        "chembl",
    )
    assert resolve_provider_entity(
        pipeline_name="chembl_activity",
        yaml_config=SimpleNamespace(provider="  ", entity_type="activity"),
    ) == ("chembl", "activity")
    assert _launch_context_value({"k": 1}, "k") == 1
    assert _launch_context_value(SimpleNamespace(k=2), "k") == 2
    status, strict = _resolve_replay_reconstructability_status(
        request=SimpleNamespace(
            replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED
        ),  # type: ignore[arg-type]
        strict_exact_replay_supported=False,
        strict_requirement=True,
        precomputed={
            "strict_requirement_requested": True,
            "replay_capability": "not_supported",
            "strict_exact_replay_supported": False,
        },
    )
    assert status == "not_reconstructable"
    assert strict is True
    assert (
        resolve_replay_lag_seconds(
            launch_context={"parent_run_age_seconds": 3},
            lag_status="blocked",
            read_attr=lambda *_a, **_k: None,
        )
        == 3.0
    )
    assert (
        resolve_replay_lag_seconds(
            launch_context=SimpleNamespace(),
            lag_status="ready",
            read_attr=lambda *_a, **_k: None,
        )
        == 0.0
    )


def test_dq_and_policy_helpers() -> None:
    class _NoChecks:
        checks = "nope"

    no_checks = _NoChecks()
    assert _trim_relaxed_silver_checks(no_checks) is no_checks  # type: ignore[arg-type]

    class _NoExpensive:
        checks = ["row_count"]

    no_expensive = _NoExpensive()
    assert _trim_relaxed_silver_checks(no_expensive) is no_expensive  # type: ignore[arg-type]

    class _NoCopy:
        checks = ["value_distribution"]

    with pytest.raises(TypeError, match="model_copy"):
        _trim_relaxed_silver_checks(_NoCopy())  # type: ignore[arg-type]

    class _Copyable:
        checks = ["value_distribution", "row_count"]

        def model_copy(self, *, update: dict[str, object]) -> _Copyable:
            other = _Copyable()
            other.checks = update["checks"]  # type: ignore[assignment]
            return other

    trimmed = _trim_relaxed_silver_checks(_Copyable())  # type: ignore[arg-type]
    assert "value_distribution" not in trimmed.checks
    assert get_layer_path(None) is None
    assert has_flat_structure(None) is False
    assert extract_dq_output_paths(None).bronze_path is None
    assert get_layer_path_impl(SimpleNamespace(path="/tmp")) == "/tmp"
    assert has_flat_structure_impl(SimpleNamespace(flat_structure=True)) is True
    empty_paths = extract_dq_output_paths_impl(
        SimpleNamespace(sink={"bronze": None, "silver": None, "gold": None}),
        get_layer_path_fn=lambda _cfg: None,
        has_flat_structure_fn=lambda _cfg: False,
    )
    assert empty_paths.bronze_path is None
    assert _resolve_sink_layer_config(SimpleNamespace(sink=None), "gold") is None
    assert (
        _resolve_sink_layer_config(SimpleNamespace(sink={"gold": "x"}), "gold") == "x"
    )
    assert _is_sink_layer_enabled(None) is True
    assert _has_lineage_sidecar_persistence(None) is False
    requires_artifact_publication_closure("forensic_grade")


def test_factory_pubchem_and_registry_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    DataSourceFactory._inject_adapter_helpers(
        provider="chembl",
        logger=None,
        adapter_kwargs={},
    )
    DataSourceFactory._inject_adapter_helpers(
        provider="chembl",
        logger=MagicMock(),
        adapter_kwargs={
            "error_handler": object(),
            "adapter_metrics": object(),
            "request_collector": object(),
            "fallback_fetch_service": object(),
        },
    )
    assert isinstance(DataSourceFactory.list_providers(), list)
    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.pubchem.load_source_config",
        lambda _provider: (_ for _ in ()).throw(ValueError("missing")),
    )
    assert _resolve_rate_limit("missing") == (5.0, 10)
    assert _resolve_circuit_breaker("missing") == (5, 300)

    async def _probe() -> None:
        runner = _create_executor_runner(MagicMock())
        assert callable(runner)

    import asyncio

    asyncio.run(_probe())
    registry = ProviderRegistry()
    assert registry.has_data_source_creator("definitely-missing-provider") is False
    assert isinstance(registry.list_keys(), list)
    assert registry.contains("definitely-missing-provider") is False

    from bioetl.composition.factories.services import factory as services_factory

    assert services_factory.__getattr__("ServicesBuilder") is not None
    with pytest.raises(AttributeError):
        services_factory.__getattr__("missing")

    loader_root = Path("configs")
    assert callable(create_pipeline_config_loader(loader_root))
    assert callable(create_source_config_loader(loader_root))
    assert create_registry() is not None
    assert phases_get_settings() is not None
    options = RunOptions(multi_filter_ids={"doi": ("a",)})
    assert _build_input_filter_context(options).enabled is True
    options_ids = RunOptions(filter_ids=("x",), filter_field="chembl_id")
    assert _build_input_filter_context(options_ids).enabled is True


def test_create_metrics_service_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    import bioetl.composition.bootstrap.runtime.metrics_bootstrap as mb

    sentinel = object()
    orig_import = mb.import_module

    def _import(name: str, *args: object, **kwargs: object) -> object:
        if name == "bioetl.composition.bootstrap.cli.metrics":
            return SimpleNamespace(create_metrics_service=lambda **_k: sentinel)
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(mb, "import_module", _import)
    assert create_metrics_service() is sentinel


def test_storage_and_composite_plan_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.composition.bootstrap.cli import storage as cli_storage
    from bioetl.composition.bootstrap.runtime._composite_control_plane_builder_support import (
        _read_composite_control_plane_settings,
    )
    from bioetl.composition.bootstrap.runtime._composite_plan_support import (
        build_bootstrap_runner_factories,
        build_support_services_impl,
        load_composite_config_impl,
    )

    sentinel = object()
    monkeypatch.setattr(cli_storage, "create_noop_logger", lambda: MagicMock())
    monkeypatch.setattr(
        cli_storage,
        "bootstrap_config_service",
        lambda **_k: SimpleNamespace(validate_pipeline_config=lambda *_a, **_k: None),
    )
    monkeypatch.setattr(
        cli_storage, "load_pipeline_contract_policy", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        cli_storage, "load_contract_registry_entries", lambda *_a, **_k: ()
    )
    service = cli_storage.bootstrap_contract_migration_service(registry=MagicMock())
    assert service is not None

    monkeypatch.setattr(
        cli_storage,
        "load_pipeline_config",
        lambda _name: SimpleNamespace(
            provider="chembl",
            entity_type="activity",
            silver_table="",
            gold_table="",
        ),
    )
    silver, gold = cli_storage._pipeline_table_names("chembl_activity")
    assert silver == "chembl.activity"
    assert gold == "chembl.activity"

    settings = SimpleNamespace(
        pipeline=SimpleNamespace(
            control_plane=SimpleNamespace(
                run_manifest_enabled=True,
                run_ledger_enabled=True,
                required_persistence_profile="degraded_observable",
            )
        )
    )
    view = _read_composite_control_plane_settings(settings)
    assert view[1] is True
    assert (
        build_bootstrap_runner_factories(
            build_runner_factories_fn=lambda **_k: sentinel,
            config=object(),  # type: ignore[arg-type]
            runtime=object(),  # type: ignore[arg-type]
            logger=MagicMock(),
        )
        is sentinel
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime._composite_plan_support.load_runtime_composite_config_impl",
        lambda *_a, **_k: sentinel,
    )
    assert (
        load_composite_config_impl(
            "x",
            resolve_config_path_fn=lambda _name: Path("x.yaml"),
            validate_payload=lambda _payload: sentinel,
        )
        is sentinel
    )
    assert (
        build_support_services_impl(
            config=object(),  # type: ignore[arg-type]
            runtime=object(),  # type: ignore[arg-type]
            infra_context=object(),  # type: ignore[arg-type]
            build_support_services_builder_fn=lambda **_k: sentinel,
            support_services_factory_cls=object,  # type: ignore[arg-type]
            resolve_gold_schema_fn=lambda _name: None,
            load_field_group_registry_fn=lambda *_a: None,
            create_dq_report_service_fn=lambda *_a: object(),
        )
        is sentinel
    )
