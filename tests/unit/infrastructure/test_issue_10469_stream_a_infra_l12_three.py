"""L12 residuals: adapters/config/export/adr/quality/observability/quarantine."""

from __future__ import annotations

import importlib
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.domain.control_plane.workflow_execution_state import WorkflowExecutionState
from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import RunID
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.chembl._client_request_helpers import (
    check_duplicate_record,
)
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.crossref._doi_batch_processor import (
    DoiBatchProcessor,
)
from bioetl.infrastructure.adapters.decorators._retry_operations import (
    retry_health_check,
)
from bioetl.infrastructure.adapters.decorators._retry_support import (
    default_retry_config,
    is_retryable_exception,
)
from bioetl.infrastructure.adapters.openalex.cursor_flow import OpenAlexCursorFlow
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_identifiers import (
    _PubChemIdentifierFetchMixin,
)
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed._filter_fetch_support import (
    empty_async_iterator,
)
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter
from bioetl.infrastructure.adr.fs_adr_service import FilesystemAdrCatalog
from bioetl.infrastructure.config._base import _get_pipeline_config_root
from bioetl.infrastructure.config._dq_config_layers import _load_unified_quality_layer
from bioetl.infrastructure.config.chembl_policy_registry_loader import (
    ChemblPolicyRegistryLoader,
)
from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)
from bioetl.infrastructure.config.reason_catalog_loader import (
    load_default_reason_catalog,
)
from bioetl.infrastructure.control_plane.file_workflow_execution_state_store import (
    FileWorkflowExecutionStateStore,
)
from bioetl.infrastructure.export.debug_export_adapter import DebugExportAdapter
from bioetl.infrastructure.export.export_writer_adapter import _write_xlsx_file
from bioetl.infrastructure.observability._metrics_server_startup import (
    start_metrics_server_runtime,
)
from bioetl.infrastructure.observability._metrics_server_state import reset_server_state
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_policy import (
    _normalize_structural_metric_labels,
)
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_publication import (
    _normalize_publication_lifecycle_labels,
    _normalize_publication_registry_labels,
)
from bioetl.infrastructure.observability.anomaly.detector import AnomalyDetector
from bioetl.infrastructure.observability.observability_backend_probes import (
    wait_for_observability_backend_ready,
    wait_for_observability_backend_required_paths_ready,
)
from bioetl.infrastructure.observability.observability_backend_process import (
    _find_posix_listener_pids_by_port,
)
from bioetl.infrastructure.quality.architecture_quality_scoring import _interpretation
from bioetl.infrastructure.quality.exemptions_registry_targets import (
    _validate_registry_entries,
)
from bioetl.infrastructure.quarantine.filtered_read_support import (
    _matches_values_filter,
    _parse_time_bound,
)
from bioetl.infrastructure.schemas._composite_config_merge_schema import (
    MergeSortBySchema,
)

pytestmark = pytest.mark.unit


class _PublicationMetric:
    def labels(self, **_labels: str) -> SimpleNamespace:
        return SimpleNamespace(inc=lambda: None)


def test_default_retry_config_and_non_recoverable_classification() -> None:
    config = default_retry_config()
    assert config.max_attempts >= 1
    assert is_retryable_exception(ValueError("nope"), config) is False
    assert is_retryable_exception(TimeoutError("net"), config) is True


@pytest.mark.asyncio
async def test_base_sync_adapter_run_in_executor() -> None:
    pool = ThreadPoolExecutor(max_workers=1)
    adapter = BaseSyncAdapter(
        logger=MagicMock(),
        rate_limiter=MagicMock(),
        circuit_breaker=MagicMock(),
        thread_pool=pool,
        error_handler=MagicMock(),
        owns_thread_pool=False,
    )
    try:
        result = await adapter._run_in_executor(lambda value: int(value) + 1, 40)
        assert result == 41
    finally:
        pool.shutdown(wait=False)


def test_publication_vocabulary_inherit_non_dict_nodes() -> None:
    loader = PublicationControlledVocabularyLoader(Path("."))
    assert loader._resolve_inherited_values({"a": "scalar"}, "a.b") == set()
    assert loader._resolve_inherited_values({"a": {"b": "leaf"}}, "a.b") == set()


def test_workflow_execution_state_save_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FileWorkflowExecutionStateStore(base_path=tmp_path)
    state = WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000001")),
        manifest_id="manifest-1",
        workflow_name="wf",
        execution_fingerprint="fp",
        status="running",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=None,
        selected_step_ids=(),
        steps=(),
        completed_transform_fingerprints={},
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_workflow_execution_state_store.atomic_write_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(Exception, match="Workflow execution state"):
        store.save(state)


def test_anomaly_detector_inf_inf_baseline() -> None:
    detector = AnomalyDetector()
    anomaly = detector._create_threshold_anomaly(
        "latency",
        3.0,
        float("-inf"),
        float("inf"),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert anomaly.baseline_mean == 3.0
    assert anomaly.baseline_stddev == 0.0


def test_find_posix_listener_pids_when_ss_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.observability.observability_backend_process._resolve_system_executable",
        lambda _cmd: "/usr/bin/ss",
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.observability.observability_backend_process._run_listener_probe",
        lambda _cmd: "LISTEN 0 128 0.0.0.0:8000 users:((python,pid=42,fd=3))",
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.observability.observability_backend_process._parse_posix_ss_listener_pids",
        lambda _output, port: (42,) if port == 8000 else (),
    )
    assert _find_posix_listener_pids_by_port(8000) == (42,)


def test_pyarrow_compute_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import bioetl.infrastructure.quarantine._pyarrow_helpers as helpers

    monkeypatch.setitem(sys.modules, "pyarrow.compute", None)
    reloaded = importlib.reload(helpers)
    assert reloaded.pc is None
    monkeypatch.undo()
    importlib.reload(helpers)


def test_adapter_metrics_dropped_duplicates_when_metrics_none() -> None:
    recorder = AdapterMetricsRecorder(metrics=None, provider="chembl")
    recorder.record_dropped_duplicates("activity", 4)


@pytest.mark.asyncio
async def test_empty_async_iterator_yields_nothing() -> None:
    assert [row async for row in empty_async_iterator()] == []


def test_pipeline_config_root_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: list[Path] = []

    def _resolve(path: Path | None = None) -> Path:
        if path is not None:
            seen.append(path)
            return path
        return tmp_path

    monkeypatch.setattr(
        "bioetl.infrastructure.config._base.resolve_configs_root",
        _resolve,
    )
    resolved = _get_pipeline_config_root(config_root=str(tmp_path / "configs"))
    assert resolved == tmp_path / "configs"
    assert seen[0] == tmp_path / "configs"


def test_load_quality_layer_no_keys(tmp_path: Path) -> None:
    layer = tmp_path / "quality.yaml"
    layer.write_text("unrelated: true\n", encoding="utf-8")
    loaded = _load_unified_quality_layer(
        layer_path=layer,
        fallback_keys=("thresholds",),
        load_yaml=lambda _path: {"unrelated": True},
    )
    assert loaded == {}


def test_load_default_reason_catalog_all_candidates_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_default_reason_catalog.cache_clear()
    monkeypatch.setattr(
        "bioetl.infrastructure.config.reason_catalog_loader._catalog_candidates",
        lambda: [Path("missing-a.yaml"), Path("missing-b.yaml")],
    )
    catalog = load_default_reason_catalog()
    load_default_reason_catalog.cache_clear()
    assert catalog is not None


def test_interpretation_good_band() -> None:
    assert _interpretation(8.5) == "good_targeted_improvements"
    assert _interpretation(9.9) == "good_targeted_improvements"


def test_merge_unit_companion_policies_non_dict() -> None:
    ChemblPolicyRegistryLoader._merge_unit_companion_policies({}, "not-a-dict")


def test_composite_sort_by_duplicates() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        MergeSortBySchema(silver=["id", "id"], gold=["id"])


def test_metrics_server_already_started_inside_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FlipRuntime:
        def __init__(self) -> None:
            self._reads = 0
            self.lock = __import__("threading").RLock()

        @property
        def started(self) -> bool:
            self._reads += 1
            return self._reads > 1

    monkeypatch.setattr(
        "bioetl.infrastructure.observability._metrics_server_startup._SERVER_RUNTIME",
        _FlipRuntime(),
    )
    started = start_metrics_server_runtime(
        start_http_server_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not start")
        ),
        sleep_fn=lambda _delay: None,
        publication_metric=_PublicationMetric(),
    )
    assert started is True


def test_metrics_server_retry_count_exhausted() -> None:
    reset_server_state()
    try:
        started = start_metrics_server_runtime(
            start_http_server_fn=lambda *_args, **_kwargs: None,
            sleep_fn=lambda _delay: None,
            publication_metric=_PublicationMetric(),
            retry_count=0,
        )
        assert started is False
    finally:
        reset_server_state()


def test_structural_policy_and_shadow_comparison_labels() -> None:
    policy = _normalize_structural_metric_labels(
        "bioetl_structural_policy_events_total",
        {"action": "other"},
    )
    assert policy is not None
    assert "action" in policy
    shadow = _normalize_structural_metric_labels(
        "bioetl_structural_policy_shadow_comparisons_total",
        {"comparison": "other"},
    )
    assert shadow is not None
    assert "comparison" in shadow


def test_publication_artifact_and_runtime_status_labels() -> None:
    artifact = _normalize_publication_lifecycle_labels(
        "bioetl_output_artifact_publication_events_total",
        {"stage": "silver", "status": "success"},
    )
    assert artifact is not None
    runtime = _normalize_publication_registry_labels(
        "bioetl_observability_runtime_status",
        {"component": "metrics_server"},
    )
    assert runtime is not None
    assert "component" in runtime


def test_exemptions_validate_registry_non_dict_and_unknown_context() -> None:
    errors: list[str] = []
    _validate_registry_entries(
        registry_name="class_size",
        entries=["not-a-dict"],
        classes_by_module={},
        functions_by_module={},
        class_counts=Counter(),
        function_counts=Counter(),
        errors=errors,
    )
    _validate_registry_entries(
        registry_name="unknown_registry",
        entries={"Foo": {}},
        classes_by_module={},
        functions_by_module={},
        class_counts=Counter(),
        function_counts=Counter(),
        errors=errors,
    )
    assert errors == []


def test_debug_export_successful_xlsx_else_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.application.services.export_lineage.debug_export_service import (
        DebugExportPack,
    )

    created_at = datetime(2026, 6, 2, 10, 0, 0, tzinfo=UTC)
    pack = DebugExportPack(
        run_id="00000000-0000-0000-0000-000000000321",
        pipeline_id="chembl_activity",
        provider_id="chembl",
        workflow_id="standalone",
        manifest_id=None,
        status="success",
        output_root=str(tmp_path),
        formats=("csv", "xlsx"),
        include_bom=False,
        max_rows_per_sheet=3,
        created_at=created_at,
        tables={"silver_full": ()},
        reason_dictionary=(),
    )
    adapter = DebugExportAdapter()

    def _write_xlsx(path: Path, *_args: object, **_kwargs: object) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"xlsx")

    monkeypatch.setattr(adapter, "_write_xlsx", _write_xlsx)
    result = adapter.write_pack(pack=pack)
    assert any(str(path).endswith("debug_export.xlsx") for path in result.file_paths)


def test_write_xlsx_file_success_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out.xlsx"
    dataframe = SimpleNamespace(to_excel=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "bioetl.domain.serialization.flatten_arrow_table_for_export",
        lambda _table: SimpleNamespace(to_pandas=lambda: dataframe),
    )
    assert _write_xlsx_file(object(), output) == output


def test_chembl_duplicate_wrappers() -> None:
    logger = MagicMock()
    metrics = AdapterMetricsRecorder(metrics=None, provider="chembl")
    seen: set[str] = set()
    assert (
        check_duplicate_record(
            record={"activity_id": "1"},
            pk_field="activity_id",
            seen_ids=seen,
            entity_type="activity",
            logger=logger,
            adapter_metrics=metrics,
        )
        is False
    )
    adapter = ChemblAdapter.__new__(ChemblAdapter)
    adapter._logger = logger
    adapter._adapter_metrics = metrics
    seen_client: set[str] = set()
    assert (
        ChemblAdapter._is_duplicate_record(
            adapter,
            {"activity_id": "2"},
            "activity_id",
            seen_client,
            "activity",
        )
        is False
    )


@pytest.mark.asyncio
async def test_doi_batch_processor_runtime_fallback() -> None:
    processor = DoiBatchProcessor(
        http=SimpleNamespace(get=AsyncMock(return_value=None)),
        logger=MagicMock(),
        metrics=SimpleNamespace(
            measure_request=lambda *_a, **_k: __import__("contextlib").nullcontext()
        ),
        mailto="a@b.c",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {},
    )

    async def _fail(_dois: list[str]) -> Any:
        raise TimeoutError("batch down")

    async def _fallback(dois: list[str]) -> Any:
        for doi in dois:
            yield {"DOI": doi}

    processor._execute_batch_request = _fail  # type: ignore[method-assign]
    processor._fallback_individual_fetch = _fallback  # type: ignore[method-assign]
    rows = [row async for row in processor.fetch_batch(["10.1000/xyz"])]
    assert rows == [{"DOI": "10.1000/xyz"}]


def test_crossref_fallback_decorator_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        CrossRefAdapter, "_bootstrap_dataclass_http_adapter", lambda self: None
    )
    monkeypatch.setattr(
        CrossRefAdapter, "_bind_fallback_fetch_service", lambda self, _svc: None
    )
    monkeypatch.setattr(
        CrossRefAdapter, "configure_fallback_policy", lambda self, _policy: None
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.crossref.client.build_crossref_runtime_services",
        lambda **_kwargs: SimpleNamespace(
            query_builder=None,
            response_mapper=None,
            batch_fetcher=None,
            search_paginator=None,
            fallback_handler=None,
        ),
    )
    adapter = CrossRefAdapter.__new__(CrossRefAdapter)
    adapter.fallback_fetch_service = MagicMock()
    adapter.query_builder = None
    adapter.response_mapper = None
    adapter.batch_fetcher = None
    adapter.search_paginator = None
    adapter.title_fallback_handler = None
    adapter.fetch_flow = None
    adapter._fallback_decorator = None
    adapter._logger = MagicMock()
    with pytest.raises(RuntimeError, match="fallback decorator"):
        adapter.__post_init__()


@pytest.mark.asyncio
async def test_retry_health_check_reraises_circuit_open() -> None:
    async def _open() -> Any:
        raise CircuitBreakerOpenError("chembl", retry_after=1.0)

    with pytest.raises(CircuitBreakerOpenError):
        await retry_health_check(
            health_check_fn=_open,
            retry_config=RetryConfig(max_attempts=3),
            logger=MagicMock(),
            metrics=None,
            provider_name="chembl",
        )


@pytest.mark.asyncio
async def test_openalex_doi_batch_limit_inner_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = OpenAlexCursorFlow(
        mailto=None,
        batch_size=10,
        title_search_cache_size=1,
        normalize_doi=lambda value: value,
        escape_title_for_search=lambda value: value,
        query_executor=MagicMock(),
        response_mapper=SimpleNamespace(
            mark_lookup=lambda work, **_kwargs: work,
        ),
        logger=MagicMock(),
        runtime_errors=(TimeoutError,),
    )

    async def _iter_by_dois(self: OpenAlexCursorFlow, dois: list[str]) -> Any:
        del self
        for doi in dois:
            yield {"doi": doi}

    monkeypatch.setattr(OpenAlexCursorFlow, "iter_by_dois", _iter_by_dois)
    rows = [
        row async for row in flow.iter_doi_batches_for_fallback(["a", "b"], limit=1)
    ]
    assert rows == [{"doi": "a"}]


@pytest.mark.asyncio
async def test_pubchem_identifier_exception_and_inchikey_limit() -> None:
    class _Host(_PubChemIdentifierFetchMixin):
        FETCH_STRATEGY_ERRORS = (ValueError,)
        _logger = MagicMock()
        _provider_name = "pubchem"

        async def _fetch_single_smiles(self, smiles: str) -> list[dict[str, str]]:
            raise RuntimeError(smiles)

        def _filter_valid_inchikeys(self, keys: list[str]) -> list[str]:
            return keys

        async def _iter_inchikey_chunk_records(self, chunk: list[str]) -> Any:
            for key in chunk:
                yield {"inchikey": key}

    host = _Host()
    with pytest.raises(RuntimeError, match="CCO"):
        async for _row in host._iter_smiles_chunk_records(["CCO"]):
            raise AssertionError("should not yield")
    rows = [
        row
        async for row in host.fetch_by_inchikey(["AAAA", "BBBB"], limit=1, batch_size=1)
    ]
    assert rows == [{"inchikey": "AAAA"}]


def test_pubchem_adapter_requires_request_collector() -> None:
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        with pytest.raises(ValueError, match="request_collector"):
            PubChemAdapter(
                logger=MagicMock(),
                rate_limiter=MagicMock(),
                circuit_breaker=MagicMock(),
                thread_pool=pool,
                entity_mapper=MagicMock(),
                fetch_strategies=MagicMock(),
                error_handler=MagicMock(),
                request_collector=None,
            )
    finally:
        pool.shutdown(wait=False)


def test_fs_adr_service_skips_when_text_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = FilesystemAdrCatalog()
    monkeypatch.setattr(
        "bioetl.infrastructure.adr.fs_adr_service.validate_filename",
        lambda _path, _issues: re.match(r"(\d+)", "0001"),
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.adr.fs_adr_service.validate_duplicate_number",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.adr.fs_adr_service.read_adr_text",
        lambda *_args, **_kwargs: None,
    )
    issues: list[object] = []
    catalog._validate_single_adr_file(
        Path("0001-example.md"),
        seen_numbers=set(),
        issues=issues,  # type: ignore[arg-type]
    )
    assert issues == []


def test_observability_backend_probe_timeout_last_call() -> None:
    assert (
        wait_for_observability_backend_ready(
            "http://127.0.0.1/health",
            timeout_seconds=0.0,
            poll_seconds=0.0,
            probe_fn=lambda _url: False,
            sleep_fn=lambda _delay: None,
        )
        is False
    )
    assert (
        wait_for_observability_backend_required_paths_ready(
            "http://127.0.0.1/health",
            required_probe_paths=("/metrics",),
            timeout_seconds=0.0,
            poll_seconds=0.0,
            required_probe_fn=lambda *_args, **_kwargs: False,
            sleep_fn=lambda _delay: None,
        )
        is False
    )


def test_filtered_read_support_non_str_and_naive_timestamp() -> None:
    assert _matches_values_filter(12, {"activity"}) is False
    parsed = _parse_time_bound("2026-01-01T00:00:00")
    assert parsed is not None
    assert parsed.tzinfo is not None


def test_filtered_record_empty_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.infrastructure.quarantine import filtered_reads

    monkeypatch.setattr(
        filtered_reads, "DeltaTable", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(
        filtered_reads,
        "_load_scoped_pyarrow_table",
        lambda *_args, **_kwargs: SimpleNamespace(
            to_pylist=lambda: [{"payload_hash": "x"}]
        ),
    )
    monkeypatch.setattr(
        filtered_reads, "_build_run_type_lookup", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr(
        filtered_reads, "_iter_filtered_rows", lambda *_args, **_kwargs: []
    )
    assert (
        filtered_reads.get_filtered_record(
            "table",
            None,
            payload_hash="x",
            pipeline="chembl_activity",
        )
        is None
    )


@pytest.mark.asyncio
async def test_unified_quarantine_empty_write_and_missing_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.infrastructure.quarantine import unified

    store = unified.UnifiedQuarantineAdapter.__new__(unified.UnifiedQuarantineAdapter)
    await unified.UnifiedQuarantineAdapter.write_many(store, [])
    store.base_path = "unused"
    store.status_events_path = Path("unused")
    monkeypatch.setattr(unified, "DeltaTable", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        unified,
        "read_delta_records",
        lambda _dt: [{"payload_hash": "other", "pipeline": "p"}],
    )
    assert store.get_record(payload_hash="missing") is None
