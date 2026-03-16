"""Unit tests for runtime runner builder leaf module."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.composition.runtime_builders import observability_builder
from bioetl.composition.runtime_builders import runner_builder


class _FakeFactory:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def create_runner(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return "runner-instance"


class _FakeRegistry:
    def __init__(self, factory: _FakeFactory) -> None:
        self._factory = factory

    def get(self, pipeline_name: str) -> SimpleNamespace:
        return SimpleNamespace(factory=self._factory, pipeline_name=pipeline_name)


def test_build_pipeline_runner_defaults_to_provider_registry_bootstrap() -> None:
    """Default provider bootstrap should come from ProviderRegistry facade."""
    default_fn = runner_builder.build_pipeline_runner.__kwdefaults__[
        "ensure_providers_loaded_fn"
    ]

    assert getattr(default_fn, "__self__", None) is runner_builder.ProviderRegistry
    assert getattr(default_fn, "__func__", None) is (
        runner_builder.ProviderRegistry.ensure_loaded.__func__
    )


def test_build_pipeline_runner_wires_dependencies() -> None:
    """Builder should assemble dependencies and pass them to pipeline factory."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)

    calls: dict[str, object] = {}

    def get_settings_fn() -> SimpleNamespace:
        return SimpleNamespace(
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
        return SimpleNamespace(logger=logger)

    def assemble_vacuum_settings_fn(**_: object) -> str:
        return "vacuum"

    def assemble_runtime_config_fn(**_: object) -> str:
        return "runtime"

    def assemble_filter_config_fn(**_: object) -> SimpleNamespace:
        return SimpleNamespace(
            source_path="ids.csv",
            column_name="molecule_id",
            filter_field="molecule_id",
        )

    def assemble_cached_bronze_context_fn(_: object) -> SimpleNamespace:
        return SimpleNamespace(
            enabled=True,
            bronze_path="/tmp/bronze",
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
    assert fake_factory.kwargs["runtime"] == "runtime"
    assert fake_factory.kwargs["cached_bronze"].enabled is True
    assert [event for event, _ in logger_calls] == [
        "input_filter_enabled",
        "cached_bronze_mode_enabled",
    ]


def test_build_pipeline_runner_creates_registry_when_not_provided() -> None:
    """Builder should create a fresh registry when no explicit registry is provided."""
    fake_factory = _FakeFactory()
    created_registry = _FakeRegistry(factory=fake_factory)

    def get_settings_fn() -> SimpleNamespace:
        return SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=15),
            test_mode=True,
        )

    def load_pipeline_config_fn(_: str) -> SimpleNamespace:
        return SimpleNamespace(
            maintenance=None,
            input_filter=None,
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
        )

    def build_observability_bundle_fn(**_: object) -> SimpleNamespace:
        return SimpleNamespace(
            logger=SimpleNamespace(info=lambda *_, **__: None),
        )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=None,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        input_filter=SimpleNamespace(enabled=False),
    )

    result = runner_builder.build_pipeline_runner(
        context,
        create_registry_fn=lambda: created_registry,
        ensure_providers_loaded_fn=lambda: None,
        register_all_pipelines_fn=lambda registry=None: None,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_observability_bundle_fn,
        assemble_vacuum_settings_fn=lambda **_: None,
        assemble_runtime_config_fn=lambda **_: "runtime",
        assemble_filter_config_fn=lambda **_: None,
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(enabled=False),
    )

    assert result == "runner-instance"
    assert fake_factory.kwargs is not None
    assert fake_factory.kwargs["runtime"] == "runtime"


def test_build_pipeline_runner_registers_pipelines_into_created_registry() -> None:
    """Builder should register pipelines against the created runtime registry."""
    fake_factory = _FakeFactory()
    created_registry = _FakeRegistry(factory=fake_factory)
    calls: dict[str, object] = {}

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=None,
        query=None,
        dry_run=False,
        skip_gold=False,
        start_offset=None,
        input_filter=SimpleNamespace(enabled=False),
    )

    result = runner_builder.build_pipeline_runner(
        context,
        create_registry_fn=lambda: created_registry,
        ensure_providers_loaded_fn=lambda: calls.setdefault("providers", True),
        register_all_pipelines_fn=lambda registry=None: calls.setdefault(
            "pipelines_registry", registry
        ),
        get_settings_fn=lambda: SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=15),
            test_mode=True,
        ),
        load_pipeline_config_fn=lambda _: SimpleNamespace(
            maintenance=None,
            input_filter=None,
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
        ),
        build_observability_bundle_fn=lambda **_: SimpleNamespace(
            logger=SimpleNamespace(info=lambda *_, **__: None),
        ),
        assemble_vacuum_settings_fn=lambda **_: None,
        assemble_runtime_config_fn=lambda **_: "runtime",
        assemble_filter_config_fn=lambda **_: None,
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(enabled=False),
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
        observability="observability",
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
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    captured: dict[str, object] = {}

    def get_settings_fn() -> SimpleNamespace:
        return SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="strict"),
            test_mode=True,
        )

    def load_pipeline_config_fn(_: str) -> SimpleNamespace:
        return SimpleNamespace(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            input_filter=SimpleNamespace(),
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
            batch_size=100,
            provider="chembl",
        )

    def assemble_runtime_config_fn(**kwargs: object) -> str:
        captured.update(kwargs)
        return "runtime"

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=SimpleNamespace(enabled=None, retention_days=7),
        run_type="incremental",
        resume=False,
        limit=None,
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
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=lambda **_: SimpleNamespace(
            logger=SimpleNamespace(info=lambda *_, **__: None)
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=lambda **_: None,
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(enabled=False),
    )

    assert captured["health_check_mode"] == "probe"


def test_build_pipeline_runner_uses_configured_mode_outside_test_mode() -> None:
    """Builder must pass configured health mode when test_mode is disabled."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)
    captured: dict[str, object] = {}

    def get_settings_fn() -> SimpleNamespace:
        return SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="probe"),
            test_mode=False,
        )

    def load_pipeline_config_fn(_: str) -> SimpleNamespace:
        return SimpleNamespace(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            input_filter=SimpleNamespace(),
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
            batch_size=100,
            provider="chembl",
        )

    def assemble_runtime_config_fn(**kwargs: object) -> str:
        captured.update(kwargs)
        return "runtime"

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=SimpleNamespace(enabled=None, retention_days=7),
        run_type="incremental",
        resume=False,
        limit=None,
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
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=lambda **_: SimpleNamespace(
            logger=SimpleNamespace(info=lambda *_, **__: None)
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=lambda **_: None,
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(enabled=False),
    )

    assert captured["health_check_mode"] == "probe"


def test_build_pipeline_runner_forces_skip_gold_when_sink_disabled() -> None:
    """Builder should disable Gold writes when pipeline YAML disables Gold sink."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)

    def get_settings_fn() -> SimpleNamespace:
        return SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="strict"),
            test_mode=False,
        )

    def load_pipeline_config_fn(_: str) -> SimpleNamespace:
        return SimpleNamespace(
            pipeline_name="chembl_activity",
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            input_filter=SimpleNamespace(),
            business_primary_keys=["activity_id"],
            technical_primary_key="entity_id",
            batch_size=100,
            provider="chembl",
            sink={"gold": SimpleNamespace(enabled=False)},
        )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=SimpleNamespace(enabled=None, retention_days=7),
        run_type="incremental",
        resume=False,
        limit=None,
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
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=lambda **_: SimpleNamespace(
            logger=SimpleNamespace(info=lambda *_, **__: None)
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=runner_builder.assemble_runtime_config,
        assemble_filter_config_fn=lambda **_: None,
        assemble_cached_bronze_context_fn=lambda _: SimpleNamespace(enabled=False),
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
            observability=SimpleNamespace(
                tracing_enabled=False,
                metrics_enabled=False,
                dq_monitor_enabled=False,
            )
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
        observability=SimpleNamespace(
            tracing_enabled=True,
            metrics_enabled=True,
            dq_monitor_enabled=True,
            dq_baseline_window=20,
            dq_z_score_threshold=2.5,
            dq_min_baseline_samples=12,
            dq_error_rate_max=0.3,
            dq_quality_score_min=0.7,
        )
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
        primary_keys=None,
        technical_primary_key="entity_id",
    )

    with pytest.raises(ValueError, match="business_primary_keys must be non-empty"):
        inputs_resolver.validate_pk_contract(config)


def test_validate_pk_contract_rejects_legacy_pk_mismatch() -> None:
    config = SimpleNamespace(
        business_primary_keys=["entity_id"],
        primary_keys=["legacy_id"],
        technical_primary_key="entity_id",
    )

    with pytest.raises(ValueError, match="PK mismatch"):
        inputs_resolver.validate_pk_contract(config)


def test_validate_pk_contract_requires_technical_primary_key() -> None:
    config = SimpleNamespace(
        business_primary_keys=["entity_id"],
        primary_keys=["entity_id"],
        technical_primary_key="",
    )

    with pytest.raises(ValueError, match="technical_primary_key must be non-empty"):
        inputs_resolver.validate_pk_contract(config)
