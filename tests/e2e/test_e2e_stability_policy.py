"""Policy tests for E2E transient retries and cassette resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bioetl.domain.exceptions.network import ExternalServiceError

from .conftest import (
    E2E_FIXED_RUN_ID,
    E2E_FIXED_STARTED_AT,
    _resolve_e2e_provider_cassette_dir,
    build_e2e_run_context,
    build_e2e_skip_reason,
    build_e2e_replay_context,
    create_test_context,
    create_deterministic_test_context,
    _create_retry_run_context,
    assert_bronze_files_exist,
    assert_bronze_metadata_files_exist,
    assert_bronze_payload_files_exist,
    is_strict_persistence_snapshot_gap,
    run_pipeline_or_skip_transient,
    wrap_bootstrap_pipeline_runner_for_e2e,
)
from .test_pipeline_matrix_e2e import (
    ACTIVE_PIPELINE_CASES,
    CRITICAL_SMOKE_PIPELINES,
    MATRIX_REPLAY_DEFERRED_PIPELINES,
    NON_EMPTY_CASSETTE_CONTRACT_PIPELINES,
    PIPELINE_CASES,
    PipelineE2ECase,
    _build_e2e_fail_reason,
    _requires_non_empty_cassette_contract,
    _resolve_cassette_name,
)

pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("strict_dq_env")]


def test_strict_persistence_snapshot_gap_detects_fail_closed_replay_errors() -> None:
    """Strict replay-profile snapshot gaps should be classified deterministically."""
    exc = RuntimeError(
        "Exact replay and strict persistence profiles require immutable input "
        "snapshots; no snapshot-backed source refs were resolved for required "
        "persistence profile 'replay_ready'"
    )
    assert is_strict_persistence_snapshot_gap(exc) is True


def test_strict_persistence_snapshot_gap_ignores_unrelated_runtime_errors() -> None:
    """Unrelated runtime failures must not be classified as snapshot gaps."""
    exc = RuntimeError("Delta write failed because parquet schema is incompatible")
    assert is_strict_persistence_snapshot_gap(exc) is False


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


def test_wrap_bootstrap_pipeline_runner_for_e2e_skips_on_snapshot_gap() -> None:
    """Direct bootstrap imports must classify strict replay-policy gaps as skips."""
    context = create_test_context("chembl_activity", limit=1)

    def _failing_bootstrap(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError(
            "Exact replay and strict persistence profiles require immutable input "
            "snapshots; no snapshot-backed source refs were resolved for required "
            "persistence profile 'replay_ready'"
        )

    guarded_bootstrap = wrap_bootstrap_pipeline_runner_for_e2e(_failing_bootstrap)

    with pytest.raises(pytest.skip.Exception) as exc_info:
        guarded_bootstrap(context)

    skip_text = str(exc_info.value)
    assert "E2E_SKIP[PERSISTENCE_SNAPSHOT_GAP]" in skip_text
    assert "pipeline=chembl_activity" in skip_text


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


@pytest.mark.asyncio
async def test_run_pipeline_or_skip_transient_skips_on_snapshot_gap() -> None:
    """Bootstrap-time snapshot gaps must skip deterministically before retries."""
    context = create_test_context("chembl_activity", limit=1)
    error = RuntimeError(
        "Exact replay and strict persistence profiles require immutable input "
        "snapshots; no snapshot-backed source refs were resolved for required "
        "persistence profile 'replay_ready'"
    )

    with (
        patch(
            "bioetl.composition.bootstrap.bootstrap_pipeline_runner",
            side_effect=error,
        ),
        pytest.raises(pytest.skip.Exception) as exc_info,
    ):
        await run_pipeline_or_skip_transient(context)

    skip_text = str(exc_info.value)
    assert "E2E_SKIP[PERSISTENCE_SNAPSHOT_GAP]" in skip_text
    assert "pipeline=chembl_activity" in skip_text


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


def test_e2e_provider_cassette_dir_override_is_resolved_per_test_name() -> None:
    """Per-test multi-provider cassette overrides must not collapse to module default."""
    provider_dir = _resolve_e2e_provider_cassette_dir(
        node_name="test_chembl_and_uniprot_sequential_run",
        module_path="tests/e2e/test_advanced_scenarios_e2e.py",
    )
    assert provider_dir == "multi_provider"


def test_non_empty_contract_covers_all_matrix_pipelines() -> None:
    """Critical smoke pipelines must enforce non-empty cassette output."""
    declared = {case.pipeline_name for case in PIPELINE_CASES}
    assert CRITICAL_SMOKE_PIPELINES <= declared
    assert NON_EMPTY_CASSETTE_CONTRACT_PIPELINES == CRITICAL_SMOKE_PIPELINES
    assert all(
        _requires_non_empty_cassette_contract(name)
        for name in NON_EMPTY_CASSETTE_CONTRACT_PIPELINES
    )


def test_deferred_matrix_cases_are_excluded_from_default_smoke_parametrization() -> None:
    """Replay-unsupported matrix cases stay declared but are not collected by default."""
    active = {case.pipeline_name for case in ACTIVE_PIPELINE_CASES}
    declared = {case.pipeline_name for case in PIPELINE_CASES}

    assert MATRIX_REPLAY_DEFERRED_PIPELINES <= declared
    assert active.isdisjoint(MATRIX_REPLAY_DEFERRED_PIPELINES)


def test_bronze_payload_assertion_does_not_accept_metadata_only(
    tmp_path: Path,
) -> None:
    """Metadata sidecars are not raw Bronze payload evidence."""
    bronze_path = tmp_path / "output" / "bronze" / "pubchem" / "compound"
    bronze_path.mkdir(parents=True)
    metadata_file = bronze_path / "pubchem_compound_metadata.yaml"
    metadata_file.write_text("records: 1\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="No raw Bronze payload files found"):
        assert_bronze_payload_files_exist(tmp_path, "pubchem", "compound")

    assert assert_bronze_metadata_files_exist(tmp_path, "pubchem", "compound") == [
        metadata_file
    ]
    with pytest.raises(AssertionError, match="No raw Bronze payload files found"):
        assert_bronze_files_exist(tmp_path, "pubchem", "compound")


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
    assert context.started_at == E2E_FIXED_STARTED_AT


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
        run_id_seed=str(E2E_FIXED_RUN_ID),
    )
    ctx2 = build_e2e_run_context(
        "chembl_activity",
        limit=3,
        resume=False,
        run_id_seed=str(E2E_FIXED_RUN_ID),
    )

    assert ctx1.run_id == ctx2.run_id
    assert ctx1.started_at == ctx2.started_at


def test_create_deterministic_test_context_is_stable_for_same_inputs() -> None:
    """Control-plane assertion tests can opt into one stable replay-safe context."""
    ctx1 = create_deterministic_test_context(
        "pubchem_compound",
        limit=5,
        query="aspirin",
    )
    ctx2 = create_deterministic_test_context(
        "pubchem_compound",
        limit=5,
        query="aspirin",
    )

    assert ctx1.run_id == ctx2.run_id
    assert ctx1.started_at == ctx2.started_at == E2E_FIXED_STARTED_AT


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
