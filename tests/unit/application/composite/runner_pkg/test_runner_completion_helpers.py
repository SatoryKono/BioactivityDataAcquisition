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
"""Focused tests for composite runner completion helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_completion_helpers import (
    CompositePipelineFinalizationRequest,
    CompositeResultBuildRequest,
    build_composite_result,
    finalize_pipeline,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.exceptions import StorageError


def _build_request(
    *,
    enrichment_results: dict[str, EnrichmentResult] | None = None,
) -> CompositeResultBuildRequest:
    started_at = datetime(2026, 4, 12, 12, 0, tzinfo=UTC)
    return CompositeResultBuildRequest(
        artifacts=SimpleNamespace(
            seed_result=SeedResult(
                pipeline_name="seed_pipeline",
                records_extracted=10,
                records_silver=9,
            ),
            dependency_results={
                "dep_a": DependencyResult(
                    pipeline_name="dep_a",
                    status=DependencyStatus.SUCCESS,
                )
            },
            enrichment_results=enrichment_results or {},
            merge_result=MergeResult(
                records_merged=9,
                records_from_seed=10,
            ),
        ),
        composite_name="test_composite",
        run_id="run-123",
        start_time=100.0,
        started_at=started_at,
        original_run_id="original-run-1",
        required_enrichers=frozenset(),
        required_dependencies=frozenset({"dep_a"}),
    )


class _FinalizationHost:
    def __init__(self) -> None:
        self.completed_state = SimpleNamespace(name="completed")
        self._checkpoint_manager = SimpleNamespace(
            delete_orphaned=AsyncMock(side_effect=StorageError("orphan cleanup failed"))
        )
        self._transition_to_completed_state = MagicMock(
            return_value=self.completed_state
        )
        self._persist_completed_state = AsyncMock()
        self._delete_checkpoint_safe = AsyncMock()


@pytest.mark.unit
def test_build_composite_result_marks_optional_failures_as_warnings() -> None:
    logger = MagicMock()
    observer_logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=observer_logger)
    request = _build_request(
        enrichment_results={
            "optional_a": EnrichmentResult(
                enricher_name="optional_a",
                status=EnrichmentStatus.FAILED,
            )
        }
    )

    with patch(
        "bioetl.application.composite.runner_pkg.runner_completion_helpers.derive_completion_timestamp",
        return_value=(request.started_at + timedelta(seconds=12.5), 12.5),
    ):
        result = build_composite_result(
            request=request,
            logger=logger,
            observer=observer,
        )

    assert result.had_warnings is True
    assert result.completed_at == request.started_at + timedelta(seconds=12.5)
    completion_call = observer_logger.info.call_args_list[-1]
    assert completion_call.kwargs["status"] == "completed_with_warnings"
    assert completion_call.kwargs["had_warnings"] is True


@pytest.mark.unit
def test_build_composite_result_requires_captured_start_context() -> None:
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=MagicMock())
    request = _build_request()
    request = CompositeResultBuildRequest(
        artifacts=request.artifacts,
        composite_name=request.composite_name,
        run_id=request.run_id,
        start_time=None,
        started_at=request.started_at,
        original_run_id=request.original_run_id,
        required_enrichers=request.required_enrichers,
        required_dependencies=request.required_dependencies,
    )

    with pytest.raises(RuntimeError, match="captured start context"):
        build_composite_result(request=request, logger=logger, observer=observer)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_pipeline_suppresses_orphan_cleanup_errors() -> None:
    host = _FinalizationHost()
    state = SimpleNamespace(name="merging")

    result = await finalize_pipeline(
        host,
        CompositePipelineFinalizationRequest(state=state),
    )

    assert result.completed_state is host.completed_state
    host._transition_to_completed_state.assert_called_once_with(state)
    host._persist_completed_state.assert_awaited_once_with(host.completed_state)
    host._delete_checkpoint_safe.assert_awaited_once()
    host._checkpoint_manager.delete_orphaned.assert_awaited_once()
