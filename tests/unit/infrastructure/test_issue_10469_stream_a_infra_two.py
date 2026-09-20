"""Stream A infrastructure residuals for #10469 / #10517 / #10516."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pyarrow as pa
import pytest

from bioetl.domain.config import MemoryConfig
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactReplayImpact,
    ControlPlaneArtifactSurface,
)
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import RunID
from bioetl.infrastructure.audit._file_audit_payloads import (
    build_canonical_event_payload,
    coerce_text,
    default_severity,
)
from bioetl.infrastructure.audit._file_audit_readers import (
    matches_filters,
    parse_entry,
    process_audit_file,
    process_audit_line,
)
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.export.csv_exporter_io_ops import (
    _csv_temp_directory,
    _publish_csv_payload,
    atomic_csv_write,
)
from bioetl.infrastructure.export.debug_export_adapter import DebugExportAdapter
from bioetl.infrastructure.export.export_writer_adapter import ExportWriterAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.system import memory_monitor as memory_monitor_module
from bioetl.infrastructure.system.memory_monitor import MemoryMonitor
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

pytestmark = pytest.mark.unit


class _Span:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}
        self.exceptions: list[Exception] = []

    def __enter__(self) -> _Span:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, exc: Exception) -> None:
        self.exceptions.append(exc)


class _Tracing:
    def __init__(self) -> None:
        self.spans: list[_Span] = []

    def get_tracer(self, _name: str) -> SimpleNamespace:
        def _start(_span_name: str) -> _Span:
            span = _Span()
            self.spans.append(span)
            return span

        return SimpleNamespace(start_as_current_span=_start)


def _run_id() -> RunID:
    return RunID(deterministic_run_uuid_from_callsite("stream_a_infra_two"))


def _entry() -> AuditEntry:
    return AuditEntry(
        run_id=_run_id(),
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        layer=AuditLayer.BRONZE,
        table_name="chembl.activity",
        operation=AuditOperation.WRITE,
        records_count=1,
        metadata={"provider": "chembl"},
    )


def _entry_payload() -> dict[str, object]:
    return {
        "run_id": str(UUID(int=1)),
        "timestamp": "2024-01-15T12:00:00",
        "layer": "bronze",
        "table_name": "chembl.activity",
        "operation": "write",
        "records_count": 2,
    }


@pytest.mark.asyncio
async def test_file_audit_closed_and_oserror_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracing = _Tracing()
    metrics = MagicMock()
    adapter = FileAuditAdapter(
        tmp_path / "audit",
        NoOpLogger(),
        metrics=metrics,
        tracing=tracing,  # type: ignore[arg-type]
    )
    await adapter.aclose()
    with pytest.raises(RuntimeError, match="has been closed"):
        await adapter.log_event(
            "PipelineRunStarted",
            {},
            timestamp=datetime(2024, 1, 15, tzinfo=UTC),
        )
    with pytest.raises(RuntimeError, match="has been closed"):
        await adapter.get_entries()

    defaulted = FileAuditAdapter(tmp_path / "audit2", NoOpLogger())
    assert isinstance(defaulted.metrics, NoOpMetrics)

    async def _raise_oserror(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(
        "bioetl.infrastructure.audit.file_audit.asyncio.to_thread",
        _raise_oserror,
    )
    open_adapter = FileAuditAdapter(
        tmp_path / "audit3",
        NoOpLogger(),
        metrics=metrics,
        tracing=_Tracing(),  # type: ignore[arg-type]
    )
    with pytest.raises(OSError, match="disk full"):
        await open_adapter.log_write(_entry())
    with pytest.raises(OSError, match="disk full"):
        await open_adapter.log_event(
            "PipelineRunFailed",
            {"status": "failed"},
            timestamp=datetime(2024, 1, 15, tzinfo=UTC),
        )
    with pytest.raises(OSError, match="disk full"):
        await open_adapter.get_entries(layer=AuditLayer.BRONZE)
    assert metrics.increment_counter.call_count >= 2


def test_file_audit_readers_and_payloads_cover_edge_rows(tmp_path: Path) -> None:
    parsed = parse_entry(_entry_payload())
    assert parsed.timestamp.tzinfo is UTC
    assert matches_filters(parsed, None, AuditLayer.SILVER, None, None, None) is False
    assert (
        matches_filters(
            parsed,
            None,
            None,
            "other",
            None,
            None,
        )
        is False
    )
    start = datetime(2024, 1, 16, tzinfo=UTC)
    assert matches_filters(parsed, None, None, None, start, None) is False
    end = datetime(2024, 1, 14, tzinfo=UTC)
    assert matches_filters(parsed, None, None, None, None, end) is False

    assert process_audit_line("  ", None, None, None, None, None) is None
    assert process_audit_line("[]", None, None, None, None, None) is None
    assert process_audit_line("{", None, None, None, None, None) is None
    line = json.dumps({**_entry_payload(), "timestamp": "2024-01-15T12:00:00+00:00"})
    matched = process_audit_line(line, None, None, None, None, None)
    assert matched is not None

    missing = process_audit_file(
        tmp_path / "missing.jsonl",
        None,
        None,
        None,
        None,
        None,
        10,
        0,
    )
    assert missing == []
    directory = tmp_path / "not-a-file"
    directory.mkdir()
    assert process_audit_file(directory, None, None, None, None, None, 10, 0) == []

    assert coerce_text(None, fallback="info") == "info"
    assert coerce_text("  ", fallback="info") == "info"
    assert default_severity({"severity": "warning"}) == "warning"
    assert default_severity({"status": "failed"}) == "error"
    assert default_severity({"status": "degraded"}) == "warning"
    assert default_severity({}) == "info"
    payload = build_canonical_event_payload(
        event_name="PipelineRunStarted",
        event_data={"pipeline": "chembl_activity", "phase": "extract"},
        timestamp=datetime(2024, 1, 15, tzinfo=UTC),
    )
    assert payload["event_name"] == "PipelineRunStarted"
    assert payload["phase"] == "extract"


@pytest.mark.asyncio
async def test_pubmed_adapter_models_and_factory() -> None:
    from bioetl.infrastructure.adapters.pubmed._adapter_support import (
        _create_pubmed_adapter,
        _require_pubmed_runtime,
        _resolve_pubmed_api_key,
        _resolve_pubmed_email,
    )
    from bioetl.infrastructure.adapters.pubmed._filter_fetch_support import (
        fetch_from_filter_ids,
    )
    from bioetl.infrastructure.adapters.pubmed import PubMedAdapter

    logger = MagicMock()
    http = AsyncMock()
    kwargs = build_http_adapter_runtime_kwargs(
        "pubmed",
        logger=logger,
        include_fallback_service=True,
    )
    adapter = PubMedAdapter(
        http_client=http,
        logger=logger,
        email="test@example.com",
        **kwargs,
    )

    async def _fetch(**_kwargs: object):
        yield {
            "pmid": "1",
            "article_title": "Kinase paper",
            "_raw_xml": "<PubmedArticle/>",
        }

    adapter.fetch = _fetch  # type: ignore[method-assign]
    validated = [row async for row in adapter.fetch_as_models("publication")]
    assert validated[0].pmid == "1"
    constructed = [
        row async for row in adapter.fetch_as_models("publication", validate=False)
    ]
    assert constructed[0].title == "Kinase paper"
    with pytest.raises(ValueError, match="No DTO model"):
        async for _row in adapter.fetch_as_models("gene"):
            raise AssertionError("should not yield")

    assert _resolve_pubmed_email(None, {"email": "kw@example.com"}) == "kw@example.com"
    assert _resolve_pubmed_email(None, {}) is None
    assert _resolve_pubmed_email(SimpleNamespace(default_email=None), {}) is None
    assert (
        _resolve_pubmed_email(SimpleNamespace(default_email="s@example.com"), {})
        == "s@example.com"
    )
    assert _resolve_pubmed_api_key(None, {"api_key": "k"}) == "k"
    assert _resolve_pubmed_api_key(None, {}) is None
    assert _resolve_pubmed_api_key(SimpleNamespace(), {}) is None
    empty_secret = SimpleNamespace(pubmed_api_key="")
    assert _resolve_pubmed_api_key(empty_secret, {}) is None
    secret = SimpleNamespace(
        pubmed_api_key=SimpleNamespace(get_secret_value=lambda: "secret-k")
    )
    assert _resolve_pubmed_api_key(secret, {}) == "secret-k"
    with pytest.raises(ValueError, match="requires http_client"):
        _require_pubmed_runtime(None, logger, kwargs)
    with pytest.raises(ValueError, match="requires logger"):
        _require_pubmed_runtime(http, None, kwargs)
    with pytest.raises(ValueError, match="requires fallback_fetch_service"):
        _require_pubmed_runtime(http, logger, {})
    with pytest.raises(ValueError, match="requires email"):
        _create_pubmed_adapter(http, logger, None, **kwargs)

    class _Host:
        async def fetch_filtered(
            self,
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None = None,
        ):
            assert entity_type == "publication"
            assert filter_field == "pmid"
            assert limit == 1
            for pmid in filter_ids[: limit or len(filter_ids)]:
                yield {"pmid": pmid}

    rows = [
        row
        async for row in fetch_from_filter_ids(
            _Host(),  # type: ignore[arg-type]
            entity_type="publication",
            filter_ids=["10", "11"],
            filter_field=None,
            limit=1,
        )
    ]
    assert rows == [{"pmid": "10"}]


@pytest.mark.asyncio
async def test_semanticscholar_fetch_mixin_limit_and_extractor() -> None:
    from bioetl.infrastructure.adapters.semanticscholar.fetch_adapter_mixin import (
        SemanticScholarFetchAdapterMixin,
    )
    from bioetl.infrastructure.adapters.semanticscholar._search_fetch_flow import (
        _SemanticScholarSearchFetchMixin,
    )

    class _Host(SemanticScholarFetchAdapterMixin):
        def __init__(self) -> None:
            self._logger = MagicMock()
            self.batch_size = 2
            self._fallback_decorator = SimpleNamespace()
            self._normalize_doi = lambda value: value.lower()

        async def _fetch_by_dois(self, batch: list[str]):
            for doi in batch:
                yield {"doi": doi}

        async def _fetch_batch_with_nulls(self, batch: list[str]):
            return [None for _doi in batch]

    host = _Host()
    unlimited = [
        row
        async for row in host.fetch_filtered(
            "publication",
            ["a", "b"],
            "doi",
            limit=None,
        )
    ]
    assert [row["doi"] for row in unlimited] == ["a", "b"]

    resolved: set[str] = set()
    skipped = [
        row
        async for row in host._batch_doi_phase(
            ["10.1/A", "10.2/B"],
            resolved,
            limit=1,
            start_count=1,
        )
    ]
    assert skipped == []

    class _Fallback:
        def __init__(self) -> None:
            self.extract = None

        async def execute(self, **kwargs: object):
            self.extract = kwargs["extract_record_id"]
            yield {"ok": True}

    host._fallback_decorator = _Fallback()
    rows = [
        row
        async for row in host.fetch_filtered_with_fallback(
            "publication",
            ["10.1/A"],
            "doi",
            {"10.1/A": "Title"},
        )
    ]
    assert rows == [{"ok": True}]
    assert host._fallback_decorator.extract({"_resolved_doi": 12}) is None
    assert host._fallback_decorator.extract({"_resolved_doi": "  "}) is None

    class _SearchHost(_SemanticScholarSearchFetchMixin):
        def __init__(self) -> None:
            self.fields = "title"
            self._adapter_metrics = SimpleNamespace(
                measure_request=lambda *_a, **_k: _Span()
            )
            self._http_client = SimpleNamespace(
                get_once=AsyncMock(
                    return_value=SimpleNamespace(
                        json=lambda: {"data": [{"paperId": "p1"}], "next": None}
                    )
                )
            )
            self._build_headers = lambda: {}
            self._request_collector = SimpleNamespace(
                record_from_response=MagicMock(side_effect=RuntimeError("telemetry"))
            )

        def _validate_entity_type(self, entity_type: str) -> None:
            return super()._validate_entity_type(entity_type)

    search_host = _SearchHost()
    search_host._validate_entity_type("paper")
    with pytest.raises(ValueError, match="got: gene"):
        search_host._validate_entity_type("gene")
    page_rows = [row async for row in search_host._paginate_search(query=None, limit=1)]
    assert page_rows == [{"paperId": "p1"}]


def test_lifecycle_apply_records_missing_and_skips_retained(tmp_path: Path) -> None:
    now = datetime(2026, 4, 22, tzinfo=UTC)
    missing = tmp_path / "gone.json"
    retained = tmp_path / "keep.json"
    retained.write_text("{}", encoding="utf-8")
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=now,
        cutoff=now,
        dry_run=False,
        artifacts=(
            ControlPlaneArtifactRef(
                surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
                path=str(missing),
                artifact_id="missing",
                decision=ControlPlaneArtifactLifecycleDecision.DELETE,
                reason="retention_expired",
                replay_impact=ControlPlaneArtifactReplayImpact.NO_REPLAY_EVIDENCE,
            ),
            ControlPlaneArtifactRef(
                surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
                path=str(retained),
                artifact_id="keep",
                decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
                reason="protected_reference",
            ),
        ),
    )
    store = FileControlPlaneArtifactLifecycleStore(base_path=tmp_path)
    result = store.apply(plan)
    assert result.missing_paths == (str(missing),)
    assert result.deleted_paths == ()
    assert retained.exists()


def test_debug_export_write_pack_includes_lineage_table(tmp_path: Path) -> None:
    from bioetl.domain.types import DebugExportPack

    adapter = DebugExportAdapter()
    pack = DebugExportPack(
        run_id="00000000-0000-0000-0000-000000000123",
        pipeline_id="chembl_activity",
        provider_id="chembl",
        workflow_id="wf-1",
        manifest_id="manifest-1",
        status="complete",
        output_root=str(tmp_path),
        formats=("csv",),
        include_bom=False,
        max_rows_per_sheet=10,
        created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        tables={"rows": ({"a": 1},)},
        reason_dictionary=(),
    )
    adapter._load_lineage_rows = lambda _pack: [  # type: ignore[method-assign]
        {"fragment_id": "f1", "node_id": "n1"}
    ]
    result = adapter.write_pack(pack=pack)
    lineage_csv = Path(result.root_path) / "lineage.csv"
    assert lineage_csv.exists()
    assert "fragment_id" in lineage_csv.read_text(encoding="utf-8")


def test_memory_monitor_leftover_fallback_and_pressure_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(memory_monitor_module, "_psutil_available", None)
    monkeypatch.setattr(memory_monitor_module, "_psutil_module", None)
    real_import = __import__

    def _block_psutil(name: str, *args: object, **kwargs: object):
        if name == "psutil":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _block_psutil)
    assert memory_monitor_module._check_psutil_available() is False
    assert memory_monitor_module._check_psutil_available() is False

    logger = MagicMock()
    monitor = MemoryMonitor(config=MemoryConfig(), logger=logger)
    assert monitor._psutil_available is False
    logger.debug.assert_called()

    resource_mod = SimpleNamespace(
        RUSAGE_SELF=0,
        getrusage=lambda _mode: SimpleNamespace(ru_maxrss=2048),
    )
    monkeypatch.setitem(sys.modules, "resource", resource_mod)
    meminfo = "incomplete\nMemTotal: 0 kB\nMemAvailable: 0 kB\n"

    class _Meminfo:
        def __enter__(self):
            from io import StringIO

            return StringIO(meminfo)

        def __exit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setattr(
        memory_monitor_module.Path, "open", lambda *_a, **_k: _Meminfo()
    )
    stats = monitor._get_stats_resource()
    assert stats.percent_used == pytest.approx(0.5)
    assert monitor.get_monitor_mode() == "resource"

    class _Boom:
        def __enter__(self) -> None:
            raise KeyError("meminfo")

        def __exit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setattr(memory_monitor_module.Path, "open", lambda *_a, **_k: _Boom())
    estimated = monitor._get_stats_resource()
    assert estimated.process_mb == pytest.approx(256.0)

    monitor._recovery_target_batch_size = 40
    monitor._update_recovery_tracking(80)
    assert monitor._recovery_target_batch_size == 80
    monitor._log_batch_size_reduction(
        current_batch_size=100,
        new_size=50,
        stats=stats,
    )
    logger.warning.assert_called()

    tight = MemoryMonitor(
        config=MemoryConfig(min_batch_size=100, memory_pressure_threshold=0.1),
        logger=logger,
    )
    tight.get_memory_stats = lambda: SimpleNamespace(percent_used=0.9)  # type: ignore[method-assign]
    assert tight.get_recommended_batch_size(100) == 100


def test_export_writer_tsv_xlsx_and_csv_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = pa.Table.from_pydict({"col": ["a"], "n": [1]})
    adapter = ExportWriterAdapter()
    tsv_path = Path(
        adapter.write_export(
            table=table,
            table_name="chembl.activity",
            layer="silver",
            fmt="tsv",
            output_dir=str(tmp_path / "exports"),
        )
    )
    assert tsv_path.exists()
    assert tsv_path.suffix == ".tsv"

    class _Frame:
        def to_excel(self, *_args: object, **_kwargs: object) -> None:
            raise ImportError("openpyxl missing")

    monkeypatch.setattr(
        "bioetl.domain.serialization.flatten_arrow_table_for_export",
        lambda _table: SimpleNamespace(to_pandas=lambda: _Frame()),
    )
    with pytest.raises(ImportError, match="openpyxl is required"):
        adapter.write_export(
            table=table,
            table_name="chembl.activity",
            layer="silver",
            fmt="xlsx",
            output_dir=str(tmp_path / "exports"),
        )

    import bioetl.infrastructure.export.csv_exporter_io_ops as csv_ops

    assert _csv_temp_directory(tmp_path) is None or isinstance(
        _csv_temp_directory(tmp_path), Path
    )
    monkeypatch.setattr(csv_ops.os, "name", "posix")
    assert _csv_temp_directory(tmp_path) == tmp_path
    source = tmp_path / "src.csv"
    target = tmp_path / "dst.csv"
    source.write_text("a,b\n", encoding="utf-8")
    _publish_csv_payload(source, target)
    assert target.exists()

    logger = MagicMock()
    monkeypatch.setattr(
        csv_ops,
        "_publish_csv_payload",
        lambda *_a, **_k: (_ for _ in ()).throw(PermissionError("locked")),
    )
    atomic_csv_write(
        table,
        tmp_path / "locked.csv",
        pa.csv.WriteOptions(),
        logger,
    )
    logger.warning.assert_called()
