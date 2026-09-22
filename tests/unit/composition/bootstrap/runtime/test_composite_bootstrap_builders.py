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
"""Unit tests for composite bootstrap builder owner bindings.

The ``composite_bootstrap_builders`` re-export shim was removed in #10595;
composite bootstrap callers now bind directly to ``runtime_basics`` and
``runner_assembly`` owners.
"""

from __future__ import annotations

import importlib.util
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime import composite
from bioetl.composition.bootstrap.runtime import composite_support_helpers
from bioetl.composition.bootstrap.runtime import runner_assembly
from bioetl.composition.bootstrap.runtime import runtime_basics


@pytest.mark.unit
def test_composite_bootstrap_builders_shim_is_gone() -> None:
    """The pure re-export shim must not be resurrected."""
    assert (
        importlib.util.find_spec(
            "bioetl.composition.bootstrap.runtime.composite_bootstrap_builders"
        )
        is None
    )


@pytest.mark.unit
def test_composite_callers_bind_directly_to_owner_builders() -> None:
    """Composite bootstrap callers should alias the runtime_basics/runner_assembly owners."""
    assert (
        composite_support_helpers._bootstrap_runtime_basics_builder_impl
        is runtime_basics.bootstrap_runtime_basics
    )
    assert (
        composite_support_helpers._build_runner_factories_builder_impl
        is runtime_basics.build_runner_factories
    )
    assert (
        composite_support_helpers._build_support_services_builder_impl
        is runtime_basics.build_support_services
    )
    assert (
        composite._create_composite_runner_builder_impl
        is runner_assembly.create_composite_runner
    )


@pytest.mark.unit
def test_bootstrap_runtime_basics_forwards_injected_runtime_dependencies() -> None:
    """Owner builder must forward injected runtime providers unchanged."""
    config = SimpleNamespace(name="composite_publication")
    settings = SimpleNamespace(metrics_enabled=False)
    logger = MagicMock()
    metrics = MagicMock()
    tracer = MagicMock()
    storage = MagicMock()
    lock = MagicMock()

    with patch(
        "bioetl.composition.bootstrap.runtime.runtime_basics.bootstrap_runtime_basics"
    ) as mock_runtime_basics:
        mock_runtime_basics.return_value = SimpleNamespace(
            run_id="rid-123",
            settings=settings,
            logger=logger,
            metrics=metrics,
            tracer=tracer,
            storage=storage,
            lock=lock,
        )

        result = runtime_basics.bootstrap_runtime_basics(
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
