"""Stream A storage residuals without gold_writer/silver_writer/deltalake."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pyarrow as pa
import pytest

from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.domain.ports import RowReconciliationConfig, RowReconciliationLayer
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.workflow.foreign_key_reconciliation import ForeignKeyReconciliationRequest
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze.metadata_builders import (
    BronzeLineageMetadataRequest,
    BronzeMetadataPayloadRequest,
    build_bronze_lineage_metadata,
    build_bronze_metadata_payload,
    build_full_bronze_metadata,
)
from bioetl.infrastructure.storage.bronze.metadata_snapshot_refs import (
    attach_live_snapshot_to_source_metadata,
    build_bronze_source_metadata_with_live_snapshot,
    build_live_input_snapshot_ref,
    build_live_input_snapshot_ref_if_available,
    content_addressed_snapshot_id,
)
from bioetl.infrastructure.storage.delta.arrow_converter import (
    ArrowDataConverter,
    build_arrow_schema_preparation_context,
    filter_record_for_schema,
    serialize_value_for_arrow_schema,
    sort_arrow_table_by_primary_keys,
)
from bioetl.infrastructure.storage.delta.schema_ops import (
    coerce_null_types_for_delta,
    delta_schema_to_pyarrow,
    drop_nondeterministic_persisted_fields,
)
from bioetl.infrastructure.storage.lineage_persistence import (
    emit_composite_source_selection_metrics,
    emit_lineage_refs_missing_metric,
    lineage_fragment_publication_required,
    persist_lineage_fragment_if_present,
    resolve_metadata_and_lineage_fragment,
)
from bioetl.infrastructure.storage.metadata.builder_base import (
    _MetadataBuilderBase,
    _build_gold_artifact_id,
    _build_silver_artifact_id,
    _get_git_commit_cached,
    _parse_table_name,
    _resolve_metadata_timestamp,
    _resolve_records_metadata_timestamp,
)
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    CheckpointPathError,
    CheckpointSizeError,
    FileCompositeCheckpointWriter,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine_keys import (
    build_orphan_key_rows,
    require_sql_identifier,
    resolve_mutation_identity_keys,
    resolve_present_column,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    complete_dry_run,
    complete_without_mutation,
    emit_reconcile_debug_artifacts,
    filter_source_rows_to_current_run,
    normalize_value,
    partition_source_rows,
    record_reconciliation_metrics,
    reference_value_set,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import (
    StorageRowReconciliationAdapter,
)

pytestmark = pytest.mark.unit


def _fk_request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload = {
        "source_table": "src",
        "reference_table": "ref",
        "source_key": "parent_id",
        "reference_key": "id",
        "primary_keys": ("id",),
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)


class TestBuilderBase:
    def test_parse_table_name_variants(self) -> None:
        assert _parse_table_name("chembl.activity") == ("chembl", "activity")
        assert _parse_table_name("chembl/activity") == ("chembl", "activity")
        assert _parse_table_name("chembl_activity") == ("chembl", "activity")
        assert _parse_table_name("activity") == ("unknown", "activity")
        assert _parse_table_name("") == ("unknown", "unknown")

    def test_timestamp_resolution_and_artifact_ids(self) -> None:
        naive = datetime(2024, 1, 1, 12, 0, 0)
        records = [
            {"_ingestion_ts": "2024-01-02T00:00:00+00:00"},
            {"_lineage_created_at": naive},
            {"_ingestion_ts": "not-a-ts"},
        ]
        resolved = _resolve_records_metadata_timestamp(records)
        assert resolved is not None
        assert _resolve_metadata_timestamp(explicit=naive, records=[]) == naive.replace(
            tzinfo=UTC
        )
        with pytest.raises(ValueError, match="Deterministic metadata timestamp"):
            _resolve_metadata_timestamp(explicit=None, records=[{}])
        assert "silver" in _build_silver_artifact_id("chembl.activity", 3)
        assert "gold" in _build_gold_artifact_id("chembl/activity")

    def test_git_commit_cache_missing_and_dq_signal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("shutil.which", lambda _name: None)
        assert _get_git_commit_cached() is None
        monkeypatch.setattr("shutil.which", lambda _name: "git")
        monkeypatch.setattr(
            "subprocess.run",
            lambda *_a, **_k: (_ for _ in ()).throw(FileNotFoundError("git")),
        )
        assert _get_git_commit_cached() is None
        builder = _MetadataBuilderBase(transform_version="9.0.0", transform_steps=("a",))
        runtime, pipeline, lineage = builder._build_composite_runtime_pipeline_lineage(
            table_name="chembl.activity",
            now=datetime(2024, 1, 1, tzinfo=UTC),
            run_id="run-1",
            sources_used=["chembl"],
        )
        assert pipeline.provider == "chembl"
        assert lineage.transform_steps == ["a"]
        assert runtime.run_id == "run-1"
        summary = _MetadataBuilderBase._build_merged_dq_summary(
            [{"_cv_error": True}, {"_cv_warn": True}]
        )
        assert summary.error_records == 1
        assert summary.warning_records == 1
        env = _MetadataBuilderBase._build_environment_metadata()
        assert env.hostname


class TestForeignKeySupport:
    def test_current_run_scope_and_partition(self) -> None:
        rows = [{"id": "1", "_run_id": "run-a"}, {"id": "2", "_run_id": "run-b"}]
        scoped, disposition = filter_source_rows_to_current_run(
            rows, source_scope="current_run", source_run_ids=("run-a",)
        )
        assert disposition == "current_run"
        assert [row["id"] for row in scoped] == ["1"]
        empty, blocked = filter_source_rows_to_current_run(
            rows, source_scope="current_run", source_run_ids=()
        )
        assert empty == []
        assert blocked == "blocked"
        no_col, blocked_col = filter_source_rows_to_current_run(
            [{"id": "1"}], source_scope="current_run", source_run_ids=("run-a",)
        )
        assert no_col == []
        assert blocked_col == "blocked"
        passthrough, all_current = filter_source_rows_to_current_run(
            rows, source_scope="all_current", source_run_ids=()
        )
        assert passthrough == rows
        assert all_current == "all_current"

        request = _fk_request()
        refs = reference_value_set(request, [{"id": 5}, {"id": "skip"}])
        retained, orphans = partition_source_rows(
            request,
            source_rows=[
                {"id": "1", "parent_id": None},
                {"id": "2", "parent_id": 5},
                {"id": "3", "parent_id": 9},
            ],
            reference_values=refs,
        )
        assert len(retained) == 2
        assert [row["id"] for row in orphans] == ["3"]

    def test_complete_paths_metrics_and_debug(self) -> None:
        host = SimpleNamespace(_log=MagicMock())
        request = _fk_request(dry_run=True)
        no_op = complete_without_mutation(
            host, request, scanned_rows=2, retained_rows=2, orphan_rows_deleted=0
        )
        assert no_op.mutated is False
        dry = complete_dry_run(
            host, request, scanned_rows=3, retained_rows=1, orphan_rows_deleted=2
        )
        assert dry.would_mutate is True
        record_reconciliation_metrics(
            None, scanned=1, retained=1, deleted=0,
            scanned_metric="s", retained_metric="r", deleted_metric="d",
        )
        metrics = MagicMock()
        record_reconciliation_metrics(
            metrics, scanned=1, retained=1, deleted=0,
            scanned_metric="s", retained_metric="r", deleted_metric="d",
        )
        metrics.increment_counter.assert_called()
        emit_reconcile_debug_artifacts(
            MagicMock(),
            request,
            no_op,
            retained_rows=[],
            orphan_rows=[],
        )
        sink = MagicMock()
        enabled = _fk_request(
            debug_export_enabled=True,
            workflow_run_id="run-1",
            step_id="step-1",
        )
        emit_reconcile_debug_artifacts(
            sink, enabled, no_op, retained_rows=[{"id": "1"}], orphan_rows=[]
        )
        sink.write_reconcile_debug_artifacts.assert_called_once()
        assert normalize_value(5.0) == ("int", 5)
        assert normalize_value(True) == ("bool", True)
        assert normalize_value("  ") is None

    def test_quarantine_keys(self) -> None:
        assert require_sql_identifier("parent_id", "col") == "parent_id"
        with pytest.raises(ValueError, match="safe SQL identifier"):
            require_sql_identifier("1bad", "col")
        rows = [{"_is_current": True, "id": "1"}]
        assert resolve_present_column(rows, ("_is_current", "is_current")) == "_is_current"
        with pytest.raises(ValueError, match="SCD2 metadata column"):
            resolve_present_column([{"id": "1"}], ("_is_current",))
        keys = resolve_mutation_identity_keys(
            [{"id": "1", "_run_id": "run-a"}, {"id": "2", "_run_id": "run-a"}],
            ("id",),
            source_scope="all_current",
        )
        assert keys == ("id", "_run_id")
        with pytest.raises(ValueError, match="mixed row identity"):
            resolve_mutation_identity_keys(
                [{"id": "1", "_run_id": "a"}, {"id": "2"}],
                ("id",),
                source_scope="current_run",
            )
        projected = build_orphan_key_rows(
            [{"id": "1"}, {"id": "1"}, {"id": "2"}],
            ("id",),
            operation="delete",
        )
        assert [row["id"] for row in projected] == ["1", "2"]
        with pytest.raises(ValueError, match="non-null primary key"):
            build_orphan_key_rows([{"id": None}], ("id",), operation="delete")


class TestBronzeMetadata:
    def test_lineage_and_payload_builders(self) -> None:
        now = datetime(2024, 1, 1, tzinfo=UTC)
        request = BronzeLineageMetadataRequest(
            run_id=RunID(UUID("00000000-0000-4000-8000-000000000001")),
            run_type=RunType.INCREMENTAL,
            effective_ts=now,
            provider="chembl",
            entity="activity",
            batch_id=BatchID(UUID("00000000-0000-4000-8000-000000000002")),
        )
        lineage = build_bronze_lineage_metadata(request)
        assert lineage["provider"] == "chembl"
        payload_request = BronzeMetadataPayloadRequest(
            run_id=request.run_id,
            run_type=RunType.BACKFILL,
            provider="chembl",
            entity="activity",
            record_count=2,
            compressed_size=10,
            output_path="chembl/activity/batch.jsonl.zst",
            started_at=now,
            completed_at=now,
            duration_seconds=1.5,
            source_metadata=None,
        )
        payload = build_bronze_metadata_payload(payload_request)
        assert payload["pipeline"].entity == "activity"
        metadata = build_full_bronze_metadata(payload_request)
        assert metadata.output.record_count == 2

    def test_live_snapshot_refs(self, tmp_path: Path) -> None:
        snapshot = InputSnapshotRef(
            snapshot_id="sha256:abc",
            content_hash="abc",
            immutable_uri="bronze://a.jsonl",
            query_fingerprint=None,
            captured_at=None,
        )
        assert build_bronze_source_metadata_with_live_snapshot(
            source_metadata=None, snapshot=None
        ) is None
        created = build_bronze_source_metadata_with_live_snapshot(
            source_metadata=None, snapshot=snapshot
        )
        assert created is not None
        assert created.input_snapshots[0].snapshot_id == "sha256:abc"
        source = SourceMetadata(type="api", input_snapshots=[snapshot])
        same = attach_live_snapshot_to_source_metadata(
            source_metadata=source, snapshot=snapshot
        )
        assert same is source
        assert build_live_input_snapshot_ref_if_available(
            base_path=tmp_path, relative_path="missing.jsonl", query_string=None
        ) is None
        batch = tmp_path / "batch.jsonl"
        batch.write_bytes(b"abc")
        live = build_live_input_snapshot_ref(
            full_path=batch, relative_path="p/batch.jsonl", query_string="q=1"
        )
        assert live.snapshot_id == content_addressed_snapshot_id(live.content_hash)
        assert live.query_fingerprint is not None


class TestDeltaHelpers:
    def test_schema_ops_and_arrow_converter(self) -> None:
        schema = pa.schema([("ok", pa.string()), ("empty", pa.null())])
        table = pa.table({"ok": ["a"], "empty": [None]})
        coerced = coerce_null_types_for_delta(table)
        assert not pa.types.is_null(coerced.schema.field("empty").type)
        lists = pa.table({"items": pa.array([None], type=pa.list_(pa.null()))})
        coerced_lists = coerce_null_types_for_delta(lists)
        assert pa.types.is_list(coerced_lists.schema.field("items").type)
        dropped = drop_nondeterministic_persisted_fields(
            pa.table({"id": ["1"], "_ingestion_ts": ["x"]})
        )
        assert "_ingestion_ts" not in dropped.column_names
        converted = delta_schema_to_pyarrow(SimpleNamespace(to_arrow=lambda: schema))
        assert converted.names == ["ok", "empty"]
        with pytest.raises(TypeError, match="Unsupported delta schema"):
            delta_schema_to_pyarrow(SimpleNamespace())

        converter = ArrowDataConverter(logger=MagicMock())
        assert pa.types.is_string(converter.sanitize_type_for_delta(pa.null()))
        nested = converter.sanitize_type_for_delta(pa.list_(pa.null()))
        assert pa.types.is_list(nested)
        empty = converter.convert_records_to_arrow([])
        assert empty.num_rows == 0
        records = [{"id": "2", "payload": {"k": 1}}, {"id": "1", "payload": {"k": 0}}]
        ordered = converter.convert_records_to_arrow(
            records, primary_keys=["id"], column_order=["id", "payload"]
        )
        assert ordered.column("id").to_pylist() == ["1", "2"]
        schema_aware = pa.schema([("id", pa.string()), ("payload", pa.string())])
        converted_schema = converter.convert_records_to_arrow_with_schema(
            records, schema_aware, primary_keys=["id"]
        )
        assert converted_schema.num_rows == 2
        context = build_arrow_schema_preparation_context(schema_aware)
        filtered = filter_record_for_schema({"id": "1", "payload": {"a": 1}}, context)
        assert isinstance(filtered["payload"], str)
        assert serialize_value_for_arrow_schema(None, True) is None
        unsorted = sort_arrow_table_by_primary_keys(
            pa.table({"id": ["b", "a"]}), ["missing"], logger=MagicMock()
        )
        assert unsorted.column("id").to_pylist() == ["b", "a"]


class TestLineagePersistence:
    def test_publication_required_and_metrics(self) -> None:
        assert lineage_fragment_publication_required(None) is False
        coordinator = SimpleNamespace(
            run_context=SimpleNamespace(exact_replay=True, required_persistence_profile="")
        )
        assert lineage_fragment_publication_required(coordinator) is True
        metrics = MagicMock()
        emit_lineage_refs_missing_metric(
            metrics, pipeline_name=None, layer="gold", ref_type="silver", missing_count=0
        )
        metrics.increment_counter.assert_not_called()
        emit_lineage_refs_missing_metric(
            metrics, pipeline_name=None, layer="gold", ref_type="silver"
        )
        emit_composite_source_selection_metrics(
            metrics,
            pipeline_name="p",
            layer="gold",
            sources_used=["chembl"],
            records=[{"_source_providers": ["pubmed"], "_field_sources": {"id": "chembl"}}],
        )
        metadata, fragment = resolve_metadata_and_lineage_fragment(
            coordinator=None,
            bundle_factory_name="create_gold_metadata_bundle",
            coordinator_factory_name=None,
            input_data=None,
            fallback_factory=lambda: "fallback",
        )
        assert metadata == "fallback"
        assert fragment is None
        bundle_coord = SimpleNamespace(
            create_gold_metadata_bundle=lambda _inp: SimpleNamespace(
                metadata="meta", lineage_fragment="frag"
            )
        )
        resolved, lineage = resolve_metadata_and_lineage_fragment(
            coordinator=bundle_coord,
            bundle_factory_name="create_gold_metadata_bundle",
            coordinator_factory_name=None,
            input_data={},
            fallback_factory=lambda: "fallback",
        )
        assert resolved == "meta"
        assert lineage == "frag"

    async def test_persist_fragment_paths(self) -> None:
        with pytest.raises(RuntimeError, match="requires a lineage fragment"):
            await persist_lineage_fragment_if_present(
                lineage_store=MagicMock(),
                lineage_fragment=None,
                required=True,
            )
        with pytest.raises(RuntimeError, match="requires a lineage store"):
            await persist_lineage_fragment_if_present(
                lineage_store=None,
                lineage_fragment=SimpleNamespace(fragment_id="ok", nodes=[], edges=[]),
                required=True,
            )
        incomplete = SimpleNamespace(fragment_id="gold", nodes=[], edges=[])
        await persist_lineage_fragment_if_present(
            lineage_store=MagicMock(),
            lineage_fragment=incomplete,
            required=False,
        )
        store = MagicMock()
        store.save = MagicMock(side_effect=OSError("disk"))
        metrics = MagicMock()
        with pytest.raises(OSError, match="disk"):
            await persist_lineage_fragment_if_present(
                lineage_store=store,
                lineage_fragment=SimpleNamespace(
                    fragment_id="frag-1", nodes=[], edges=[]
                ),
                metrics=metrics,
                pipeline_name="p",
                layer="gold",
            )
        store.save = MagicMock()
        await persist_lineage_fragment_if_present(
            lineage_store=store,
            lineage_fragment=SimpleNamespace(fragment_id="frag-1", nodes=[], edges=[]),
            metrics=metrics,
            pipeline_name="p",
            layer="gold",
        )


class TestCheckpointAndRowReconciliation:
    def test_checkpoint_writer_guards(self, tmp_path: Path) -> None:
        writer = FileCompositeCheckpointWriter(tmp_path, max_checkpoint_bytes=8)
        with pytest.raises(CheckpointPathError, match="relative"):
            writer.read("/abs.json")
        with pytest.raises(CheckpointPathError, match="escapes"):
            writer.read("../x.json")
        assert writer.read("missing.json") is None
        writer.write_atomic("ok.json", "hi")
        assert writer.exists("ok.json") is True
        assert writer.read("ok.json") == "hi"
        with pytest.raises(CheckpointSizeError, match="payload exceeds"):
            writer.write_atomic("big.json", "too-large-payload")
        oversized = tmp_path / "ok.json"
        oversized.write_bytes(b"0123456789")
        with pytest.raises(CheckpointSizeError, match="exceeds max size"):
            writer.read("ok.json")
        assert writer.delete("missing.json") is False
        assert writer.list_glob("*.json")
        tiny = FileCompositeCheckpointWriter(tmp_path, max_glob_matches=0)
        with pytest.raises(CheckpointSizeError, match="glob matched"):
            tiny.list_glob("*.json")
        empty = FileCompositeCheckpointWriter(tmp_path / "none")
        assert empty.list_glob("*.json") == []

    async def test_row_reconciliation_adapter_branches(self) -> None:
        logger = NoOpLogger()
        metrics = MagicMock()

        class _Silver:
            async def read_silver(self, table: str, limit: int | None = None, columns=None):
                return [{"id": "1"}, {"id": "2"}] if table == "left" else [{"id": "1"}]

        adapter = StorageRowReconciliationAdapter(
            silver_reader=_Silver(),
            gold_reader=SimpleNamespace(),
            logger=logger,
            metrics=metrics,
        )
        config = RowReconciliationConfig(
            layer=RowReconciliationLayer.SILVER,
            left_table="left",
            right_table="right",
            left_columns=("id",),
            right_columns=("id",),
            left_primary_keys=("id",),
            max_rows=10,
        )
        result = await adapter.reconcile_rows(config)
        assert result.kept_rows == 1
        metrics.increment_counter.assert_called()

        class _Gold:
            def read_gold(self, table: str, **_kwargs: object):
                return [{"id": "x"}]

        gold_adapter = StorageRowReconciliationAdapter(
            silver_reader=SimpleNamespace(),
            gold_reader=_Gold(),
            logger=logger,
        )
        gold_config = RowReconciliationConfig(
            layer="gold",
            left_table="gleft",
            right_table="gright",
            left_columns=("id",),
            right_columns=("id",),
            left_primary_keys=("id",),
        )
        gold_result = await gold_adapter.reconcile_rows(gold_config)
        assert gold_result.input_left_rows == 1

        missing = StorageRowReconciliationAdapter(
            silver_reader=SimpleNamespace(),
            gold_reader=SimpleNamespace(),
            logger=logger,
        )
        with pytest.raises(Exception, match="does not expose"):
            await missing.reconcile_rows(config)
