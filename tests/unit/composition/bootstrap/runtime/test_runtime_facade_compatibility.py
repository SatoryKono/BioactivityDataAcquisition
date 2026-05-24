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
        "bootstrap_composite_runner",
        "load_composite_config",
    ]
    assert (
        runtime_facade.bootstrap_composite_runner
        is composite_runtime.bootstrap_composite_runner
    )
    assert (
        runtime_facade.load_composite_config is composite_runtime.load_composite_config
    )


@pytest.mark.unit
def test_composite_runtime_patch_points_remain_available() -> None:
    """Legacy tests rely on these patch points for monkeypatching internals."""
    expected_attrs = {
        "DEFAULT_COMPOSITE_CONFIG_DIR",
        "DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY",
        "create_composite_runner_service",
        "ValidationError",
        "_resolve_composite_config_path",
        "validate_composite_config_payload",
    }
    missing = [
        name for name in sorted(expected_attrs) if not hasattr(composite_runtime, name)
    ]
    assert not missing, f"Missing composite runtime patch points: {missing}"


@pytest.mark.unit
def test_composite_runtime_does_not_expose_helper_only_symbols() -> None:
    """Helper-only wiring symbols should not leak through the runtime facade."""
    unexpected_attrs = {
        "CompositeFilterExtractor",
        "CompositeSupportServicesFactory",
        "MemoryLock",
        "RunnerFactoryBuilder",
        "resolve_bronze_opts",
        "bootstrap_pipeline_runner",
        "bootstrap_logger",
        "bootstrap_storage_adapter",
        "get_settings",
        "uuid4",
    }
    leaked = [
        name for name in sorted(unexpected_attrs) if hasattr(composite_runtime, name)
    ]
    assert not leaked, (
        f"Unexpected helper symbols leaked via composite runtime: {leaked}"
    )


@pytest.mark.unit
def test_composite_runtime_signatures_stable() -> None:
    """Public composite bootstrap function signatures should remain stable."""
    runner_sig = inspect.signature(composite_runtime.bootstrap_composite_runner)
    assert tuple(runner_sig.parameters) == ("config", "runtime", "run_id")
    assert runner_sig.parameters["run_id"].default is None

    load_sig = inspect.signature(composite_runtime.load_composite_config)
    assert tuple(load_sig.parameters) == ("name",)


@pytest.mark.unit
def test_composite_runtime_load_config_stays_on_helper_path() -> None:
    """Composite runtime config loading should stay delegated to the helper seam."""
    source = inspect.getsource(composite_runtime.load_composite_config)
    assert "_load_runtime_composite_config_impl" in source
    assert "_load_composite_config_impl(" not in source


@pytest.mark.unit
def test_composite_runtime_bootstrap_runner_stays_plan_based() -> None:
    """Public composite bootstrap should stay on the declarative plan path."""
    source = inspect.getsource(composite_runtime.bootstrap_composite_runner)
    assert "_build_composite_bootstrap_plan" in source
    assert "_create_composite_runner_from_plan" in source
    assert "_bootstrap_runtime_basics" not in source
    assert "_build_runner_factories" not in source
    assert "_build_support_services" not in source
    assert "_create_composite_runner(" not in source


@pytest.mark.unit
def test_runtime_plan_support_retires_legacy_runtime_compatibility() -> None:
    """Runtime plan support must stay on explicit named-bundle contracts."""
    from bioetl.composition.bootstrap.runtime import (
        _composite_plan_runtime_support as plan_runtime_support,
    )

    source = inspect.getsource(plan_runtime_support)
    assert "_is_legacy_runtime_basics_tuple" not in source
    assert "_call_supported_kwargs" not in source
    assert "inspect.signature" not in source


.mark.unit
def test_observability_runtime_public_exports_stable() -> None:
    """Observability runtime facade should preserve stable public __all__."""
    assert observability_runtime.__all__ == [
        "MetricsServerError",
        "bootstrap_dq_monitor",
        "bootstrap_logger",
        "bootstrap_metrics",
        "bootstrap_observability_bundle",
        "bootstrap_tracer",
        "maybe_start_metrics_server",
        "validate_observability_preflight",
    ]
    assert (
        runtime_facade.bootstrap_observability_bundle
        is observability_runtime.bootstrap_observability_bundle
    )
    assert runtime_facade.bootstrap_logger is observability_runtime.bootstrap_logger
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
        "yaml_config",
        "skip_gold",
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
        "allow_noop_in_prod",
        "audit",
        "audit_required",
        "control_plane",
        "yaml_config",
        "skip_gold",
    )
