"""Fast smoke tests for contract-aware validator policy mechanics."""

from __future__ import annotations

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind
from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
)


class TestContractAwareGoldValidatorSmoke:
    """Smoke tests focused on policy resolver behavior."""

    def test_policy_resolver_integration(self) -> None:
        """Policy resolver should emit escalated outcomes from validator config."""
        config = DQConfig(
            contract_ref="test_contract",
            contract_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.critical_field": DQDisposition.FAIL,
            },
        )
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="test.rule",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
        )

        assert outcome.rule_id == "test.rule"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.severity == "high"
        assert outcome.disposition == DQDisposition.QUARANTINE

    def test_disposition_override(self) -> None:
        """Explicit rule overrides should win over default disposition policy."""
        validator = ContractAwareGoldValidator(
            schema=None,
            dq_config=DQConfig(
                default_disposition_policy=DQDisposition.WARN,
                disposition_overrides={
                    "schema.critical_field": DQDisposition.FAIL,
                },
            ),
        )

        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.critical_field",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )

        assert outcome.disposition == DQDisposition.FAIL


class TestProvenanceInformationSimple:
    """Smoke tests for provenance on generated rule outcomes."""

    def test_outcome_provenance(self) -> None:
        """Outcomes should preserve contract provenance and config source path."""
        config = DQConfig(
            contract_ref="provenance_test",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
        )
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        config_path = "contracts/provenance_test/dq_rules.yaml"
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.required_field",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            affected_fields=["required_field"],
            config_path=config_path,
        )

        assert outcome.rule_id == "schema.required_field"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.affected_fields == ["required_field"]
        assert outcome.config_path == config_path
        assert validator.policy_ref is not None
        assert validator.policy_ref.contract_ref == "provenance_test"
        assert validator.policy_ref.contract_version == "2.0.0"


class TestDispositionResolutionSimple:
    """Smoke tests for default and mode-adjusted disposition resolution."""

    def test_default_disposition_applied(self) -> None:
        """Default disposition should apply when no override exists."""
        validator = ContractAwareGoldValidator(
            schema=None,
            dq_config=DQConfig(
                default_disposition_policy=DQDisposition.QUARANTINE,
            ),
        )

        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.normal_field",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )

        assert outcome.disposition == DQDisposition.QUARANTINE

    def test_strict_mode_escalation(self) -> None:
        """Strict mode should escalate medium-severity violations."""
        validator = ContractAwareGoldValidator(
            schema=None,
            dq_config=DQConfig(
                default_disposition_policy=DQDisposition.WARN,
                strictness_mode="strict",
            ),
        )

        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.test_field",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )

        assert outcome.disposition == DQDisposition.QUARANTINE

    def test_lenient_mode_de_escalation(self) -> None:
        """Lenient mode should de-escalate medium-severity violations."""
        validator = ContractAwareGoldValidator(
            schema=None,
            dq_config=DQConfig(
                default_disposition_policy=DQDisposition.QUARANTINE,
                strictness_mode="lenient",
            ),
        )

        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.test_field",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )

        assert outcome.disposition == DQDisposition.WARN
