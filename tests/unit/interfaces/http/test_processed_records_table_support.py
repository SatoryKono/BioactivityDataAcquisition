"""Unit tests for Processed Records table support helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import ARTIFACT_PUBLISHED_EVENT
from bioetl.interfaces.http import _processed_records_table_support as support
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite


pytestmark = pytest.mark.unit


def test_fetch_processed_record_values_queries_all_visible_rows_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Prometheus fetch helper should issue one scoped vector query."""
    calls: list[tuple[tuple[str, ...], str]] = []

    def fake_query(
        *,
        prometheus_base_urls: tuple[str, ...],
        query: str,
    ) -> dict[str, float]:
        calls.append((prometheus_base_urls, query))
        return {support.PROCESSED_RECORDS_ROW_SPECS[0].metric: 1.0}

    monkeypatch.setattr(support, "_query_prometheus_vector_with_fallbacks", fake_query)

    values = support.fetch_processed_record_values(
        prometheus_base_url="http://localhost:9090/",
        pipeline="{chembl_activity,pubchem_compound}",
        run_type="backfill",
    )

    assert len(values) == len(support.PROCESSED_RECORDS_ROW_SPECS)
    assert values[support.PROCESSED_RECORDS_ROW_SPECS[0].metric] == 1.0
    assert values[support.PROCESSED_RECORDS_ROW_SPECS[1].metric] is None
    assert len(calls) == 1
    assert calls[0][0] == (
        "http://localhost:9090",
        "http://prometheus:9090",
        "http://host.docker.internal:9090",
    )
    assert 'pipeline=~"(?:chembl_activity|pubchem_compound)"' in calls[0][1]
    assert 'run_type=~"backfill"' in calls[0][1]
    assert calls[0][1].startswith("sum by (__name__)")


def test_processed_record_selector_and_formatting_edges() -> None:
    """Dashboard selector helpers should normalize placeholders and bad values."""
    assert support.read_processed_records_run_id(None) is None
    assert support.read_processed_records_run_id("-") is None
    assert support.read_processed_records_run_id("{one,two}") is None
    assert support.read_processed_records_run_id("not-a-uuid") is None

    assert support.selector_tokens(" $__all ") == ()
    assert support.selector_tokens("{a,b,a}") == ("a", "b")
    assert support.selector_tokens("a,*,b") == ()
    assert support.selector_tokens(" , ") == ()
    assert support.is_unknown_scope(" unknown ") is True

    assert support.as_float(None) is None
    assert support.as_float(float("inf")) is None
    assert support.sum_metric_values({"a": 1, "b": None}, ("a", "b")) is None
    assert support.sum_metric_values({"a": 1, "b": 2.5}, ("a", "b")) == 3.5
    assert support.is_deficit(total=None, minimum=1) is False
    assert support.is_deficit(total=1, minimum=2) is True
    assert support.count_text(1.25) == "1.25"
    assert support.count_text(1200.0) == "1 200"
    assert support.padded_count_text(None, 8) == "No data"
    assert support.padded_count_text(7, 3) == "  7"
    assert (
        support.row_status(
            parameter="02 silver_valid_records",
            silver_deficit=True,
            gold_deficit=False,
        )
        == "silver_deficit"
    )
    assert (
        support.row_status(
            parameter="07 gold_written_records",
            silver_deficit=False,
            gold_deficit=True,
        )
        == "gold_deficit"
    )
    assert (
        support.format_percentage(
            value=None,
            bronze_value=10,
            denominator="constant_100",
            percent_format="constant_100",
        )
        == "No data"
    )
    assert (
        support.format_percentage(
            value=5,
            bronze_value=0,
            denominator="bronze",
            percent_format="fixed_1",
        )
        == "No data"
    )
    assert (
        support.format_percentage(
            value=1,
            bronze_value=3,
            denominator="bronze",
            percent_format="fixed_1",
        )
        == "33.3%"
    )
    assert (
        support.format_percentage(
            value=1,
            bronze_value=8,
            denominator="bronze",
            percent_format="trimmed_3",
        )
        == "12.5%"
    )
    assert (
        support.format_percentage(
            value=5,
            bronze_value=10,
            denominator="bronze",
            percent_format="constant_100",
        )
        == "100%"
    )


def test_processed_record_prometheus_selector_query_edges() -> None:
    """PromQL selector helpers should cover literal, wildcard, and fallback edges."""
    assert support._processed_record_value_query(
        metric="bioetl_processed_records_bronze_current",
        pipeline='chembl"activity',
        run_type=None,
    ) == (
        "round(sum(bioetl_processed_records_bronze_current{"
        'pipeline=~"chembl\\"activity",run_type=~".*"}))'
    )
    assert support._processed_record_value_query(
        metric="bioetl_processed_records_bronze_current",
        pipeline="chembl\\activity",
        run_type="backfill",
    ) == (
        "round(sum(bioetl_processed_records_bronze_current{"
        r'pipeline=~"chembl\\\\activity",run_type=~"backfill"}))'
    )
    assert support._candidate_prometheus_base_urls("http://custom:9090/") == (
        "http://custom:9090",
    )


def test_processed_record_ledger_helpers_ignore_non_authoritative_entries() -> None:
    """Ledger helpers should only use snapshots and published stage artifacts."""
    run_id = deterministic_run_uuid_from_callsite("processed_records_support")
    occurred_at = datetime(2026, 6, 16, 10, 0, tzinfo=UTC)
    entries = (
        RunLedgerEntry(
            entry_id="started",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type="run_started",
            occurred_at=occurred_at,
            status="running",
            details={"stage": "bronze", "record_count": 999},
        ),
        RunLedgerEntry(
            entry_id="bad-artifact",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type=ARTIFACT_PUBLISHED_EVENT,
            occurred_at=occurred_at,
            status="published",
            details={"stage": "other", "record_count": True},
        ),
        RunLedgerEntry(
            entry_id="stage-artifact",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type=ARTIFACT_PUBLISHED_EVENT,
            occurred_at=occurred_at,
            status="published",
            stage="silver",
            details=None,
        ),
    )

    assert support.latest_metrics_snapshot(entries) is None
    assert support.published_layer_artifact_counts(entries) == {}


def test_processed_record_ledger_helpers_use_authoritative_entries() -> None:
    """Ledger helpers should use the latest metrics snapshot and valid stage artifacts."""
    run_id = deterministic_run_uuid_from_callsite(
        "processed_records_support_authoritative"
    )
    occurred_at = datetime(2026, 6, 16, 10, 0, tzinfo=UTC)
    entries = (
        RunLedgerEntry(
            entry_id="older",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type="run_finished",
            occurred_at=occurred_at,
            status="success",
            metrics_snapshot={"records_bronze": 1},
        ),
        RunLedgerEntry(
            entry_id="newer",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type="run_finished",
            occurred_at=occurred_at,
            status="success",
            metrics_snapshot={"records_bronze": 2},
        ),
        RunLedgerEntry(
            entry_id="bronze-artifact",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type=ARTIFACT_PUBLISHED_EVENT,
            occurred_at=occurred_at,
            status="published",
            details={"stage": "bronze", "record_count": "2"},
        ),
        RunLedgerEntry(
            entry_id="gold-artifact",
            manifest_id="manifest-a",
            run_id=run_id,
            event_type=ARTIFACT_PUBLISHED_EVENT,
            occurred_at=occurred_at,
            status="published",
            stage="gold",
            details={"record_count": 1},
        ),
    )

    assert support.latest_metrics_snapshot(entries) == {"records_bronze": 2}
    assert support.published_layer_artifact_counts(entries) == {
        "bronze": 2,
        "gold": 1,
    }


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_query_prometheus_scalar_parses_success_and_missing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scalar query parsing should reject malformed or non-finite Prometheus values."""
    payloads = iter(
        (
            {"status": "success", "data": {"result": [{"value": [1, "42"]}]}},
            {"status": "success", "data": {"result": []}},
            {"status": "success", "data": {"result": [{"value": ["bad"]}]}},
            {"status": "success", "data": {"result": [{"value": [1, "nan"]}]}},
            {"status": "error", "error": "bad query"},
        )
    )
    urls: list[str] = []

    def fake_urlopen(url: str, *, timeout: float) -> _FakeResponse:
        urls.append(url)
        assert timeout == support.PROMETHEUS_QUERY_TIMEOUT_SECONDS
        return _FakeResponse(next(payloads))

    monkeypatch.setattr(support, "_open_url", fake_urlopen)

    assert (
        support._query_prometheus_scalar(
            prometheus_base_url="http://prometheus.example/",
            query='metric{label="value"}',
        )
        == 42.0
    )
    assert (
        support._query_prometheus_scalar(
            prometheus_base_url="http://prometheus.example",
            query="empty",
        )
        is None
    )
    assert (
        support._query_prometheus_scalar(
            prometheus_base_url="http://prometheus.example",
            query="malformed",
        )
        is None
    )
    assert (
        support._query_prometheus_scalar(
            prometheus_base_url="http://prometheus.example",
            query="nan",
        )
        is None
    )
    with pytest.raises(RuntimeError, match="bad query"):
        support._query_prometheus_scalar(
            prometheus_base_url="http://prometheus.example",
            query="error",
        )

    assert urls[0].startswith("http://prometheus.example/api/v1/query?")
    assert "%5C%22" not in urls[0]


def test_query_prometheus_scalar_with_fallbacks_reports_all_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback helper should try candidates in order and report exhausted errors."""
    calls: list[str] = []

    def flaky_query(*, prometheus_base_url: str, query: str) -> float:
        calls.append(f"{prometheus_base_url}:{query}")
        if len(calls) == 1:
            raise RuntimeError("first failed")
        return 7.0

    monkeypatch.setattr(support, "_query_prometheus_scalar", flaky_query)

    assert (
        support._query_prometheus_scalar_with_fallbacks(
            prometheus_base_urls=("http://one", "http://two"),
            query="up",
        )
        == 7.0
    )
    assert calls == ["http://one:up", "http://two:up"]

    def always_fails(*, prometheus_base_url: str, query: str) -> float:
        raise RuntimeError(f"{query} failed")

    monkeypatch.setattr(support, "_query_prometheus_scalar", always_fails)

    with pytest.raises(RuntimeError, match=r"http://one: .*http://two:"):
        support._query_prometheus_scalar_with_fallbacks(
            prometheus_base_urls=("http://one", "http://two"),
            query="down",
        )


def test_query_prometheus_vector_preserves_metric_names_and_missing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": {"__name__": "bioetl_processed_records_bronze_current"},
                    "value": [1, "42"],
                },
                {
                    "metric": {
                        "__name__": "bioetl_processed_records_gold_written_current"
                    },
                    "value": [1, "nan"],
                },
                {"metric": {}, "value": [1, "7"]},
            ]
        },
    }
    monkeypatch.setattr(
        support, "_open_url", lambda *_args, **_kwargs: _FakeResponse(payload)
    )

    values = support._query_prometheus_vector(
        prometheus_base_url="http://prometheus.example",
        query="sum by (__name__) (...) ",
    )

    assert values == {"bioetl_processed_records_bronze_current": 42.0}
