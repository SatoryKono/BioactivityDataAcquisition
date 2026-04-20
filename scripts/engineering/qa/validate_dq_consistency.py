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

    def _load_config_data(self, config_path: Path) -> dict[str, Any] | None:
        """Load YAML/JSON config data when the file type is supported."""
        if config_path.suffix == ".yaml":
            import yaml

            with config_path.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        elif config_path.suffix == ".json":
            with config_path.open("r", encoding="utf-8") as f:
                config_data = json.load(f)
        else:
            self.warnings.append(f"Skipping non-YAML/JSON config file: {config_path}")
            return None

        if isinstance(config_data, dict):
            return config_data
        return None

    def _contract_field_presence(
        self, config_data: dict[str, Any]
    ) -> tuple[bool, bool, bool]:
        """Return presence flags for contract metadata fields."""
        return (
            "contract_ref" in config_data,
            "contract_version" in config_data,
            "rule_bundle_version" in config_data,
        )

    def _validate_contract_field_group(
        self,
        config_path: Path,
        *,
        has_contract_ref: bool,
        has_contract_version: bool,
        has_rule_bundle: bool,
    ) -> bool:
        """Ensure partial contract references are not allowed."""
        if not (has_contract_ref or has_contract_version or has_rule_bundle):
            return True
        if has_contract_ref and has_contract_version and has_rule_bundle:
            return True
        self.issues.append(
            f"Incomplete contract reference in {config_path}:"
            f" contract_ref={has_contract_ref}, "
            f"contract_version={has_contract_version}, "
            f"rule_bundle_version={has_rule_bundle}"
        )
        return False

    def _validate_contract_ref(
        self, config_path: Path, config_data: dict[str, Any]
    ) -> bool:
        """Validate the required contract_ref field."""
        contract_ref = config_data["contract_ref"]
        if isinstance(contract_ref, str) and contract_ref:
            return True
        self.issues.append(f"Invalid contract_ref in {config_path}: '{contract_ref}'")
        return False

    def _validate_contract_versions(
        self, config_path: Path, config_data: dict[str, Any]
    ) -> bool:
        """Validate semantic versions for contract-related fields."""
        for version_field in ("contract_version", "rule_bundle_version"):
            version = config_data[version_field]
            if isinstance(version, str) and self._is_valid_version(version):
                continue
            self.issues.append(
                f"Invalid {version_field} in {config_path}: "
                f"'{version}' (should be semantic version)"
            )
            return False
        return True

    def validate_config_contract_references(self, config_path: Path) -> bool:
        """Validate that DQ configs have proper contract references."""
        try:
            config_data = self._load_config_data(config_path)
            if config_data is None:
                return True

            (
                has_contract_ref,
                has_contract_version,
                has_rule_bundle,
            ) = self._contract_field_presence(config_data)
            if not self._validate_contract_field_group(
                config_path,
                has_contract_ref=has_contract_ref,
                has_contract_version=has_contract_version,
                has_rule_bundle=has_rule_bundle,
            ):
                return False
            if not (has_contract_ref and has_contract_version and has_rule_bundle):
                return True
            if not self._validate_contract_ref(config_path, config_data):
                return False
            return self._validate_contract_versions(config_path, config_data)

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
        provenance_entries = metadata.get("dq_rule_provenance")
        if provenance_entries is None:
            return True

        if not isinstance(provenance_entries, list) or not provenance_entries:
            self.issues.append("Invalid dq_rule_provenance: should be non-empty list")
            return False

        for i, entry in enumerate(provenance_entries):
            if not self._validate_provenance_entry(i, entry):
                return False

        if report_data and "rule_outcomes" in report_data:
            report_outcomes = report_data["rule_outcomes"]
            if len(provenance_entries) != len(report_outcomes):
                self.warnings.append(
                    f"Provenance count ({len(provenance_entries)}) "
                    f"does not match report outcomes ({len(report_outcomes)})"
                )

        return True

    def _validate_provenance_entry(self, index: int, entry: Any) -> bool:
        """Validate one provenance entry payload."""
        if not isinstance(entry, dict):
            self.issues.append(f"Provenance entry {index} is not a dict: {type(entry)}")
            return True
        if not self._validate_provenance_required_fields(index, entry):
            return False
        return self._validate_provenance_disposition(index, entry["disposition"])

    def _validate_provenance_required_fields(
        self, index: int, entry: dict[str, Any]
    ) -> bool:
        """Ensure required provenance fields are present."""
        required_fields = ("rule_id", "contract_version", "severity", "disposition")
        for field in required_fields:
            if field in entry:
                continue
            self.issues.append(
                f"Provenance entry {index} missing required field: {field}"
            )
            return False
        return True

    def _validate_provenance_disposition(self, index: int, disposition: Any) -> bool:
        """Validate disposition value and enum compatibility."""
        if not isinstance(disposition, str):
            self.issues.append(
                f"Provenance entry {index} has invalid disposition: {disposition}"
            )
            return False
        try:
            DQDisposition(disposition)
        except ValueError:
            self.issues.append(
                f"Provenance entry {index} has invalid disposition value: {disposition}"
            )
            return False
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
        print("\nDQ Consistency Check Summary:")
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
