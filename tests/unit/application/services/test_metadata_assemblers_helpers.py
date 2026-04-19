"""Dedicated unit tests for metadata assembler helper functions."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.application.services.lineage.metadata_assemblers_helpers import (
    _build_dataset_content_hash,
    _build_gold_lineage,
    _build_gold_output,
    _build_gold_scd,
    _build_runtime_duration,
    _build_silver_delta,
    _build_silver_dq_summary,
    _build_silver_lineage,
    _extract_composite_output_ext,
    _parse_composite_list,
    _parse_composite_status,
    _parse_lineage_created_at,
    _resolve_bronze_paths,
    _resolve_gold_source_tables,
    _resolve_record_count,
    _resolve_source_batch_ids,
    _resolve_transform_metadata,
)
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import CompositeOutputExt, DQSummary
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput, SilverRef
from bioetl.domain.types import BatchID, RunID, RunType, ScdConfig
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.run_context import RunContext

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-metadata-assemblers-helpers-"))
SILVER_TABLE_PATH = str(TEST_ROOT / "silver" / "table")
GOLD_TABLE_PATH = str(TEST_ROOT / "gold" / "table")
SILVER_REF_A_PATH = str(TEST_ROOT / "silver" / "a")
SILVER_REF_B_PATH = str(TEST_ROOT / "silver" / "b")


def _make_silver_input(**overrides: object) -> SilverMetadataInput:
    payload: dict[str, object] = {
        "table_path": SILVER_TABLE_PATH,
        "primary_keys": ["id"],
        "mode": SilverWriteMode.MERGE,
        "records": [{"id": 1}],
        "version_after": 11,
    }
    payload.update(overrides)
    return SilverMetadataInput(**payload)


def _make_bronze_ref(relative_path: str) -> BronzeWriteResult:
    return BronzeWriteResult(
        batch_id=BatchID(uuid4()),
        relative_path=relative_path,
        absolute_path=str(TEST_ROOT / relative_path),
        record_count=1,
        compressed_size=10,
        uncompressed_size=20,
        checksum_blake2="deadbeef",
    )


def _make_gold_input(**overrides: object) -> GoldMetadataInput:
    payload: dict[str, object] = {
        "table_path": GOLD_TABLE_PATH,
        "table_name": "gold.test",
        "mode": GoldWriteMode.APPEND,
        "records": [{"id": 1}],
        "total_bytes": 128,
        "started_at": datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
        "completed_at": datetime(2026, 3, 17, 10, 0, 5, tzinfo=UTC),
    }
    payload.update(overrides)
    return GoldMetadataInput(**payload)


@pytest.mark.unit
def test_parse_composite_list_from_list_and_stringified_list() -> None:
    assert _parse_composite_list(["a", 1, None]) == ["a", "1", "None"]
    assert _parse_composite_list("['chembl', 'pubchem']") == ["chembl", "pubchem"]
    assert _parse_composite_list("{'not': 'list'}") == []
    assert _parse_composite_list(123) == []


@pytest.mark.unit
def test_parse_composite_status_from_dict_and_stringified_dict() -> None:
    assert _parse_composite_status({"a": "ok", "b": 2}) == {"a": "ok", "b": "2"}
    assert _parse_composite_status("{'x': 'done', 'y': 'warn'}") == {
        "x": "done",
        "y": "warn",
    }
    assert _parse_composite_status("[1,2,3]") == {}
    assert _parse_composite_status(None) == {}


@pytest.mark.unit
def test_parse_lineage_created_at_handles_valid_invalid_and_non_string() -> None:
    parsed = _parse_lineage_created_at("2026-03-17T10:10:10+00:00")
    assert parsed is not None and parsed.year == 2026
    assert _parse_lineage_created_at("not-a-date") is None
    assert _parse_lineage_created_at(123) is None


@pytest.mark.unit
def test_extract_composite_output_ext_returns_none_for_empty_or_plain_records() -> None:
    assert _extract_composite_output_ext([], partition_count=1) is None
    assert (
        _extract_composite_output_ext([{"id": 1, "name": "plain"}], partition_count=1)
        is None
    )


@pytest.mark.unit
def test_extract_composite_output_ext_parses_composite_and_lineage_fields() -> None:
    records = [
        {
            "_source_providers": "['chembl', 'uniprot']",
            "_enrichment_status": "{'chembl':'ok','uniprot':'ok'}",
        }
    ]
    ext = _extract_composite_output_ext(
        records,
        partition_count=3,
        schema_validation_enabled=True,
        schema_validation_strict=False,
        composite_run_id="cmp-001",
        lineage_created_at=datetime(2026, 3, 17, 11, 0, tzinfo=UTC),
    )

    assert ext is not None
    assert ext.partition_count == 3
    assert ext.composite_run_id == "cmp-001"
    assert ext.source_providers == ["chembl", "uniprot"]
    assert ext.enrichment_status == {"chembl": "ok", "uniprot": "ok"}
    assert ext.lineage_created_at is not None
    assert ext.schema_validation.enabled is True
    assert ext.schema_validation.strict is False
    assert ext.schema_validation.status == "passed"


@pytest.mark.unit
def test_extract_composite_output_ext_defaults_schema_status_when_not_enabled() -> None:
    ext = _extract_composite_output_ext(
        [{"_source_providers": ["chembl"]}],
        partition_count=1,
        schema_validation_enabled=False,
        composite_run_id="cmp-002",
    )
    assert ext is not None
    assert ext.composite_run_id == "cmp-002"
    assert ext.schema_validation.status == "not_run"


@pytest.mark.unit
def test_resolve_source_batch_ids_prefers_explicit_ids() -> None:
    input_data = _make_silver_input(
        source_batch_ids=["batch-explicit"],
        records=[{"_source_batch_id": "batch-record"}],
    )
    assert _resolve_source_batch_ids(input_data) == ["batch-explicit"]


@pytest.mark.unit
def test_resolve_source_batch_ids_from_records_deduplicates_missing_values() -> None:
    input_data = _make_silver_input(
        source_batch_ids=None,
        records=[
            {"_source_batch_id": "a"},
            {"_source_batch_id": "b"},
            {"_source_batch_id": "a"},
            {},
        ],
    )
    assert set(_resolve_source_batch_ids(input_data)) == {"a", "b"}


@pytest.mark.unit
def test_resolve_bronze_paths_handles_none_and_extracts_relative_paths() -> None:
    empty_input = _make_silver_input(bronze_refs=None)
    assert _resolve_bronze_paths(empty_input) == []

    refs_input = _make_silver_input(
        bronze_refs=[
            _make_bronze_ref("chembl/activity/2026-03-17/batch_1.jsonl.zst"),
            _make_bronze_ref("chembl/assay/2026-03-17/batch_2.jsonl.zst"),
        ]
    )
    assert _resolve_bronze_paths(refs_input) == [
        "chembl/activity/2026-03-17/batch_1.jsonl.zst",
        "chembl/assay/2026-03-17/batch_2.jsonl.zst",
    ]


@pytest.mark.unit
def test_resolve_transform_metadata_uses_override_then_context_defaults() -> None:
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        transform_version="ctx-1.0.0",
        transform_steps=("normalize", "dedup"),
    )

    override_version, override_steps = _resolve_transform_metadata(
        run_context=run_context,
        transform_version="override-2.0.0",
        transform_steps=("trim",),
    )
    assert override_version == "override-2.0.0"
    assert override_steps == ["trim"]

    fallback_version, fallback_steps = _resolve_transform_metadata(
        run_context=run_context,
        transform_version=None,
        transform_steps=None,
    )
    assert fallback_version == "ctx-1.0.0"
    assert fallback_steps == ["normalize", "dedup"]


@pytest.mark.unit
def test_resolve_transform_metadata_returns_empty_version_when_absent() -> None:
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        transform_version=None,
        transform_steps=(),
    )
    resolved_version, resolved_steps = _resolve_transform_metadata(
        run_context=run_context,
        transform_version=None,
        transform_steps=None,
    )
    assert resolved_version == ""
    assert resolved_steps == []


@pytest.mark.unit
def test_resolve_record_count_prefers_total_records() -> None:
    assert _resolve_record_count(records=[{"id": 1}], total_records=10) == 10
    assert (
        _resolve_record_count(records=[{"id": 1}, {"id": 2}], total_records=None) == 2
    )
    assert _resolve_record_count(records=None, total_records=None) == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "operation"),
    [
        (SilverWriteMode.MERGE, "merge"),
        (SilverWriteMode.APPEND, "append"),
        (SilverWriteMode.DELETE, "overwrite"),
    ],
)
def test_build_silver_delta_maps_modes(mode: SilverWriteMode, operation: str) -> None:
    input_data = _make_silver_input(mode=mode, partition_by=None, version_after=42)

    delta = _build_silver_delta(input_data, rows_inserted=7)

    assert delta.operation == operation
    assert delta.table_path == SILVER_TABLE_PATH
    assert delta.primary_key == ["id"]
    assert delta.partition_by == []
    assert delta.version_after == 42
    assert delta.rows_inserted == 7


@pytest.mark.unit
def test_build_silver_dq_summary_defaults_to_record_count() -> None:
    summary = _build_silver_dq_summary(_make_silver_input(), record_count=8)

    assert summary.total_records == 8
    assert summary.valid_records == 8
    assert summary.rule_provenance == []


@pytest.mark.unit
def test_build_silver_dq_summary_uses_metrics_and_rule_provenance() -> None:
    class _MetricsStub:
        def to_dq_summary(self) -> DQSummary:
            return DQSummary(total_records=9, valid_records=7, error_records=2)

    provenance = [
        {
            "rule_id": "gold.not_null.id",
            "config_path": "configs/dq/gold.yaml",
            "layer": "gold",
            "field": "id",
            "severity": "error",
            "decision": "fail",
        }
    ]
    input_data = _make_silver_input(
        dq_metrics=_MetricsStub(),
        dq_rule_provenance=provenance,
    )

    summary = _build_silver_dq_summary(input_data, record_count=100)

    assert summary.total_records == 9
    assert summary.valid_records == 7
    assert summary.error_records == 2
    assert summary.rule_provenance == provenance


@pytest.mark.unit
def test_build_runtime_duration_computes_seconds_or_zero() -> None:
    started = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)
    completed = datetime(2026, 3, 17, 12, 0, 2, 500000, tzinfo=UTC)

    assert _build_runtime_duration(started, completed) == pytest.approx(2.5)
    assert _build_runtime_duration(None, completed) == pytest.approx(0.0)
    assert _build_runtime_duration(started, None) == pytest.approx(0.0)


@pytest.mark.unit
def test_build_dataset_content_hash_is_order_insensitive_and_excludes_row_hash() -> (
    None
):
    records_a = [
        {"id": 1, "value": "A", "content_hash": "row-hash-a"},
        {"id": 2, "value": "B", "content_hash": "row-hash-b"},
    ]
    records_b = [
        {"id": 2, "value": "B", "content_hash": "changed-row-hash-b"},
        {"id": 1, "value": "A", "content_hash": "changed-row-hash-a"},
    ]

    hash_a = _build_dataset_content_hash(provider="chembl", records=records_a)
    hash_b = _build_dataset_content_hash(provider="chembl", records=records_b)

    assert isinstance(hash_a, str)
    assert hash_a == hash_b


@pytest.mark.unit
def test_build_dataset_content_hash_returns_none_without_records() -> None:
    assert _build_dataset_content_hash(provider="chembl", records=None) is None
    assert _build_dataset_content_hash(provider="chembl", records=[]) is None


@pytest.mark.unit
def test_build_dataset_content_hash_ignores_occurrence_only_runtime_fields() -> None:
    records_a = [
        {
            "id": 1,
            "value": "A",
            "run_id": "run-a",
            "manifest_id": "manifest-a",
            "composite_run_id": "composite-a",
            "lineage_created_at": "2026-04-13T12:00:00+00:00",
            "write_started_at": "2026-04-13T12:00:01+00:00",
            "_lineage_created_at": "2026-04-13T12:00:00+00:00",
            "_composite_run_id": "composite-a",
        }
    ]
    records_b = [
        {
            "id": 1,
            "value": "A",
            "run_id": "run-b",
            "manifest_id": "manifest-b",
            "composite_run_id": "composite-b",
            "lineage_created_at": "2026-04-13T13:00:00+00:00",
            "write_started_at": "2026-04-13T13:00:01+00:00",
            "_lineage_created_at": "2026-04-13T13:00:00+00:00",
            "_composite_run_id": "composite-b",
        }
    ]

    assert _build_dataset_content_hash(provider="chembl", records=records_a) == (
        _build_dataset_content_hash(provider="chembl", records=records_b)
    )


@pytest.mark.unit
def test_build_lineage_helpers_populate_expected_fields() -> None:
    silver_lineage = _build_silver_lineage(
        source_batch_ids=["batch-1"],
        bronze_paths=["chembl/activity/file1"],
        transform_version="2.1.0",
        transform_steps=["normalize", "dedup"],
    )
    assert silver_lineage.source_batch_ids == ["batch-1"]
    assert silver_lineage.bronze_paths == ["chembl/activity/file1"]
    assert silver_lineage.transform_version == "2.1.0"
    assert silver_lineage.transform_steps == ["normalize", "dedup"]

    gold_lineage = _build_gold_lineage(
        source_tables={"chembl.activity": 3},
        transform_version="3.0.0",
        transform_steps=["merge", "rank"],
    )
    assert gold_lineage.source_tables == {"chembl.activity": 3}
    assert gold_lineage.transform_version == "3.0.0"
    assert gold_lineage.transform_steps == ["merge", "rank"]


@pytest.mark.unit
def test_resolve_gold_source_tables_handles_empty_and_populates_refs() -> None:
    assert _resolve_gold_source_tables(_make_gold_input(silver_refs=None)) == {}

    refs = [
        SilverRef(
            table_name="chembl.activity",
            table_path=SILVER_REF_A_PATH,
            delta_version=10,
        ),
        SilverRef(
            table_name="chembl.assay",
            table_path=SILVER_REF_B_PATH,
            delta_version=11,
        ),
    ]
    assert _resolve_gold_source_tables(_make_gold_input(silver_refs=refs)) == {
        "chembl.activity": 10,
        "chembl.assay": 11,
    }


@pytest.mark.unit
def test_build_gold_scd_returns_none_unless_scd2_with_config() -> None:
    assert _build_gold_scd(_make_gold_input(mode=GoldWriteMode.APPEND)) is None
    assert (
        _build_gold_scd(_make_gold_input(mode=GoldWriteMode.SCD2, scd_config=None))
        is None
    )

    scd_config = ScdConfig(
        valid_from_col="valid_from",
        valid_to_col="valid_to",
        current_flag_col="is_current",
    )
    scd = _build_gold_scd(
        _make_gold_input(mode=GoldWriteMode.SCD2, scd_config=scd_config)
    )

    assert scd is not None
    assert scd.enabled is True
    assert scd.effective_date_column == "valid_from"
    assert scd.end_date_column == "valid_to"
    assert scd.current_flag_column == "is_current"


@pytest.mark.unit
def test_build_gold_output_uses_composite_run_id_when_present() -> None:
    input_data = _make_gold_input(total_bytes=999)
    composite_ext = CompositeOutputExt(partition_count=2, composite_run_id="cmp-123")

    output = _build_gold_output(
        input_data=input_data,
        record_count=12,
        composite_ext=composite_ext,
    )

    assert output.record_count == 12
    assert output.total_bytes == 999
    assert output.content_hash is None
    assert output.composite_run_id == "cmp-123"
    assert output.write_started_at == input_data.started_at
    assert output.write_completed_at == input_data.completed_at


@pytest.mark.unit
def test_build_gold_output_sets_dataset_content_hash_with_run_context() -> None:
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
    )
    output = _build_gold_output(
        run_context=run_context,
        input_data=_make_gold_input(records=[{"id": 1, "value": "A"}]),
        record_count=1,
        composite_ext=None,
    )

    assert isinstance(output.content_hash, str)


@pytest.mark.unit
def test_build_gold_output_sets_composite_run_id_none_when_no_composite_ext() -> None:
    output = _build_gold_output(
        input_data=_make_gold_input(),
        record_count=4,
        composite_ext=None,
    )
    assert output.record_count == 4
    assert output.composite_run_id is None
