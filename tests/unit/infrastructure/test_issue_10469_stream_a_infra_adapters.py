"""Stream A adapter residuals for #10469 / #10517 / #10516."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError, RecoverableError
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import CircuitBreakerState, HealthStatus
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
    ProteinClassLevel,
)
from bioetl.infrastructure.adapters.adapter_error_classifier import (
    AdapterErrorClassifier,
    ErrorCategory,
    classify_exception,
    classify_http_error,
)
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.chembl._client_request_helpers import (
    batch_ids,
    build_filter_in_params,
    build_request_params,
    iter_chembl_as_models,
    process_chembl_response,
    resolve_chembl_dto_model,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_coerce import (
    coerce_int,
    coerce_int_tuple,
    coerce_positive_int,
    coerce_str,
    load_json_if_needed,
    validate_contiguous_levels,
    validated_class_level,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_rows import (
    component_leaf_ids_from_row,
    leaf_ids_from_forensic_value,
    leaf_ids_from_value,
    node_from_row,
)
from bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin import (
    ChemblFetchAdapterMixin,
)
from bioetl.infrastructure.adapters.common._title_fallback_flow import (
    MissingDoiTitleFallbackRequest,
    get_fallback_title,
    iter_missing_doi_fallback_records,
    iter_title_only_fallback_records,
    truncate_title,
)
from bioetl.infrastructure.adapters.circuit_breaker_contract import (
    CircuitBreakerSnapshot,
)
from bioetl.infrastructure.adapters.decorators._circuit_breaker_support import (
    log_failure_recorded,
    log_manual_reset,
    raise_if_circuit_open,
    unhealthy_status_if_circuit_open,
)
from bioetl.infrastructure.adapters.decorators._retry_support import (
    is_retryable_exception,
    raise_retry_exhausted,
    retryable_exception_types,
)
from bioetl.infrastructure.adapters.decorators.circuit_breaker import (
    CircuitBreakerDataSourceDecorator,
)
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client_retry_observability import (
    finalize_request_observability,
    handle_circuit_breaker_trip,
    mark_span_error,
    raise_retry_exhausted as raise_http_retry_exhausted,
    start_request_span,
)
from bioetl.infrastructure.adapters.openalex._client_support import (
    _require_openalex_runtime,
    _resolve_openalex_api_key,
    _resolve_openalex_mailto,
)
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

pytestmark = pytest.mark.unit


class _Span:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}
        self.exceptions: list[Exception] = []
        self.entered = False
        self.exited = False

    def __enter__(self) -> _Span:
        self.entered = True
        return self

    def __exit__(self, *_args: object) -> None:
        self.exited = True
        return None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, exc: Exception) -> None:
        self.exceptions.append(exc)


class _OpenBreaker:
    def snapshot(self) -> CircuitBreakerSnapshot:
        return CircuitBreakerSnapshot(
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            recovery_timeout=5.0,
            last_failure_time=None,
        )

    def get_state(self) -> CircuitBreakerState:
        return CircuitBreakerState.OPEN

    def get_failure_count(self) -> int:
        return 3


class _ClosedBreaker:
    def snapshot(self) -> CircuitBreakerSnapshot:
        return CircuitBreakerSnapshot(
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            recovery_timeout=5.0,
            last_failure_time=None,
        )

    def get_state(self) -> CircuitBreakerState:
        return CircuitBreakerState.CLOSED

    def get_failure_count(self) -> int:
        return 0


def test_openalex_client_support_resolves_settings_and_requires_runtime() -> None:
    secret = SimpleNamespace(get_secret_value=lambda: "oa-secret")
    settings = SimpleNamespace(openalex_api_key=secret, default_email="a@b.c")
    assert _resolve_openalex_api_key(settings, {}) == "oa-secret"
    assert _resolve_openalex_api_key(SimpleNamespace(openalex_api_key="plain"), {}) == (
        "plain"
    )
    assert _resolve_openalex_api_key(None, {}) is None
    assert _resolve_openalex_api_key(SimpleNamespace(openalex_api_key=None), {}) is None
    assert _resolve_openalex_mailto(settings, {}) == "a@b.c"
    assert _resolve_openalex_mailto(None, {}) is None
    assert _resolve_openalex_mailto(SimpleNamespace(default_email=None), {}) is None
    assert _resolve_openalex_mailto(settings, {"mailto": "kw@b.c"}) == "kw@b.c"

    logger = MagicMock()
    http = MagicMock()
    with pytest.raises(ValueError, match="requires http_client"):
        _require_openalex_runtime(None, logger, {"fallback_fetch_service": object()})
    with pytest.raises(ValueError, match="requires logger"):
        _require_openalex_runtime(http, None, {"fallback_fetch_service": object()})
    with pytest.raises(ValueError, match="requires fallback_fetch_service"):
        _require_openalex_runtime(http, logger, {})


def test_protein_classification_coerce_and_row_parsers() -> None:
    assert load_json_if_needed({"a": 1}) == {"a": 1}
    assert load_json_if_needed("  ") is None
    assert load_json_if_needed("[1, 2]") == [1, 2]
    with pytest.raises(ProteinClassificationResolutionError, match="canonical JSON"):
        load_json_if_needed("{")
    assert coerce_int_tuple("1,2") == ()
    assert coerce_int_tuple([1, 0, 1, "2", None, True, 2.5, "x"]) == (1, 2)
    assert coerce_int(1.0) == 1
    assert coerce_int(1.5) is None
    assert coerce_int("  ") is None
    assert coerce_int({}) is None
    assert coerce_positive_int(0) is None
    assert coerce_positive_int(3) == 3
    assert coerce_str(None) is None
    assert coerce_str("  ") is None
    node = SimpleNamespace(class_level=None, protein_class_id=9)
    with pytest.raises(
        ProteinClassificationResolutionError, match="missing class_level"
    ):
        validated_class_level(node, leaf_id=9)
    node.class_level = 0
    with pytest.raises(ProteinClassificationResolutionError, match="must be >= 1"):
        validated_class_level(node, leaf_id=9)
    node.class_level = 99
    with pytest.raises(ProteinClassificationResolutionError, match="exceeds"):
        validated_class_level(node, leaf_id=9)
    node.class_level = 2
    assert validated_class_level(node, leaf_id=9) == 2
    with pytest.raises(ProteinClassificationResolutionError, match="no protein"):
        validate_contiguous_levels({}, leaf_id=1)
    with pytest.raises(ProteinClassificationResolutionError, match="broken"):
        validate_contiguous_levels(
            {1: ProteinClassLevel(1, "a", None), 3: ProteinClassLevel(3, "c", None)},
            leaf_id=1,
        )
    validate_contiguous_levels(
        {1: ProteinClassLevel(1, "a", None), 2: ProteinClassLevel(2, "b", None)},
        leaf_id=2,
    )

    assert node_from_row({"protein_class_id": 0}) is None
    parsed = node_from_row(
        {
            "protein_class_id": "4",
            "parent_id": "1",
            "class_level": "2",
            "pref_name": " Kinase ",
        }
    )
    assert parsed is not None and parsed.protein_class_id == 4
    assert component_leaf_ids_from_row({"component_id": 0}) == (None, ())
    assert component_leaf_ids_from_row(
        {"component_id": 8, "protein_classification_ids": "[3, 3]"}
    ) == (8, (3,))
    with pytest.raises(ProteinClassificationResolutionError):
        leaf_ids_from_value("{")
    assert leaf_ids_from_value(None) == ()
    assert leaf_ids_from_value("  ") == ()
    assert leaf_ids_from_value([4, 5]) == (4, 5)
    assert leaf_ids_from_forensic_value(None) == ()
    assert leaf_ids_from_forensic_value({"x": 1}) == ()
    assert leaf_ids_from_forensic_value(
        [{"protein_classification_id": 7}, {"protein_classification_id": 0}]
    ) == (7,)


@pytest.mark.asyncio
async def test_chembl_fetch_mixin_and_request_helpers() -> None:
    from bioetl.domain.models.filter import ExtractionParams

    params = build_request_params(
        offset=10,
        entity_type="protein_class",
        page_size=50,
        extraction_params=ExtractionParams.empty(),
    )
    assert "limit" not in params
    filled = build_request_params(
        offset=10,
        entity_type="activity",
        page_size=50,
        extraction_params=ExtractionParams(params={"molecule_chembl_id": "CHEMBL1"}),
    )
    assert filled["limit"] == 50
    assert list(batch_ids(["a", "b", "c"], 2)) == [["a", "b"], ["c"]]
    assert build_filter_in_params({"id": [], "x": ["1"]}) == {"x__in": "1"}
    with pytest.raises(ValueError, match="No DTO model"):
        resolve_chembl_dto_model("unknown")
    mapper = SimpleNamespace(
        get_plural_key=lambda entity: "activities",
    )
    response = SimpleNamespace(
        json=lambda: {
            "activities": [
                {"document_chembl_id": "CHEMBLDOC1"},
                {"publication_id": "keep"},
            ],
            "page_meta": {"next": None},
        }
    )
    records, has_next = process_chembl_response(
        response=response,
        entity_type="publication",
        mapper=mapper,  # type: ignore[arg-type]
    )
    assert records[0]["publication_id"] == "CHEMBLDOC1"
    assert has_next is False

    async def _fetch(**_kwargs: object):
        yield {"activity_id": "A1", "molecule_id": "CHEMBL1"}

    models = [
        model
        async for model in iter_chembl_as_models(
            fetch_fn=_fetch,
            entity_type="activity",
            limit=1,
            query=None,
            filter_ids=None,
            filter_field=None,
            validate=False,
        )
    ]
    assert models[0].activity_id == "A1"

    class _Host(ChemblFetchAdapterMixin):
        def __init__(self) -> None:
            self.filtered: list[tuple[object, ...]] = []
            self.standard: list[tuple[object, ...]] = []

        async def _fetch_filtered(
            self,
            entity_type: str,
            limit: int | None,
            filter_ids: list[str],
            filter_field: str,
        ):
            self.filtered.append((entity_type, limit, tuple(filter_ids), filter_field))
            yield {"id": "f"}

        async def _fetch_standard(
            self, entity_type: str, limit: int | None, offset: int = 0
        ):
            self.standard.append((entity_type, limit, offset))
            yield {"id": "s"}

    host = _Host()
    filtered = [
        row
        async for row in host.fetch(
            "activity",
            limit=2,
            filter_ids=["1"],
            filter_field="molecule_chembl_id",
        )
    ]
    assert filtered == [{"id": "f"}]
    standard = [row async for row in host.fetch("activity", offset=5)]
    assert standard == [{"id": "s"}]
    fallback = [
        row
        async for row in host.fetch_filtered_with_fallback(
            "activity",
            ["1"],
            "molecule_chembl_id",
            {"1": "ignored"},
        )
    ]
    assert fallback == [{"id": "f"}]


@pytest.mark.asyncio
async def test_chembl_standard_fetch_stops_at_limit() -> None:
    class _Host(ChemblFetchAdapterMixin):
        _logger = MagicMock()
        _adapter_metrics = None

        def _get_api_pk_field(self, _entity_type: str) -> str:
            return "activity_id"

        def _get_api_dedup_fields(self, _entity_type: str) -> tuple[str, ...]:
            return ("activity_id",)

        def _compute_composite_key(
            self, record: dict[str, Any], pk_fields: tuple[str, ...]
        ) -> str:
            return str(record[pk_fields[0]])

        async def _page_iterator(
            self, _entity_type: str, _limit: int | None, start_offset: int = 0
        ):
            del start_offset
            yield [
                {"activity_id": "1"},
                {"activity_id": "1"},
                {"activity_id": "2"},
            ]

    host = _Host()
    rows = [row async for row in host._fetch_standard("activity", limit=1)]
    assert rows == [{"activity_id": "1"}]


def test_adapter_error_classifier_fallback_and_wrappers() -> None:
    logger = MagicMock()
    typed = AdapterErrorClassifier(
        classifier=SimpleNamespace(  # type: ignore[arg-type]
            classify=lambda _error: SimpleNamespace(
                value="OTHER",
                is_critical=lambda: False,
                is_recoverable=lambda: False,
                is_data_quality=lambda: False,
            )
        ),
        logger=logger,
    )
    assert typed.classify(error=ValueError("x")) is ErrorCategory.RECOVERABLE
    logger.warning.assert_called()
    assert classify_http_error(200, logger=logger) is ErrorCategory.RECOVERABLE
    from bioetl.domain.error_classifier import ErrorClassifier

    real = AdapterErrorClassifier(classifier=ErrorClassifier(), logger=logger)
    assert classify_exception(
        ValueError("bad"), classifier=ErrorClassifier(), logger=logger
    ) is (ErrorCategory.DATA_QUALITY)
    assert real.classify(error=ValueError("bad")) is ErrorCategory.DATA_QUALITY


def test_retry_and_circuit_support_helpers() -> None:
    config = RetryConfig(retryable_exceptions=(TimeoutError,))
    assert (
        is_retryable_exception(CircuitBreakerOpenError("chembl", retry_after=1), config)
        is False
    )
    assert is_retryable_exception(RecoverableError("retry"), config) is True
    assert Exception in retryable_exception_types(
        RetryConfig(retryable_exceptions=(Exception,))
    )
    metrics = MagicMock()
    with pytest.raises(Exception, match="Exhausted"):
        raise_retry_exhausted(
            metrics=metrics,
            provider_name="chembl",
            operation="fetch",
            retries=2,
            target="activity",
            max_attempts=3,
            last_error=TimeoutError("down"),
        )
    metrics.increment_counter.assert_called()

    logger = MagicMock()
    raise_if_circuit_open(
        circuit_breaker=_ClosedBreaker(),  # type: ignore[arg-type]
        provider_name="chembl",
        logger=logger,
    )
    with pytest.raises(CircuitBreakerOpenError):
        raise_if_circuit_open(
            circuit_breaker=_OpenBreaker(),  # type: ignore[arg-type]
            provider_name="chembl",
            logger=logger,
        )
    log_failure_recorded(
        None,
        circuit_breaker=_ClosedBreaker(),  # type: ignore[arg-type]
        provider_name="chembl",
        error=RuntimeError("x"),
    )
    log_failure_recorded(
        logger,
        circuit_breaker=_ClosedBreaker(),  # type: ignore[arg-type]
        provider_name="chembl",
        error=RuntimeError("x"),
    )
    assert (
        unhealthy_status_if_circuit_open(
            circuit_breaker=_ClosedBreaker(),  # type: ignore[arg-type]
            provider_name="chembl",
            logger=logger,
        )
        is None
    )
    assert (
        unhealthy_status_if_circuit_open(
            circuit_breaker=_OpenBreaker(),  # type: ignore[arg-type]
            provider_name="chembl",
            logger=logger,
        )
        is HealthStatus.UNHEALTHY
    )
    log_manual_reset(None, provider_name="chembl")
    log_manual_reset(logger, provider_name="chembl")


@pytest.mark.asyncio
async def test_circuit_breaker_decorator_success_race_and_health() -> None:
    source = SimpleNamespace(
        provider_name="chembl",
        health_check=AsyncMock(return_value=HealthStatus.HEALTHY),
        aclose=AsyncMock(),
    )
    breaker = MagicMock()
    breaker.get_state.return_value = CircuitBreakerState.CLOSED
    breaker.get_failure_count.return_value = 2
    breaker.snapshot.return_value = CircuitBreakerSnapshot(
        state=CircuitBreakerState.CLOSED,
        failure_count=0,
        recovery_timeout=1.0,
        last_failure_time=None,
    )
    breaker.call = AsyncMock(
        side_effect=CircuitBreakerOpenError("chembl", retry_after=1.0)
    )
    breaker.reset = MagicMock()
    decorator = CircuitBreakerDataSourceDecorator(
        data_source=source,  # type: ignore[arg-type]
        circuit_breaker=breaker,
        logger=MagicMock(),
    )
    await decorator._record_fetch_success()
    assert await decorator.health_check() is HealthStatus.UNHEALTHY
    await decorator.aclose()
    source.aclose.assert_awaited()
    assert decorator.get_failure_count() == 2
    decorator.reset_circuit()
    breaker.reset.assert_called_once()


@pytest.mark.asyncio
async def test_http_retry_observability_and_http_circuit_snapshot() -> None:
    noop = start_request_span(
        None, provider="chembl", run_id=None, method="GET", url="http://x"
    )
    mark_span_error(noop, "timeout")
    span = _Span()
    mark_span_error(span, "boom", RuntimeError("x"))
    assert span.exceptions

    class _Tracer:
        def get_tracer(self, _name: str) -> SimpleNamespace:
            return SimpleNamespace(start_as_current_span=lambda *_a, **_k: _Span())

    traced = start_request_span(
        _Tracer(),  # type: ignore[arg-type]
        provider="chembl",
        run_id=None,
        method="POST",
        url="http://x",
    )
    recorded: list[tuple[object, ...]] = []
    finalize_request_observability(
        traced,
        SimpleNamespace(retries=1, status_code=200, attempts_made=2, last_error=None),
        method="POST",
        start_time=0.0,
        record_metrics=lambda *args: recorded.append(args),
    )
    assert recorded
    with pytest.raises(Exception, match="Exhausted"):
        raise_http_retry_exhausted(
            "http://x",
            SimpleNamespace(last_error=TimeoutError("x"), attempts_made=3),
            span,
        )
    logger = MagicMock()
    handle_circuit_breaker_trip(
        CircuitBreakerOpenError("chembl", retry_after=2.0),
        method="GET",
        url="http://x",
        span=span,
        provider="chembl",
        run_id="run-1",
        logger=logger,
    )
    handle_circuit_breaker_trip(
        CircuitBreakerOpenError("chembl", retry_after=2.0),
        method="GET",
        url="http://x",
        span=span,
        provider="chembl",
        run_id="run-1",
        logger=None,
    )
    guard = CircuitBreakerGuard(provider="chembl")
    assert guard.get_last_failure_time() is None
    guard.force_open()
    assert guard.get_last_failure_time() is not None
    snapshot = guard.snapshot()
    assert snapshot.state is CircuitBreakerState.OPEN


@pytest.mark.asyncio
async def test_health_check_mixin_and_sync_base_leftovers() -> None:
    class _Adapter(HealthCheckProviderMixin):
        provider_name = "chembl"
        logger = MagicMock()
        _logger = logger
        metrics = None

        @property
        def _circuit_breaker(self) -> object:
            return SimpleNamespace(
                get_state=lambda: CircuitBreakerState.CLOSED,
                get_failure_count=lambda: 0,
            )

    adapter = _Adapter()
    assert adapter._get_health_endpoint() == ""
    assert adapter._get_metrics() is None
    ctx = adapter._start_health_check()
    status = await adapter._probe_health()
    assert status in {
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.UNHEALTHY,
    }
    adapter._handle_health_check_result(ctx, HealthStatus.HEALTHY)
    adapter._get_error_context("fetch")
    result = await adapter.check_health()
    assert result.provider == "chembl"

    class _Failing(_Adapter):
        async def _probe_health(self) -> HealthStatus:
            raise TimeoutError("down")

    failing = _Failing()
    failed = await failing.check_health()
    assert failed.status is not HealthStatus.HEALTHY

    with pytest.raises(TypeError, match="unexpected kwargs"):
        BaseSyncAdapter(
            logger=MagicMock(),
            rate_limiter=MagicMock(),
            circuit_breaker=MagicMock(),
            thread_pool=ThreadPoolExecutor(max_workers=1),
            error_handler=MagicMock(),
            unexpected=True,
        )
    pool = ThreadPoolExecutor(max_workers=1)
    sync = BaseSyncAdapter(
        logger=MagicMock(),
        rate_limiter=MagicMock(),
        circuit_breaker=MagicMock(),
        thread_pool=pool,
        error_handler=MagicMock(),
        owns_thread_pool=False,
        metrics=MagicMock(),
    )
    async with sync:
        await sync.aclose()
    pool.shutdown(wait=False)


@pytest.mark.asyncio
async def test_title_fallback_flow_errors_and_title_only_limits() -> None:
    logger = MagicMock()
    request = MissingDoiTitleFallbackRequest(
        dois=["DOI-1"],
        found_dois=set(),
        fallback_mapping={"doi-1": "Title"},
        normalize_fn=lambda value: value.lower(),
        limit=0,
        fetched=0,
        get_fallback_title=get_fallback_title,
        truncate_title=truncate_title,
        search_by_title=AsyncMock(return_value=None),
        get_result_identifier=lambda row: ("id", row["id"]),
        process_found_result=lambda row, doi: row,
        logger=logger,
        event_no_fallback_title="no_title",
        event_fallback_attempt="attempt",
        event_fallback_success="ok",
        event_fallback_not_found="missing",
    )
    with pytest.raises(TypeError, match="unexpected keyword"):
        async for _row in iter_missing_doi_fallback_records(request, dois=["x"]):
            raise AssertionError("should not yield")
    with pytest.raises(TypeError, match="unexpected keyword"):
        async for _row in iter_missing_doi_fallback_records(unknown=1):
            raise AssertionError("should not yield")
    empty = [row async for row in iter_missing_doi_fallback_records(request)]
    assert empty == []

    async def _search(title: str):
        return None if title == "skip" else {"id": title}

    rows = [
        row
        async for row in iter_title_only_fallback_records(
            entries=["missing", "__title_only_1__", "second"],
            fallback_mapping={"__title_only_1__": "keep", "second": "skip"},
            limit=1,
            fetched=0,
            truncate_title=truncate_title,
            search_by_title=_search,
            get_result_identifier=lambda row: ("id", row["id"]),
            process_title_only_result=lambda row: row,
            logger=logger,
            event_title_only_attempt="attempt",
            event_title_only_success="ok",
            event_title_only_not_found="missing",
        )
    ]
    assert rows == [{"id": "keep"}]


def test_base_metrics_none_port_and_zero_fallback() -> None:
    recorder = AdapterMetricsRecorder(metrics=None, provider="chembl")
    recorder.record_batch_size("/activity", 10)
    recorder.record_dropped_duplicates("activity", 2)
    recorder.record_fallback_outcome("title", candidates=0, hits=3)
    recorder.record_fallback_outcome("title", candidates=-1, hits=1)
    metrics = MagicMock()
    with_metrics = AdapterMetricsRecorder(metrics=metrics, provider="chembl")
    with_metrics.record_fallback_outcome("title", candidates=2, hits=0)


@pytest.mark.asyncio
async def test_crossref_fetch_flow_and_doi_batch_edges() -> None:
    from bioetl.infrastructure.adapters.crossref._doi_batch_processor import (
        DoiBatchProcessor,
    )
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.adapters.crossref.response_mapper import (
        CrossRefResponseMapper,
    )

    logger = MagicMock()
    mapper = CrossRefResponseMapper()
    batch_fetcher = SimpleNamespace(
        fetch_batch=lambda dois: _aiter([{"DOI": doi} for doi in dois])
    )

    async def _search(query: str, limit: int | None):
        yield {"query": query, "limit": limit}

    flow = CrossRefFetchFlow(
        logger=logger,
        batch_fetcher=batch_fetcher,  # type: ignore[arg-type]
        search_paginator=SimpleNamespace(search=_search),  # type: ignore[arg-type]
        fallback_decorator=SimpleNamespace(),
        batch_size=1,
        response_mapper=mapper,
    )
    warned = [
        row
        async for row in flow.fetch_filtered(
            "publication",
            ["10.1/a", "10.2/b"],
            "pmid",
            limit=1,
        )
    ]
    assert len(warned) == 1
    logger.warning.assert_called()
    with pytest.raises(ValueError, match="filter_ids|query"):
        async for _row in flow.fetch("publication"):
            raise AssertionError("should not yield")
    searched = [row async for row in flow.fetch("publication", query="kinase")]
    assert searched[0]["query"] == "kinase"

    processor = DoiBatchProcessor(
        http=SimpleNamespace(get=AsyncMock(return_value=None)),
        logger=logger,
        metrics=SimpleNamespace(measure_request=lambda *_a, **_k: nullcontext()),
        mailto="a@b.c",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {},
    )
    assert await processor.fetch_single("   ") is None
    assert [row async for row in processor.fetch_batch([])] == []
    assert [row async for row in processor.fetch_batch(["   "])] == []


async def _aiter(items: list[dict[str, str]]):
    for item in items:
        yield item
