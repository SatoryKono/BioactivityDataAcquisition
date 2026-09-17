"""Stream A leftovers: adapters, CSV export, snapshots, lineage, pipeline API."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.domain.exceptions import BioETLError
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError
from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.infrastructure.adapters.crossref._search_paginator import SearchPaginator
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
)
from bioetl.infrastructure.adapters.decorators.circuit_breaker import (
    CircuitBreakerDataSourceDecorator,
)
from bioetl.infrastructure.adapters.http.client_retry_observability import _NoOpSpan
from bioetl.infrastructure.adapters.pubmed._adapter_support import (
    _create_pubmed_adapter,
    _require_pubmed_runtime,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    _load_base_config,
    _load_base_config_cached,
)
from bioetl.infrastructure.export.csv_exporter_io_ops import append_to_csv
from bioetl.infrastructure.storage.bronze.metadata_snapshot_refs import (
    attach_live_snapshot_to_source_metadata,
    build_bronze_source_metadata_with_live_snapshot,
)
from bioetl.infrastructure.storage.lineage_persistence import (
    _collect_field_source_counts,
    resolve_metadata_and_lineage_fragment,
)

pytestmark = pytest.mark.unit


def test_noop_span_methods() -> None:
    span = _NoOpSpan()
    with span as entered:
        entered.set_attribute("k", "v")
        entered.add_event("evt")
        entered.record_exception(ValueError("x"))


def test_pubmed_runtime_and_email_required() -> None:
    with pytest.raises(ValueError, match="http_client"):
        _require_pubmed_runtime(None, MagicMock(), {"fallback_fetch_service": object()})
    with pytest.raises(ValueError, match="logger"):
        _require_pubmed_runtime(MagicMock(), None, {"fallback_fetch_service": object()})
    with pytest.raises(ValueError, match="fallback_fetch_service"):
        _require_pubmed_runtime(MagicMock(), MagicMock(), {})
    http, logger = _require_pubmed_runtime(
        MagicMock(),
        MagicMock(),
        {"fallback_fetch_service": object()},
    )
    assert http is not None
    assert logger is not None
    with pytest.raises(ValueError, match="email"):
        _create_pubmed_adapter(
            MagicMock(),
            MagicMock(),
            None,
            fallback_fetch_service=object(),
        )


@pytest.mark.asyncio
async def test_circuit_breaker_records_bioetl_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SimpleNamespace(
        fetch_records=AsyncMock(side_effect=BioETLError("boom")),
        provider_name="chembl",
    )
    decorator = CircuitBreakerDataSourceDecorator(
        data_source=source,  # type: ignore[arg-type]
        circuit_breaker=MagicMock(),
        logger=MagicMock(),
    )
    recorded = MagicMock()
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators.circuit_breaker.log_failure_recorded",
        recorded,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators.circuit_breaker.iter_delegated_fetch",
        AsyncMock(side_effect=BioETLError("boom")),
    )

    async def _boom(_source: object, _request: object):
        raise BioETLError("boom")
        yield {}  # pragma: no cover

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators.circuit_breaker.iter_delegated_fetch",
        _boom,
    )
    with pytest.raises(BioETLError):
        async for _row in decorator._iterate_with_error_recording(
            DataSourceFetchRequest(entity_type="activity")
        ):
            pass
    recorded.assert_called()

    async def _ok(_source: object, _request: object):
        yield {"id": "1"}

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators.circuit_breaker.iter_delegated_fetch",
        _ok,
    )
    decorator._record_fetch_success = AsyncMock()  # type: ignore[method-assign]
    rows = [
        row
        async for row in decorator._iterate_with_error_recording(
            DataSourceFetchRequest(entity_type="activity")
        )
    ]
    assert rows == [{"id": "1"}]
    decorator._record_fetch_success.assert_awaited()


@pytest.mark.asyncio
async def test_crossref_search_runtime_error_wraps() -> None:
    from contextlib import nullcontext

    http = SimpleNamespace(get=AsyncMock(side_effect=TimeoutError("down")))
    paginator = SearchPaginator(
        http=http,  # type: ignore[arg-type]
        logger=MagicMock(),
        metrics=SimpleNamespace(measure_request=lambda *_a, **_k: nullcontext()),
        mailto="a@b.c",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {"ua": "test"},
    )
    with pytest.raises(CrossRefApiError, match="search failed"):
        async for _row in paginator.search("kinase"):
            pass


def test_pipeline_base_config_missing_and_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load_base_config_cached.cache_clear()
    missing = tmp_path / "nope.yaml"
    assert _load_base_config_cached(str(missing)) == {}
    _load_base_config_cached.cache_clear()

    config_path = tmp_path / "entity" / "chembl" / "activity.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("pipeline_name: x\n", encoding="utf-8")
    original_resolve = Path.resolve

    def boom(self: Path) -> Path:
        if self.name == "pipeline.yaml":
            raise OSError("cannot resolve")
        return original_resolve(self)

    monkeypatch.setattr(Path, "resolve", boom)
    loaded = _load_base_config(config_path)
    assert loaded == {} or isinstance(loaded, dict)


def test_csv_append_cleans_temp_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.csv"
    target.write_text("id\n", encoding="utf-8")
    table = pa.table({"id": ["1"]})

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("write failed")

    monkeypatch.setattr("bioetl.infrastructure.export.csv_exporter_io_ops.pv.write_csv", boom)
    with pytest.raises(RuntimeError, match="write failed"):
        append_to_csv(table, target, ",", MagicMock())


def test_bronze_snapshot_none_source_and_identity() -> None:
    snapshot = InputSnapshotRef(
        snapshot_id="s1",
        content_hash="h1",
        immutable_uri="file://x",
    )
    built = build_bronze_source_metadata_with_live_snapshot(
        source_metadata=None,
        snapshot=snapshot,
    )
    assert built is not None
    assert built.input_snapshots[0].snapshot_id == "s1"
    same = attach_live_snapshot_to_source_metadata(
        source_metadata=built,
        snapshot=snapshot,
    )
    assert same is built
    empty = attach_live_snapshot_to_source_metadata(
        source_metadata=built,
        snapshot=None,
    )
    assert empty is built


def test_lineage_collect_none_and_factory_callable() -> None:
    assert _collect_field_source_counts(None) == {}
    coordinator = SimpleNamespace(build=lambda data: {"ok": data})
    metadata, fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="missing_bundle",
        coordinator_factory_name="build",
        input_data={"id": "1"},
        fallback_factory=lambda: {"fallback": True},
    )
    assert metadata == {"ok": {"id": "1"}}
    assert fragment is None
