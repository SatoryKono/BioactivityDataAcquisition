# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Split owner tests for silver/gold/runtime-profile metadata coordinator families."""

from __future__ import annotations

import pytest

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    CompositeOutputExt,
    GoldMetadata,
    SilverMetadata,
)
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput, SilverRef

pytestmark = pytest.mark.unit

from tests.unit.application.services.test_metadata_coordinator import *
from tests.unit.application.services.test_metadata_coordinator import _FIXED_TIME


class TestSilverMetadata:
    """Tests for Silver metadata creation."""

    def test_pipeline_metadata_carries_normalization_profile_identity(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            normalization_profile_ref="chembl.activity",
            normalization_profile_version="2.0.0",
            normalization_profile_hash="a" * 64,
        )
        metadata = MetadataCoordinator(context).create_silver_metadata(
            SilverMetadataInput(
                table_path="/data/silver/chembl/activity",
                records=[
                    {
                        "_run_id": str(context.run_id),
                        "_run_type": "incremental",
                        "_source_batch_id": str(
                            deterministic_uuid_from_callsite("replay-sensitive")
                        ),
                        "_ingestion_ts": _FIXED_TIME.isoformat(),
                        "chembl_id": "CHEMBL123",
                    }
                ],
                primary_keys=["chembl_id"],
                mode=SilverWriteMode.MERGE,
                dq_metrics=None,
                started_at=_FIXED_TIME,
                completed_at=_FIXED_TIME,
            )
        )

        assert metadata.pipeline.normalization_profile_ref == "chembl.activity"
        assert metadata.pipeline.normalization_profile_version == "2.0.0"
        assert metadata.pipeline.normalization_profile_hash == "a" * 64

    def test_create_silver_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Silver metadata."""
        records = [
            {
                "_run_id": str(coordinator.run_context.run_id),
                "_run_type": "incremental",
                "_source_batch_id": str(
                    deterministic_uuid_from_callsite("replay-sensitive")
                ),
                "_ingestion_ts": _FIXED_TIME.isoformat(),
                "chembl_id": "CHEMBL123",
            }
        ]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["chembl_id"],
            mode=SilverWriteMode.MERGE,
            version_after=5,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert isinstance(metadata, SilverMetadata)
        assert metadata.layer == Layer.SILVER
        assert metadata.version == "1.1"  # ADR-029 version bump

    def test_silver_with_empty_records_raises(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that empty records raises ValueError."""
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=[],
            primary_keys=["chembl_id"],
            mode=SilverWriteMode.MERGE,
        )

        with pytest.raises(ValueError, match="without records"):
            coordinator.create_silver_metadata(input_data)

    def test_silver_lineage_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Silver lineage metadata extracts batch IDs."""
        batch_id_1 = str(deterministic_uuid_from_callsite("replay-sensitive"))
        batch_id_2 = str(deterministic_uuid_from_callsite("replay-sensitive"))
        records = [
            {"_source_batch_id": batch_id_1, "id": 1},
            {"_source_batch_id": batch_id_2, "id": 2},
            {"_source_batch_id": batch_id_1, "id": 3},  # Duplicate batch_id
        ]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        # Should deduplicate batch IDs
        assert len(metadata.lineage.source_batch_ids) == 2
        assert batch_id_1 in metadata.lineage.source_batch_ids
        assert batch_id_2 in metadata.lineage.source_batch_ids

    def test_silver_delta_metrics(self, coordinator: MetadataCoordinator) -> None:
        """Test Silver Delta metrics."""
        records = [{"id": i} for i in range(10)]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
            version_after=10,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.delta.operation == "append"
        assert metadata.delta.primary_key == ["id"]
        assert metadata.delta.version_after == 10
        assert metadata.delta.rows_inserted == 10

    def test_silver_metadata_includes_rule_provenance(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Silver metadata should include DQ rule provenance when provided."""
        records = [{"id": 1}]
        provenance = [
            {
                "rule_id": "R_TRACE_01",
                "config_path": "configs/entities/chembl/activity.yaml",
                "layer": "gold",
                "field": "value",
                "severity": "error",
                "decision": "quarantine",
            }
        ]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            dq_rule_provenance=provenance,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.dq_summary.rule_provenance == provenance

    def test_silver_metadata_surfaces_composite_cv_trace_in_dq_summary(self) -> None:
        """Composite CV markers should become DQ summary counts and provenance."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="composite",
            entity="publication",
            contract_version="2.0.0",
        )
        coordinator = MetadataCoordinator(context)
        input_data = SilverMetadataInput(
            table_path="/data/silver/composite/publication",
            records=[
                {"id": 1, "_cv_warn": True},
                {"id": 2, "_cv_error": True, "_cv_quarantine": True},
            ],
            primary_keys=["id"],
            mode=SilverWriteMode.DELETE,
            dq_report_path="reports/dq/composite-publication.json",
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.dq_summary.warning_records == 1
        assert metadata.dq_summary.error_records == 1
        assert metadata.dq_summary.valid_records == 1
        assert metadata.dq_summary.validation_passed is False
        assert metadata.dq_summary.error_rate == pytest.approx(0.5)
        assert metadata.dq_summary.rule_provenance == [
            {
                "rule_id": "composite.cross_validation.warning",
                "contract_version": "2.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "warning",
                "decision": "warn",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication.json",
                "record_count": "1",
            },
            {
                "rule_id": "composite.cross_validation.quarantine",
                "contract_version": "2.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "error",
                "decision": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication.json",
                "record_count": "1",
            },
        ]

    def test_silver_mode_to_operation_mapping(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Silver write mode to Delta operation mapping."""
        records = [{"id": 1}]

        # Test MERGE mode
        input_merge = SilverMetadataInput(
            table_path="/data/silver/t",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        assert (
            coordinator.create_silver_metadata(input_merge).delta.operation == "merge"
        )

        # Test APPEND mode
        input_append = SilverMetadataInput(
            table_path="/data/silver/t",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )
        assert (
            coordinator.create_silver_metadata(input_append).delta.operation == "append"
        )

        # Test DELETE mode (maps to overwrite)
        input_delete = SilverMetadataInput(
            table_path="/data/silver/t",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.DELETE,
        )
        assert (
            coordinator.create_silver_metadata(input_delete).delta.operation
            == "overwrite"
        )


class TestGoldMetadata:
    """Tests for Gold metadata creation."""

    def test_create_gold_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Gold metadata."""
        records = [{"compound_id": "CMP123", "activity_value": 5.5}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert isinstance(metadata, GoldMetadata)
        assert metadata.layer == Layer.GOLD
        assert metadata.version == "1.1"  # ADR-029 version bump

    def test_gold_with_empty_records_raises(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that empty records raises ValueError."""
        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=[],
            mode=GoldWriteMode.OVERWRITE,
        )

        with pytest.raises(ValueError, match="without records"):
            coordinator.create_gold_metadata(input_data)

    def test_gold_scd2_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Gold SCD2 metadata creation."""
        records = [{"compound_id": "CMP123", "value": 1.0}]
        scd_config = {
            "valid_from_col": "effective_from",
            "valid_to_col": "effective_to",
            "current_flag_col": "is_active",
        }

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.SCD2,
            scd_config=scd_config,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.scd is not None
        assert metadata.scd.enabled is True
        assert metadata.scd.effective_date_column == "effective_from"
        assert metadata.scd.end_date_column == "effective_to"
        assert metadata.scd.current_flag_column == "is_active"

    def test_gold_without_scd2_has_no_scd_metadata(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold without SCD2 mode has no SCD metadata."""
        records = [{"id": 1}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.APPEND,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.scd is None

    def test_gold_output_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Gold output metadata."""
        records = [{"id": i} for i in range(25)]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.output.record_count == 25

    def test_gold_composite_output_extension(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test composite records are mapped to CompositeOutputExt metadata."""
        records = [
            {
                "id": 1,
                "_source_providers": "['seed', 'openalex']",
                "_enrichment_status": "{'openalex': 'ok'}",
            }
        ]

        input_data = GoldMetadataInput(
            table_path="/data/gold/composite/publication",
            table_name="composite.publication",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            composite_run_id="comp-run-123",
            lineage_created_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            schema_validation_enabled=True,
            schema_validation_strict=True,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.output.composite_run_id == "comp-run-123"
        assert isinstance(metadata.output_ext, CompositeOutputExt)
        assert metadata.output_ext.composite_run_id == "comp-run-123"
        assert metadata.output_ext.source_providers == ["seed", "openalex"]
        assert metadata.output_ext.enrichment_status == {"openalex": "ok"}
        assert metadata.output_ext.schema_validation.enabled is True
        assert metadata.output_ext.schema_validation.strict is True
        assert metadata.output_ext.schema_validation.status == "passed"

    def test_gold_lineage_with_silver_refs(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage metadata with Silver source references (REQ-LINEAGE-002)."""
        records = [{"compound_id": "CMP123", "activity_value": 5.5}]
        silver_refs = [
            SilverRef(
                table_name="chembl.activity",
                table_path="/data/silver/chembl/activity",
                delta_version=42,
            )
        ]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=silver_refs,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.source_tables == {"chembl.activity": 42}

    def test_gold_lineage_without_silver_refs(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage metadata is empty when no Silver refs provided (backward compat)."""
        records = [{"id": 1}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=None,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.source_tables == {}

    def test_gold_lineage_with_multiple_silver_sources(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage with multiple Silver table sources."""
        records = [{"compound_id": "CMP123", "target_id": "TGT456", "activity": 1.0}]
        silver_refs = [
            SilverRef(
                table_name="chembl.compound",
                table_path="/data/silver/chembl/compound",
                delta_version=10,
            ),
            SilverRef(
                table_name="chembl.target",
                table_path="/data/silver/chembl/target",
                delta_version=20,
            ),
            SilverRef(
                table_name="chembl.activity",
                table_path="/data/silver/chembl/activity",
                delta_version=30,
            ),
        ]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/compound_activity",
            table_name="chembl.compound_activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=silver_refs,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.source_tables == {
            "chembl.compound": 10,
            "chembl.target": 20,
            "chembl.activity": 30,
        }


class TestTransformVersionTracking:
    """Tests for transform version and steps tracking in metadata."""

    def test_silver_lineage_includes_transform_version_from_input(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Silver lineage includes transform_version from SilverMetadataInput."""
        records = [{"id": 1}]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            transform_version="1.0.0",
            transform_steps=("normalize_values", "add_metadata"),
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.lineage.transform_version == "1.0.0"
        assert metadata.lineage.transform_steps == ["normalize_values", "add_metadata"]

    def test_gold_lineage_includes_transform_version_from_input(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage includes transform_version from GoldMetadataInput."""
        records = [{"id": 1}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            transform_version="2.1.0",
            transform_steps=("flatten_json", "validate_schema"),
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.transform_version == "2.1.0"
        assert metadata.lineage.transform_steps == ["flatten_json", "validate_schema"]

    def test_silver_uses_run_context_transform_when_input_none(self) -> None:
        """Test Silver falls back to RunContext transform info when input is None."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="3.0.0",
            transform_steps=("step1", "step2", "step3"),
        )
        coord = MetadataCoordinator(context)

        records = [{"id": 1}]
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            # transform_version and transform_steps are None
        )

        metadata = coord.create_silver_metadata(input_data)

        # Should fall back to RunContext values
        assert metadata.lineage.transform_version == "3.0.0"
        assert metadata.lineage.transform_steps == ["step1", "step2", "step3"]

    def test_gold_uses_run_context_transform_when_input_none(self) -> None:
        """Test Gold falls back to RunContext transform info when input is None."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="4.0.0",
            transform_steps=("transform_step_a", "transform_step_b"),
        )
        coord = MetadataCoordinator(context)

        records = [{"id": 1}]
        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            # transform_version and transform_steps are None
        )

        metadata = coord.create_gold_metadata(input_data)

        # Should fall back to RunContext values
        assert metadata.lineage.transform_version == "4.0.0"
        assert metadata.lineage.transform_steps == [
            "transform_step_a",
            "transform_step_b",
        ]

    def test_run_context_with_transform_info(self) -> None:
        """Test RunContext can be created with transform version and steps."""
        run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
        started_at = _FIXED_TIME

        context = RunContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            started_at=started_at,
            provider="chembl",
            entity="activity",
            transform_version="1.2.3",
            transform_steps=("step1", "step2"),
        )

        assert context.transform_version == "1.2.3"
        assert context.transform_steps == ("step1", "step2")

    def test_run_context_defaults_empty_transform(self) -> None:
        """Test RunContext defaults to None/empty for transform fields."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
        )

        assert context.transform_version is None
        assert context.transform_steps == ()

    def test_silver_input_takes_precedence_over_run_context(self) -> None:
        """Test that SilverMetadataInput values take precedence over RunContext."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="1.0.0",
            transform_steps=("context_step",),
        )
        coord = MetadataCoordinator(context)

        records = [{"id": 1}]
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            transform_version="2.0.0",  # Different from context
            transform_steps=("input_step1", "input_step2"),  # Different from context
        )

        metadata = coord.create_silver_metadata(input_data)

        # Input values should take precedence
        assert metadata.lineage.transform_version == "2.0.0"
        assert metadata.lineage.transform_steps == ["input_step1", "input_step2"]


class TestRunTypeMappings:
    """Tests for RunType to RunTypeEnum mapping."""

    @pytest.mark.parametrize(
        "run_type,expected_enum",
        [
            (RunType.INCREMENTAL, RunTypeEnum.INCREMENTAL),
            (RunType.BACKFILL, RunTypeEnum.BACKFILL),
            (RunType.REBUILD, RunTypeEnum.REBUILD),
        ],
    )
    def test_run_type_mapping(
        self, run_type: RunType, expected_enum: RunTypeEnum
    ) -> None:
        """Test RunType to RunTypeEnum mapping."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=run_type,
            started_at=_FIXED_TIME,
            provider="test",
            entity="entity",
        )
        coordinator = MetadataCoordinator(context)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=1,
            compressed_size=100,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        metadata = coordinator.create_bronze_metadata(input_data)
        assert metadata.runtime.run_type == expected_enum


class TestConsistencyAcrossLayers:
    """Tests for metadata consistency across layers."""

    def test_run_id_consistent_across_layers(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that run_id is consistent across Bronze, Silver, Gold."""
        run_id_str = str(coordinator.run_context.run_id)

        # Bronze
        bronze_input = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )
        bronze = coordinator.create_bronze_metadata(bronze_input)

        # Silver
        silver_input = SilverMetadataInput(
            table_path="/silver/t",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        silver = coordinator.create_silver_metadata(silver_input)

        # Gold
        gold_input = GoldMetadataInput(
            table_path="/gold/t",
            table_name="t",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
        )
        gold = coordinator.create_gold_metadata(gold_input)

        # All should have the same run_id
        assert bronze.runtime.run_id == run_id_str
        assert silver.runtime.run_id == run_id_str
        assert gold.runtime.run_id == run_id_str

    def test_pipeline_metadata_consistent_across_layers(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that pipeline metadata is consistent across layers."""
        bronze_input = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )
        bronze = coordinator.create_bronze_metadata(bronze_input)

        silver_input = SilverMetadataInput(
            table_path="/silver/t",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        silver = coordinator.create_silver_metadata(silver_input)

        gold_input = GoldMetadataInput(
            table_path="/gold/t",
            table_name="t",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
        )
        gold = coordinator.create_gold_metadata(gold_input)

        # All should have consistent pipeline metadata
        assert (
            bronze.pipeline.provider
            == silver.pipeline.provider
            == gold.pipeline.provider
        )
        assert bronze.pipeline.entity == silver.pipeline.entity == gold.pipeline.entity
        assert bronze.pipeline.name == silver.pipeline.name == gold.pipeline.name

    def test_environment_metadata_consistent_across_layers(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that environment metadata is consistent (same object)."""
        bronze_input = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )
        bronze = coordinator.create_bronze_metadata(bronze_input)

        silver_input = SilverMetadataInput(
            table_path="/silver/t",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        silver = coordinator.create_silver_metadata(silver_input)

        gold_input = GoldMetadataInput(
            table_path="/gold/t",
            table_name="t",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
        )
        gold = coordinator.create_gold_metadata(gold_input)

        # Environment should be the same cached object
        assert bronze.environment is silver.environment is gold.environment
