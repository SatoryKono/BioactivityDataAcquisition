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
        # Start with the default disposition from config
        base_disposition = self.config.default_disposition_policy

        # Adjust based on severity
        if severity == "high":
            if base_disposition in (DQDisposition.PASS, DQDisposition.WARN):
                base_disposition = DQDisposition.QUARANTINE
            elif base_disposition == DQDisposition.QUARANTINE:
                base_disposition = DQDisposition.FAIL
        elif severity == "low":
            if base_disposition == DQDisposition.FAIL:
                base_disposition = DQDisposition.QUARANTINE
            elif base_disposition == DQDisposition.QUARANTINE:
                base_disposition = DQDisposition.WARN

        # Apply strictness mode adjustments
        if self.config.strictness_mode == "strict":
            # In strict mode, escalate dispositions
            if base_disposition == DQDisposition.WARN:
                base_disposition = DQDisposition.QUARANTINE
            elif base_disposition == DQDisposition.QUARANTINE:
                base_disposition = DQDisposition.FAIL
        elif self.config.strictness_mode == "lenient":
            # In lenient mode, de-escalate dispositions
            if base_disposition == DQDisposition.QUARANTINE:
                base_disposition = DQDisposition.WARN
            elif base_disposition == DQDisposition.FAIL:
                base_disposition = DQDisposition.QUARANTINE

        # Special handling for different violation kinds
        if violation_kind == DQViolationKind.SCHEMA_VIOLATION:
            # Schema violations are usually more severe
            if base_disposition in (DQDisposition.PASS, DQDisposition.WARN):
                base_disposition = DQDisposition.QUARANTINE
        elif (
            violation_kind == DQViolationKind.ANOMALY_SIGNAL
            and base_disposition == DQDisposition.FAIL
        ):
            # Anomaly signals are usually less severe
            base_disposition = DQDisposition.QUARANTINE

        return base_disposition

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
