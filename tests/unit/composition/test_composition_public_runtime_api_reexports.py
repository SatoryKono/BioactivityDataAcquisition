# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Runtime coverage for thin composition-layer public runtime API re-exports."""

from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest


@pytest.mark.unit
def test_composite_api_reexports_bootstrap_entrypoints() -> None:
    """Public composite API should expose owner helpers unchanged."""
    # Do not evict ``composite_catalog`` from ``sys.modules``: it now owns
    # ``list_configured_pipeline_names`` (#10595) and other tests assert identity
    # against the already-imported owner.
    compat_module = importlib.import_module("bioetl.composition.composite_catalog")
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
def test_bootstrap_package_root_reexports_curated_lazy_helpers() -> None:
    """Package bootstrap root should expose only the curated bootstrap surface."""
    sys.modules.pop("bioetl.composition.bootstrap", None)

    bootstrap_module = importlib.import_module("bioetl.composition.bootstrap")
    # E2E autouse may leave a stale lazy-export cache on the package root.
    bootstrap_module.__dict__.pop("bootstrap_pipeline_runner", None)
    runtime_pipeline_module = importlib.import_module(
        "bioetl.composition.bootstrap.runtime.pipeline"
    )
    runtime_composite_module = importlib.import_module(
        "bioetl.composition.bootstrap.runtime.composite"
    )
    config_module = importlib.import_module(
        "bioetl.infrastructure.config.pipeline_config_api"
    )

    assert "bootstrap_pipeline_runner" in bootstrap_module.__all__
    assert bootstrap_module.bootstrap_pipeline_runner is (
        runtime_pipeline_module.bootstrap_pipeline_runner
    )
    assert bootstrap_module.bootstrap_composite_runner is (
        runtime_composite_module.bootstrap_composite_runner
    )
    assert bootstrap_module.load_pipeline_config is config_module.load_pipeline_config


@pytest.mark.unit
def test_pipeline_construction_owners_are_importable_without_shim() -> None:
    """Construction helpers are owned directly; the aggregate shim is gone (#10595)."""
    assert (
        importlib.util.find_spec("bioetl.composition.factories.pipeline.construction")
        is None
    )
    assert callable(
        importlib.import_module(
            "bioetl.composition.factories.pipeline.transformer_builder"
        ).TransformerBuilder
    )
    assert callable(
        importlib.import_module(
            "bioetl.composition.factories.pipeline.run_context_factory"
        ).RunContextFactory
    )
    assert callable(
        importlib.import_module(
            "bioetl.infrastructure.config.domain_config_resolver"
        ).DomainConfigResolver
    )
