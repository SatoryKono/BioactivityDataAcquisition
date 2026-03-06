"""Compatibility tests for runtime bootstrap thin facades.

These tests guard public signatures/import paths and monkeypatch patch-points
while implementation details are decomposed into helper modules.
"""

from __future__ import annotations

import inspect

import pytest

import bioetl.composition.bootstrap.runtime as runtime_facade
import bioetl.composition.bootstrap.runtime.composite as composite_runtime
import bioetl.composition.bootstrap.runtime.observability as observability_runtime


@pytest.mark.unit
def test_composite_runtime_public_exports_stable() -> None:
    """Composite runtime facade should preserve stable public __all__."""
    assert composite_runtime.__all__ == [
        "CompositeRuntimeConfig",
        "bootstrap_composite_pipeline",
        "bootstrap_composite_runner",
        "load_composite_config",
    ]
    assert (
        runtime_facade.bootstrap_composite_runner
        is composite_runtime.bootstrap_composite_runner
    )
    assert (
        runtime_facade.bootstrap_composite_pipeline
        is composite_runtime.bootstrap_composite_pipeline
    )
    assert (
        runtime_facade.load_composite_config is composite_runtime.load_composite_config
    )


@pytest.mark.unit
def test_composite_runtime_patch_points_remain_available() -> None:
    """Legacy tests rely on these patch points for monkeypatching internals."""
    expected_attrs = {
        "COMPOSITE_CONFIG_DIR",
        "COMPOSITE_GOLD_SCHEMA_REGISTRY",
        "CompositePipelineRunner",
        "ValidationError",
        "_resolve_composite_config_path",
        "validate_composite_config_payload",
    }
    missing = [
        name for name in sorted(expected_attrs) if not hasattr(composite_runtime, name)
    ]
    assert not missing, f"Missing composite runtime patch points: {missing}"


@pytest.mark.unit
def test_composite_runtime_signatures_stable() -> None:
    """Public composite bootstrap function signatures should remain stable."""
    runner_sig = inspect.signature(composite_runtime.bootstrap_composite_runner)
    assert tuple(runner_sig.parameters) == ("config", "runtime", "run_id")
    assert runner_sig.parameters["run_id"].default is None

    load_sig = inspect.signature(composite_runtime.load_composite_config)
    assert tuple(load_sig.parameters) == ("name",)


@pytest.mark.unit
def test_observability_runtime_public_exports_stable() -> None:
    """Observability runtime facade should preserve stable public __all__."""
    assert observability_runtime.__all__ == [
        "MetricsServerError",
        "bootstrap_dq_monitor",
        "bootstrap_dq_monitor_port",
        "bootstrap_logger",
        "bootstrap_logger_port",
        "bootstrap_metrics",
        "bootstrap_metrics_port",
        "bootstrap_observability",
        "bootstrap_observability_bundle",
        "bootstrap_tracer",
        "bootstrap_tracer_port",
        "maybe_start_metrics_server",
        "start_metrics_server",
        "validate_observability_preflight",
    ]
    assert (
        runtime_facade.bootstrap_observability_bundle
        is observability_runtime.bootstrap_observability_bundle
    )
    assert (
        runtime_facade.bootstrap_logger_port
        is observability_runtime.bootstrap_logger_port
    )
    assert (
        runtime_facade.maybe_start_metrics_server
        is observability_runtime.maybe_start_metrics_server
    )


@pytest.mark.unit
def test_observability_runtime_patch_points_remain_available() -> None:
    """Legacy tests monkeypatch these runtime observability symbols."""
    expected_attrs = {
        "OpenTelemetryTracer",
        "PrometheusMetrics",
        "UnifiedLogger",
        "start_metrics_server",
    }
    missing = [
        name
        for name in sorted(expected_attrs)
        if not hasattr(observability_runtime, name)
    ]
    assert not missing, f"Missing observability runtime patch points: {missing}"


@pytest.mark.unit
def test_observability_runtime_signatures_stable() -> None:
    """Public observability bootstrap signatures should remain stable."""
    bundle_sig = inspect.signature(observability_runtime.bootstrap_observability_bundle)
    assert tuple(bundle_sig.parameters) == (
        "pipeline",
        "run_id",
        "settings",
        "log_level",
    )
    assert bundle_sig.parameters["log_level"].default == "INFO"

    validate_sig = inspect.signature(
        observability_runtime.validate_observability_preflight
    )
    assert tuple(validate_sig.parameters) == (
        "tracer",
        "metrics",
        "environment",
        "logger",
    )
