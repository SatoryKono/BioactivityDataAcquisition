"""Focused tests for composite runner completion helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

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
        started_at=datetime.now(tz=UTC),
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
    request = _build_request(
        enrichment_results={
            "optional_a": EnrichmentResult(
                enricher_name="optional_a",
                status=EnrichmentStatus.FAILED,
            )
        }
    )

    result = build_composite_result(request=request, logger=logger)

    assert result.had_warnings is True
    completion_call = logger.info.call_args_list[-1]
    assert completion_call.kwargs["status"] == "completed_with_warnings"
    assert completion_call.kwargs["had_warnings"] is True


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
