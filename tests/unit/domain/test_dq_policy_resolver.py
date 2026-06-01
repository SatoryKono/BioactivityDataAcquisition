"""Unit tests for DQPolicyResolver service."""

from __future__ import annotations

import pytest
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind


pytestmark = pytest.mark.unit

class TestDQPolicyResolverInitialization:
    """Test DQPolicyResolver initialization and basic functionality."""

    def test_resolver_initialization_with_default_config(self):
        """Test resolver initialization with default configuration."""
        config = DQConfig()
        resolver = DQPolicyResolver(config)

        assert resolver.config == config
        assert resolver.config.default_disposition_policy == DQDisposition.WARN
        assert resolver.config.strictness_mode == "moderate"

    def test_resolver_initialization_with_custom_config(self):
        """Test resolver initialization with custom configuration."""
        config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.2.0",
            rule_bundle_version="2.1.0",
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="strict",
        )
        resolver = DQPolicyResolver(config)

        assert resolver.config.contract_ref == "chembl_molecule"
        assert resolver.config.default_disposition_policy == DQDisposition.QUARANTINE

    def test_resolver_with_invalid_default_disposition(self):
        """Test that invalid default disposition raises error."""
        config = DQConfig(default_disposition_policy="invalid")  # type: ignore

        with pytest.raises(ValueError, match="Invalid default_disposition_policy"):
            DQPolicyResolver(config)

    def test_resolver_with_invalid_disposition_override(self):
        """Test that invalid disposition override raises error."""
        config = DQConfig(disposition_overrides={"rule1": "invalid"})  # type: ignore

        with pytest.raises(ValueError, match="Invalid disposition override"):
            DQPolicyResolver(config)


class TestPolicyReferenceBuilding:
    """Test policy reference building functionality."""

    def test_build_policy_ref_with_full_contract_info(self):
        """Test building policy ref with complete contract information."""
        config = DQConfig(
            contract_ref="pubmed_article",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
        )
        resolver = DQPolicyResolver(config)
        policy_ref = resolver.build_policy_ref()

        assert policy_ref.contract_ref == "pubmed_article"
        assert policy_ref.contract_version == "2.0.0"
        assert policy_ref.rule_bundle_version == "1.5.0"
        assert policy_ref.policy_hash is not None
        assert len(policy_ref.policy_hash) == 64  # SHA256 hash length

    def test_build_policy_ref_with_defaults(self):
        """Test building policy ref with default values."""
        config = DQConfig()
        resolver = DQPolicyResolver(config)
        policy_ref = resolver.build_policy_ref()

        assert policy_ref.contract_ref == "default"
        assert policy_ref.contract_version == "1.0.0"
        assert policy_ref.rule_bundle_version == "1.0.0"
        assert policy_ref.policy_hash is not None

    def test_reference_building__hash_stability__16a21443(self):
        """Test that policy hash is stable for same configuration."""
        config1 = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        config2 = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        resolver1 = DQPolicyResolver(config1)
        resolver2 = DQPolicyResolver(config2)

        hash1 = resolver1.build_policy_ref().policy_hash
        hash2 = resolver2.build_policy_ref().policy_hash

        assert hash1 == hash2

    def test_policy_hash_changes_with_config(self):
        """Test that policy hash changes when configuration changes."""
        config1 = DQConfig(default_disposition_policy=DQDisposition.WARN)
        config2 = DQConfig(default_disposition_policy=DQDisposition.QUARANTINE)

        resolver1 = DQPolicyResolver(config1)
        resolver2 = DQPolicyResolver(config2)

        hash1 = resolver1.build_policy_ref().policy_hash
        hash2 = resolver2.build_policy_ref().policy_hash

        assert hash1 != hash2


class TestDispositionResolution:
    """Test disposition resolution logic."""

    def test_disposition_resolution_with_default_policy(self):
        """Test disposition resolution using default policy."""
        config = DQConfig(default_disposition_policy=DQDisposition.WARN)
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="schema.not_null",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )

        # Should return WARN as default, but escalated due to schema violation
        assert disposition == DQDisposition.QUARANTINE

    def test_disposition_resolution_with_override(self):
        """Test that disposition overrides take precedence."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.not_null": DQDisposition.FAIL,
            },
        )
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="schema.not_null",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )

        # Should use the override, not the default
        assert disposition == DQDisposition.FAIL

    def test_disposition_resolution_high_severity(self):
        """Test that high severity violations get escalated dispositions."""
        config = DQConfig(default_disposition_policy=DQDisposition.WARN)
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="threshold.completeness",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="high",
        )

        # High severity should escalate WARN to QUARANTINE
        assert disposition == DQDisposition.QUARANTINE

    def test_disposition_resolution_low_severity(self):
        """Test that low severity violations get de-escalated dispositions."""
        config = DQConfig(default_disposition_policy=DQDisposition.QUARANTINE)
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="anomaly.detection",
            violation_kind=DQViolationKind.ANOMALY_SIGNAL,
            severity="low",
        )

        # Low severity should de-escalate QUARANTINE to WARN
        assert disposition == DQDisposition.WARN

    def test_disposition_resolution_strict_mode(self):
        """Test disposition resolution in strict mode."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            strictness_mode="strict",
        )
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="threshold.completeness",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )

        # Strict mode should escalate WARN to QUARANTINE
        assert disposition == DQDisposition.QUARANTINE

    def test_disposition_resolution_lenient_mode(self):
        """Test disposition resolution in lenient mode."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="lenient",
        )
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="threshold.completeness",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )

        # Lenient mode should de-escalate QUARANTINE to WARN
        assert disposition == DQDisposition.WARN

    def test_schema_violation_escalation(self):
        """Test that schema violations are automatically escalated."""
        config = DQConfig(default_disposition_policy=DQDisposition.WARN)
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="schema.not_null",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )

        # Schema violations should escalate WARN to QUARANTINE
        assert disposition == DQDisposition.QUARANTINE

    def test_anomaly_signal_de_escalation(self):
        """Test that anomaly signals are automatically de-escalated."""
        config = DQConfig(default_disposition_policy=DQDisposition.FAIL)
        resolver = DQPolicyResolver(config)

        disposition = resolver.resolve_disposition(
            rule_id="anomaly.detection",
            violation_kind=DQViolationKind.ANOMALY_SIGNAL,
            severity="high",
        )

        # Anomaly signals should de-escalate FAIL to QUARANTINE
        assert disposition == DQDisposition.QUARANTINE


class TestRuleOutcomeCreation:
    """Test rule outcome creation functionality."""

    def test_create_rule_outcome_basic(self):
        """Test basic rule outcome creation."""
        config = DQConfig(default_disposition_policy=DQDisposition.WARN)
        resolver = DQPolicyResolver(config)

        outcome = resolver.create_rule_outcome(
            rule_id="schema.not_null",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            affected_fields=["id", "name"],
            config_path="configs/quality/chembl.yaml",
        )

        assert outcome.rule_id == "schema.not_null"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.severity == "high"
        assert outcome.disposition == DQDisposition.QUARANTINE  # Escalated from WARN
        assert outcome.affected_fields == ["id", "name"]
        assert outcome.config_path == "configs/quality/chembl.yaml"

    def test_create_rule_outcome_with_override(self):
        """Test rule outcome creation with disposition override."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "critical.field": DQDisposition.FAIL,
            },
        )
        resolver = DQPolicyResolver(config)

        outcome = resolver.create_rule_outcome(
            rule_id="critical.field",
            violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
            severity="high",
        )

        assert outcome.disposition == DQDisposition.FAIL  # Uses override

    def test_create_rule_outcome_with_defaults(self):
        """Test rule outcome creation with default values."""
        config = DQConfig()
        resolver = DQPolicyResolver(config)

        outcome = resolver.create_rule_outcome(
            rule_id="threshold.completeness",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )

        assert outcome.affected_fields == []  # Default empty list
        assert outcome.config_path is None  # Default None
        assert outcome.disposition == DQDisposition.WARN  # Default disposition


class TestPolicySummary:
    """Test effective policy summary functionality."""

    def test_get_effective_policy_summary(self):
        """Test getting effective policy summary."""
        config = DQConfig(
            contract_ref="pubmed_article",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="strict",
            disposition_overrides={
                "critical.field": DQDisposition.FAIL,
                "optional.field": DQDisposition.WARN,
            },
        )
        resolver = DQPolicyResolver(config)

        summary = resolver.get_effective_policy_summary()

        assert summary["contract_ref"] == "pubmed_article"
        assert summary["contract_version"] == "2.0.0"
        assert summary["rule_bundle_version"] == "1.5.0"
        assert summary["default_disposition"] == "quarantine"
        assert summary["strictness_mode"] == "strict"
        assert summary["disposition_override_count"] == 2
        assert summary["policy_hash"] is not None
        assert len(summary["policy_hash"]) == 64

    def test_policy_summary_with_defaults(self):
        """Test policy summary with default configuration."""
        config = DQConfig()
        resolver = DQPolicyResolver(config)

        summary = resolver.get_effective_policy_summary()

        assert summary["contract_ref"] is None
        assert summary["contract_version"] is None
        assert summary["rule_bundle_version"] is None
        assert summary["default_disposition"] == "warn"
        assert summary["strictness_mode"] == "moderate"
        assert summary["disposition_override_count"] == 0


class TestPolicyResolverIntegration:
    """Integration tests for policy resolver."""

    def test_complex_policy_resolution_scenario(self):
        """Test a complex policy resolution scenario."""
        config = DQConfig(
            contract_ref="chembl_molecule_gold",
            contract_version="3.0.0",
            rule_bundle_version="2.0.0",
            default_disposition_policy=DQDisposition.WARN,
            strictness_mode="strict",
            disposition_overrides={
                "schema.molecule_id": DQDisposition.FAIL,
                "threshold.min_records": DQDisposition.QUARANTINE,
            },
        )
        resolver = DQPolicyResolver(config)

        # Test 1: Override takes precedence
        disposition1 = resolver.resolve_disposition(
            rule_id="schema.molecule_id",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
        )
        assert disposition1 == DQDisposition.FAIL

        # Test 2: Strict mode + schema violation escalation
        disposition2 = resolver.resolve_disposition(
            rule_id="schema.assay_id",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )
        assert (
            disposition2 == DQDisposition.QUARANTINE
        )  # WARN -> QUARANTINE (strict mode)

        # Test 3: Override with medium severity
        disposition3 = resolver.resolve_disposition(
            rule_id="threshold.min_records",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )
        assert disposition3 == DQDisposition.QUARANTINE  # Uses override

        # Test 4: Low severity anomaly in strict mode
        disposition4 = resolver.resolve_disposition(
            rule_id="anomaly.outlier",
            violation_kind=DQViolationKind.ANOMALY_SIGNAL,
            severity="low",
        )
        assert (
            disposition4 == DQDisposition.QUARANTINE
        )  # WARN -> QUARANTINE (strict mode overrides anomaly de-escalation)

    def test_policy_consistency_across_instances(self):
        """Test that same configuration produces consistent results."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="strict",
        )

        resolver1 = DQPolicyResolver(config)
        resolver2 = DQPolicyResolver(config)

        # Test same inputs produce same outputs
        disposition1 = resolver1.resolve_disposition(
            rule_id="test.rule",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="high",
        )

        disposition2 = resolver2.resolve_disposition(
            rule_id="test.rule",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="high",
        )

        assert disposition1 == disposition2
        assert (
            resolver1.build_policy_ref().policy_hash
            == resolver2.build_policy_ref().policy_hash
        )
