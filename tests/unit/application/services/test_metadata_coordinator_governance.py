"""Governance-focused unit tests for MetadataCoordinator."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    GovernanceLineageConfig,
    GovernanceMetadata,
    QualityExpectations,
)
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext


pytestmark = pytest.mark.unit


@pytest.fixture
def run_context() -> RunContext:
    return RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
    )


@pytest.fixture
def coordinator(run_context: RunContext) -> MetadataCoordinator:
    MetadataCoordinator.reset_environment_cache()
    return MetadataCoordinator(run_context)


class TestGovernanceMetadata:
    """Tests for governance metadata in sidecar files."""

    def test_bronze_metadata_with_governance(
        self, coordinator: MetadataCoordinator
    ) -> None:
        governance = GovernanceMetadata(
            owner="data-team",
            steward="chembl-owner",
            description="Raw ChEMBL activity data",
            tags=["chembl", "activity", "raw"],
            retention_days=90,
            sla_freshness_hours=24,
            lineage=GovernanceLineageConfig(
                source_system="chembl",
                source_version="v33",
                extraction_method="api",
            ),
        )
        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            governance=governance,
        )
        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.governance is not None
        assert metadata.governance.owner == "data-team"
        assert metadata.governance.steward == "chembl-owner"
        assert metadata.governance.description == "Raw ChEMBL activity data"
        assert metadata.governance.tags == ["chembl", "activity", "raw"]
        assert metadata.governance.retention_days == 90
        assert metadata.governance.sla_freshness_hours == 24
        assert metadata.governance.lineage.source_system == "chembl"
        assert metadata.governance.lineage.extraction_method == "api"

    def test_bronze_metadata_without_governance(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        metadata = coordinator.create_bronze_metadata(input_data)
        assert metadata.governance is None

    def test_silver_metadata_with_governance(
        self, coordinator: MetadataCoordinator
    ) -> None:
        governance = GovernanceMetadata(
            owner="data-team",
            description="Cleansed ChEMBL activity data",
            tags=["chembl", "activity", "silver", "validated"],
            lineage=GovernanceLineageConfig(
                source_layer="bronze",
                transformations=["deduplication", "normalization", "dq_validation"],
            ),
            quality_expectations=QualityExpectations(
                completeness=0.95,
                accuracy=0.99,
            ),
        )
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": str(uuid4())}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            governance=governance,
        )
        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.governance is not None
        assert metadata.governance.description == "Cleansed ChEMBL activity data"
        assert "validated" in metadata.governance.tags
        assert metadata.governance.lineage.source_layer == "bronze"
        assert "deduplication" in metadata.governance.lineage.transformations
        assert metadata.governance.quality_expectations.completeness == pytest.approx(
            0.95
        )
        assert metadata.governance.quality_expectations.accuracy == pytest.approx(0.99)

    def test_gold_metadata_with_governance(
        self, coordinator: MetadataCoordinator
    ) -> None:
        governance = GovernanceMetadata(
            owner="analytics-team",
            description="Business-ready ChEMBL activity data",
            tags=["chembl", "activity", "gold", "ml-ready"],
            lineage=GovernanceLineageConfig(
                source_layer="silver",
                filters_applied=True,
                business_domain="drug-discovery",
                use_cases=["ml-training", "reporting", "analytics"],
            ),
        )
        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"compound_id": "CMP123", "activity_value": 5.5}],
            mode=GoldWriteMode.OVERWRITE,
            governance=governance,
        )
        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.governance is not None
        assert metadata.governance.owner == "analytics-team"
        assert "ml-ready" in metadata.governance.tags
        assert metadata.governance.lineage.filters_applied is True
        assert metadata.governance.lineage.business_domain == "drug-discovery"
        assert "ml-training" in metadata.governance.lineage.use_cases

    def test_gold_metadata_includes_rule_provenance(self) -> None:
        context = RunContext.create(
            run_id=RunID(uuid4()),
            run_type=RunType.REBUILD,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            provider="composite",
            entity="publication",
            contract_version="3.0.0",
        )
        coordinator = MetadataCoordinator(context)
        provenance = [
            {
                "rule_id": "R_TRACE_02",
                "contract_version": "3.0.0",
                "severity": "error",
                "decision": "fail",
            }
        ]
        input_data = GoldMetadataInput(
            table_path="/data/gold/composite/publication",
            table_name="composite.publication",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            dq_rule_provenance=provenance,
        )
        metadata = coordinator.create_gold_metadata(input_data)
        assert metadata.dq_summary.rule_provenance == provenance

    def test_gold_metadata_surfaces_composite_cv_trace_in_dq_summary(self) -> None:
        context = RunContext.create(
            run_id=RunID(uuid4()),
            run_type=RunType.REBUILD,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            provider="composite",
            entity="publication",
            contract_version="4.0.0",
        )
        coordinator = MetadataCoordinator(context)
        input_data = GoldMetadataInput(
            table_path="/data/gold/composite/publication",
            table_name="composite.publication",
            records=[
                {"id": 1, "_cv_warn": True},
                {"id": 2, "_cv_error": True},
                {"id": 3, "_cv_error": True, "_cv_quarantine": True},
            ],
            mode=GoldWriteMode.OVERWRITE,
            dq_report_path="reports/dq/composite-publication-gold.json",
        )
        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.dq_summary.warning_records == 1
        assert metadata.dq_summary.error_records == 2
        assert metadata.dq_summary.valid_records == 1
        assert metadata.dq_summary.validation_passed is False
        assert metadata.dq_summary.error_rate == pytest.approx(2 / 3)
        assert metadata.dq_summary.rule_provenance == [
            {
                "rule_id": "composite.cross_validation.warning",
                "contract_version": "4.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "warning",
                "decision": "warn",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication-gold.json",
                "record_count": "1",
            },
            {
                "rule_id": "composite.cross_validation.nullify",
                "contract_version": "4.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "error",
                "decision": "skip",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication-gold.json",
                "record_count": "1",
            },
            {
                "rule_id": "composite.cross_validation.quarantine",
                "contract_version": "4.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "error",
                "decision": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication-gold.json",
                "record_count": "1",
            },
        ]

    def test_governance_metadata_immutable(self) -> None:
        governance = GovernanceMetadata(owner="data-team", tags=["tag1"])
        assert governance.owner == "data-team"
        assert governance.tags == ["tag1"]

    def test_governance_lineage_config_defaults(self) -> None:
        lineage = GovernanceLineageConfig()

        assert lineage.source_system is None
        assert lineage.source_version is None
        assert lineage.extraction_method is None
        assert lineage.source_layer is None
        assert lineage.transformations == []
        assert lineage.filters_applied is None
        assert lineage.business_domain is None
        assert lineage.use_cases == []

    def test_quality_expectations_defaults(self) -> None:
        qe = QualityExpectations()
        assert qe.completeness is None
        assert qe.accuracy is None

    def test_governance_metadata_defaults(self) -> None:
        governance = GovernanceMetadata()

        assert governance.owner is None
        assert governance.steward is None
        assert governance.description is None
        assert governance.tags == []
        assert governance.retention_days is None
        assert governance.sla_freshness_hours is None
        assert governance.classification is None
        assert governance.lineage is not None
        assert governance.quality_expectations is not None
