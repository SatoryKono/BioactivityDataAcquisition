"""Behavior tests for one-line infrastructure coverage residuals in #10469."""

from __future__ import annotations

import importlib
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.types import RunID
from bioetl.infrastructure.adapters.chembl._fetch_paging_filtered import (
    _ChemblFetchPagingFilteredMixin,
)
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
    ProteinClassificationNode,
    ProteinClassificationResolutionError,
)
from bioetl.infrastructure.adapters.common._fetch_resilience_batch_iter import (
    iter_deduplicated_filtered_id_batches,
)
from bioetl.infrastructure.adapters.error_handling import AdapterErrorHandler
from bioetl.infrastructure.adapters.pubmed._health import PubMedHealthMixin
from bioetl.infrastructure.adapters.pubmed._search import PubMedSearchMixin
from bioetl.infrastructure.adapters.uniprot.filtering_adapter_mixin import (
    UniProtFilteringAdapterMixin,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_runtime_protections import (
    collect_lineage_protections,
)
from bioetl.infrastructure.control_plane._file_lineage_index import append_jsonl_payload
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_core import (
    validate_metric_label_policy,
)
from bioetl.infrastructure.observability.anomaly.monitor import DataQualityMonitor
from bioetl.infrastructure.storage.gold.io_delta_protocols import (
    GoldWriterDeltaModuleProtocol,
)
from bioetl.infrastructure.storage.gold.io_execution import _export_gold_merged_csv
from bioetl.infrastructure.storage.gold.writer_implementation import (
    _write_dual_targets_impl,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer_public import MetadataWriter
from bioetl.infrastructure.storage.silver.key_nullability_operations import (
    _collect_key_violations,
)
from bioetl.infrastructure.storage.silver.metadata_write_preparation import (
    _raise_missing_silver_metadata_bundle,
)
from bioetl.infrastructure.storage.silver.operations.delta_operations import (
    _SilverDeltaOperationFacade,
)
from bioetl.infrastructure.storage.silver.operations.arrow_operations import (
    SilverArrowOperations,
)
from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
    SilverMaintenanceOperations,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine_keys import (
    resolve_present_column,
)
from bioetl.infrastructure.storage.support.atomic_group import AtomicWriteGroup
from bioetl.infrastructure.storage.workflow_row_reconciliation_support import (
    _validate_strict_key_types,
)
from bioetl.infrastructure.quality._decomposition_owner_policy import (
    _validate_owner_decomposition_targets_section,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_filtered_pagination_stops_on_empty_page() -> None:
    host = SimpleNamespace(
        CHEMBL_ADAPTER_ERRORS=(OSError,),
        _build_params=lambda offset, entity: {"offset": offset, "entity": entity},
        _build_filter_params=lambda entity, field, ids: {field: ids},
        _fetch_page=AsyncMock(return_value=([], True)),
        _yield_deduplicated=MagicMock(),
        _logger=MagicMock(),
    )

    records = [
        record
        async for record in _ChemblFetchPagingFilteredMixin._paginate_filter_results(
            host,
            "/resource",
            ["1"],
            "id",
            "activity",
            "activity_id",
            set(),
            0,
            None,
        )
    ]

    assert records == []
    host._yield_deduplicated.assert_not_called()


@pytest.mark.asyncio
async def test_filtered_batch_iterator_returns_at_global_limit() -> None:
    async def _fetch(*_args: object, **_kwargs: object):
        yield {"id": "1"}
        yield {"id": "2"}

    host = SimpleNamespace(
        _get_api_pk_field=lambda _entity: "id",
        _get_api_dedup_fields=lambda _entity: None,
        _batch_ids=lambda ids, batch_size: [ids[:batch_size]],
        _fetch_batch_with_reduction=_fetch,
    )

    records = [
        record
        async for record in iter_deduplicated_filtered_id_batches(
            host,
            entity_type="activity",
            limit=1,
            filter_ids=["1", "2"],
            filter_field="id",
            batch_size=2,
        )
    ]

    assert records == [{"id": "1"}]


def test_adapter_error_handler_delegates_category_resolution() -> None:
    classifier = MagicMock()
    classifier.classify.return_value = "network"
    handler = AdapterErrorHandler(
        logger=MagicMock(),
        adapter_classifier=classifier,
    )
    error = OSError("offline")

    assert handler._resolve_error_category(error=error, status_code=503) == "network"
    classifier.classify.assert_called_once_with(error=error, status_code=503)


@pytest.mark.asyncio
async def test_pubmed_health_includes_real_api_key() -> None:
    response = SimpleNamespace(status_code=200)
    host = SimpleNamespace(
        email="operator@example.test",
        api_key="secret-key",
        _adapter_metrics=SimpleNamespace(measure_request=lambda _path: nullcontext()),
        http_client=SimpleNamespace(get_once=AsyncMock(return_value=response)),
        _logger=MagicMock(),
    )

    with patch(
        "bioetl.infrastructure.adapters.pubmed._health.is_slow_health_probe",
        return_value=False,
    ):
        status = await PubMedHealthMixin._probe_health(host)

    assert status.value == "HEALTHY"
    assert (
        host.http_client.get_once.call_args.kwargs["params"]["api_key"] == "secret-key"
    )


@pytest.mark.asyncio
async def test_pubmed_search_includes_real_api_key() -> None:
    response = MagicMock()
    response.json.return_value = {"esearchresult": {"idlist": ["1"]}}
    host = SimpleNamespace(
        email="operator@example.test",
        api_key="secret-key",
        _adapter_metrics=SimpleNamespace(measure_request=lambda _path: nullcontext()),
        http_client=SimpleNamespace(get=AsyncMock(return_value=response)),
        _request_collector=MagicMock(),
        _error_handler=MagicMock(),
        provider_name="pubmed",
    )

    assert await PubMedSearchMixin._get_pmids(host, "query", 1) == ["1"]
    assert host.http_client.get.call_args.kwargs["params"]["api_key"] == "secret-key"


def test_lineage_protection_scan_skips_empty_payload(tmp_path: Path) -> None:
    refs = SimpleNamespace(
        manifest_ids=set(),
        run_ids=set(),
        evidence_floor_manifest_ids=(),
        evidence_floor_run_ids=(),
        lineage_fragment_ids=set(),
        evidence_floor_lineage_fragment_ids=set(),
    )
    fragment = tmp_path / "empty.json"
    fragment.write_text("{}", encoding="utf-8")
    with patch(
        "bioetl.infrastructure.control_plane."
        "_file_artifact_lifecycle_runtime_protections.lineage_fragment_files",
        return_value=(fragment,),
    ):
        collect_lineage_protections(base_path=tmp_path, refs=refs)

    assert refs.lineage_fragment_ids == set()


def test_jsonl_append_preserves_original_error_when_rollback_fails(
    tmp_path: Path,
) -> None:
    os_module = MagicMock()
    os_module.open.return_value = 7
    os_module.fstat.return_value = SimpleNamespace(st_size=3)
    os_module.write.side_effect = [1, OSError("write failed")]
    os_module.ftruncate.side_effect = OSError("rollback failed")

    with pytest.raises(OSError, match="write failed"):
        append_jsonl_payload(
            tmp_path / "index.jsonl",
            b"ab",
            open_flags=1,
            os_module=os_module,
            flush_file_descriptor=MagicMock(),
        )

    os_module.close.assert_called_once_with(7)


@pytest.mark.asyncio
async def test_memory_lock_try_acquire_is_non_reentrant() -> None:
    lock = MemoryLock()
    owner = RunID("owner-1")
    first = await lock._try_acquire("key", owner)
    second = await lock._try_acquire("key", owner)

    assert first is not None
    assert second is None


def test_metric_label_policy_rejects_source_file_cardinality() -> None:
    with pytest.raises(ValueError, match="source_file"):
        validate_metric_label_policy("bioetl_test_total", {"source_file": "x.py"})


def test_quality_monitor_returns_empty_without_timestamp() -> None:
    monitor = DataQualityMonitor(logger=MagicMock())
    assert monitor.check_quality({"rows": 1.0}, timestamp=None) == []


def test_delta_protocol_stub_fails_closed() -> None:
    with pytest.raises(NotImplementedError):
        GoldWriterDeltaModuleProtocol.write_deltalake(
            object(),
            table_or_uri="table",
            data=object(),
            mode="append",
            partition_by=None,
            schema_mode=None,
        )


def test_partition_key_nullability_violation_is_reported() -> None:
    rule = SimpleNamespace(nullable=False)
    violations = _collect_key_violations(
        [{"partition": None}],
        {("partition", "partition"): rule},
        [],
        ["partition"],
    )
    assert violations == [("partition", "partition", 1)]


def test_missing_silver_metadata_bundle_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="MetadataCoordinator"):
        _raise_missing_silver_metadata_bundle(
            table_path="silver/table",
            table_name="table",
        )


def test_delta_facade_uses_injected_loader() -> None:
    expected = object()
    host = SimpleNamespace(_load_delta_module=lambda: expected)
    assert _SilverDeltaOperationFacade._load_silver_writer_module(host) is expected


@pytest.mark.asyncio
async def test_silver_csv_export_is_optional() -> None:
    host = SimpleNamespace(_csv_exporter=None)
    await SilverMaintenanceOperations.maybe_export_csv(
        host,
        "table",
        object(),
        "table.csv",
    )


def test_foreign_key_reconciliation_rejects_missing_scd2_column() -> None:
    with pytest.raises(ValueError, match="SCD2 metadata"):
        resolve_present_column([{"id": 1}], ("_valid_from", "_valid_to"))


def test_protein_classification_rejects_duplicate_levels() -> None:
    graph = ChEMBLProteinClassificationGraph(
        nodes={
            1: ProteinClassificationNode(1, 2, 1, "leaf"),
            2: ProteinClassificationNode(2, None, 1, "parent"),
        },
        component_leaf_ids={},
    )
    with pytest.raises(ProteinClassificationResolutionError, match="duplicate"):
        graph._walk_path(1)


@pytest.mark.asyncio
async def test_uniprot_fallback_ignores_non_string_accession() -> None:
    class _Decorator:
        async def execute(self, **kwargs: object):
            extract = kwargs["extract_record_id"]
            assert callable(extract)
            assert extract({"accession": 123}) is None
            if False:
                yield {}

    host = SimpleNamespace(
        _should_do_fallback=MagicMock(),
        _do_fallback_search=MagicMock(),
        _fallback_decorator=_Decorator(),
    )
    records = [
        record
        async for record in UniProtFilteringAdapterMixin.fetch_filtered_with_fallback(
            host,
            "protein",
            ["P1"],
            "accession",
            {},
        )
    ]
    assert records == []


@pytest.mark.asyncio
async def test_memory_lock_handles_lock_state_change_before_acquire() -> None:
    class _RacingLock:
        def __init__(self) -> None:
            self.calls = 0

        def locked(self) -> bool:
            self.calls += 1
            return self.calls > 1

    lock = MemoryLock()
    lock._locks["key"] = ("other", _RacingLock(), None, None, 1)
    assert await lock._try_acquire("key", RunID("owner-1")) is None


def test_metric_label_policy_reaches_source_file_specific_guard() -> None:
    with (
        patch(
            "bioetl.infrastructure.observability."
            "_prometheus_metric_label_dispatch_core."
            "FORBIDDEN_PROMETHEUS_LABEL_NAMES",
            frozenset(),
        ),
        pytest.raises(ValueError, match="source_file"),
    ):
        validate_metric_label_policy("bioetl_test_total", {"source_file": "x.py"})


def test_metrics_definitions_detects_export_registry_drift() -> None:
    import bioetl.infrastructure.observability.metrics_export_names as registry
    import bioetl.infrastructure.observability.metrics_definitions as definitions

    original = registry.METRICS_DEFINITION_EXPORT_NAMES
    try:
        registry.METRICS_DEFINITION_EXPORT_NAMES = frozenset()
        with pytest.raises(RuntimeError, match="out of sync"):
            importlib.reload(definitions)
    finally:
        registry.METRICS_DEFINITION_EXPORT_NAMES = original
        sys.modules.pop(definitions.__name__, None)
        importlib.import_module(definitions.__name__)


@pytest.mark.asyncio
async def test_gold_merged_csv_delegates_to_exporter() -> None:
    exporter = SimpleNamespace(export=AsyncMock())
    prepared = SimpleNamespace(
        request=SimpleNamespace(table_name="activity"),
        arrow_table=object(),
    )
    await _export_gold_merged_csv(SimpleNamespace(csv_exporter=exporter), prepared)
    exporter.export.assert_awaited_once_with(
        "activity",
        prepared.arrow_table,
        append=False,
    )


@pytest.mark.asyncio
async def test_gold_writer_clear_delegates_to_thread() -> None:
    writer = object.__new__(GoldWriter)
    writer.base_path = Path("gold")
    writer._resolve_table_path = lambda _table: "gold/activity"
    with patch(
        "bioetl.infrastructure.storage.gold_writer.asyncio.to_thread",
        new=AsyncMock(return_value=3),
    ) as to_thread:
        assert await writer.clear_gold("activity", dry_run=True) == 3
    assert to_thread.await_count == 1


@pytest.mark.asyncio
async def test_metadata_writer_delegates_private_write() -> None:
    request = object()
    host = SimpleNamespace(
        _operations=SimpleNamespace(write_metadata=AsyncMock(return_value="sidecar"))
    )
    assert await MetadataWriter._write_metadata(host, request) == "sidecar"


def test_silver_arrow_operation_delegates_to_standalone_preparer() -> None:
    expected = object()
    with patch(
        "bioetl.infrastructure.storage.silver.operations.arrow_operations."
        "_prepare_arrow_data_standalone",
        return_value=expected,
    ) as prepare:
        result = SilverArrowOperations._prepare_arrow_data(
            object(),
            [{"id": 1}],
            object(),
            ["id"],
        )
    assert result is expected
    prepare.assert_called_once()


def test_atomic_group_preserves_failure_before_target_selection() -> None:
    class _BrokenPending:
        def __iter__(self):
            raise OSError("cannot enumerate")

        def clear(self) -> None:
            return None

    group = AtomicWriteGroup()
    group._pending = _BrokenPending()
    group._cleanup_uncommitted = MagicMock()
    with pytest.raises(OSError, match="cannot enumerate"):
        group.commit()


def test_row_reconciliation_rejects_non_strict_type_policy() -> None:
    config = SimpleNamespace(type_policy=SimpleNamespace(value="coerce"))
    with pytest.raises(Exception, match="Unsupported reconcile_rows"):
        _validate_strict_key_types(config, left_rows=[], right_rows=[])


def test_owner_decomposition_skips_invalid_allocations_after_valid_quarter() -> None:
    errors: list[str] = []
    _validate_owner_decomposition_targets_section(
        {"owner_decomposition_targets": [{"quarter": "2026-Q4", "allocations": {}}]},
        quarter_budget_map={"2026-Q4": 0},
        owner_diversification_start=None,
        min_distinct_owners=1,
        errors=errors,
    )
    assert errors == [
        "owner_decomposition_targets[0].allocations: expected non-empty mapping"
    ]


@pytest.mark.asyncio
async def test_dual_gold_write_rejects_missing_version_schema() -> None:
    writer = SimpleNamespace(
        _contract_rollout_policy=SimpleNamespace(
            write_versions=("1.0.0",),
            active_version="1.0.0",
        )
    )
    request = SimpleNamespace(table_name="activity")
    schema_policy = SimpleNamespace(for_version=lambda _version: None)
    with (
        patch(
            "bioetl.infrastructure.storage.gold.writer_implementation."
            "validate_write_versions"
        ),
        patch(
            "bioetl.infrastructure.storage.gold.writer_implementation."
            "get_write_targets",
            return_value=("activity_v1",),
        ),
        patch(
            "bioetl.infrastructure.storage.gold.writer_implementation."
            "iterate_write_targets",
            return_value=(("1.0.0", "activity_v1"),),
        ),
    ):
        with pytest.raises(ValueError, match="No Gold schema"):
            await _write_dual_targets_impl(
                writer,
                request=request,
                schema_policy=schema_policy,
            )
