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
    parts = _numeric_semver_parts(version)
    if parts is None:
        return version
    padded = parts[:_SEMVER_PARTS_COUNT]
    while len(padded) < _SEMVER_PARTS_COUNT:
        padded.append("0")
    return ".".join(padded)


def _numeric_semver_parts(version: str) -> list[str] | None:
    parts = [part for part in version.split(".") if part != ""]
    if _is_numeric_version_parts(parts):
        return [str(int(part)) for part in parts]
    return None


def _is_numeric_version_parts(parts: list[str]) -> bool:
    return bool(parts) and all(part.isdigit() for part in parts)


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


def _metadata_value(value: str | None) -> str:
    """Return runtime metadata string for one optional identity field."""
    return "" if value is None else value


def _base_identity_issues(
    contract_ref: str,
    contract_version: str,
    schema_hash: str,
) -> list[str]:
    """Return validation issues for the required identity fields."""
    checks = (
        (
            _has_contract_ref_namespace(contract_ref),
            f"Invalid contract_ref format: {contract_ref}",
        ),
        (
            _is_semver(contract_version),
            f"Invalid version format: {contract_version} (expected X.Y.Z)",
        ),
        (
            _is_sha256_hex(schema_hash),
            f"Invalid schema_hash format: {schema_hash}",
        ),
    )
    return [message for ok, message in checks if not ok]


def _normalization_values_are_complete(values: tuple[str | None, ...]) -> bool:
    """Return True when all optional normalization identity parts are present."""
    return all(isinstance(value, str) and value for value in values)


def _has_partial_normalization_identity(
    profile_ref: str | None,
    profile_version: str | None,
    profile_hash: str | None,
) -> bool:
    """Return True when any normalization identity field is present but not all."""
    values = (profile_ref, profile_version, profile_hash)
    has_any = any(value is not None for value in values)
    is_complete = _normalization_values_are_complete(values)
    return has_any and not is_complete


def _normalization_profile_identity_issues(
    profile_ref: str | None,
    profile_version: str | None,
    profile_hash: str | None,
) -> list[str]:
    """Return validation issues for optional normalization identity fields."""
    issues: list[str] = []
    if _has_partial_normalization_identity(profile_ref, profile_version, profile_hash):
        issues.append(
            "Normalization profile identity must include ref, version, and hash together"
        )
    if profile_hash is not None and not _is_sha256_hex(profile_hash):
        issues.append(f"Invalid normalization_profile_hash format: {profile_hash}")
    return issues


@dataclass(frozen=True)
class ContractIdentity:
    """Immutable contract identity with explicit versioning."""

    contract_ref: str
    contract_version: str
    compatibility_level: CompatibilityLevel
    schema_hash: str
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None

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
            "dq_policy_ref": _metadata_value(self.dq_policy_ref),
            "rule_bundle_version": _metadata_value(self.rule_bundle_version),
            "normalization_profile_ref": _metadata_value(
                self.normalization_profile_ref
            ),
            "normalization_profile_version": _metadata_value(
                self.normalization_profile_version
            ),
            "normalization_profile_hash": _metadata_value(
                self.normalization_profile_hash
            ),
        }

    def validate(self) -> list[str]:
        """Validate contract identity fields."""
        issues = _base_identity_issues(
            self.contract_ref,
            self.contract_version,
            self.schema_hash,
        )
        issues.extend(
            _normalization_profile_identity_issues(
                self.normalization_profile_ref,
                self.normalization_profile_version,
                self.normalization_profile_hash,
            )
        )
        return issues


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
