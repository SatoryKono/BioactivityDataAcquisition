"""Policy tests for E2E transient retries and cassette resolution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bioetl.domain.exceptions.network import ExternalServiceError

from .conftest import (
    build_e2e_run_context,
    build_e2e_skip_reason,
    build_e2e_replay_context,
    create_test_context,
    _create_retry_run_context,
    run_pipeline_or_skip_transient,
)
from .test_pipeline_matrix_e2e import (
    CRITICAL_SMOKE_PIPELINES,
    NON_EMPTY_CASSETTE_CONTRACT_PIPELINES,
    PIPELINE_CASES,
    PipelineE2ECase,
    _build_e2e_fail_reason,
    _requires_non_empty_cassette_contract,
    _resolve_cassette_name,
)

pytestmark = pytest.mark.e2e


def test_build_e2e_skip_reason_is_deterministic() -> None:
    """Skip reason format must stay parseable for CI classification."""
    reason = build_e2e_skip_reason(
        "INFRA_FLAKY_429",
        pipeline_name="semanticscholar_publication",
        detail="transient upstream 429",
    )
    assert reason.startswith("E2E_SKIP[INFRA_FLAKY_429] pipeline=")
    assert "semanticscholar_publication" in reason
    assert "transient upstream 429" in reason


@pytest.mark.asyncio
async def test_run_pipeline_or_skip_transient_retries_then_succeeds() -> None:
    """Transient upstream errors should retry before succeeding."""
    context = create_test_context("chembl_activity", limit=1)
    transient_error = ExternalServiceError(
        "Too Many Requests",
        service_name="chembl",
        status_code=429,
    )
    failing_runner = MagicMock()
    failing_runner.run = AsyncMock(side_effect=transient_error)
    successful_runner = MagicMock()
    successful_runner.run = AsyncMock(return_value=None)

    with (
        patch(
            "bioetl.composition.bootstrap.bootstrap_pipeline_runner",
            side_effect=[failing_runner, successful_runner],
        ) as mock_bootstrap,
        patch("tests.e2e.conftest.asyncio.sleep", new=AsyncMock()) as mock_sleep,
    ):
        runner = await run_pipeline_or_skip_transient(context)

    assert runner is successful_runner
    assert mock_bootstrap.call_count == 2
    mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_pipeline_or_skip_transient_skips_after_retry_exhaustion() -> None:
    """Transient upstream 429 must produce deterministic skip reason when exhausted."""
    context = create_test_context("semanticscholar_publication", limit=1)
    request = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper")
    response = httpx.Response(429, request=request)
    error = httpx.HTTPStatusError(
        "429 Too Many Requests", request=request, response=response
    )
    flaky_runner = MagicMock()
    flaky_runner.run = AsyncMock(side_effect=error)

    with (
        patch(
            "bioetl.composition.bootstrap.bootstrap_pipeline_runner",
            side_effect=[flaky_runner, flaky_runner, flaky_runner],
        ),
        patch("tests.e2e.conftest.asyncio.sleep", new=AsyncMock()),
        pytest.raises(pytest.skip.Exception) as exc_info,
    ):
        await run_pipeline_or_skip_transient(context)

    skip_text = str(exc_info.value)
    assert "E2E_SKIP[INFRA_FLAKY_429]" in skip_text
    assert "pipeline=semanticscholar_publication" in skip_text


def test_resolve_cassette_name_uses_matrix_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matrix fallback cassette should be used when explicit candidates are absent."""
    monkeypatch.setenv("VCR_RECORD_MODE", "none")
    case = PipelineE2ECase(
        pipeline_name="chembl_protein_class",
        provider="chembl",
        entity="protein_class",
    )
    assert _resolve_cassette_name(case) == "test_pipeline_matrix__chembl_protein_class"


def test_non_empty_contract_covers_all_matrix_pipelines() -> None:
    """Critical smoke pipelines must enforce non-empty cassette output."""
    declared = {case.pipeline_name for case in PIPELINE_CASES}
    assert CRITICAL_SMOKE_PIPELINES <= declared
    assert NON_EMPTY_CASSETTE_CONTRACT_PIPELINES == CRITICAL_SMOKE_PIPELINES
    assert all(
        _requires_non_empty_cassette_contract(name)
        for name in NON_EMPTY_CASSETTE_CONTRACT_PIPELINES
    )


def test_build_e2e_fail_reason_is_deterministic() -> None:
    """Failure reason format must stay parseable for CI classification."""
    reason = _build_e2e_fail_reason(
        "CODE_REGRESSION",
        pipeline_name="chembl_activity",
        detail="error_type=RuntimeError; boom",
    )
    assert reason.startswith("E2E_FAIL[CODE_REGRESSION] pipeline=")
    assert "chembl_activity" in reason
    assert "error_type=RuntimeError; boom" in reason


def test_create_test_context_initializes_started_at() -> None:
    """E2E test contexts must not inherit the sentinel runtime timestamp."""
    context = create_test_context("chembl_activity", limit=1)
    assert context.started_at.isoformat() == "2026-04-28T12:00:00+00:00"


def test_create_test_context_uses_unique_occurrence_run_ids() -> None:
    """Repeated E2E contexts must not collide in control-plane run-id indexes."""
    ctx1 = create_test_context("chembl_activity", limit=3, resume=False)
    ctx2 = create_test_context("chembl_activity", limit=3, resume=False)

    assert ctx1.run_id != ctx2.run_id
    assert ctx1.started_at == ctx2.started_at


def test_build_e2e_run_context_accepts_explicit_deterministic_seed() -> None:
    """Tests that need stable replay IDs must opt in with an explicit seed."""
    ctx1 = build_e2e_run_context(
        "chembl_activity",
        limit=3,
        resume=False,
        run_id_seed="stable-case",
    )
    ctx2 = build_e2e_run_context(
        "chembl_activity",
        limit=3,
        resume=False,
        run_id_seed="stable-case",
    )

    assert ctx1.run_id == ctx2.run_id
    assert ctx1.started_at == ctx2.started_at


def test_retry_run_context_uses_deterministic_attempt_seed() -> None:
    """Retry contexts must derive stable per-attempt IDs instead of uuid4()."""
    context = create_test_context("chembl_activity", limit=1)

    retry1 = _create_retry_run_context(context, 1)
    retry1_again = _create_retry_run_context(context, 1)
    retry2 = _create_retry_run_context(context, 2)

    assert retry1.run_id == retry1_again.run_id
    assert retry1.run_id != context.run_id
    assert retry2.run_id != retry1.run_id
    assert retry1.started_at == context.started_at


def test_build_e2e_replay_context_tracks_parentage_deterministically() -> None:
    """Replay helper must preserve deterministic timestamps and parent links."""
    context = create_test_context("chembl_activity", limit=2)

    replay = build_e2e_replay_context(
        context,
        replay_of_manifest_id="manifest-123",
    )

    assert replay.replay_of_run_id == str(context.run_id)
    assert replay.replay_of_manifest_id == "manifest-123"
    assert replay.run_id != context.run_id
    assert replay.started_at == context.started_at
