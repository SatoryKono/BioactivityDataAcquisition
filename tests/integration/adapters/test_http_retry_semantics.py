# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration checks for HTTP retry semantics on real adapter paths."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID

from httpx import HTTPStatusError, Request, Response
import pytest
import respx

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.infrastructure.adapters.crossref.client import CROSSREF_API_BASE
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)
from bioetl.domain.resilience import RetryConfig
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


def _build_retrying_http_client(provider: str) -> UnifiedHTTPClient:
    """Build a real UnifiedHTTPClient with deterministic retry behavior."""
    return UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(
            rate=50.0,
            capacity=50.0,
            provider=provider,
        ),
        circuit_breaker=CircuitBreakerGuard(provider=provider),
        retry_config=RetryConfig(
            max_attempts=2,
            base_delay=0.0,
            max_delay=0.0,
            jitter_range=(0.0, 0.0),
        ),
        timeout=10.0,
        provider=provider,
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.mark.integration
async def test_crossref_adapter_retries_retryable_http_status(
    mock_logger: MagicMock,
) -> None:
    """CrossRef adapter should recover from a transient 503 via UnifiedHTTPClient retry."""
    adapter = create_crossref_adapter(
        http_client=_build_retrying_http_client("crossref_retry_semantics"),
        logger=mock_logger,
        settings=None,
        mailto="bioetl-test@example.com",
        batch_size=10,
    )
    call_count = 0

    def _crossref_side_effect(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(
                503,
                request=request,
                json={"status": "error", "message": {"items": []}},
            )
        return Response(
            200,
            request=request,
            json={
                "status": "ok",
                "message": {
                    "items": [
                        {
                            "DOI": "10.1038/nature12373",
                            "title": ["Crystal structure of rhodopsin"],
                        }
                    ]
                },
            },
        )

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        route = respx_mock.get("/works")
        route.side_effect = _crossref_side_effect
        async with adapter._http_client:
            records = [
                record
                async for record in adapter.fetch_filtered(
                    entity_type="publication",
                    filter_ids=["10.1038/nature12373"],
                    filter_field="doi",
                )
            ]

    assert route.call_count == 2
    assert len(records) == 1
    assert records[0]["DOI"] == "10.1038/nature12373"


@pytest.mark.integration
async def test_pubmed_adapter_retries_rate_limit_response(
    mock_logger: MagicMock,
) -> None:
    """PubMed adapter should retry once on a transient 429 and then succeed."""
    adapter = PubMedAdapter(
        http_client=_build_retrying_http_client("pubmed_retry_semantics"),
        logger=mock_logger,
        email="bioetl-test@example.com",
        api_key=None,
        batch_size=100,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )
    call_count = 0
    mock_xml = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>35486828</PMID>
      <Article><ArticleTitle>Retry Success</ArticleTitle></Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

    def _pubmed_side_effect(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(
                429,
                request=request,
                headers={"Retry-After": "0"},
                text="rate limited",
            )
        return Response(200, request=request, text=mock_xml)

    with respx.mock(base_url=ENTREZ_API_BASE) as respx_mock:
        route = respx_mock.get("efetch.fcgi")
        route.side_effect = _pubmed_side_effect
        async with adapter._http_client:
            records = [
                record
                async for record in adapter.fetch_filtered(
                    entity_type="publication",
                    filter_ids=["35486828"],
                    filter_field="pmid",
                )
            ]

    assert route.call_count == 2
    assert len(records) == 1
    assert records[0]["pmid"] == "35486828"


def _build_semanticscholar_adapter(mock_logger: MagicMock) -> SemanticScholarAdapter:
    """Build Semantic Scholar with the real unified retry client."""
    return SemanticScholarAdapter(
        http_client=_build_retrying_http_client("semanticscholar_retry_semantics"),
        logger=mock_logger,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


@pytest.mark.integration
async def test_semanticscholar_search_retries_429_then_succeeds(
    mock_logger: MagicMock,
) -> None:
    """Semantic Scholar search delegates retries to UnifiedHTTPClient."""
    adapter = _build_semanticscholar_adapter(mock_logger)
    call_count = 0

    def _search_side_effect(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(
                429,
                request=request,
                headers={"Retry-After": "0"},
                text="rate limited",
            )
        return Response(
            200,
            request=request,
            json={"data": [{"paperId": "paper-1"}], "next": None},
        )

    with respx.mock(base_url=SEMANTICSCHOLAR_BASE_URL) as respx_mock:
        route = respx_mock.get("/paper/search")
        route.side_effect = _search_side_effect
        async with adapter._http_client:
            records = [
                record
                async for record in adapter.fetch(
                    entity_type="publication",
                    query="bounded retry",
                    limit=1,
                )
            ]

    assert route.call_count == 2
    assert records == [{"paperId": "paper-1"}]


@pytest.mark.integration
async def test_semanticscholar_search_exhausts_exact_request_budget(
    mock_logger: MagicMock,
) -> None:
    """Persistent 429 responses stop at the configured attempt count."""
    adapter = _build_semanticscholar_adapter(mock_logger)

    with respx.mock(base_url=SEMANTICSCHOLAR_BASE_URL) as respx_mock:
        route = respx_mock.get("/paper/search").mock(
            return_value=Response(
                429,
                headers={"Retry-After": "0"},
                text="rate limited",
            )
        )
        async with adapter._http_client:
            with pytest.raises(RetryExhaustedError) as caught:
                _ = [
                    record
                    async for record in adapter.fetch(
                        entity_type="publication",
                        query="bounded retry",
                        limit=1,
                    )
                ]

    assert caught.value.attempts == 2
    assert route.call_count == 2
    assert isinstance(caught.value.last_error, HTTPStatusError)
    assert caught.value.last_error.response.status_code == 429


@pytest.mark.integration
async def test_semanticscholar_retry_wait_is_bounded_and_cancellable(
    mock_logger: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit wait cap bounds retries, and cancellation stops the loop."""
    adapter = _build_semanticscholar_adapter(mock_logger)
    adapter._http_client.retry_config = RetryConfig(
        max_attempts=3,
        base_delay=1,
        max_delay=10,
        max_retry_after_seconds=4,
        jitter_range=(0.0, 0.0),
    )
    sleep = AsyncMock()
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.http.client_retry_mixin.asyncio.sleep", sleep
    )
    with respx.mock(base_url=SEMANTICSCHOLAR_BASE_URL) as router:
        route = router.get("/paper/search").respond(
            429, headers={"Retry-After": "99999"}
        )
        async with adapter._http_client:
            with pytest.raises(RetryExhaustedError) as caught:
                _ = [r async for r in adapter.fetch("publication", query="test")]
            assert caught.value.attempts == 3
            assert route.call_count == 3
            assert sleep.await_args_list == [call(4.0), call(4.0)]
            assert caught.value.last_error.response.headers["Retry-After"] == "99999"
            assert caught.value.url.endswith("/paper/search")
            sleep.reset_mock()
            sleep.side_effect = asyncio.CancelledError
            with pytest.raises(asyncio.CancelledError):
                _ = [r async for r in adapter.fetch("publication", query="test")]
            assert route.call_count == 4
            sleep.assert_awaited_once_with(4.0)


@pytest.mark.integration
async def test_semanticscholar_exhaustion_writes_one_failed_report(
    mock_logger: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real transport exhaustion reaches the runner report and CLI failure policy."""
    from bioetl.application.services.execution.pipeline_run_context_service import (
        PipelineRunContextService,
    )
    from bioetl.application.services.execution.pipeline_run_execution_service import (
        PipelineRunExecutionService,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult,
        RunOptions,
    )
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        map_status_to_exit_code,
    )
    from tests.helpers.clock import FixedClock

    from bioetl.application.services.execution import (
        _pipeline_runner_support as report_support,
    )

    writer = MagicMock(wraps=report_support.write_pipeline_run_report)
    monkeypatch.setattr(report_support, "write_pipeline_run_report", writer)
    adapter = _build_semanticscholar_adapter(mock_logger)

    async def run_search():
        async with adapter._http_client:
            _ = [r async for r in adapter.fetch("publication", query="bounded retry")]

    runner = MagicMock()
    runner.run = AsyncMock(side_effect=run_search)
    runner.shutdown_signal = None
    runner.execution_metrics = {}
    runner.run_id = "00000000-0000-0000-0000-000000010577"
    runner.debug_export_uri = None
    runner.debug_export_hash = None
    runner.manifest_id = None
    factory = MagicMock()
    factory.create.return_value = runner
    factory.contains.return_value = True
    extractor = MagicMock()
    extractor.extract_metrics.return_value = {}
    clock = FixedClock(datetime(2026, 9, 22, tzinfo=UTC))
    service = PipelineRunnerService(
        runner_factory=factory,
        metrics_extractor=extractor,
        logger=mock_logger,
        clock=clock,
        metrics=MagicMock(),
        audit=MagicMock(log_event=AsyncMock()),
        _context_service=PipelineRunContextService(),
        _execution_service=PipelineRunExecutionService(clock=clock),
        run_id_factory=lambda: UUID("00000000-0000-0000-0000-000000010577"),
        report_store=FileRunReportStoreAdapter(),
        report_root=tmp_path,
    )
    with respx.mock(base_url=SEMANTICSCHOLAR_BASE_URL) as router:
        route = router.get("/paper/search").respond(429, headers={"Retry-After": "0"})
        result = await service.run("semanticscholar_publication", options=RunOptions())
    assert route.call_count == 2
    runner.run.assert_awaited_once()
    assert result.status == PipelineRunResult.FAILED
    assert result.error_type == "RetryExhaustedError"
    assert result.records_quarantined == 0
    assert result.run_report_error is None
    from bioetl.interfaces.cli.commands.domains.run.result_flow import (
        finalize_run_result,
    )
    from bioetl.interfaces.cli.commands.domains.run.result_presenter import (
        echo_run_result,
    )

    with pytest.raises(SystemExit) as exit_result:
        finalize_run_result(
            result,
            presenter=echo_run_result,
            status_mapper=map_status_to_exit_code,
            exit_func=sys.exit,
        )
    assert exit_result.value.code != 0
    report = json.loads(Path(result.run_report_json_path).read_text())
    assert report["identity"]["status"] == "failed"
    assert report["identity"]["run_id"] == result.run_id
    writer.assert_called_once()
    reports = list(tmp_path.rglob("pipeline-run-report.json"))
    assert reports == [Path(result.run_report_json_path)]
