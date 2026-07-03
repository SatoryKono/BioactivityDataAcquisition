"""Edge-case unit tests for EnrichmentCoordinatorService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.exceptions import BioETLError
from tests.helpers.clock import FixedClock


def _make_enricher(
    pipeline: str = "crossref_publication",
    *,
    required: bool = False,
    filter_condition: str | None = None,
    timeout_seconds: int = 30,
) -> MagicMock:
    enricher = MagicMock()
    enricher.pipeline = pipeline
    enricher.required = required
    enricher.filter_condition = filter_condition
    enricher.timeout_seconds = timeout_seconds
    return enricher


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_dq_config() -> MagicMock:
    config = MagicMock()
    config.get_enricher_hard_threshold = MagicMock(return_value=0.50)
    return config


@pytest.fixture
def coordinator(
    mock_logger: MagicMock,
    mock_dq_config: MagicMock,
) -> EnrichmentCoordinatorService:
    return EnrichmentCoordinatorService(
        logger=mock_logger,
        dq_config=mock_dq_config,
        max_concurrency=2,
        clock=FixedClock(datetime(2026, 4, 28, 12, 0, tzinfo=UTC)),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_enrichers_returns_empty_when_all_are_completed(
    coordinator: EnrichmentCoordinatorService,
) -> None:
    keys = pl.DataFrame({"doi": ["10.1/a"]})
    enricher = _make_enricher()

    result = await coordinator.run_enrichers(
        keys=keys,
        enrichers=[enricher],
        completed=frozenset({enricher.pipeline}),
        runner_factory=lambda _name, _keys: MagicMock(),
    )

    assert result == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_enrichers_filter_excludes_all_records_marks_skipped(
    coordinator: EnrichmentCoordinatorService,
) -> None:
    keys = pl.DataFrame({"doi": [None, None]})
    enricher = _make_enricher(filter_condition="doi IS NOT NULL")
    runner_factory = MagicMock()

    result = await coordinator.run_enrichers(
        keys=keys,
        enrichers=[enricher],
        completed=frozenset(),
        runner_factory=runner_factory,
    )

    assert result[enricher.pipeline].status == EnrichmentStatus.SKIPPED
    runner_factory.assert_not_called()


@pytest.mark.unit
def test_apply_filter_handles_is_null_case_insensitive(
    coordinator: EnrichmentCoordinatorService,
) -> None:
    keys = pl.DataFrame({"DOI": [None, "10.1/a"]})
    enricher = _make_enricher(filter_condition="doi is null")

    filtered = coordinator._apply_filter(keys, enricher)

    assert len(filtered) == 1
    assert filtered["DOI"][0] is None


@pytest.mark.unit
def test_apply_filter_complex_condition_falls_back_to_original_keys(
    coordinator: EnrichmentCoordinatorService,
    mock_logger: MagicMock,
) -> None:
    keys = pl.DataFrame({"doi": ["10.1/a"]})
    enricher = _make_enricher(filter_condition="doi = '10.1/a'")

    filtered = coordinator._apply_filter(keys, enricher)

    assert filtered.equals(keys)
    mock_logger.warning.assert_called()


@pytest.mark.unit
def test_apply_filter_handles_filter_errors_and_returns_original(
    coordinator: EnrichmentCoordinatorService,
    mock_logger: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keys = pl.DataFrame({"doi": ["10.1/a"]})
    enricher = _make_enricher(filter_condition="doi IS NULL")
    monkeypatch.setattr(
        coordinator,
        "_find_column_case_insensitive",
        MagicMock(side_effect=ValueError("bad filter")),
    )

    filtered = coordinator._apply_filter(keys, enricher)

    assert filtered.equals(keys)
    mock_logger.warning.assert_called()


@pytest.mark.unit
def test_apply_filter_handles_bioetl_errors_with_reason_code(
    coordinator: EnrichmentCoordinatorService,
    mock_logger: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keys = pl.DataFrame({"doi": ["10.1/a"]})
    enricher = _make_enricher(filter_condition="doi IS NULL")
    monkeypatch.setattr(
        coordinator,
        "_find_column_case_insensitive",
        MagicMock(side_effect=BioETLError("domain failure")),
    )

    filtered = coordinator._apply_filter(keys, enricher)

    assert filtered.equals(keys)
    kwargs = mock_logger.warning.call_args.kwargs
    assert kwargs.get("reason_code") == "unexpected_bioetl_error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_single_enricher_optional_bioetl_error_returns_failed(
    coordinator: EnrichmentCoordinatorService,
    mock_logger: MagicMock,
) -> None:
    keys = pl.DataFrame({"chembl_id": ["CHEMBL1"]})
    enricher = _make_enricher(required=False)
    runner = MagicMock()
    runner.run = AsyncMock(side_effect=BioETLError("adapter failed"))

    result = await coordinator._run_single_enricher(
        enricher=enricher,
        keys=keys,
        runner_factory=lambda _pipeline, _keys: runner,
    )

    assert result.status == EnrichmentStatus.FAILED
    assert "adapter failed" in (result.error_message or "")
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.duration_seconds == pytest.approx(
        (result.completed_at - result.started_at).total_seconds(),
        abs=1e-6,
    )
    kwargs = mock_logger.warning.call_args.kwargs
    assert kwargs.get("reason_code") == "unexpected_bioetl_error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_single_enricher_required_bioetl_error_reraises(
    coordinator: EnrichmentCoordinatorService,
    mock_logger: MagicMock,
) -> None:
    keys = pl.DataFrame({"chembl_id": ["CHEMBL1"]})
    enricher = _make_enricher(required=True)
    runner = MagicMock()
    runner.run = AsyncMock(side_effect=BioETLError("required adapter failed"))

    with pytest.raises(BioETLError, match="required adapter failed"):
        await coordinator._run_single_enricher(
            enricher=enricher,
            keys=keys,
            runner_factory=lambda _pipeline, _keys: runner,
        )

    kwargs = mock_logger.error.call_args.kwargs
    assert kwargs.get("reason_code") == "unexpected_bioetl_error"


@pytest.mark.unit
def test_process_results_maps_names_to_results(
    coordinator: EnrichmentCoordinatorService,
) -> None:
    """With fail-fast, _process_results receives only EnrichmentResult values."""
    result = EnrichmentResult.failed(
        enricher_name="crossref_publication",
        error_message="boom",
    )
    processed = coordinator._process_results(
        ["crossref_publication"],
        [result],
    )

    assert processed["crossref_publication"] is result
    assert processed["crossref_publication"].status == EnrichmentStatus.FAILED
