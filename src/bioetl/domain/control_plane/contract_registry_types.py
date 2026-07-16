"""Domain types for contract registry validation and entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from bioetl.domain._immutability import freeze_fields
from bioetl.domain.types.contract_identity import ContractIdentity, LifecycleStatus


class RegistryValidationError(Exception):
    """Error raised for contract registry validation failures."""


class RegistryValidationSeverity(Enum):
    """Severity levels for registry validation issues."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass(frozen=True)
class RegistryValidationIssue:
    """Single validation issue found in registry."""

    message: str
    severity: RegistryValidationSeverity
    contract_ref: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class RegistryValidationResult:
    """Result of registry validation."""

    valid: bool
    issues: list[RegistryValidationIssue] = field(default_factory=list)

    def __post_init__(self) -> None:
        freeze_fields(self, ("issues",))

    @property
    def has_blocking_issues(self) -> bool:
        """Return True when at least one blocking issue exists."""
        return any(
            issue.severity == RegistryValidationSeverity.BLOCKING
            for issue in self.issues
        )

    @property
    def has_warnings(self) -> bool:
        """Return True when at least one warning issue exists."""
        return any(
            issue.severity == RegistryValidationSeverity.WARNING
            for issue in self.issues
        )


def _build_identity_issues(identity: ContractIdentity) -> list[RegistryValidationIssue]:
    """Map identity validation messages into registry validation issues."""
    return [
        RegistryValidationIssue(
            message=message,
            severity=RegistryValidationSeverity.BLOCKING,
            contract_ref=identity.contract_ref,
            field="identity",
        )
        for message in identity.validate()
    ]


def _build_required_field_issues(
    contract_ref: str,
    source_path: str,
    last_updated: str,
    owners: list[str],
) -> list[RegistryValidationIssue]:
    """Validate required entry fields and return issues."""
    issues: list[RegistryValidationIssue] = []
    if not source_path:
        issues.append(
            RegistryValidationIssue(
                message="Missing source_path",
                severity=RegistryValidationSeverity.BLOCKING,
                contract_ref=contract_ref,
                field="source_path",
            )
        )
    if not last_updated:
        issues.append(
            RegistryValidationIssue(
                message="Missing last_updated timestamp",
                severity=RegistryValidationSeverity.WARNING,
                contract_ref=contract_ref,
                field="last_updated",
            )
        )
    if not owners:
        issues.append(
            RegistryValidationIssue(
                message="No owners specified",
                severity=RegistryValidationSeverity.WARNING,
                contract_ref=contract_ref,
                field="owners",
            )
        )
    return issues


def _build_supported_version_issues(
    contract_ref: str,
    current_version: str,
    supported_versions: list[str],
) -> list[RegistryValidationIssue]:
    """Validate that current version is included in supported versions list."""
    if current_version in supported_versions:
        return []
    return [
        RegistryValidationIssue(
            message=f"Current version {current_version} not in supported_versions",
            severity=RegistryValidationSeverity.BLOCKING,
            contract_ref=contract_ref,
            field="supported_versions",
        )
    ]


def _build_dq_identity_alignment_issues(
    entry: ContractRegistryEntry,
) -> list[RegistryValidationIssue]:
    """Validate DQ metadata is identical in identity and entry payloads."""
    checks = (
        (
            "dq_policy_ref",
            entry.identity.dq_policy_ref,
            entry.dq_policy_ref,
        ),
        (
            "rule_bundle_version",
            entry.identity.rule_bundle_version,
            entry.rule_bundle_version,
        ),
        (
            "normalization_profile_ref",
            entry.identity.normalization_profile_ref,
            entry.normalization_profile_ref,
        ),
        (
            "normalization_profile_version",
            entry.identity.normalization_profile_version,
            entry.normalization_profile_version,
        ),
        (
            "normalization_profile_hash",
            entry.identity.normalization_profile_hash,
            entry.normalization_profile_hash,
        ),
    )
    issues: list[RegistryValidationIssue] = []
    for field_name, identity_value, entry_value in checks:
        if identity_value == entry_value:
            continue
        issues.append(
            RegistryValidationIssue(
                message=(
                    f"{field_name} mismatch between identity and registry entry: "
                    f"identity={identity_value!r}, entry={entry_value!r}"
                ),
                severity=RegistryValidationSeverity.BLOCKING,
                contract_ref=entry.identity.contract_ref,
                field=field_name,
            )
        )
    return issues


@dataclass(frozen=True)
class ContractRegistryEntry:
    """Single entry in the contract registry."""

    identity: ContractIdentity
    status: LifecycleStatus
    source_path: str
    published_artifacts: list[str] = field(default_factory=list)
    supported_versions: list[str] = field(default_factory=list)
    migration_guides: dict[str, str] = field(default_factory=dict)
    last_updated: str = ""
    owners: list[str] = field(default_factory=list)
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None

    def __post_init__(self) -> None:
        freeze_fields(
            self,
            (
                "published_artifacts",
                "supported_versions",
                "migration_guides",
                "owners",
            ),
        )

    def validate(self) -> list[RegistryValidationIssue]:
        """Validate the registry entry."""
        issues = _build_identity_issues(self.identity)
        issues.extend(
            _build_required_field_issues(
                contract_ref=self.identity.contract_ref,
                source_path=self.source_path,
                last_updated=self.last_updated,
                owners=self.owners,
            )
        )
        issues.extend(
            _build_supported_version_issues(
                contract_ref=self.identity.contract_ref,
                current_version=self.identity.contract_version,
                supported_versions=self.supported_versions,
            )
        )
        issues.extend(_build_dq_identity_alignment_issues(self))
        return issues
