"""Gold layer contract definitions with explicit identity and governance metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bioetl.domain.types import JsonDict
from bioetl.domain.types.contract_identity import (
    ContractIdentity,
    ContractProvenance,
    LifecycleStatus,
)


class CompatibilityVerdict(Enum):
    """Verdict for contract compatibility checks."""

    COMPATIBLE = "compatible"
    MINOR_INCOMPATIBLE = "minor_incompatible"
    MAJOR_INCOMPATIBLE = "major_incompatible"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CompatibilityCheckResult:
    """Result of contract compatibility verification."""

    verdict: CompatibilityVerdict
    message: str
    details: JsonDict

    @classmethod
    def compatible(cls) -> CompatibilityCheckResult:
        """Create a compatible result."""
        return cls(
            verdict=CompatibilityVerdict.COMPATIBLE,
            message="Contracts are compatible",
            details={},
        )

    @classmethod
    def incompatible(
        cls,
        verdict: CompatibilityVerdict,
        message: str,
        details: JsonDict | None = None,
    ) -> CompatibilityCheckResult:
        """Create an incompatible result."""
        return cls(
            verdict=verdict,
            message=message,
            details=details or {},
        )


def _parse_semver(version: str) -> tuple[int, int, int]:
    """Parse X.Y.Z version string into integer tuple."""
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _minor_version_compatible(compatibility_rules: JsonDict | None) -> bool:
    """Return True when minor version bumps are allowed by contract rules."""
    if compatibility_rules is None:
        return True
    flag = compatibility_rules.get("minor_version_compatibility")
    return bool(flag) if flag is not None else True


def _minor_version_verdict(
    compatibility_rules: JsonDict | None,
    source_version: str,
    target_version: str,
) -> CompatibilityCheckResult:
    """Return compatibility verdict for minor version change."""
    if _minor_version_compatible(compatibility_rules):
        return CompatibilityCheckResult.compatible()
    return CompatibilityCheckResult.incompatible(
        CompatibilityVerdict.MINOR_INCOMPATIBLE,
        f"Minor version change: {source_version} -> {target_version}",
    )


@dataclass(frozen=True)
class GoldContract:
    """Gold layer contract with explicit identity and governance metadata."""

    identity: ContractIdentity
    schema: dict[str, object]
    provenance: ContractProvenance
    lifecycle_status: LifecycleStatus
    owners: list[str]
    downstream_dependencies: list[str]
    migration_notes: str | None = None
    compatibility_rules: JsonDict | None = None

    def validate_compatibility(self, other: GoldContract) -> CompatibilityCheckResult:
        """Validate compatibility with another contract version."""
        if self.identity.contract_ref != other.identity.contract_ref:
            return CompatibilityCheckResult.incompatible(
                CompatibilityVerdict.UNKNOWN,
                "Different contract references cannot be compared",
            )

        self_parts = _parse_semver(self.identity.contract_version)
        other_parts = _parse_semver(other.identity.contract_version)

        if self_parts[0] != other_parts[0]:
            return CompatibilityCheckResult.incompatible(
                CompatibilityVerdict.MAJOR_INCOMPATIBLE,
                "Major version change: "
                f"{self.identity.contract_version} -> {other.identity.contract_version}",
            )

        if self_parts[1] != other_parts[1]:
            return _minor_version_verdict(
                compatibility_rules=self.compatibility_rules,
                source_version=self.identity.contract_version,
                target_version=other.identity.contract_version,
            )

        if self_parts[2] != other_parts[2]:
            return CompatibilityCheckResult.compatible()

        return CompatibilityCheckResult.compatible()

    def get_identity_metadata(self) -> JsonDict:
        """Get complete identity metadata for runtime use."""
        return {
            **self.identity.to_runtime_metadata(),
            "lifecycle_status": self.lifecycle_status.value,
            "owners": self.owners,
            "provenance": {
                "source_file": self.provenance.source_file,
                "generated_by": self.provenance.generated_by,
                "generation_time": self.provenance.generation_time,
                "source_commit": self.provenance.source_commit or "",
            },
        }

    def validate(self) -> list[str]:
        """Validate the contract definition."""
        errors: list[str] = []

        identity_errors = self.identity.validate()
        errors.extend([f"Identity: {err}" for err in identity_errors])

        if not self.schema or not isinstance(self.schema, dict):
            errors.append("Invalid or missing schema definition")

        if not self.provenance.source_file:
            errors.append("Missing source file in provenance")

        return errors


class GoldContractRegistry:
    """Registry for Gold contracts with lookup and validation."""

    def __init__(self) -> None:
        self.contracts: dict[str, GoldContract] = {}

    def register(self, contract: GoldContract) -> None:
        """Register a Gold contract."""
        if contract.identity.contract_ref in self.contracts:
            existing = self.contracts[contract.identity.contract_ref]
            if existing.identity.contract_version != contract.identity.contract_version:
                raise ValueError(
                    f"Version conflict for {contract.identity.contract_ref}: "
                    f"{existing.identity.contract_version} vs "
                    f"{contract.identity.contract_version}"
                )

        self.contracts[contract.identity.contract_ref] = contract

    def get(self, contract_ref: str) -> GoldContract | None:
        """Get a contract by reference."""
        return self.contracts.get(contract_ref)

    def validate_all(self) -> dict[str, list[str]]:
        """Validate all registered contracts."""
        results: dict[str, list[str]] = {}
        for contract_ref, contract in self.contracts.items():
            errors = contract.validate()
            if errors:
                results[contract_ref] = errors
        return results


def create_gold_contract_registry() -> GoldContractRegistry:
    """Factory function for GoldContractRegistry."""
    return GoldContractRegistry()
