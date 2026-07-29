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
"""Unit tests for _CompositeRunnerStageEnrichmentMixin."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.runner_pkg.runner_stage_enrichment_mixin import (
    _CompositeRunnerStageEnrichmentMixin,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError
from tests.unit.application.composite.runner_pkg.runner_pkg_test_support import (
    failed_enrichment,
    initialize_runner_pkg_harness,
    make_enricher_cfg,
    make_runner_state,
    success_enrichment,
)


# ---------------------------------------------------------------------------
# Fakes / factories
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _EnrichmentHarness(_CompositeRunnerStageEnrichmentMixin):
    """Concrete test harness wiring all abstract seam methods."""

    def __init__(
        self,
        config: Any | None = None,
        enricher_results: dict[str, EnrichmentResult] | None = None,
    ) -> None:
        initialize_runner_pkg_harness(
            self,
            config=config
            or SimpleNamespace(
                name="test_composite",
                enrichers=[],
                required_enrichers=[],
            ),
            runtime=SimpleNamespace(required_only=False),
            run_id_str="run-enrich-test",
        )
        self._coordinator = MagicMock()
        self._coordinator.run_enrichers = AsyncMock(return_value=enricher_results or {})
        self._enricher_runner_factory = MagicMock()

        # Seam implementations
        self._seam_enrichers_to_run: list[Any] = []
        self._seam_check_required_raises: bool = False
        self._required_enricher_check_calls = 0

    # --- seam stubs ---

    def _call_get_enrichers_to_run(self, state: Any) -> list[Any]:
        return self._seam_enrichers_to_run

    def _call_check_required_enrichers(self, results: Any) -> None:
        self._required_enricher_check_calls += 1
        if self._seam_check_required_raises:
            raise InvalidStateError("Required enricher failed: req_a")

    async def _call_save_checkpoint_safe(self, state: Any, operation: str) -> bool:
        await asyncio.sleep(0)
        return True

    def _transition_state_with_fsm_log(
        self,
        state: Any,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        **kwargs: object,
    ) -> Any:
        state.with_state(to_state)
        return state

    async def _persist_failed_state(
        self,
        state: Any,
        *,
        stage: str,
        error: str,
    ) -> Any:
        await asyncio.sleep(0)
        return state

    def _record_enrichment_stage_started(self, enricher_names: list[str]) -> None:
        del enricher_names

    def _record_enrichment_stage_completed(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        del enrichment_results


# ---------------------------------------------------------------------------
# _prepare_enrichment_run_context
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prepare_enrichment_run_context_when_enrichers_selected_then_returns_names() -> (
    None
):
    enrichers = [make_enricher_cfg("crossref"), make_enricher_cfg("pubmed")]
    harness = _EnrichmentHarness()
    harness._seam_enrichers_to_run = enrichers
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)

    context = harness._prepare_enrichment_run_context(state)

    assert context.enrichers_to_run == enrichers
    assert context.enricher_names == ["crossref", "pubmed"]


# ---------------------------------------------------------------------------
# _record_completed_enrichment_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_record_completed_enrichment_results_when_success_then_state_updated() -> None:
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)
    results = {"enricher_a": success_enrichment("enricher_a")}

    new_state = harness._record_completed_enrichment_results(state, results)

    state.with_enricher_completed.assert_called_once_with(
        "enricher_a",
        results["enricher_a"],
        clock=harness._clock,
    )
    assert new_state is state


@pytest.mark.unit
def test_record_completed_enrichment_results_when_failed_then_state_not_updated() -> (
    None
):
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)
    results = {"enricher_a": failed_enrichment("enricher_a")}

    harness._record_completed_enrichment_results(state, results)

    state.with_enricher_completed.assert_not_called()


@pytest.mark.unit
def test_record_completed_enrichment_results_when_skipped_then_state_updated() -> None:
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)
    skipped = EnrichmentResult(
        enricher_name="enricher_a", status=EnrichmentStatus.SKIPPED
    )
    results = {"enricher_a": skipped}

    harness._record_completed_enrichment_results(state, results)

    state.with_enricher_completed.assert_called_once_with(
        "enricher_a",
        skipped,
        clock=harness._clock,
    )


@pytest.mark.unit
def test_record_completed_enrichment_results_when_clock_missing_then_raises() -> None:
    harness = _EnrichmentHarness()
    harness._clock = None
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)
    results = {"enricher_a": success_enrichment("enricher_a")}

    with pytest.raises(RuntimeError, match="ClockPort is required"):
        harness._record_completed_enrichment_results(state, results)


# ---------------------------------------------------------------------------
# _skip_enrichment_stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skip_enrichment_stage_when_called_then_logs_and_returns_empty() -> None:
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)

    new_state, results = await harness._skip_enrichment_stage(state)

    assert new_state is state
    assert results == {}
    harness._logger.info.assert_called_once()


# ---------------------------------------------------------------------------
# _finalize_enrichment_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_enrichment_results_when_required_only_false_then_no_not_run_added() -> (
    None
):
    enrichers = [make_enricher_cfg("opt_a", required=False)]
    config = SimpleNamespace(
        name="composite",
        enrichers=enrichers,
        required_enrichers=[],
    )
    harness = _EnrichmentHarness(config=config)
    harness._runtime.required_only = False
    state = make_runner_state(
        state=CompositePipelineState.SEED_COMPLETED,
        enrichment_results={},
    )
    harness._seam_enrichers_to_run = enrichers
    context = harness._prepare_enrichment_run_context(state)

    result = harness._finalize_enrichment_results(
        state=state,
        context=context,
        enrichment_results={},
    )

    # In non-required_only mode: add_not_run_results returns unchanged dict
    assert "opt_a" not in result


@pytest.mark.unit
def test_finalize_enrichment_results_when_checkpoint_has_results_then_merged() -> None:
    enrichers = [make_enricher_cfg("enricher_a")]
    config = SimpleNamespace(
        name="composite",
        enrichers=enrichers,
        required_enrichers=[],
    )
    harness = _EnrichmentHarness(config=config)
    completed_result = success_enrichment("enricher_a")
    state = make_runner_state(
        state=CompositePipelineState.SEED_COMPLETED,
        enrichment_results={"enricher_a": completed_result},
    )
    context = harness._prepare_enrichment_run_context(state)

    result = harness._finalize_enrichment_results(
        state=state,
        context=context,
        enrichment_results={},
    )

    assert "enricher_a" in result


# ---------------------------------------------------------------------------
# _transition_to_enrichment_completed
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transition_to_enrichment_completed_when_enriching_then_calls_complete() -> (
    None
):
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.ENRICHING)
    harness._call_save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await harness._transition_to_enrichment_completed(state)

    harness._observer_logger.info.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transition_to_enrichment_completed_when_seed_completed_then_transitions_through_enriching() -> (
    None
):
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)
    harness._call_save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await harness._transition_to_enrichment_completed(state)

    # FSM log should have been called for enrichment_start_empty
    harness._fsm.log_fsm_transition.assert_not_called()  # our stub replaces it
    state.with_state.assert_called()


# ---------------------------------------------------------------------------
# _save_failed_enrichment_state
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_failed_enrichment_state_when_called_then_logs_error() -> None:
    harness = _EnrichmentHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)
    error = InvalidStateError("Required enricher failed")

    await harness._save_failed_enrichment_state(state, error)

    harness._logger.error.assert_called_once()
    error_args = harness._logger.error.call_args.args[0]
    assert "FAILED" in error_args or "failed" in error_args.lower()


# ---------------------------------------------------------------------------
# _validate_required_enrichment_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_required_enrichment_results_when_all_ok_then_no_exception() -> (
    None
):
    harness = _EnrichmentHarness()
    harness._seam_check_required_raises = False
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)

    await harness._validate_required_enrichment_results(state, {})

    assert harness._required_enricher_check_calls == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_required_enrichment_results_when_required_failed_then_raises() -> (
    None
):
    harness = _EnrichmentHarness()
    harness._seam_check_required_raises = True
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)

    with pytest.raises(InvalidStateError):
        await harness._validate_required_enrichment_results(state, {})
