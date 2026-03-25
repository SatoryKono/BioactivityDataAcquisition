"""Contract identity model with explicit versioning and governance metadata."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

_SEMVER_PARTS_COUNT = 3
_SCHEMA_HASH_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


class CompatibilityLevel(Enum):
    """Compatibility levels for contract evolution."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    MANUAL_REVIEW = "manual_review"


class LifecycleStatus(Enum):
    """Lifecycle status for contracts."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    SUNSET = "sunset"


def _normalize_semver(version: str) -> str:
    """Normalize legacy version strings into SemVer-like X.Y.Z."""
    return version if version.count(".") == _SEMVER_PARTS_COUNT - 1 else f"{version}.0"


def _has_contract_ref_namespace(contract_ref: str) -> bool:
    """Return True when contract reference includes a namespace separator."""
    return bool(contract_ref) and "." in contract_ref


def _is_semver(version: str) -> bool:
    """Return True when version follows X.Y.Z numeric format."""
    parts = version.split(".")
    return len(parts) == _SEMVER_PARTS_COUNT and all(part.isdigit() for part in parts)


def _is_sha256_hex(schema_hash: str) -> bool:
    """Return True when hash looks like lowercase SHA256 hex."""
    return len(schema_hash) == _SCHEMA_HASH_LENGTH and all(
        char in _HEX_DIGITS for char in schema_hash
    )


@dataclass(frozen=True)
class ContractIdentity:
    """Immutable contract identity with explicit versioning."""

    contract_ref: str
    contract_version: str
    compatibility_level: CompatibilityLevel
    schema_hash: str
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None

    @classmethod
    def from_legacy(cls, contract_ref: str, version: str) -> ContractIdentity:
        """Create contract identity from legacy contract + version inputs."""
        normalized_version = _normalize_semver(version)
        schema_hash = hashlib.sha256(
            f"{contract_ref}-{normalized_version}".encode()
        ).hexdigest()
        return cls(
            contract_ref=f"{contract_ref}.v{normalized_version}",
            contract_version=normalized_version,
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash=schema_hash,
        )

    def to_runtime_metadata(self) -> dict[str, str]:
        """Convert to runtime-compatible metadata format."""
        return {
            "contract_ref": self.contract_ref,
            "contract_version": self.contract_version,
            "compatibility_level": self.compatibility_level.value,
            "schema_hash": self.schema_hash,
            "dq_policy_ref": self.dq_policy_ref or "",
            "rule_bundle_version": self.rule_bundle_version or "",
        }

    def validate(self) -> list[str]:
        """Validate contract identity fields."""
        checks = (
            (
                _has_contract_ref_namespace(self.contract_ref),
                f"Invalid contract_ref format: {self.contract_ref}",
            ),
            (
                _is_semver(self.contract_version),
                f"Invalid version format: {self.contract_version} (expected X.Y.Z)",
            ),
            (
                _is_sha256_hex(self.schema_hash),
                f"Invalid schema_hash format: {self.schema_hash}",
            ),
        )
        return [message for ok, message in checks if not ok]


@dataclass(frozen=True)
class ContractProvenance:
    """Provenance information for contract definitions."""

    source_file: str
    generated_by: str
    generation_time: str
    source_commit: str | None = None


@dataclass(frozen=True)
class DQContractCompatibility:
    """Data Quality contract compatibility information."""

    policy_ref: str
    rule_bundle_version: str
    compatibility_hash: str
    contract_ref: str
    contract_version: str

    def validate_alignment(self, contract_identity: ContractIdentity) -> bool:
        """Validate alignment with contract identity."""
        expected = (
            contract_identity.contract_ref,
            contract_identity.contract_version,
            contract_identity.dq_policy_ref or "",
            contract_identity.rule_bundle_version or "",
        )
        actual = (
            self.contract_ref,
            self.contract_version,
            self.policy_ref,
            self.rule_bundle_version,
        )
        return actual == expected
