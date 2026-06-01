"""Unit tests for DQ consistency validator script."""

from __future__ import annotations

import pytest

import tempfile
import yaml
from pathlib import Path

from scripts.engineering.qa.validate_dq_consistency import DQConsistencyValidator
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver


pytestmark = pytest.mark.unit

class TestDQConsistencyValidator:
    """Test DQ consistency validator functionality."""

    def test_valid_config_with_contract_references(self):
        """Test validation of config with proper contract references."""
        validator = DQConsistencyValidator()

        # Create a temporary config file with valid contract references
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "contract_ref": "chembl_molecule",
                    "contract_version": "1.0.0",
                    "rule_bundle_version": "1.0.0",
                    "default_disposition_policy": "warn",
                },
                f,
            )
            config_path = Path(f.name)

        try:
            result = validator.validate_config_contract_references(config_path)
            assert result is True
            assert len(validator.issues) == 0
        finally:
            config_path.unlink()

    def test_invalid_config_missing_contract_ref(self):
        """Test validation of config missing contract_ref."""
        validator = DQConsistencyValidator()

        # Create a temporary config file missing contract_ref
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "contract_version": "1.0.0",
                    "rule_bundle_version": "1.0.0",
                },
                f,
            )
            config_path = Path(f.name)

        try:
            result = validator.validate_config_contract_references(config_path)
            assert result is False
            assert len(validator.issues) == 1
            assert "Incomplete contract reference" in validator.issues[0]
        finally:
            config_path.unlink()

    def test_invalid_version_format(self):
        """Test validation of config with invalid version format."""
        validator = DQConsistencyValidator()

        # Create a temporary config file with invalid version
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "contract_ref": "test",
                    "contract_version": "invalid",
                    "rule_bundle_version": "1.0.0",
                },
                f,
            )
            config_path = Path(f.name)

        try:
            result = validator.validate_config_contract_references(config_path)
            assert result is False
            assert len(validator.issues) == 1
            assert "Invalid contract_version" in validator.issues[0]
        finally:
            config_path.unlink()

    def test_valid_provenance_entries(self):
        """Test validation of metadata with valid provenance entries."""
        validator = DQConsistencyValidator()

        metadata = {
            "dq_rule_provenance": [
                {
                    "rule_id": "schema.not_null",
                    "contract_version": "1.0.0",
                    "severity": "high",
                    "disposition": "fail",
                },
                {
                    "rule_id": "threshold.completeness",
                    "contract_version": "1.0.0",
                    "severity": "medium",
                    "disposition": "warn",
                },
            ]
        }

        result = validator.validate_provenance_consistency(metadata)
        assert result is True
        assert len(validator.issues) == 0

    def test_invalid_provenance_missing_fields(self):
        """Test validation of metadata with invalid provenance entries."""
        validator = DQConsistencyValidator()

        metadata = {
            "dq_rule_provenance": [
                {
                    "rule_id": "schema.test",
                    # Missing required fields
                },
            ]
        }

        result = validator.validate_provenance_consistency(metadata)
        assert result is False
        assert len(validator.issues) == 1
        assert "missing required field" in validator.issues[0]

    def test_invalid_provenance_disposition(self):
        """Test validation of metadata with invalid disposition values."""
        validator = DQConsistencyValidator()

        metadata = {
            "dq_rule_provenance": [
                {
                    "rule_id": "schema.test",
                    "contract_version": "1.0.0",
                    "severity": "high",
                    "disposition": "invalid_disposition",
                },
            ]
        }

        result = validator.validate_provenance_consistency(metadata)
        assert result is False
        assert len(validator.issues) == 1
        assert "invalid disposition value" in validator.issues[0]

    def test_consistency_validator__hash_stability__af1528ae(self):
        """Test that policy hash is stable for same configuration."""
        validator = DQConsistencyValidator()

        config = DQConfig(
            contract_ref="test_contract",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        # Get hash twice
        result1 = validator.validate_policy_hash_stability(config)
        result2 = validator.validate_policy_hash_stability(config)

        assert result1 is True
        assert result2 is True

    def test_policy_hash_with_expected_value(self):
        """Test policy hash validation with expected value."""
        validator = DQConsistencyValidator()

        config = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        # Get the actual hash first
        resolver = DQPolicyResolver(config)
        expected_hash = resolver.build_policy_ref().policy_hash

        # Test with correct hash
        result = validator.validate_policy_hash_stability(config, expected_hash)
        assert result is True

        # Test with wrong hash
        result = validator.validate_policy_hash_stability(config, "wrong_hash")
        assert result is False
        assert len(validator.issues) == 1

    def test_disposition_determinism(self):
        """Test that disposition resolution is deterministic."""
        validator = DQConsistencyValidator()

        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.critical_field": DQDisposition.FAIL,
            },
        )

        result = validator.validate_disposition_determinism(
            config,
            "schema.test_field",
            DQViolationKind.SCHEMA_VIOLATION,
            "high",
        )

        assert result is True
        assert len(validator.issues) == 0

    def test_validator_run_all_checks(self):
        """Test running all checks."""
        validator = DQConsistencyValidator()

        # Should return True with no issues when no configs found
        result = validator.run_all_checks()
        assert result is True
        assert len(validator.issues) == 0

    def test_validator_with_issues(self):
        """Test validator behavior when issues are found."""
        validator = DQConsistencyValidator()

        # Add some issues manually
        validator.issues.append("Test issue 1")
        validator.issues.append("Test issue 2")
        validator.warnings.append("Test warning 1")

        result = validator.run_all_checks()
        assert result is False
        assert len(validator.issues) == 2
        assert len(validator.warnings) == 1


class TestVersionValidation:
    """Test version validation logic."""

    def test_valid_semantic_versions(self):
        """Test validation of valid semantic versions."""
        validator = DQConsistencyValidator()

        valid_versions = [
            "1.0.0",
            "2.1.3",
            "10.20.30",
            "0.0.1",
        ]

        for version in valid_versions:
            assert validator._is_valid_version(version) is True

    def test_invalid_semantic_versions(self):
        """Test validation of invalid semantic versions."""
        validator = DQConsistencyValidator()

        invalid_versions = [
            "1.0",
            "1",
            "1.0.0.0",
            "a.b.c",
            "1.0.",
            ".1.0.0",
            "",
            "1.0.0-alpha",  # No pre-release versions in simple check
        ]

        for version in invalid_versions:
            assert validator._is_valid_version(version) is False


class TestIntegrationScenarios:
    """Test integration scenarios for DQ consistency."""

    def test_complete_dq_workflow_validation(self):
        """Test a complete DQ workflow validation scenario."""
        validator = DQConsistencyValidator()

        # Step 1: Validate config
        config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.2.0",
            rule_bundle_version="2.1.0",
            default_disposition_policy=DQDisposition.WARN,
            strictness_mode="strict",
        )

        config_valid = validator.validate_policy_hash_stability(config)
        assert config_valid is True

        # Step 2: Create provenance from config
        resolver = DQPolicyResolver(config)
        outcome = resolver.create_rule_outcome(
            rule_id="schema.molecule_id",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            config_path="contracts/chembl_molecule/dq_rules.yaml",
        )

        # Convert outcome to dict format for metadata
        provenance_dict = {
            "rule_id": outcome.rule_id,
            "contract_version": config.contract_version,
            "severity": outcome.severity,
            "disposition": outcome.disposition,
            "config_path": outcome.config_path,
        }

        # Step 3: Validate provenance
        metadata = {
            "dq_rule_provenance": [provenance_dict],
            "dq_report_path": "/reports/chembl_dq_report.json",
        }

        provenance_valid = validator.validate_provenance_consistency(metadata)
        assert provenance_valid is True

        # Step 4: Test determinism
        determinism_valid = validator.validate_disposition_determinism(
            config,
            "schema.molecule_id",
            DQViolationKind.SCHEMA_VIOLATION,
            "high",
        )
        assert determinism_valid is True

        # Overall validation should pass
        assert len(validator.issues) == 0
        assert len(validator.warnings) == 0
