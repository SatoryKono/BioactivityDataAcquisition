"""Domain service for resolving DQ policy dispositions.

This service implements the contract-based policy resolution logic,
determining the appropriate disposition for DQ rule violations based on
contract configurations, rule severity, and violation types.
"""

from __future__ import annotations

import hashlib

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQPolicyRef,
    DQRuleOutcome,
    DQViolationKind,
)


class DQPolicyResolver:
    """Domain service for resolving DQ policy dispositions.

    Uses contract-based configuration to determine appropriate dispositions
    for data quality violations.
    """

    def __init__(self, config: DQConfig):
        """Initialize policy resolver with DQ configuration.

        Args:
            config: DQ configuration containing policy rules and contracts
        """
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that the configuration is consistent and complete."""
        # Validate that default disposition is a valid DQDisposition
        if not isinstance(self.config.default_disposition_policy, DQDisposition):
            raise ValueError(
                f"Invalid default_disposition_policy: {self.config.default_disposition_policy}"
            )

        # Validate disposition overrides (handle both dict and tuple formats)
        overrides = self._get_disposition_overrides_dict()
        for rule_id, disposition in overrides.items():
            if not isinstance(disposition, DQDisposition):
                raise ValueError(
                    f"Invalid disposition override for rule '{rule_id}': {disposition}"
                )

    def _get_disposition_overrides_dict(self) -> dict[str, DQDisposition]:
        """Get disposition overrides as a dictionary.

        Handles both the original dict format and the frozen tuple format.
        """
        if isinstance(self.config.disposition_overrides, dict):
            return self.config.disposition_overrides
        if isinstance(self.config.disposition_overrides, (tuple, list)):
            return dict(self.config.disposition_overrides)
        return {}

    def build_policy_ref(self) -> DQPolicyRef:
        """Build a policy reference from the current configuration.

        Returns:
            DQPolicyRef containing contract and version information
        """
        return DQPolicyRef(
            contract_ref=self.config.contract_ref or "default",
            contract_version=self.config.contract_version or "1.0.0",
            rule_bundle_version=self.config.rule_bundle_version or "1.0.0",
            policy_hash=self._compute_policy_hash(),
        )

    def _compute_policy_hash(self) -> str:
        """Compute a stable hash of the effective policy configuration.

        Returns:
            SHA256 hash of the policy configuration
        """
        # Create a stable representation of the policy
        overrides = self._get_disposition_overrides_dict()
        policy_data = {
            "contract_ref": self.config.contract_ref or "default",
            "contract_version": self.config.contract_version or "1.0.0",
            "rule_bundle_version": self.config.rule_bundle_version or "1.0.0",
            "default_disposition": self.config.default_disposition_policy.value,
            "disposition_overrides": overrides,
            "strictness_mode": self.config.strictness_mode,
            "soft_fail_threshold": self.config.soft_fail_threshold,
            "hard_fail_threshold": self.config.hard_fail_threshold,
            "strict_validation": self.config.strict_validation,
        }

        # Convert to sorted JSON for stable hashing
        import json

        policy_json = json.dumps(policy_data, sort_keys=True)
        return hashlib.sha256(policy_json.encode("utf-8")).hexdigest()

    def resolve_disposition(
        self,
        rule_id: str,
        violation_kind: DQViolationKind,
        severity: str,
        threshold_breach: bool = False,
        anomaly_signal: bool = False,
    ) -> DQDisposition:
        """Resolve the appropriate disposition for a DQ violation.

        Args:
            rule_id: Identifier of the rule that was violated
            violation_kind: Type of violation that occurred
            severity: Severity level of the violation (low, medium, high)
            threshold_breach: Whether this is a threshold breach violation
            anomaly_signal: Whether this is an anomaly detection signal

        Returns:
            DQDisposition indicating how to handle the violation
        """
        # Step 1: Check for explicit disposition overrides
        overrides = self._get_disposition_overrides_dict()
        if rule_id in overrides:
            return overrides[rule_id]

        # Step 2: Apply strictness mode adjustments
        disposition = self._apply_strictness_mode(
            violation_kind, severity, threshold_breach, anomaly_signal
        )

        # Step 3: Apply contract-specific adjustments
        disposition = self._apply_contract_adjustments(disposition, violation_kind)

        return disposition

    def _apply_strictness_mode(
        self,
        violation_kind: DQViolationKind,
        severity: str,
        _threshold_breach: bool = False,
        _anomaly_signal: bool = False,
    ) -> DQDisposition:
        """Apply strictness mode adjustments to base disposition."""
        disposition = self._apply_severity_adjustment(
            self.config.default_disposition_policy,
            severity,
        )
        disposition = self._apply_mode_adjustment(disposition)
        return self._apply_violation_kind_adjustment(disposition, violation_kind)

    def _apply_severity_adjustment(
        self,
        base_disposition: DQDisposition,
        severity: str,
    ) -> DQDisposition:
        """Adjust disposition by rule severity."""
        if severity == "high":
            escalation_map = {
                DQDisposition.PASS: DQDisposition.QUARANTINE,
                DQDisposition.WARN: DQDisposition.QUARANTINE,
                DQDisposition.QUARANTINE: DQDisposition.FAIL,
            }
            return escalation_map.get(base_disposition, base_disposition)

        if severity == "low":
            deescalation_map = {
                DQDisposition.FAIL: DQDisposition.QUARANTINE,
                DQDisposition.QUARANTINE: DQDisposition.WARN,
            }
            return deescalation_map.get(base_disposition, base_disposition)

        return base_disposition

    def _apply_mode_adjustment(self, disposition: DQDisposition) -> DQDisposition:
        """Adjust disposition by configured strictness mode."""
        if self.config.strictness_mode == "strict":
            strict_map = {
                DQDisposition.WARN: DQDisposition.QUARANTINE,
                DQDisposition.QUARANTINE: DQDisposition.FAIL,
            }
            return strict_map.get(disposition, disposition)

        if self.config.strictness_mode == "lenient":
            lenient_map = {
                DQDisposition.QUARANTINE: DQDisposition.WARN,
                DQDisposition.FAIL: DQDisposition.QUARANTINE,
            }
            return lenient_map.get(disposition, disposition)

        return disposition

    def _apply_violation_kind_adjustment(
        self,
        disposition: DQDisposition,
        violation_kind: DQViolationKind,
    ) -> DQDisposition:
        """Apply violation-kind specific guardrails."""
        if violation_kind == DQViolationKind.SCHEMA_VIOLATION:
            if disposition in (DQDisposition.PASS, DQDisposition.WARN):
                return DQDisposition.QUARANTINE
            return disposition
        if violation_kind == DQViolationKind.ANOMALY_SIGNAL:
            if disposition == DQDisposition.FAIL:
                return DQDisposition.QUARANTINE
            return disposition
        return disposition

    def _apply_contract_adjustments(
        self,
        disposition: DQDisposition,
        _violation_kind: DQViolationKind,
    ) -> DQDisposition:
        """Apply contract-specific adjustments to disposition."""
        # If we have a specific contract, we might have contract-specific rules
        # For now, this is a placeholder for future contract-specific logic
        if (
            self.config.contract_ref
            and "gold" in self.config.contract_ref.lower()
            and disposition == DQDisposition.WARN
        ):
            # Example: Gold contracts might be stricter
            disposition = DQDisposition.QUARANTINE

        return disposition

    def create_rule_outcome(
        self,
        rule_id: str,
        violation_kind: DQViolationKind,
        severity: str,
        affected_fields: list[str] | None = None,
        config_path: str | None = None,
        threshold_breach: bool = False,
        anomaly_signal: bool = False,
    ) -> DQRuleOutcome:
        """Create a complete rule outcome with resolved disposition.

        Args:
            rule_id: Identifier of the rule
            violation_kind: Type of violation
            severity: Severity level
            affected_fields: Fields affected by the violation
            config_path: Path to the configuration for this rule
            threshold_breach: Whether this is a threshold breach
            anomaly_signal: Whether this is an anomaly signal

        Returns:
            DQRuleOutcome with resolved disposition
        """
        disposition = self.resolve_disposition(
            rule_id,
            violation_kind,
            severity,
            threshold_breach,
            anomaly_signal,
        )

        return DQRuleOutcome(
            rule_id=rule_id,
            violation_kind=violation_kind,
            severity=severity,
            disposition=disposition,
            affected_fields=affected_fields or [],
            config_path=config_path,
            policy_ref=self.build_policy_ref(),
        )

    def get_effective_policy_summary(self) -> dict[str, object]:
        """Get a summary of the effective policy configuration.

        Returns:
            Dictionary containing the effective policy settings
        """
        return {
            "contract_ref": self.config.contract_ref,
            "contract_version": self.config.contract_version,
            "rule_bundle_version": self.config.rule_bundle_version,
            "default_disposition": self.config.default_disposition_policy.value,
            "strictness_mode": self.config.strictness_mode,
            "disposition_override_count": len(self.config.disposition_overrides),
            "policy_hash": self.build_policy_ref().policy_hash,
        }
