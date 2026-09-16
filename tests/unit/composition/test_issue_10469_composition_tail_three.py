"""Behavioral tests for composition registry and bootstrap seams."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest

from bioetl.composition import _pipeline_execution, _service_registry, observability
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime import (
    _composite_control_plane_support as control_plane_support,
)
from bioetl.composition.bootstrap.runtime import (
    _composite_plan_runtime_support as plan_support,
)
from bioetl.composition.bootstrap.runtime.assembly import (
    assemble_cached_bronze_context,
)
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractor,
)
from bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder import (
    _create_join_type_resolver,
)
from bioetl.domain.control_plane import ReplayCapability


pytestmark = pytest.mark.unit


def test_typed_port_selector_preserves_runtime_registry_key() -> None:
    class _Port:
        pass

    selector = _service_registry.typed_port[_Port]

    assert selector(_Port) is _Port


def test_registry_snapshot_isolated_from_registered_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Port:
        pass

    instance = _Port()
    monkeypatch.setitem(_service_registry._REGISTRY, _Port, lambda: instance)

    snapshot = _service_registry.registered_ports()
    snapshot.clear()

    assert _service_registry.resolve(_Port) is instance
    assert _Port in _service_registry.registered_ports()


def test_registry_rejects_unregistered_port() -> None:
    class _MissingPort:
        pass

    with pytest.raises(KeyError, match="no composition factory registered"):
        _service_registry.resolve(_MissingPort)


def test_lazy_service_factory_invokes_callable_and_rejects_non_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = object()
    monkeypatch.setattr(
        _service_registry,
        "import_module",
        lambda _name: SimpleNamespace(factory=lambda: expected, value=42),
    )

    assert _service_registry._LazyServiceFactory("module", "factory")() is expected
    with pytest.raises(TypeError, match=r"module\.value is not callable"):
        _service_registry._LazyServiceFactory("module", "value")()


def test_lazy_contextual_factory_returns_callable_without_invoking_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Mock()
    monkeypatch.setattr(
        _service_registry,
        "import_module",
        lambda _name: SimpleNamespace(factory=factory, value=42),
    )

    assert _service_registry._LazyContextualFactory("module", "factory")() is factory
    factory.assert_not_called()
    with pytest.raises(TypeError, match=r"module\.value is not callable"):
        _service_registry._LazyContextualFactory("module", "value")()


def test_pipeline_execution_wrappers_delegate_all_runtime_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(name="settings")
    context = object()
    captured: dict[str, object] = {}
    monkeypatch.setattr(_pipeline_execution, "_get_settings_impl", lambda: settings)
    monkeypatch.setattr(
        _pipeline_execution,
        "_maybe_start_metrics_server",
        lambda value: value is settings,
    )

    def _build(name: str, options: object, **kwargs: object) -> object:
        captured.update(name=name, options=options, **kwargs)
        return context

    monkeypatch.setattr(_pipeline_execution, "build_pipeline_context_impl", _build)
    options = object()
    run_id = UUID("00000000-0000-0000-0000-000000000001")

    assert _pipeline_execution.get_settings() is settings
    assert _pipeline_execution.maybe_start_metrics_server(settings)
    assert (
        _pipeline_execution.build_pipeline_context(
            "chembl_activity",
            options,
            run_id=run_id,
        )
        is context
    )
    assert captured["name"] == "chembl_activity"
    assert captured["options"] is options
    assert captured["run_id"] == run_id


def test_pipeline_metrics_gateway_wrapper_preserves_optional_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _push(**kwargs: object) -> bool:
        captured.update(kwargs)
        return True

    monkeypatch.setattr(_pipeline_execution, "push_metrics_to_gateway_impl", _push)

    assert _pipeline_execution.push_metrics_to_gateway(
        run_label="run",
        pipeline_name="chembl_activity",
        run_type="incremental",
        grouping_key_extra={"scope": "test"},
        metric_names=("records",),
    )
    assert captured["grouping_key_extra"] == {"scope": "test"}
    assert captured["metric_names"] == ("records",)


def test_pipeline_runner_contract_rejects_incomplete_runner() -> None:
    with pytest.raises(TypeError, match="ExecutionMetricsRunnerPort"):
        _pipeline_execution._require_execution_metrics_runner(object())


@dataclass(frozen=True)
class _FrozenObservability:
    logger: object


def test_logger_rebind_returns_frozen_observability_when_assignment_is_rejected() -> (
    None
):
    logger = SimpleNamespace(bind=lambda **_kwargs: object())
    bundle = _FrozenObservability(logger=logger)

    assert (
        observability._rebind_observability_logger(
            observability=bundle,
            manifest_id="manifest-1",
        )
        is bundle
    )


def test_composite_control_plane_helpers_delegate_and_bind_conditionally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "00000000-0000-0000-0000-000000000002"
    assert str(control_plane_support.coerce_run_id(run_id)) == run_id
    assert (
        control_plane_support.compute_composite_input_snapshot_fingerprint(()) is None
    )

    expected_path = object()
    monkeypatch.setattr(
        control_plane_support,
        "_shared_control_plane_root",
        lambda settings, leaf: expected_path,
    )
    monkeypatch.setattr(
        control_plane_support,
        "_shared_to_serializable_mapping",
        lambda value: {"value": value},
    )
    settings = object()
    assert (
        control_plane_support.control_plane_root(settings, "run_ledger")
        is expected_path
    )
    assert control_plane_support.normalize_object("payload") == {"value": "payload"}

    logger = Mock()
    logger.bind.return_value = "rebound"
    assert control_plane_support.bind_manifest_logger(logger, None) is logger
    plain_logger = object()
    assert (
        control_plane_support.bind_manifest_logger(plain_logger, "manifest")
        is plain_logger
    )
    assert control_plane_support.bind_manifest_logger(logger, "manifest") == "rebound"
    logger.bind.assert_called_once_with(manifest_id="manifest")


@pytest.mark.parametrize(
    ("resume_requested", "expected"),
    [
        (False, ReplayCapability.REBUILD_ONLY),
        (True, ReplayCapability.RESUME_ONLY),
    ],
)
def test_composite_replay_capability_matches_supported_runtime_mode(
    resume_requested: bool,
    expected: ReplayCapability,
) -> None:
    assert (
        control_plane_support.resolve_composite_replay_capability(
            source_refs=(),
            required_persistence_profile="best_effort",
            resume_requested=resume_requested,
        )
        is expected
    )


def _infrastructure_context() -> CompositeInfrastructureContext:
    return CompositeInfrastructureContext(
        run_id="run-1",
        settings=SimpleNamespace(),
        logger=Mock(),
        metrics=Mock(),
        tracer=Mock(),
        storage=Mock(),
        lock=Mock(),
        clock=None,
    )


def test_bootstrap_runtime_resource_properties_expose_named_context() -> None:
    context = _infrastructure_context()
    resources = plan_support.BootstrapRuntimeResources(infra_context=context)

    assert resources.run_id == "run-1"
    assert resources.settings is context.settings
    assert resources.logger is context.logger
    assert resources.metrics is context.metrics
    assert resources.tracer is context.tracer
    assert resources.storage is context.storage
    assert resources.lock is context.lock
    assert resources.clock is None


def test_bootstrap_resources_accept_named_bundle_and_reject_legacy_tuple() -> None:
    context = _infrastructure_context()
    named = SimpleNamespace(
        run_id=context.run_id,
        settings=context.settings,
        logger=context.logger,
        metrics=context.metrics,
        tracer=context.tracer,
        storage=context.storage,
        lock=context.lock,
    )

    resources = plan_support.build_bootstrap_runtime_resources(
        bootstrap_runtime_basics_fn=lambda **_kwargs: named,
        config=SimpleNamespace(),
        run_id=None,
    )

    assert isinstance(resources.infra_context, CompositeInfrastructureContext)
    assert resources.clock is None
    assert plan_support._coerce_named_runtime_bundle(object()) is None
    with pytest.raises(TypeError, match="legacy tuple bundles"):
        plan_support.build_bootstrap_runtime_resources(
            bootstrap_runtime_basics_fn=lambda **_kwargs: ("legacy",),
            config=SimpleNamespace(),
            run_id=None,
        )


def test_bootstrap_resources_preserve_canonical_context_instance() -> None:
    context = _infrastructure_context()

    resources = plan_support.build_bootstrap_runtime_resources(
        bootstrap_runtime_basics_fn=lambda **_kwargs: context,
        config=SimpleNamespace(),
        run_id="run-1",
    )

    assert resources.infra_context is context


def test_composite_plan_delegates_support_and_runner_builders() -> None:
    context = _infrastructure_context()
    resources = plan_support.BootstrapRuntimeResources(context)
    support_builder = Mock(return_value="support-services")

    assert (
        plan_support.build_bootstrap_support_services(
            build_support_services_fn=support_builder,
            config="config",
            runtime="runtime",
            resources=resources,
        )
        == "support-services"
    )
    support_builder.assert_called_once_with(
        config="config",
        runtime="runtime",
        infra_context=context,
    )

    plan = SimpleNamespace(
        run_id="run-1",
        logger="logger",
        metrics="metrics",
        tracer="tracer",
        lock="lock",
        seed_runner_factory="seed",
        dependencies_runner_factory="dependencies",
        enricher_runner_factory="enricher",
        support_services="support",
    )
    runner = object()
    runner_builder = Mock(return_value=runner)

    assert (
        plan_support.create_composite_runner_from_plan_impl(
            config="config",
            runtime="runtime",
            plan=plan,
            create_composite_runner_builder_fn=runner_builder,
            runner_factory="runner-factory",
        )
        is runner
    )
    runner_builder.assert_called_once_with(
        config="config",
        runtime="runtime",
        run_id="run-1",
        logger="logger",
        metrics="metrics",
        tracer="tracer",
        lock="lock",
        seed_runner_factory="seed",
        dependencies_runner_factory="dependencies",
        enricher_runner_factory="enricher",
        support_services="support",
        runner_factory="runner-factory",
    )


def test_filter_extractor_empty_inputs_are_explicit_and_logged() -> None:
    logger = Mock()
    extractor = CompositeFilterExtractor(logger=logger)
    enricher = SimpleNamespace(pipeline="crossref", join_keys=("doi",))

    assert extractor.find_filter_key(("title", "doi"), ["title"]) is None
    assert extractor.extract_enricher_filters(enricher, None) == (None, None, None)
    assert extractor.resolve_dependency_filter_inputs(None, None) == (
        None,
        None,
        None,
    )
    logger.debug.assert_called_once()


def test_cached_bronze_context_is_forwarded_unchanged() -> None:
    cached = object()
    context = SimpleNamespace(cached_bronze=cached)

    assert assemble_cached_bronze_context(context) is cached


def test_join_type_resolver_defers_strategy_mapping_until_called() -> None:
    strategy = object()
    resolver = Mock(return_value="left")
    deferred = _create_join_type_resolver(strategy, resolver)

    resolver.assert_not_called()
    assert deferred() == "left"
    resolver.assert_called_once_with(strategy)
