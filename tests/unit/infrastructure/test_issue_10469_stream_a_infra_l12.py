"""Stream A L12 infrastructure residuals for #10469 / #10516."""

from __future__ import annotations

import errno
from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError, MetricsServerError
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref._search_paginator import SearchPaginator
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
)
from bioetl.infrastructure.adapters.decorators._retry_operations import (
    retry_fetch_records,
    retry_health_check,
)
from bioetl.infrastructure.adapters.openalex.cursor_flow import OpenAlexCursorFlow
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_identifiers import (
    _PubChemIdentifierFetchMixin,
)
from bioetl.infrastructure.observability._metrics_server_startup import (
    start_metrics_server_runtime,
)
from bioetl.infrastructure.observability._metrics_server_state import reset_server_state
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger
from bioetl.infrastructure.quarantine.filtered_read_support import (
    _build_payload_preview,
    _clamp_limit,
    _normalize_error_details,
    _normalize_filter_values,
    _normalize_timestamp,
    _single_filter_value,
)

pytestmark = pytest.mark.unit


class _PublicationMetric:
    def labels(self, **_labels: str) -> SimpleNamespace:
        return SimpleNamespace(inc=lambda: None)


def _paginator(http: object) -> SearchPaginator:
    return SearchPaginator(
        http=http,  # type: ignore[arg-type]
        logger=MagicMock(),
        metrics=SimpleNamespace(measure_request=lambda *_a, **_k: nullcontext()),
        mailto="a@b.c",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {"ua": "test"},
    )


@pytest.mark.asyncio
async def test_crossref_search_no_response_and_non_dict_items() -> None:
    http = SimpleNamespace(get=AsyncMock(return_value=None))
    with pytest.raises(CrossRefApiError, match="no response"):
        async for _row in _paginator(http).search("kinase"):
            raise AssertionError("should not yield")

    response = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "message": {
                "items": [{"DOI": "10.1/x"}, "skip", 3],
                "next-cursor": 12,
            }
        },
    )
    http.get = AsyncMock(return_value=response)
    rows = [row async for row in _paginator(http).search("kinase")]
    assert rows == [{"DOI": "10.1/x"}]


@pytest.mark.asyncio
async def test_retry_fetch_records_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    async def _delegated(_source: object, _request: object):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("flaky")
            yield {}  # pragma: no cover
        yield {"id": "ok"}

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators._retry_operations.iter_delegated_fetch",
        _delegated,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators._retry_operations.calculate_and_wait_retry_delay",
        AsyncMock(return_value=0.0),
    )
    request = DataSourceFetchRequest(entity_type="activity")
    rows = [
        row
        async for row in retry_fetch_records(
            data_source=SimpleNamespace(),  # type: ignore[arg-type]
            retry_config=RetryConfig(
                max_attempts=3,
                retryable_exceptions=(TimeoutError,),
                base_delay=0.0,
                jitter_range=(0.0, 0.0),
            ),
            logger=MagicMock(),
            metrics=None,
            provider_name="chembl",
            request=request,
        )
    ]
    assert rows == [{"id": "ok"}]
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_retry_fetch_does_not_restart_after_emit_and_opens_circuit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _emitted(_source: object, _request: object):
        yield {"id": "first"}
        raise TimeoutError("after-emit")

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators._retry_operations.iter_delegated_fetch",
        _emitted,
    )
    request = DataSourceFetchRequest(entity_type="activity")
    agen = retry_fetch_records(
        data_source=SimpleNamespace(),  # type: ignore[arg-type]
        retry_config=RetryConfig(retryable_exceptions=(TimeoutError,)),
        logger=None,
        metrics=None,
        provider_name="chembl",
        request=request,
    )
    assert await anext(agen) == {"id": "first"}
    with pytest.raises(TimeoutError, match="after-emit"):
        await anext(agen)

    async def _open(_source: object, _request: object):
        raise CircuitBreakerOpenError("chembl", retry_after=1.0)
        yield {}  # pragma: no cover

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators._retry_operations.iter_delegated_fetch",
        _open,
    )
    with pytest.raises(CircuitBreakerOpenError):
        async for _row in retry_fetch_records(
            data_source=SimpleNamespace(),  # type: ignore[arg-type]
            retry_config=RetryConfig(),
            logger=None,
            metrics=None,
            provider_name="chembl",
            request=request,
        ):
            pass


@pytest.mark.asyncio
async def test_retry_health_check_retries_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    states = {"n": 0}

    async def _health() -> object:
        states["n"] += 1
        if states["n"] == 1:
            raise TimeoutError("down")
        return HealthStatus.HEALTHY

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators._retry_operations.calculate_and_wait_retry_delay",
        AsyncMock(return_value=0.0),
    )
    result = await retry_health_check(
        health_check_fn=_health,  # type: ignore[arg-type]
        retry_config=RetryConfig(
            max_attempts=2,
            retryable_exceptions=(TimeoutError,),
            base_delay=0.0,
            jitter_range=(0.0, 0.0),
        ),
        logger=MagicMock(),
        metrics=None,
        provider_name="chembl",
    )
    assert result is HealthStatus.HEALTHY


def test_metrics_server_runtime_handles_in_use_and_os_errors() -> None:
    reset_server_state()
    metric = _PublicationMetric()
    logger = MagicMock()

    in_use = OSError("busy")
    in_use.errno = errno.EADDRINUSE
    with pytest.raises(MetricsServerError, match="port_in_use"):
        start_metrics_server_runtime(
            start_http_server_fn=MagicMock(side_effect=in_use),
            sleep_fn=lambda _delay: None,
            publication_metric=metric,
            fail_fast=True,
            logger=logger,
        )

    reset_server_state()
    assert (
        start_metrics_server_runtime(
            start_http_server_fn=MagicMock(side_effect=in_use),
            sleep_fn=lambda _delay: None,
            publication_metric=metric,
            fail_fast=False,
            logger=logger,
        )
        is False
    )

    reset_server_state()
    other = OSError("reset")
    other.errno = errno.ECONNRESET
    sleeper = MagicMock()
    starter = MagicMock(side_effect=[other, other, other])
    assert (
        start_metrics_server_runtime(
            start_http_server_fn=starter,
            sleep_fn=sleeper,
            publication_metric=metric,
            fail_fast=False,
            retry_count=3,
            retry_delay=0.0,
            logger=logger,
        )
        is False
    )
    assert sleeper.call_count == 2

    reset_server_state()
    with pytest.raises(MetricsServerError, match="unexpected"):
        start_metrics_server_runtime(
            start_http_server_fn=MagicMock(side_effect=RuntimeError("boom")),
            sleep_fn=lambda _delay: None,
            publication_metric=metric,
            fail_fast=True,
            logger=logger,
        )

    reset_server_state()
    assert start_metrics_server_runtime(
        start_http_server_fn=lambda *_a, **_k: None,
        sleep_fn=lambda _delay: None,
        publication_metric=metric,
        logger=logger,
    )
    assert start_metrics_server_runtime(
        start_http_server_fn=lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("already started")
        ),
        sleep_fn=lambda _delay: None,
        publication_metric=metric,
        logger=logger,
    )
    reset_server_state()


def test_filtered_read_helpers_cover_edge_payloads() -> None:
    assert _normalize_error_details({"error_details": 1}) == {}
    assert _normalize_error_details({"error_details": '{"reason_code": "x"}'}) == {
        "reason_code": "x"
    }
    assert _normalize_error_details({"error_details": "[]"}) == {}
    assert _normalize_filter_values("*") is None
    assert _normalize_filter_values(" a , * , b ") == {"a", "b"}
    assert _single_filter_value("only") == "only"
    assert _single_filter_value("a,b") is None
    assert _clamp_limit(0) == 50
    assert _clamp_limit(9999) == 500
    naive = datetime(2026, 1, 1, 12, 0, 0)
    iso, parsed = _normalize_timestamp(naive)
    assert parsed is not None and parsed.tzinfo is UTC
    assert iso.endswith("+00:00") or parsed.tzinfo is UTC
    preview = _build_payload_preview({f"k{i}": i for i in range(10)})
    assert preview["_truncated_keys"] == 2
    assert _build_payload_preview("scalar") == {"value": "scalar"}


def test_pyarrow_helpers_fail_closed_when_compute_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.infrastructure.quarantine._pyarrow_helpers as helpers

    monkeypatch.setattr(helpers, "pc", None)
    with pytest.raises(RuntimeError, match="pyarrow.compute"):
        helpers.equal_mask("left", "right")
    with pytest.raises(RuntimeError, match="pyarrow.compute"):
        helpers.and_mask("left", "right")


@pytest.mark.asyncio
async def test_openalex_title_filter_empty_and_whitespace_titles() -> None:
    flow = OpenAlexCursorFlow(
        mailto="a@b.c",
        batch_size=2,
        title_search_cache_size=1,
        normalize_doi=lambda value: value,
        escape_title_for_search=lambda value: value,
        query_executor=AsyncMock(),
        response_mapper=MagicMock(),
        logger=MagicMock(),
        runtime_errors=(RuntimeError,),
    )
    empty = [row async for row in flow.iter_filtered_by_title([], limit=None)]
    assert empty == []
    flow.logger.info.assert_called()
    rows = [row async for row in flow.iter_filtered_by_title(["   "], limit=None)]
    assert rows == []
    flow.query_executor.request_works_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_pubchem_identifier_mixin_swallows_strategy_errors() -> None:
    class _Host(_PubChemIdentifierFetchMixin):
        FETCH_STRATEGY_ERRORS = (TimeoutError,)

        def __init__(self) -> None:
            self._logger = MagicMock()
            self._provider_name = "pubchem"
            self._fetch_flow = SimpleNamespace(
                execute=AsyncMock(side_effect=TimeoutError("down"))
            )
            self._response_mapper = SimpleNamespace(map_compounds=lambda items: items)

    host = _Host()
    smiles = [row async for row in host.fetch_by_smiles(["CC", "  "])]
    assert smiles == []
    host._logger.warning.assert_any_call(
        "smiles_fetch_failed",
        provider="pubchem",
        smiles="CC",
        error="down",
    )
    keys = host._filter_valid_inchikeys(["", "not-a-key", "AAAAAAAAAAAAA-AAAAA-AAAAA"])
    assert keys == []
    host._logger.warning.assert_any_call(
        "invalid_inchikey_skipped",
        provider="pubchem",
        inchikey="not-a-key",
        reason="invalid_format",
    )


def test_unified_logger_preserves_non_mapping_extra_and_strips_correlation() -> None:
    logger = UnifiedLogger(pipeline="chembl_activity", run_id="run-1")
    logger._logger = MagicMock()
    logger.info("evt", extra="scalar", event="override")
    logger._logger.info.assert_called_once()
    kwargs = logger._logger.info.call_args.kwargs
    assert kwargs["extra"] == "scalar"
    assert kwargs["stage"] == "init"
    bound = logger.bind(run_id="hijack", pipeline="other", stage="extract")
    assert bound._run_id == "run-1"
    assert bound._pipeline == "chembl_activity"
    stripped = logger._strip_correlation_overrides({"run_id": "x", "stage": "load"})
    assert stripped == {"stage": "load"}


def test_api_request_sanitize_redacts_and_parses_headers() -> None:
    from urllib.parse import urlsplit

    from bioetl.infrastructure.adapters.common._api_request_sanitize import (
        normalize_http_method,
        parse_float_header,
        parse_int_header,
        parse_query_params,
        parse_reset_header,
        sanitize_base_url,
        sanitize_params,
    )

    assert parse_query_params("") == {}
    assert parse_query_params("a=1&b=") == {"a": "1", "b": ""}
    assert sanitize_params(
        {"api-key": "secret", "limit": 10, "flag": True, "nested": {"x": 1}}
    ) == {"api-key": "[REDACTED]", "limit": 10, "flag": True, "nested": "{'x': 1}"}
    assert normalize_http_method("post") == "POST"
    assert normalize_http_method("HEAD") == "HEAD"
    assert normalize_http_method("put") == "GET"
    assert parse_int_header(None) is None
    assert parse_int_header("7") == 7
    assert parse_int_header("nope") is None
    assert parse_float_header(None) is None
    assert parse_float_header("1.5") == 1.5
    assert parse_float_header("nope") is None
    assert parse_reset_header(None) is None
    reset = parse_reset_header("1700000000")
    assert reset is not None and reset.tzinfo is UTC
    assert parse_reset_header("Wed, 21 Oct 2015 07:28:00 GMT") is None
    ipv6 = sanitize_base_url(urlsplit("http://[2001:db8::1]:8080/path"))
    assert ipv6 == "http://[2001:db8::1]:8080"
    with pytest.raises(ValueError, match="invalid port"):
        sanitize_base_url(urlsplit("http://example.com:notaport/"))


def test_governance_validation_reports_structural_errors() -> None:
    from datetime import date

    from bioetl.infrastructure.quality._governance_validation import (
        _burn_down_priority_registries,
        _validate_governance_section,
    )

    errors: list[str] = []
    assert _validate_governance_section({}, baseline_registry_names=set(), group_names=set(), errors=errors) is False
    assert "governance: required mapping" in errors

    errors = []
    raw = {
        "governance": {
            "baseline_policy": "nope",
            "review_policy": {"new_exemption_requires": []},
            "owner_registry_q3_subsystems": {" ": "x", "a": {"owner": " "}, "b": 1},
            "growth_gate_default_mode": "block",
            "allow_grace_windows_only_for_rf": "yes",
            "growth_section_gate_rollout": "nope",
            "burn_down_priorities": {"registries": ["hotspot", 1]},
        },
        "hotspot_budgets": "nope",
    }
    _validate_governance_section(
        raw,
        baseline_registry_names={"hotspot"},
        group_names=set(),
        errors=errors,
        today=date(2026, 1, 1),
    )
    assert any("baseline_policy" in item for item in errors)
    assert any("new_exemption_requires" in item for item in errors)
    assert any("owner_registry_q3_subsystems" in item for item in errors)
    assert any("allow_grace_windows_only_for_rf" in item for item in errors)
    assert any("growth_section_gate_rollout" in item for item in errors)
    assert _burn_down_priority_registries(raw) == {"hotspot"}
    assert _burn_down_priority_registries({"governance": "x"}) == set()
    assert _burn_down_priority_registries({"governance": {"burn_down_priorities": []}}) == set()

    errors = []
    _validate_governance_section(
        {
            "governance": {
                "baseline_policy": {
                    "enforceable_section": "baseline",
                    "historical_section": "historical_baseline",
                    "registry_sync_source": "baseline",
                    "rationale": "keep shrink-only",
                },
                "review_policy": {
                    "new_exemption_requires": [
                        "owner",
                        "classification",
                        "linked_rf",
                        "expires_on",
                        "removal_step",
                    ]
                },
                "owner_registry_q3_subsystems": {
                    "s1": {"owner": "a"},
                    "s2": {"owner": "b"},
                    "s3": {"owner": "c"},
                },
                "growth_gate_default_mode": "block",
                "allow_grace_windows_only_for_rf": True,
                "growth_section_gate_rollout": {
                    "default_mode": "warn",
                    "warn_until_by_section": {
                        "": "2026-01-01",
                        "unknown": "2026-01-01",
                        "registry:hotspot": "bad-date",
                        "*": "2020-01-01",
                    },
                },
                "burn_down_priorities": {"registries": ["hotspot"]},
            },
            "hotspot_budgets": [
                "skip",
                {
                    "name": " ",
                    "rationale": "",
                    "path_prefixes": ["docs/"],
                    "registry_budgets": {},
                },
                {
                    "name": "dup",
                    "rationale": "ok",
                    "path_prefixes": ["src/bioetl/infrastructure/"],
                    "registry_budgets": {"missing": 1},
                },
                {
                    "name": "dup",
                    "rationale": "ok",
                    "path_prefixes": ["src/bioetl/infrastructure/"],
                    "registry_budgets": {"other": 0},
                },
            ],
        },
        baseline_registry_names={"hotspot"},
        group_names=set(),
        errors=errors,
        today=date(2026, 9, 17),
    )
    assert any("unknown section key" in item for item in errors)
    assert any("ISO date" in item for item in errors)
    assert any("stale cutoff" in item for item in errors)
    assert any("duplicate hotspot name" in item for item in errors)
    assert any("missing coverage" in item for item in errors)

