"""Unit tests for composite bootstrap builder aliases."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime import composite_bootstrap_builders
from bioetl.composition.bootstrap.runtime import runtime_basics
from bioetl.composition.bootstrap.runtime import runner_assembly


@pytest.mark.unit
def test_passthrough_builder_exports_alias_runtime_basics() -> None:
    """Pure passthrough builder seams should stay direct aliases."""
    assert (
        composite_bootstrap_builders.build_runner_factories
        is runtime_basics.build_runner_factories
    )
    assert (
        composite_bootstrap_builders.build_support_services
        is runtime_basics.build_support_services
    )
    assert (
        composite_bootstrap_builders.create_composite_runner
        is runner_assembly.create_composite_runner
    )


@pytest.mark.unit
def test_bootstrap_runtime_basics_forwards_injected_runtime_dependencies() -> None:
    """Composite builder must forward injected runtime providers to runtime_basics."""
    config = SimpleNamespace(name="composite_publication")
    settings = SimpleNamespace(metrics_enabled=False)
    logger = MagicMock()
    metrics = MagicMock()
    tracer = MagicMock()
    storage = MagicMock()
    lock = MagicMock()

    with patch(
        "bioetl.composition.bootstrap.runtime.composite_bootstrap_builders._bootstrap_runtime_basics_impl"
    ) as mock_runtime_basics:
        mock_runtime_basics.return_value = (
            "rid-123",
            settings,
            logger,
            metrics,
            tracer,
            storage,
            lock,
        )

        result = composite_bootstrap_builders.bootstrap_runtime_basics(
            config=config,
            run_id=None,
            settings_provider=MagicMock(return_value=settings),
            logger_bootstrapper=MagicMock(return_value=logger),
            tracer_bootstrapper=MagicMock(return_value=tracer),
            storage_bootstrapper=MagicMock(return_value=storage),
            lock_factory=MagicMock(return_value=lock),
            uuid_factory=MagicMock(),
        )

    call_kwargs = mock_runtime_basics.call_args.kwargs
    assert call_kwargs["config"] is config
    assert call_kwargs["run_id"] is None
    assert callable(call_kwargs["settings_provider"])
    assert callable(call_kwargs["logger_bootstrapper"])
    assert callable(call_kwargs["tracer_bootstrapper"])
    assert callable(call_kwargs["storage_bootstrapper"])
    assert callable(call_kwargs["lock_factory"])
    assert callable(call_kwargs["uuid_factory"])
    assert result.run_id == "rid-123"
    assert result.settings is settings
    assert result.logger is logger
    assert result.metrics is metrics
    assert result.tracer is tracer
    assert result.storage is storage
    assert result.lock is lock
