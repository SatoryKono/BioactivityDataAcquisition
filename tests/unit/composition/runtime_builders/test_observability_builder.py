"""Unit tests for runtime observability builder helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, sentinel

import pytest

from bioetl.composition.runtime_builders import observability_builder
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite


pytestmark = pytest.mark.unit


def _make_settings(
    *,
    tracing_enabled: bool = True,
    metrics_enabled: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        observability=SimpleNamespace(
            tracing_enabled=tracing_enabled,
            metrics_enabled=metrics_enabled,
        )
    )


def test_build_logger_bootstrapper_passes_canonical_logger_kwargs() -> None:
    logger_factory = MagicMock(return_value=sentinel.logger)
    bootstrapper = observability_builder._build_logger_bootstrapper(logger_factory)
    run_id = deterministic_uuid_from_callsite("test_observability_builder")

    result = bootstrapper("chembl_activity", run_id, "DEBUG")

    assert result is sentinel.logger
    logger_factory.assert_called_once_with(
        pipeline="chembl_activity",
        run_id=run_id,
        log_level="DEBUG",
        json_format=True,
    )


def test_resolve_tracer_port_bootstraps_default_when_factories_are_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    bootstrap_tracer = MagicMock(return_value=sentinel.tracer)
    monkeypatch.setattr(
        observability_builder,
        "_bootstrap_tracer_impl",
        bootstrap_tracer,
    )

    result = observability_builder._resolve_tracer_port(
        tracer_settings=settings,
        tracer_factory=None,
        noop_tracing_factory=None,
    )

    assert result is sentinel.tracer
    bootstrap_tracer.assert_called_once_with(
        settings=settings,
        service_name="bioetl",
    )


def test_resolve_tracer_port_uses_provider_factory_when_enabled() -> None:
    settings = _make_settings(tracing_enabled=True)
    tracer_factory = MagicMock(return_value=sentinel.tracer)
    noop_tracing_factory = MagicMock()

    result = observability_builder._resolve_tracer_port(
        tracer_settings=settings,
        tracer_factory=tracer_factory,
        noop_tracing_factory=noop_tracing_factory,
    )

    assert result is sentinel.tracer
    tracer_factory.assert_called_once_with("bioetl")
    noop_tracing_factory.assert_not_called()


def test_resolve_tracer_port_uses_noop_factory_when_available() -> None:
    settings = _make_settings(tracing_enabled=False)
    tracer_factory = MagicMock()
    noop_tracing_factory = MagicMock(return_value=sentinel.noop_tracer)

    result = observability_builder._resolve_tracer_port(
        tracer_settings=settings,
        tracer_factory=tracer_factory,
        noop_tracing_factory=noop_tracing_factory,
    )

    assert result is sentinel.noop_tracer
    tracer_factory.assert_not_called()
    noop_tracing_factory.assert_called_once_with()


def test_build_tracer_bootstrapper_delegates_to_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    tracer_factory = MagicMock()
    noop_tracing_factory = MagicMock()
    resolve_tracer = MagicMock(return_value=sentinel.tracer)
    monkeypatch.setattr(
        observability_builder,
        "_resolve_tracer_port",
        resolve_tracer,
    )

    bootstrapper = observability_builder._build_tracer_bootstrapper(
        tracer_factory=tracer_factory,
        noop_tracing_factory=noop_tracing_factory,
    )
    result = bootstrapper(settings)

    assert result is sentinel.tracer
    resolve_tracer.assert_called_once_with(
        tracer_settings=settings,
        tracer_factory=tracer_factory,
        noop_tracing_factory=noop_tracing_factory,
    )


def test_resolve_tracer_port_delegates_to_canonical_resolution_helper_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings(tracing_enabled=False)
    tracer_factory = MagicMock()
    resolve_tracing_port = MagicMock(return_value=sentinel.tracer)
    monkeypatch.setattr(
        observability_builder,
        "resolve_tracing_port",
        resolve_tracing_port,
    )

    result = observability_builder._resolve_tracer_port(
        tracer_settings=settings,
        tracer_factory=tracer_factory,
        noop_tracing_factory=None,
    )

    assert result is sentinel.tracer
    tracer_factory.assert_not_called()
    resolve_tracing_port.assert_called_once_with(tracer=None, settings=settings)


def test_resolve_metrics_port_bootstraps_default_when_factories_are_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    bootstrap_metrics = MagicMock(return_value=sentinel.metrics)
    monkeypatch.setattr(
        observability_builder,
        "_bootstrap_metrics_impl",
        bootstrap_metrics,
    )

    result = observability_builder._resolve_metrics_port(
        metrics_settings=settings,
        metrics_factory=None,
        noop_metrics_factory=None,
    )

    assert result is sentinel.metrics
    bootstrap_metrics.assert_called_once_with(settings=settings)


def test_resolve_metrics_port_uses_provider_factory_when_enabled() -> None:
    settings = _make_settings(metrics_enabled=True)
    metrics_factory = MagicMock(return_value=sentinel.metrics)
    noop_metrics_factory = MagicMock()

    result = observability_builder._resolve_metrics_port(
        metrics_settings=settings,
        metrics_factory=metrics_factory,
        noop_metrics_factory=noop_metrics_factory,
    )

    assert result is sentinel.metrics
    metrics_factory.assert_called_once_with()
    noop_metrics_factory.assert_not_called()


def test_resolve_metrics_port_uses_noop_factory_with_warn_on_use_disabled() -> None:
    settings = _make_settings(metrics_enabled=False)
    metrics_factory = MagicMock()
    noop_metrics_factory = MagicMock(return_value=sentinel.noop_metrics)

    result = observability_builder._resolve_metrics_port(
        metrics_settings=settings,
        metrics_factory=metrics_factory,
        noop_metrics_factory=noop_metrics_factory,
    )

    assert result is sentinel.noop_metrics
    metrics_factory.assert_not_called()
    noop_metrics_factory.assert_called_once_with(warn_on_use=False)


def test_build_metrics_bootstrapper_delegates_to_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    metrics_factory = MagicMock()
    noop_metrics_factory = MagicMock()
    resolve_metrics = MagicMock(return_value=sentinel.metrics)
    monkeypatch.setattr(
        observability_builder,
        "_resolve_metrics_port",
        resolve_metrics,
    )

    bootstrapper = observability_builder._build_metrics_bootstrapper(
        metrics_factory=metrics_factory,
        noop_metrics_factory=noop_metrics_factory,
    )
    result = bootstrapper(settings)

    assert result is sentinel.metrics
    resolve_metrics.assert_called_once_with(
        metrics_settings=settings,
        metrics_factory=metrics_factory,
        noop_metrics_factory=noop_metrics_factory,
    )


def test_resolve_metrics_port_delegates_to_canonical_resolution_helper_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings(metrics_enabled=False)
    metrics_factory = MagicMock()
    resolve_metrics_port = MagicMock(return_value=sentinel.metrics)
    monkeypatch.setattr(
        observability_builder,
        "resolve_metrics_port",
        resolve_metrics_port,
    )

    result = observability_builder._resolve_metrics_port(
        metrics_settings=settings,
        metrics_factory=metrics_factory,
        noop_metrics_factory=None,
    )

    assert result is sentinel.metrics
    metrics_factory.assert_not_called()
    resolve_metrics_port.assert_called_once_with(metrics=None, settings=settings)


def test_build_dq_monitor_bootstrapper_delegates_to_bootstrap_impl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    logger = MagicMock()
    dq_monitor_factory = MagicMock()
    noop_logger_factory = MagicMock()
    bootstrap_dq_monitor = MagicMock(return_value=sentinel.dq_monitor)
    monkeypatch.setattr(
        observability_builder,
        "_bootstrap_dq_monitor_impl",
        bootstrap_dq_monitor,
    )

    bootstrapper = observability_builder._build_dq_monitor_bootstrapper(
        dq_monitor_factory=dq_monitor_factory,
        noop_logger_factory=noop_logger_factory,
    )
    result = bootstrapper(settings, logger)

    assert result is sentinel.dq_monitor
    bootstrap_dq_monitor.assert_called_once_with(
        settings=settings,
        logger=logger,
        monitor_factory=dq_monitor_factory,
        noop_logger_factory=noop_logger_factory,
    )


def test_build_audit_bootstrapper_delegates_to_audit_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    create_audit_port = MagicMock(return_value=sentinel.audit)
    monkeypatch.setattr(
        observability_builder,
        "create_audit_port",
        create_audit_port,
    )

    bootstrapper = observability_builder._build_audit_bootstrapper()
    result = bootstrapper(
        settings,
        sentinel.logger,
        sentinel.metrics,
        sentinel.tracer,
    )

    assert result is sentinel.audit
    create_audit_port.assert_called_once_with(
        settings=settings,
        logger=sentinel.logger,
        metrics=sentinel.metrics,
        tracing=sentinel.tracer,
    )


def test_build_observability_bundle_passes_canonical_wiring_to_bootstrap_impl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    run_id = deterministic_uuid_from_callsite("test_observability_builder_bundle")
    logger_factory = MagicMock(return_value=sentinel.logger)
    tracer_factory = MagicMock(return_value=sentinel.tracer)
    metrics_factory = MagicMock(return_value=sentinel.metrics)
    noop_tracing_factory = MagicMock(return_value=sentinel.noop_tracer)
    noop_metrics_factory = MagicMock(return_value=sentinel.noop_metrics)
    dq_monitor_factory = MagicMock(return_value=sentinel.dq_monitor)
    noop_logger_factory = MagicMock(return_value=sentinel.noop_logger)
    captured: dict[str, object] = {}

    def _bootstrap_bundle(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel.bundle

    monkeypatch.setattr(
        observability_builder,
        "bootstrap_observability_bundle_impl",
        _bootstrap_bundle,
    )

    result = observability_builder.build_observability_bundle(
        pipeline="chembl_activity",
        run_id=run_id,
        settings=settings,
        log_level="WARNING",
        yaml_config=sentinel.yaml_config,
        skip_gold=True,
        logger_factory=logger_factory,
        tracer_factory=tracer_factory,
        metrics_factory=metrics_factory,
        noop_tracing_factory=noop_tracing_factory,
        noop_metrics_factory=noop_metrics_factory,
        dq_monitor_factory=dq_monitor_factory,
        noop_logger_factory=noop_logger_factory,
    )

    assert result is sentinel.bundle
    assert captured["pipeline"] == "chembl_activity"
    assert captured["run_id"] == run_id
    assert captured["settings"] is settings
    assert captured["log_level"] == "WARNING"
    assert captured["yaml_config"] is sentinel.yaml_config
    assert captured["skip_gold"] is True
    assert captured["preflight_validator"] is (
        observability_builder.validate_observability_preflight_impl
    )
    assert callable(captured["logger_bootstrapper"])
    assert callable(captured["tracer_bootstrapper"])
    assert callable(captured["metrics_bootstrapper"])
    assert callable(captured["audit_bootstrapper"])
    assert callable(captured["dq_monitor_bootstrapper"])
