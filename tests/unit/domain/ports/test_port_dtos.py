"""Tests for DTOs exported from the domain ports facade."""

from __future__ import annotations


import pytest

from bioetl.domain.ports import (
    AdrDocument,
    AdrInfo,
    AdrValidationReport,
    AuditEntry,
    AuditLayer,
    AuditOperation,
    BronzeMetadataInput,
)
from tests.helpers.clock import FIXED_TEST_TIME


@pytest.mark.unit
class TestAuditDataClasses:
    """Tests for audit port DTOs: AuditEntry, AuditOperation, AuditLayer."""

    def test_audit_operation_values(self) -> None:
        assert AuditOperation.WRITE == "write"
        assert AuditOperation.MERGE == "merge"
        assert AuditOperation.APPEND == "append"
        assert AuditOperation.DELETE == "delete"
        assert AuditOperation.OVERWRITE == "overwrite"

    def test_audit_layer_values(self) -> None:
        assert AuditLayer.BRONZE == "bronze"
        assert AuditLayer.SILVER == "silver"
        assert AuditLayer.GOLD == "gold"

    def test_audit_entry_creation(self) -> None:
        now = FIXED_TEST_TIME
        entry = AuditEntry(
            run_id="run-123",
            timestamp=now,
            layer=AuditLayer.SILVER,
            table_name="chembl.activity",
            operation=AuditOperation.MERGE,
            records_count=1000,
        )
        assert entry.run_id == "run-123"
        assert entry.layer == AuditLayer.SILVER
        assert entry.records_count == 1000
        assert entry.metadata == {}

    def test_audit_entry_with_metadata(self) -> None:
        now = FIXED_TEST_TIME
        entry = AuditEntry(
            run_id="run-456",
            timestamp=now,
            layer=AuditLayer.BRONZE,
            table_name="pubmed.publication",
            operation=AuditOperation.WRITE,
            records_count=500,
            metadata={"batch_id": "batch-001", "provider": "pubmed"},
        )
        assert entry.metadata["provider"] == "pubmed"

    def test_audit_entry_to_dict(self) -> None:
        now = FIXED_TEST_TIME
        entry = AuditEntry(
            run_id="run-789",
            timestamp=now,
            layer=AuditLayer.GOLD,
            table_name="gold.compounds",
            operation=AuditOperation.OVERWRITE,
            records_count=200,
        )
        result = entry.to_dict()
        assert result["run_id"] == "run-789"
        assert result["layer"] == "gold"
        assert result["operation"] == "overwrite"
        assert result["records_count"] == 200
        assert result["timestamp"] == now.isoformat()

    def test_audit_entry_immutable(self) -> None:
        now = FIXED_TEST_TIME
        entry = AuditEntry(
            run_id="run-1",
            timestamp=now,
            layer=AuditLayer.BRONZE,
            table_name="t",
            operation=AuditOperation.WRITE,
            records_count=1,
        )
        with pytest.raises((AttributeError, TypeError)):
            entry.records_count = 999  # type: ignore[misc]


@pytest.mark.unit
class TestAdrDataClasses:
    """Tests for ADR port DTOs."""

    def test_adr_info_creation(self) -> None:
        info = AdrInfo(number=1, title="Use Delta Lake", path="docs/adr/001.md")
        assert info.number == 1
        assert info.title == "Use Delta Lake"
        assert info.path == "docs/adr/001.md"

    def test_adr_info_immutable(self) -> None:
        info = AdrInfo(number=1, title="Test", path="test.md")
        with pytest.raises((AttributeError, TypeError)):
            info.number = 2  # type: ignore[misc]

    def test_adr_document_creation(self) -> None:
        doc = AdrDocument(
            number=5,
            title="PII Hashing Strategy",
            content="# ADR-005\n...",
            path="docs/adr/005.md",
            status="accepted",
            date="2024-01-15",
        )
        assert doc.status == "accepted"
        assert doc.date == "2024-01-15"

    def test_adr_document_optional_fields(self) -> None:
        doc = AdrDocument(number=1, title="T", content="C", path="p.md")
        assert doc.status is None
        assert doc.date is None

    def test_adr_validation_issue_defaults(self) -> None:
        from bioetl.domain.ports.adr import AdrValidationIssue

        issue = AdrValidationIssue(
            number=None,
            path="docs/adr/bad.md",
            message="Missing status field",
        )
        assert issue.severity == "error"
        assert issue.number is None

    def test_adr_validation_report(self) -> None:
        from bioetl.domain.ports.adr import AdrValidationIssue

        report = AdrValidationReport(
            valid=False,
            total=10,
            errors=2,
            warnings=1,
            issues=[AdrValidationIssue(number=3, path="p", message="err")],
        )
        assert not report.valid
        assert report.total == 10
        assert len(report.issues) == 1


@pytest.mark.unit
class TestMetadataCoordinatorDataClasses:
    """Tests for metadata coordinator DTOs."""

    def test_bronze_metadata_input(self) -> None:
        now = FIXED_TEST_TIME
        inp = BronzeMetadataInput(
            batch_id="batch-001",
            record_count=100,
            compressed_size=4096,
            output_path="bronze/chembl/activity/2024-01-01/batch-001.jsonl.zst",
            started_at=now,
            completed_at=now,
        )
        assert inp.batch_id == "batch-001"
        assert inp.record_count == 100
        assert inp.source_metadata is None
        assert inp.governance is None

    def test_bronze_metadata_input_immutable(self) -> None:
        now = FIXED_TEST_TIME
        inp = BronzeMetadataInput(
            batch_id="b",
            record_count=1,
            compressed_size=1,
            output_path="p",
            started_at=now,
            completed_at=now,
        )
        with pytest.raises((AttributeError, TypeError)):
            inp.record_count = 999  # type: ignore[misc]

    def test_silver_metadata_input_defaults(self) -> None:
        from bioetl.domain.ports import SilverMetadataInput

        inp = SilverMetadataInput(
            table_path="/data/silver/chembl.activity",
            primary_keys=["entity_id"],
            mode="merge",
        )
        assert inp.records is None
        assert inp.total_records is None
        assert inp.version_before is None
        assert inp.total_bytes == 0

    def test_silver_ref_creation(self) -> None:
        from bioetl.domain.ports import SilverRef

        ref = SilverRef(
            table_name="chembl.activity",
            table_path="/data/silver/chembl.activity",
            delta_version=42,
        )
        assert ref.delta_version == 42
        assert ref.table_name == "chembl.activity"

    def test_gold_metadata_input_defaults(self) -> None:
        from bioetl.domain.ports import GoldMetadataInput

        inp = GoldMetadataInput(
            table_path="/data/gold/compounds",
            table_name="compounds",
            mode="overwrite",
        )
        assert inp.total_bytes == 0
        assert inp.partition_count == 0
        assert inp.schema_validation_enabled is False
        assert inp.schema_validation_strict is None
