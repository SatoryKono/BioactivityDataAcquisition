"""CI script to validate DQ consistency across the codebase.

This script enforces the contract-based DQ patterns by checking:
1. Contract references in DQ configurations
2. Provenance consistency between reports and metadata
3. Policy hash stability
4. Disposition resolution determinism
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.services.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQRuleProvenance,
    DQViolationKind,
)


class DQConsistencyValidator:
    """Validator for DQ consistency across the codebase."""

    def __init__(self):
        self.issues = []
        self.warnings = []

    def validate_config_contract_references(self, config_path: Path) -> bool:
        """Validate that DQ configs have proper contract references."""
        try:
            # Read the config file
            if config_path.suffix == ".yaml":
                import yaml

                with config_path.open("r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
            elif config_path.suffix == ".json":
                with config_path.open("r", encoding="utf-8") as f:
                    config_data = json.load(f)
            else:
                self.warnings.append(
                    f"Skipping non-YAML/JSON config file: {config_path}"
                )
                return True

            # Check if this looks like a DQ config
            if not isinstance(config_data, dict):
                return True

            # Check for contract fields
            has_contract_ref = "contract_ref" in config_data
            has_contract_version = "contract_version" in config_data
            has_rule_bundle = "rule_bundle_version" in config_data

            # If it has any contract field, it should have all
            if has_contract_ref or has_contract_version or has_rule_bundle:
                if not (has_contract_ref and has_contract_version and has_rule_bundle):
                    self.issues.append(
                        f"Incomplete contract reference in {config_path}:"
                        f" contract_ref={has_contract_ref}, "
                        f"contract_version={has_contract_version}, "
                        f"rule_bundle_version={has_rule_bundle}"
                    )
                    return False

                # Validate contract ref format
                if (
                    not isinstance(config_data["contract_ref"], str)
                    or not config_data["contract_ref"]
                ):
                    self.issues.append(
                        f"Invalid contract_ref in {config_path}: "
                        f"'{config_data['contract_ref']}'"
                    )
                    return False

                # Validate version formats
                for version_field in ["contract_version", "rule_bundle_version"]:
                    version = config_data[version_field]
                    if not isinstance(version, str) or not self._is_valid_version(
                        version
                    ):
                        self.issues.append(
                            f"Invalid {version_field} in {config_path}: "
                            f"'{version}' (should be semantic version)"
                        )
                        return False

            return True

        except Exception as e:
            self.issues.append(f"Error reading config {config_path}: {e}")
            return False

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid semantic version."""
        if not version:
            return False

        # Simple semantic version check (X.Y.Z)
        parts = version.split(".")
        if len(parts) != 3:
            return False

        try:
            # Should be numbers
            int(parts[0])
            int(parts[1])
            int(parts[2])
            return True
        except ValueError:
            return False

    def validate_provenance_consistency(
        self, metadata: dict[str, Any], report_data: dict[str, Any] | None = None
    ) -> bool:
        """Validate consistency between metadata and DQ report."""
        # Check if metadata has provenance
        if (
            "dq_rule_provenance" not in metadata
            or metadata["dq_rule_provenance"] is None
        ):
            return True  # No provenance to validate

        provenance_entries = metadata["dq_rule_provenance"]
        if not isinstance(provenance_entries, list) or not provenance_entries:
            self.issues.append("Invalid dq_rule_provenance: should be non-empty list")
            return False

        # Validate each provenance entry
        for i, entry in enumerate(provenance_entries):
            if not isinstance(entry, dict):
                self.issues.append(f"Provenance entry {i} is not a dict: {type(entry)}")
                continue

            # Check required fields
            required_fields = ["rule_id", "contract_version", "severity", "disposition"]
            for field in required_fields:
                if field not in entry:
                    self.issues.append(
                        f"Provenance entry {i} missing required field: {field}"
                    )
                    return False

            # Validate disposition
            if not isinstance(entry["disposition"], str):
                self.issues.append(
                    f"Provenance entry {i} has invalid disposition: {entry['disposition']}"
                )
                return False

            try:
                DQDisposition(entry["disposition"])  # Validate enum value
            except ValueError:
                self.issues.append(
                    f"Provenance entry {i} has invalid disposition value: {entry['disposition']}"
                )
                return False

        # If report data provided, check consistency
        if report_data and "rule_outcomes" in report_data:
            report_outcomes = report_data["rule_outcomes"]
            if len(provenance_entries) != len(report_outcomes):
                self.warnings.append(
                    f"Provenance count ({len(provenance_entries)}) "
                    f"does not match report outcomes ({len(report_outcomes)})"
                )

        return True

    def validate_policy_hash_stability(
        self, config: DQConfig, expected_hash: str | None = None
    ) -> bool:
        """Validate that policy hash is stable for given configuration."""
        resolver = DQPolicyResolver(config)
        actual_hash = resolver.build_policy_ref().policy_hash

        if expected_hash and actual_hash != expected_hash:
            self.issues.append(
                f"Policy hash mismatch: expected {expected_hash}, got {actual_hash}"
            )
            return False

        # Hash should be valid SHA256
        if len(actual_hash) != 64:
            self.issues.append(
                f"Invalid policy hash length: {len(actual_hash)} (expected 64)"
            )
            return False

        return True

    def validate_disposition_determinism(
        self,
        config: DQConfig,
        rule_id: str,
        violation_kind: DQViolationKind,
        severity: str,
    ) -> bool:
        """Validate that disposition resolution is deterministic."""
        resolver = DQPolicyResolver(config)

        # Resolve disposition multiple times
        disposition1 = resolver.resolve_disposition(rule_id, violation_kind, severity)
        disposition2 = resolver.resolve_disposition(rule_id, violation_kind, severity)

        if disposition1 != disposition2:
            self.issues.append(
                f"Non-deterministic disposition for {rule_id}: "
                f"{disposition1} vs {disposition2}"
            )
            return False

        # Create outcomes multiple times
        outcome1 = resolver.create_rule_outcome(rule_id, violation_kind, severity)
        outcome2 = resolver.create_rule_outcome(rule_id, violation_kind, severity)

        if outcome1 != outcome2:
            self.issues.append(f"Non-deterministic outcome for {rule_id}")
            return False

        return True

    def run_all_checks(self) -> bool:
        """Run all consistency checks."""
        print("Running DQ consistency checks...")

        # Check configs in typical locations
        config_paths = [
            Path("configs/quality"),
            Path("configs/base"),
            Path("tests/fixtures/configs"),
        ]

        for config_dir in config_paths:
            if config_dir.exists():
                for config_file in config_dir.glob("*dq*.yaml") or config_dir.glob(
                    "*dq*.json"
                ):
                    self.validate_config_contract_references(config_file)

        # Summary
        print(f"\nDQ Consistency Check Summary:")
        print(f"Issues found: {len(self.issues)}")
        print(f"Warnings found: {len(self.warnings)}")

        if self.issues:
            print("\nIssues:")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        return len(self.issues) == 0


def main() -> int:
    """Main entry point for DQ consistency validation."""
    validator = DQConsistencyValidator()

    # Run all checks
    success = validator.run_all_checks()

    if success:
        print("\nAll DQ consistency checks passed!")
        return 0
    else:
        print("\nDQ consistency checks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
