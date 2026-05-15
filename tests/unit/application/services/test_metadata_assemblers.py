"""Direct unit tests for metadata assembly services."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from bioetl.application.services.lineage.metadata_assemblers import (
    GoldMetadataService,
    PipelineMetadataBuilderProtocol,
    RuntimeMetadataBuilderProtocol,
    SilverMetadataService,
)
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    CompositeOutputExt,
    EnvironmentMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
)
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput, SilverRef
from bioetl.domain.types import BatchID, RunID, RunType, ScdConfig
from bioetl.domain.types.dq_contracts import DQRuleProvenance
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.run_context import RunContext
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.helpers.synthetic_paths import synthetic_test_root

TEST_ROOT = synthetic_test_root("metadata-assemblers")
SILVER_TABLE_PATH = str(TEST_ROOT / "silver" / "activity")
GOLD_TABLE_PATH = str(TEST_ROOT / "gold" / "activity")
SILVER_DQ_REPORT_PATH = str(TEST_ROOT / "reports" / "silver_dq.json")
GOLD_DQ_REPORT_PATH = str(TEST_ROOT / "reports" / "gold_dq.json")


def _make_run_context() -> RunContext:
    return RunContext(
        run_id=RunID(deterministic_uuid("metadata-assemblers:run-context")),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 3, 19, 10, 0, tzinfo=UTC),
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        transform_version="ctx-1.0.0",
        transform_steps=("normalize", "dedup"),
        pipeline_version="2.0.0",
        git_commit="abc1234",
        config_hash="cfg-001",
    )


def _make_environment() -> EnvironmentMetadata:
    return EnvironmentMetadata(
        hostname="test-host",
        python_version="3.13.7",
        bioetl_version="5.24.0",
    )


def _make_runtime_builder(
    run_context: RunContext,
) -> tuple[RuntimeMetadataBuilderProtocol, list[dict[str, object | None]]]:
    calls: list[dict[str, object | None]] = []

    def _builder(
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> RuntimeMetadata:
        calls.append(
            {
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_seconds": duration_seconds,
            }
        )
        return RuntimeMetadata(
            run_id=str(run_context.run_id),
            run_type=RunTypeEnum(run_context.run_type.value),
            started_at_utc=started_at or run_context.started_at,
            completed_at_utc=completed_at,
            duration_seconds=duration_seconds,
        )

    return _builder, calls


def _make_pipeline_builder(run_context: RunContext) -> PipelineMetadataBuilderProtocol:
    def _builder() -> PipelineMetadata:
        return PipelineMetadata(
            name=run_context.pipeline_name,
            provider=run_context.provider,
            entity=run_context.entity,
            version=run_context.pipeline_version or "1.0.0",
            git_commit=run_context.git_commit,
            config_hash=run_context.config_hash,
        )

    return _builder


def _make_bronze_ref(relative_path: str) -> BronzeWriteResult:
    return BronzeWriteResult(
        batch_id=BatchID(deterministic_uuid(f"metadata-assemblers:{relative_path}")),
        relative_path=relative_path,
        absolute_path=str(TEST_ROOT / relative_path),
        record_count=3,
        compressed_size=12,
        uncompressed_size=24,
        checksum_blake2="deadbeef",
    )


@pytest.mark.unit
class TestSilverMetadataService:
    def test_constructor_dependencies_use_builder_field_names(self) -> None:
        field_names = {field.name for field in fields(SilverMetadataService)}

        assert "runtime_metadata_builder" in field_names
        assert "pipeline_metadata_builder" in field_names
        assert all(not field_name.endswith("_factory") for field_name in field_names)

    def test_assemble_rejects_empty_payload_without_total_records(self) -> None:
        run_context = _make_run_context()
        runtime_builder, _calls = _make_runtime_builder(run_context)
        service = SilverMetadataService(
            run_context=run_context,
            runtime_metadata_builder=runtime_builder,
            pipeline_metadata_builder=_make_pipeline_builder(run_context),
            environment_metadata=_make_environment(),
        )
        input_data = SilverMetadataInput(
            table_path=SILVER_TABLE_PATH,
            primary_keys=["activity_id"],
            mode=SilverWriteMode.MERGE,
            records=[],
            total_records=None,
        )

        with pytest.raises(ValueError, match="Cannot create Silver metadata"):
            service.assemble(input_data)

    def test_assemble_builds_complete_metadata(self) -> None:
        run_context = _make_run_context()
        runtime_builder, calls = _make_runtime_builder(run_context)
        service = SilverMetadataService(
            run_context=run_context,
            runtime_metadata_builder=runtime_builder,
            pipeline_metadata_builder=_make_pipeline_builder(run_context),
            environment_metadata=_make_environment(),
        )
        started_at = datetime(2026, 3, 19, 10, 5, tzinfo=UTC)
        completed_at = started_at + timedelta(seconds=15)
        input_data = SilverMetadataInput(
            table_path=SILVER_TABLE_PATH,
            primary_keys=["activity_id"],
            mode=SilverWriteMode.MERGE,
            records=[
                {"activity_id": 1, "_source_batch_id": "batch-a"},
                {"activity_id": 2, "_source_batch_id": "batch-b"},
            ],
            bronze_refs=[
                _make_bronze_ref("chembl/activity/2026-03-19/batch_1.jsonl.zst")
            ],
            version_before=3,
            version_after=4,
            dq_report_path=SILVER_DQ_REPORT_PATH,
            dq_rule_provenance=cast(
                "list[DQRuleProvenance]",
                [{"rule_id": "DQ-1", "config_path": "configs/x.yaml"}],
            ),
            governance=None,
            partition_by=["activity_id"],
            started_at=started_at,
            completed_at=completed_at,
            total_bytes=256,
        )

        result = service.assemble(input_data)

        assert result.runtime.duration_seconds == pytest.approx(15.0)
        assert calls[0]["started_at"] == started_at
        assert result.pipeline.name == "chembl_activity"
        assert set(result.lineage.source_batch_ids) == {"batch-a", "batch-b"}
        assert result.lineage.bronze_paths == [
            "chembl/activity/2026-03-19/batch_1.jsonl.zst"
        ]
        assert result.lineage.transform_version == "ctx-1.0.0"
        assert result.delta.operation == "merge"
        assert result.delta.rows_inserted == 2
        assert result.output.artifact_id == "silver:chembl.activity@4"
        assert isinstance(result.output.content_hash, str)
        assert result.output.record_count == 2
        assert result.output.total_bytes == 256
        assert result.output_ext.delta_version_before == 3
        assert result.output_ext.delta_version_after == 4
        assert result.dq_summary.rule_provenance == [
            {"rule_id": "DQ-1", "config_path": "configs/x.yaml"}
        ]
        assert result.dq_report_path == SILVER_DQ_REPORT_PATH


@pytest.mark.unit
class TestGoldMetadataService:
    def test_constructor_dependencies_use_builder_field_names(self) -> None:
        field_names = {field.name for field in fields(GoldMetadataService)}

        assert "runtime_metadata_builder" in field_names
        assert "pipeline_metadata_builder" in field_names
        assert all(not field_name.endswith("_factory") for field_name in field_names)

    def test_assemble_rejects_empty_payload_without_total_records(self) -> None:
        run_context = _make_run_context()
        runtime_builder, _calls = _make_runtime_builder(run_context)
        service = GoldMetadataService(
            run_context=run_context,
            runtime_metadata_builder=runtime_builder,
            pipeline_metadata_builder=_make_pipeline_builder(run_context),
            environment_metadata=_make_environment(),
        )
        input_data = GoldMetadataInput(
            table_path=GOLD_TABLE_PATH,
            table_name="gold.activity",
            mode=GoldWriteMode.APPEND,
            records=[],
            total_records=None,
        )

        with pytest.raises(ValueError, match="Cannot create Gold metadata"):
            service.assemble(input_data)

    def test_assemble_builds_composite_output_and_scd_metadata(self) -> None:
        run_context = _make_run_context()
        runtime_builder, calls = _make_runtime_builder(run_context)
        service = GoldMetadataService(
            run_context=run_context,
            runtime_metadata_builder=runtime_builder,
            pipeline_metadata_builder=_make_pipeline_builder(run_context),
            environment_metadata=_make_environment(),
        )
        completed_at = datetime(2026, 3, 19, 11, 0, tzinfo=UTC)
        input_data = GoldMetadataInput(
            table_path=GOLD_TABLE_PATH,
            table_name="gold.activity",
            mode=GoldWriteMode.SCD2,
            records=[
                {
                    "activity_id": 1,
                    "_source_providers": "['chembl', 'pubchem']",
                    "_enrichment_status": "{'chembl': 'ok'}",
                }
            ],
            silver_refs=[SilverRef("silver.activity", SILVER_TABLE_PATH, 9)],
            scd_config=ScdConfig(
                business_key="activity_id",
                valid_from_col="_valid_from",
                valid_to_col="_valid_to",
                current_flag_col="_is_current",
            ),
            completed_at=completed_at,
            partition_count=2,
            composite_run_id="cmp-001",
            lineage_created_at=datetime(2026, 3, 19, 10, 30, tzinfo=UTC),
            schema_validation_enabled=True,
            schema_validation_strict=False,
            dq_report_path=GOLD_DQ_REPORT_PATH,
            total_bytes=512,
        )

        result = service.assemble(input_data)

        assert calls[0]["started_at"] is None
        assert calls[0]["completed_at"] == completed_at
        assert calls[0]["duration_seconds"] == pytest.approx(0.0)
        assert result.lineage.source_tables == {"silver.activity": 9}
        assert result.dq_summary.total_records == 1
        assert result.output.artifact_id == "gold:gold.activity"
        assert isinstance(result.output.content_hash, str)
        assert result.output.record_count == 1
        assert result.output.total_bytes == 512
        assert result.output_ext.partition_count == 2
        assert isinstance(result.output_ext, CompositeOutputExt)
        assert result.output_ext.composite_run_id == "cmp-001"
        assert result.output_ext.source_providers == ["chembl", "pubchem"]
        assert result.output_ext.schema_validation.status == "passed"
        assert result.scd is not None
        assert result.scd.enabled is True
        assert result.scd.effective_date_column == "_valid_from"
        assert result.dq_report_path == GOLD_DQ_REPORT_PATH
