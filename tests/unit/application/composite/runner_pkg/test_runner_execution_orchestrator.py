"""Focused tests for lock-held composite phase orchestration."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from bioetl.application.composite.runner_pkg.runner_execution_orchestrator import (
    CompositeLockedExecutionRequest,
    CompositeRunPhaseService,
    execute_locked_run_phases,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)


class _ExecutionHost:
    def __init__(self) -> None:
        self.order: list[str] = []
        self.initial_state = SimpleNamespace(name="initial")
        self.seed_state = SimpleNamespace(name="seed")
        self.dependency_state = SimpleNamespace(name="dependencies")
        self.enrichment_state = SimpleNamespace(name="enrichment")
        self.completed_enrichment_state = SimpleNamespace(name="enrichment_completed")
        self.final_state = SimpleNamespace(name="final")
        self.keys_df = SimpleNamespace(name="keys_df")
        self.seed_result = SeedResult(
            pipeline_name="seed_pipeline",
            records_extracted=10,
            records_silver=9,
        )
        self.dependency_results = {
            "dep_a": DependencyResult(
                pipeline_name="dep_a",
                status=DependencyStatus.SUCCESS,
            )
        }
        self.enrichment_results = {
            "enricher_a": EnrichmentResult(
                enricher_name="enricher_a",
                status=EnrichmentStatus.SUCCESS,
            )
        }
        self.merge_result = MergeResult(
            records_merged=9,
            records_from_seed=10,
        )

    async def _execute_seed_phase(self, state: object) -> tuple[object, SeedResult]:
        await asyncio.sleep(0)
        assert state is self.initial_state
        self.order.append("seed")
        return self.seed_state, self.seed_result

    async def _extract_enrichment_keys(self) -> object:
        await asyncio.sleep(0)
        self.order.append("keys")
        return self.keys_df

    async def _execute_dependencies_phase(
        self,
        state: object,
        keys_df: object,
    ) -> tuple[object, dict[str, DependencyResult]]:
        await asyncio.sleep(0)
        assert state is self.seed_state
        assert keys_df is self.keys_df
        self.order.append("dependencies")
        return self.dependency_state, self.dependency_results

    async def _execute_enrichment_phase(
        self,
        state: object,
        keys_df: object,
    ) -> tuple[object, dict[str, EnrichmentResult]]:
        await asyncio.sleep(0)
        assert state is self.dependency_state
        assert keys_df is self.keys_df
        self.order.append("enrichment")
        return self.enrichment_state, self.enrichment_results

    async def _transition_to_enrichment_completed(self, state: object) -> object:
        await asyncio.sleep(0)
        assert state is self.enrichment_state
        self.order.append("transition")
        return self.completed_enrichment_state

    def _record_enrichment_stage_completed(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        assert enrichment_results is self.enrichment_results
        self.order.append("record_enrichment_completed")

    async def _execute_merge_stage(
        self,
        state: object,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[object, MergeResult | None]:
        await asyncio.sleep(0)
        assert state is self.completed_enrichment_state
        assert enrichment_results is self.enrichment_results
        assert dependency_results is self.dependency_results
        self.order.append("merge")
        return self.final_state, self.merge_result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_locked_run_phases_preserves_canonical_phase_order() -> None:
    host = _ExecutionHost()

    result = await execute_locked_run_phases(
        host,
        CompositeLockedExecutionRequest(state=host.initial_state),
    )

    assert host.order == [
        "seed",
        "keys",
        "dependencies",
        "enrichment",
        "transition",
        "record_enrichment_completed",
        "merge",
    ]
    assert result.state is host.final_state
    assert result.execution_context.seed_result is host.seed_result
    assert result.execution_context.dependency_results is host.dependency_results
    assert result.execution_context.enrichment_results is host.enrichment_results
    assert result.execution_context.merge_result is host.merge_result


@pytest.mark.unit
def test_composite_run_phase_service_exposes_explicit_phase_methods() -> None:
    service = CompositeRunPhaseService()

    assert callable(service.execute_pre_merge)
    assert callable(service.execute_merge)
    assert callable(service.execute)
