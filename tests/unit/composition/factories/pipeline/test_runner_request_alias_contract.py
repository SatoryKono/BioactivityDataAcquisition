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
"""Compatibility tests for pipeline runner-request factory seams."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline import _assembler_factory
from bioetl.composition.factories.pipeline._factory_method_types import (
    build_pipeline_create_runner_request_from_kwargs,
)
from bioetl.composition.pipeline_runner_request import (
    build_pipeline_create_runner_request_from_kwargs as build_canonical_runner_request,
)
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.ports import PipelineCreateRunnerRequest
from bioetl.domain.ports.config import SettingsPort
from bioetl.domain.ports.runtime.runner import ExecutionObservabilityPort
from bioetl.domain.types import RunID, RunType


@pytest.mark.unit
def test_factory_method_types_compat_shim_delegates_to_canonical_builder() -> None:
    """Retained compat shim must remain a thin delegate to the canonical builder."""
    expected = MagicMock(spec=PipelineCreateRunnerRequest)

    with patch(
        "bioetl.composition.pipeline_runner_request.build_pipeline_create_runner_request_from_kwargs",
        return_value=expected,
    ) as mock_build:
        result = build_pipeline_create_runner_request_from_kwargs(
            run_id=RunID("00000000-0000-0000-0000-000000000001"),
            runtime=MagicMock(),
            started_at=datetime(2026, 5, 21, tzinfo=UTC),
            settings=MagicMock(),
            observability=MagicMock(),
        )

    assert result is expected
    mock_build.assert_called_once()


@pytest.mark.unit
def test_assembler_factory_imports_canonical_runner_request_builder() -> None:
    """Assembler factory must not depend on the removable compat shim internally."""
    assert (
        _assembler_factory._build_pipeline_create_runner_request_from_kwargs
        is build_canonical_runner_request
    )


@pytest.mark.unit
def test_compat_shim_builds_runner_request_for_minimal_kwargs() -> None:
    """Compat shim must continue to build a valid request for legacy callers."""
    request = build_pipeline_create_runner_request_from_kwargs(
        run_id=RunID("00000000-0000-0000-0000-000000000001"),
        runtime=RuntimeConfig(run_type=RunType.INCREMENTAL),
        started_at=datetime(2026, 5, 21, tzinfo=UTC),
        settings=MagicMock(spec=SettingsPort),
        observability=MagicMock(spec=ExecutionObservabilityPort),
        filter_config=None,
        config=None,
        cached_bronze=CachedBronzeContext.disabled(),
    )

    assert isinstance(request, PipelineCreateRunnerRequest)
    assert request.run_id == RunID("00000000-0000-0000-0000-000000000001")
