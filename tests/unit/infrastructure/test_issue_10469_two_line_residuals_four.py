"""Additional two-line infrastructure behavior coverage for #10469."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.http.client_context_mixin import (
    HTTPClientContextMixin,
)
from bioetl.infrastructure.adapters.pubmed import (
    adapter_filter_fetch_mixin as pubmed_filter,
)
from bioetl.infrastructure.adapters.semanticscholar._search_fetch_flow import (
    _SemanticScholarSearchFetchMixin,
)
from bioetl.infrastructure.config._composite_dq_externalization import (
    merge_external_dq_overrides,
)
from bioetl.infrastructure.storage import silver_writer
from bioetl.infrastructure.storage.gold.io_delta_mixins import (
    _GoldWriterSimpleDeltaMixin,
)
from bioetl.infrastructure.storage.gold.io_preparation import (
    _prepare_gold_merged_table,
)

pytestmark = pytest.mark.unit


class _HTTPHarness(HTTPClientContextMixin):
    def __init__(self, client: object) -> None:
        self._client = client  # type: ignore[assignment]
        self._client_enter_depth = 0
        self.user_agent = "BioETL"
        self.contact_email = None
        self.run_id = None
        self.timeout = 1.0
        self.read_timeout_multiplier = 1.0
        self.max_connections = 2
        self.max_keepalive_connections = 1
        self.trust_env = False


@pytest.mark.asyncio
async def test_http_context_recovers_inconsistent_open_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = SimpleNamespace(aclose=AsyncMock())
    replacement = MagicMock()
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.http.client_context_mixin.httpx.AsyncClient",
        MagicMock(return_value=replacement),
    )
    host = _HTTPHarness(stale)
    assert await host.__aenter__() is host
    stale.aclose.assert_awaited_once()
    assert host._client is replacement


@pytest.mark.asyncio
async def test_pubmed_filter_mixin_yields_delegated_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def delegated(*_args: object, **_kwargs: object):
        yield {"pmid": "1"}

    monkeypatch.setattr(pubmed_filter, "fetch_from_filter_ids", delegated)
    host = pubmed_filter.PubMedAdapterFilterFetchMixin()
    rows = [
        row
        async for row in host._fetch_from_filter_ids(  # type: ignore[arg-type]
            entity_type="publication",
            filter_ids=["1"],
            filter_field="pmid",
            limit=1,
        )
    ]
    assert rows == [{"pmid": "1"}]


@pytest.mark.asyncio
async def test_semantic_scholar_search_pagination_stops_at_limit() -> None:
    host = _SemanticScholarSearchFetchMixin()
    host._fetch_search_page = AsyncMock(  # type: ignore[attr-defined]
        return_value=([{"paperId": "1"}, {"paperId": "2"}], 100)
    )
    rows = [row async for row in host._paginate_search(query="kinase", limit=1)]
    assert rows == [{"paperId": "1"}]


@pytest.mark.asyncio
async def test_semantic_scholar_search_pagination_follows_next_offset() -> None:
    host = _SemanticScholarSearchFetchMixin()
    host._fetch_search_page = AsyncMock(  # type: ignore[attr-defined]
        side_effect=[
            ([{"paperId": "1"}], 10),
            ([{"paperId": "2"}], None),
        ]
    )
    rows = [row async for row in host._paginate_search(query="kinase", limit=None)]
    assert rows == [{"paperId": "1"}, {"paperId": "2"}]
    assert host._fetch_search_page.await_count == 2


def test_semantic_scholar_entity_type_validation() -> None:
    _SemanticScholarSearchFetchMixin._validate_entity_type("paper")
    _SemanticScholarSearchFetchMixin._validate_entity_type("publication")
    with pytest.raises(ValueError, match="supports"):
        _SemanticScholarSearchFetchMixin._validate_entity_type("author")


@pytest.mark.asyncio
async def test_semantic_scholar_fetch_search_page_swallows_collector_errors() -> None:
    class _Host(_SemanticScholarSearchFetchMixin):
        fields = "title"

        def __init__(self) -> None:
            self._adapter_metrics = SimpleNamespace(
                measure_request=lambda *_args, **_kwargs: nullcontext()
            )
            self._http_client = SimpleNamespace(
                get=AsyncMock(
                    return_value=SimpleNamespace(
                        json=lambda: {"data": [{"paperId": "1"}], "next": 7}
                    )
                )
            )
            self._request_collector = SimpleNamespace(
                record_from_response=MagicMock(side_effect=RuntimeError("ignore"))
            )

        def _build_headers(self) -> dict[str, str]:
            return {"ua": "test"}

    records, nxt = await _Host()._fetch_search_page(
        query="CRISPR", page_size=10, current_offset=0
    )
    assert records == [{"paperId": "1"}]
    assert nxt == 7


def test_external_composite_dq_skips_when_override_file_is_absent(
    tmp_path: Path,
) -> None:
    config = tmp_path / "composite.yaml"
    merge_external_dq_overrides({}, config)
    merge_external_dq_overrides({"composite": []}, config)  # type: ignore[arg-type]
    merge_external_dq_overrides({"composite": {"dq_overrides": "nope"}}, config)
    merge_external_dq_overrides(
        {"composite": {"dq_overrides": {"dq_config_file": "  "}}},
        config,
    )
    merge_external_dq_overrides(
        {"composite": {"dq_overrides": {"dq_config_file": 1}}},
        config,
    )
    raw_missing = {"composite": {"dq_overrides": {"dq_config_file": "missing.yaml"}}}
    with pytest.raises(FileNotFoundError, match="Composite DQ config not found"):
        merge_external_dq_overrides(raw_missing, config)

    external = tmp_path / "dq.yaml"
    external.write_text("threshold: 1\nnested:\n  a: 1\n", encoding="utf-8")
    raw_merge = {
        "composite": {
            "dq_overrides": {
                "dq_config_file": "dq.yaml",
                "threshold": 2,
                "nested": {"b": 2},
            }
        }
    }
    merge_external_dq_overrides(raw_merge, config)
    assert raw_merge["composite"]["dq_overrides"]["threshold"] == 2
    assert raw_merge["composite"]["dq_overrides"]["nested"] == {"a": 1, "b": 2}


def test_external_composite_dq_rejects_non_mapping_payloads(tmp_path: Path) -> None:
    config = tmp_path / "composite.yaml"
    external = tmp_path / "dq.yaml"
    external.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    raw = {"composite": {"dq_overrides": {"dq_config_file": "dq.yaml"}}}
    with pytest.raises(ValueError, match="must be a mapping"):
        merge_external_dq_overrides(raw, config)  # type: ignore[arg-type]

    external.write_text("dq_overrides: invalid\n", encoding="utf-8")
    with pytest.raises(ValueError, match="payload must be a mapping"):
        merge_external_dq_overrides(raw, config)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_gold_csv_finalizer_delegates_to_exporter() -> None:
    host = _GoldWriterSimpleDeltaMixin()
    host.csv_exporter = SimpleNamespace(finalize_csv=AsyncMock())
    await host.finalize_csv_export("gold/activity", primary_keys=["id"])
    host.csv_exporter.finalize_csv.assert_awaited_once_with(  # type: ignore[union-attr]
        "gold/activity", primary_keys=["id"]
    )


def test_gold_merged_table_drops_ingestion_timestamp() -> None:
    table = _prepare_gold_merged_table(
        records=[{"id": 1, "_ingestion_ts": "2026-09-17T00:00:00Z"}],
        primary_keys=None,
        preserve_column_order=True,
    )
    assert table.column_names == ["id"]


@pytest.mark.asyncio
async def test_silver_clear_delegates_to_delta_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cleanup = MagicMock(return_value=4)
    monkeypatch.setattr(silver_writer, "_clear_delta_tables", cleanup)
    monkeypatch.setattr(
        silver_writer.SilverWriter,
        "_resolve_table_path",
        lambda _self, name: str(tmp_path / name),
    )
    host = object.__new__(silver_writer.SilverWriter)
    host.base_path = tmp_path
    assert await host.clear_silver("activity", dry_run=True) == 4
    cleanup.assert_called_once()
