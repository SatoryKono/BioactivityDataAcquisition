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
"""Owner tests for CompositeInfrastructureContext thin package module."""

from __future__ import annotations

import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)


pytestmark = pytest.mark.unit


def test_composite_infrastructure_context_exposes_bootstrap_primitives() -> None:
    settings = SimpleNamespace(data_dir="data")
    logger = MagicMock()
    metrics = MagicMock()
    tracer = MagicMock()
    storage = MagicMock()
    lock = MagicMock()

    context = CompositeInfrastructureContext(
        run_id="run-123",
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        storage=storage,
        lock=lock,
    )

    assert context.run_id == "run-123"
    assert context.settings is settings
    assert context.logger is logger
    assert context.metrics is metrics
    assert context.tracer is tracer
    assert context.storage is storage
    assert context.lock is lock
