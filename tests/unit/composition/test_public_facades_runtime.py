"""Runtime coverage for thin composition-layer public facades."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.unit
def test_composite_api_reexports_bootstrap_entrypoints() -> None:
    """Public composite API should expose owner helpers unchanged."""
    sys.modules.pop("bioetl.composition.composite_api", None)

    compat_module = importlib.import_module("bioetl.composition.composite_api")
    target_module = importlib.import_module(
        "bioetl.composition.bootstrap.runtime.composite"
    )
    config_module = importlib.import_module(
        "bioetl.infrastructure.config.pipeline_config_api"
    )

    assert compat_module.bootstrap_composite_runner is (
        target_module.bootstrap_composite_runner
    )
    assert compat_module.load_composite_config is target_module.load_composite_config
    assert compat_module.load_pipeline_config is config_module.load_pipeline_config


@pytest.mark.unit
def test_bootstrap_package_root_exposes_sanctioned_lazy_runtime_helpers() -> None:
    """Package bootstrap root should expose the frozen lazy compatibility surface."""
    bootstrap_module = importlib.import_module("bioetl.composition.bootstrap")

    assert set(bootstrap_module.__all__) == {
        "bootstrap_composite_runner",
        "bootstrap_dq_monitor",
        "bootstrap_logger",
        "bootstrap_metrics",
        "bootstrap_observability_bundle",
        "bootstrap_pipeline_runner",
        "bootstrap_tracer",
        "load_composite_config",
        "load_pipeline_config",
        "maybe_start_metrics_server",
    }


@pytest.mark.unit
def test_pipeline_construction_module_reexports_canonical_builders() -> None:
    """Public construction seam should expose its delegated helper owners."""
    sys.modules.pop("bioetl.composition.factories.pipeline.construction", None)

    compat_module = importlib.import_module(
        "bioetl.composition.factories.pipeline.construction"
    )

    assert (
        compat_module.TransformerBuilder
        is importlib.import_module(
            "bioetl.composition.factories.pipeline.transformer_builder"
        ).TransformerBuilder
    )
    assert (
        compat_module.RunContextFactory
        is importlib.import_module(
            "bioetl.composition.factories.pipeline.run_context_factory"
        ).RunContextFactory
    )
    assert (
        compat_module.DomainConfigResolver
        is importlib.import_module(
            "bioetl.infrastructure.config.domain_config_resolver"
        ).DomainConfigResolver
    )
