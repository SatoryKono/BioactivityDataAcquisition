# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for extended metadata coordinator with DQ provenance."""

from __future__ import annotations

import pytest
from datetime import datetime

from bioetl.domain.ports.metadata.coordinator import (
    GoldMetadataInput,
    SilverMetadataInput,
)
from bioetl.domain.types.dq_contracts import DQDisposition, DQRuleProvenance


pytestmark = pytest.mark.unit


class TestSilverMetadataInputExtended:
    """Test extended SilverMetadataInput with DQ provenance."""

    def test_silver_metadata_input_creation_with_provenance(self):
        """Test SilverMetadataInput creation with DQ provenance."""
        provenance_entries = [
            DQRuleProvenance(
                rule_id="schema.not_null",
                contract_version="1.0.0",
                severity="high",
                disposition=DQDisposition.FAIL,
                config_path="configs/quality/chembl.yaml",
                report_artifact_path="/reports/dq_report.json",
            ),
            DQRuleProvenance(
                rule_id="threshold.completeness",
                contract_version="1.0.0",
                severity="medium",
                disposition=DQDisposition.WARN,
                config_path="configs/quality/common.yaml",
            ),
        ]

        metadata_input = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            primary_keys=["activity_id"],
            mode="merge",
            records=[{"activity_id": "1", "value": 10.5}],
            total_records=100,
            source_batch_ids=["batch1", "batch2"],
            version_before=5,
            version_after=6,
            dq_report_path="/reports/dq_report_20230101.json",
            dq_rule_provenance=provenance_entries,
            partition_by=["assay_type"],
            started_at=datetime(2023, 1, 1, 10, 0, 0),
            completed_at=datetime(2023, 1, 1, 10, 5, 30),
            total_bytes=1024,
        )

        assert metadata_input.table_path == "/data/silver/chembl/activity"
        assert metadata_input.dq_report_path == "/reports/dq_report_20230101.json"
        assert len(metadata_input.dq_rule_provenance) == 2
        assert metadata_input.dq_rule_provenance[0].rule_id == "schema.not_null"
        assert metadata_input.dq_rule_provenance[1].disposition == DQDisposition.WARN

    def test_silver_metadata_input_without_provenance(self):
        """Test SilverMetadataInput creation without DQ provenance."""
        metadata_input = SilverMetadataInput(
            table_path="/data/silver/test",
            primary_keys=["id"],
            mode="append",
            dq_rule_provenance=None,  # No provenance
        )

        assert metadata_input.dq_rule_provenance is None

    def test_silver_metadata_immutability_with_provenance(self):
        """Test that SilverMetadataInput remains immutable with provenance."""
        provenance = [
            DQRuleProvenance(
                rule_id="test",
                contract_version="1.0.0",
                severity="high",
                disposition=DQDisposition.FAIL,
            )
        ]

        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            dq_rule_provenance=provenance,
        )

        # Test immutability
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            metadata_input.dq_rule_provenance = []  # type: ignore


class TestGoldMetadataInputExtended:
    """Test extended GoldMetadataInput with DQ provenance."""

    def test_gold_metadata_input_creation_with_full_provenance(self):
        """Test GoldMetadataInput creation with complete DQ provenance."""
        provenance_entries = [
            DQRuleProvenance(
                rule_id="schema.not_null",
                contract_version="2.0.0",
                severity="high",
                disposition=DQDisposition.FAIL,
                config_path="contracts/gold_contract/dq_rules.yaml",
            ),
        ]

        metadata_input = GoldMetadataInput(
            table_path="/data/gold/chembl/activity_summary",
            table_name="chembl_activity_summary",
            mode="overwrite",
            records=[{"activity_id": "1", "count": 5}],
            total_records=50,
            started_at=datetime(2023, 1, 1, 11, 0, 0),
            completed_at=datetime(2023, 1, 1, 11, 10, 0),
            dq_report_path="/reports/gold_dq_report.json",
            dq_rule_provenance=provenance_entries,
            dq_policy_hash="abc123def456",
            contract_ref="chembl_gold_contract",
            contract_version="2.0.0",
            total_bytes=2048,
            partition_count=4,
            schema_validation_enabled=True,
            schema_validation_strict=True,
        )

        assert metadata_input.table_name == "chembl_activity_summary"
        assert metadata_input.dq_policy_hash == "abc123def456"
        assert metadata_input.contract_ref == "chembl_gold_contract"
        assert metadata_input.contract_version == "2.0.0"
        assert len(metadata_input.dq_rule_provenance) == 1
        assert metadata_input.dq_rule_provenance[0].rule_id == "schema.not_null"

    def test_gold_metadata_input_without_provenance(self):
        """Test GoldMetadataInput creation without DQ provenance."""
        metadata_input = GoldMetadataInput(
            table_path="/data/gold/test",
            table_name="test",
            mode="overwrite",
            dq_rule_provenance=None,
            dq_policy_hash=None,
            contract_ref=None,
            contract_version=None,
        )

        assert metadata_input.dq_rule_provenance is None
        assert metadata_input.dq_policy_hash is None
        assert metadata_input.contract_ref is None
        assert metadata_input.contract_version is None

    def test_gold_metadata_immutability_with_provenance(self):
        """Test that GoldMetadataInput remains immutable with provenance."""
        provenance = [
            DQRuleProvenance(
                rule_id="test",
                contract_version="1.0.0",
                severity="high",
                disposition=DQDisposition.FAIL,
            )
        ]

        metadata_input = GoldMetadataInput(
            table_path="/test",
            table_name="test",
            mode="overwrite",
            dq_rule_provenance=provenance,
            dq_policy_hash="test_hash",
            contract_ref="test_contract",
            contract_version="1.0.0",
        )

        # Test immutability
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            metadata_input.dq_rule_provenance = []  # type: ignore

        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            metadata_input.dq_policy_hash = "new_hash"  # type: ignore


class TestProvenanceConsistency:
    """Test consistency between DQ report paths and provenance."""

    def test_silver_provenance_report_consistency(self):
        """Test that provenance and report path are consistent."""
        report_path = "/reports/test_dq_report.json"
        provenance = DQRuleProvenance(
            rule_id="schema.test",
            contract_version="1.0.0",
            severity="high",
            disposition=DQDisposition.FAIL,
            report_artifact_path=report_path,
        )

        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            dq_report_path=report_path,
            dq_rule_provenance=[provenance],
        )

        # Both should reference the same report
        assert metadata_input.dq_report_path == report_path
        assert metadata_input.dq_rule_provenance[0].report_artifact_path == report_path

    def test_gold_provenance_report_consistency(self):
        """Test that Gold provenance and report path are consistent."""
        report_path = "/reports/gold_test_report.json"
        provenance = DQRuleProvenance(
            rule_id="schema.gold_test",
            contract_version="2.0.0",
            severity="high",
            disposition=DQDisposition.FAIL,
            report_artifact_path=report_path,
        )

        metadata_input = GoldMetadataInput(
            table_path="/test",
            table_name="test",
            mode="overwrite",
            dq_report_path=report_path,
            dq_rule_provenance=[provenance],
        )

        # Both should reference the same report
        assert metadata_input.dq_report_path == report_path
        assert metadata_input.dq_rule_provenance[0].report_artifact_path == report_path


class TestMetadataSerialization:
    """Test serialization of metadata with DQ provenance."""

    def test_silver_metadata_serialization(self):
        """Test that SilverMetadataInput with provenance can be serialized."""
        from dataclasses import asdict

        provenance = DQRuleProvenance(
            rule_id="schema.test",
            contract_version="1.0.0",
            severity="high",
            disposition=DQDisposition.FAIL,
            config_path="configs/test.yaml",
        )

        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            dq_rule_provenance=[provenance],
        )

        # Should be serializable
        metadata_dict = asdict(metadata_input)
        assert "dq_rule_provenance" in metadata_dict
        assert len(metadata_dict["dq_rule_provenance"]) == 1
        assert metadata_dict["dq_rule_provenance"][0]["rule_id"] == "schema.test"

    def test_gold_metadata_serialization(self):
        """Test that GoldMetadataInput with provenance can be serialized."""
        from dataclasses import asdict

        provenance = DQRuleProvenance(
            rule_id="schema.gold_test",
            contract_version="2.0.0",
            severity="high",
            disposition=DQDisposition.QUARANTINE,
        )

        metadata_input = GoldMetadataInput(
            table_path="/test",
            table_name="test",
            mode="overwrite",
            dq_rule_provenance=[provenance],
            dq_policy_hash="test_hash",
            contract_ref="test_contract",
            contract_version="2.0.0",
        )

        # Should be serializable
        metadata_dict = asdict(metadata_input)
        assert "dq_rule_provenance" in metadata_dict
        assert "dq_policy_hash" in metadata_dict
        assert "contract_ref" in metadata_dict
        assert "contract_version" in metadata_dict


class TestBackwardCompatibility:
    """Test backward compatibility of metadata inputs."""

    def test_silver_metadata_without_new_fields(self):
        """Test that SilverMetadataInput works without new DQ fields."""
        # This should work exactly as before
        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            # No DQ provenance fields
        )

        assert metadata_input.dq_rule_provenance is None
        # Should not raise any errors

    def test_gold_metadata_without_new_fields(self):
        """Test that GoldMetadataInput works without new DQ fields."""
        # This should work exactly as before
        metadata_input = GoldMetadataInput(
            table_path="/test",
            table_name="test",
            mode="overwrite",
            # No DQ provenance fields
        )

        assert metadata_input.dq_rule_provenance is None
        assert metadata_input.dq_policy_hash is None
        assert metadata_input.contract_ref is None
        assert metadata_input.contract_version is None
        # Should not raise any errors


class TestProvenanceValidation:
    """Test validation of provenance data."""

    def test_provenance_entry_validation(self):
        """Test that provenance entries are properly validated."""
        # Valid provenance
        valid_provenance = DQRuleProvenance(
            rule_id="schema.test",
            contract_version="1.0.0",
            severity="high",
            disposition=DQDisposition.FAIL,
        )

        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            dq_rule_provenance=[valid_provenance],
        )

        # Should not raise validation errors
        assert len(metadata_input.dq_rule_provenance) == 1

    def test_empty_provenance_list(self):
        """Test that empty provenance list is allowed."""
        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            dq_rule_provenance=[],  # Empty list
        )

        assert metadata_input.dq_rule_provenance == []

    def test_multiple_provenance_entries(self):
        """Test multiple provenance entries."""
        provenance_entries = [
            DQRuleProvenance(
                rule_id="schema.rule1",
                contract_version="1.0.0",
                severity="high",
                disposition=DQDisposition.FAIL,
            ),
            DQRuleProvenance(
                rule_id="schema.rule2",
                contract_version="1.0.0",
                severity="medium",
                disposition=DQDisposition.WARN,
            ),
            DQRuleProvenance(
                rule_id="threshold.rule3",
                contract_version="1.0.0",
                severity="low",
                disposition=DQDisposition.PASS,
            ),
        ]

        metadata_input = SilverMetadataInput(
            table_path="/test",
            primary_keys=["id"],
            mode="merge",
            dq_rule_provenance=provenance_entries,
        )

        assert len(metadata_input.dq_rule_provenance) == 3
        assert metadata_input.dq_rule_provenance[0].severity == "high"
        assert metadata_input.dq_rule_provenance[1].severity == "medium"
        assert metadata_input.dq_rule_provenance[2].severity == "low"
