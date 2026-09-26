"""Helper functions for contract registry parsing and validation."""

from __future__ import annotations

# SANCTIONED: pathlib.Path used as value object for path computation only.
# No I/O operations (open, read, write) are performed here.
# See domain/README.md#sanctioned-exceptions
from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    LifecycleStatus,
)

from .contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationIssue,
    RegistryValidationSeverity,
)


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse semantic version and return integer parts."""
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid version format: {version}")
    major, minor, patch = parts
    return int(major), int(minor), int(patch)


def _is_string_mapping(value: dict[object, object]) -> bool:
    """Return True when a mapping uses string keys and values only."""
    return all(isinstance(key, str) for key in value) and all(
        isinstance(val, str) for val in value.values()
    )


def as_string_list(value: object, field_name: str) -> list[str]:
    """Validate a list[str] field and return normalized value."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must contain only strings")
    return list(value)


def as_string_dict(value: object, field_name: str) -> dict[str, str]:
    """Validate a dict[str, str] field and return normalized value."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    if not _is_string_mapping(value):
        raise ValueError(f"{field_name} must be a mapping of strings")
    return dict(value)


def _parse_identity(contract_ref: str, identity_data: JsonDict) -> ContractIdentity:
    """Parse contract identity payload from raw registry data."""
    compatibility_raw = str(identity_data.get("compatibility_level", "patch"))
    try:
        compatibility_level = CompatibilityLevel(compatibility_raw)
    except ValueError as exc:
        raise ValueError(
            f"Invalid compatibility_level for {contract_ref}: {compatibility_raw}"
        ) from exc
    return ContractIdentity(
        contract_ref=contract_ref,
        contract_version=str(identity_data.get("contract_version", "1.0.0")),
        compatibility_level=compatibility_level,
        schema_hash=str(identity_data.get("schema_hash", "")),
        dq_policy_ref=identity_data.get("dq_policy_ref"),
        rule_bundle_version=identity_data.get("rule_bundle_version"),
        normalization_profile_ref=identity_data.get("normalization_profile_ref"),
        normalization_profile_version=identity_data.get(
            "normalization_profile_version"
        ),
        normalization_profile_hash=identity_data.get("normalization_profile_hash"),
    )


def _parse_status(contract_ref: str, raw_status: object) -> LifecycleStatus:
    """Parse lifecycle status with contextual error."""
    try:
        return LifecycleStatus(str(raw_status))
    except ValueError as exc:
        raise ValueError(f"Invalid status for {contract_ref}: {raw_status}") from exc


def parse_entry_payload(contract_ref: str, data: JsonDict) -> ContractRegistryEntry:
    """Parse one registry entry from raw dictionary payload."""
    identity_data = data.get("identity")
    if identity_data is None:
        identity_data = {}
    if not isinstance(identity_data, dict):
        raise ValueError(f"Invalid identity payload for {contract_ref}")

    return ContractRegistryEntry(
        identity=_parse_identity(contract_ref, identity_data),
        status=_parse_status(contract_ref, data.get("status", "active")),
        source_path=str(data.get("source_path", "")),
        published_artifacts=as_string_list(
            data.get("published_artifacts"), "published_artifacts"
        ),
        supported_versions=as_string_list(
            data.get("supported_versions"), "supported_versions"
        ),
        migration_guides=as_string_dict(
            data.get("migration_guides"), "migration_guides"
        ),
        last_updated=str(data.get("last_updated", "")),
        owners=as_string_list(data.get("owners"), "owners"),
        dq_policy_ref=data.get("dq_policy_ref"),
        rule_bundle_version=data.get("rule_bundle_version"),
        normalization_profile_ref=data.get("normalization_profile_ref"),
        normalization_profile_version=data.get("normalization_profile_version"),
        normalization_profile_hash=data.get("normalization_profile_hash"),
    )


def entry_payload(entry: ContractRegistryEntry) -> JsonDict:
    """Build serialization payload for one registry entry."""
    return {
        "identity": {
            "contract_version": entry.identity.contract_version,
            "compatibility_level": entry.identity.compatibility_level.value,
            "schema_hash": entry.identity.schema_hash,
            "dq_policy_ref": entry.identity.dq_policy_ref,
            "rule_bundle_version": entry.identity.rule_bundle_version,
            "normalization_profile_ref": entry.identity.normalization_profile_ref,
            "normalization_profile_version": entry.identity.normalization_profile_version,
            "normalization_profile_hash": entry.identity.normalization_profile_hash,
        },
        "status": entry.status.value,
        "source_path": entry.source_path,
        "published_artifacts": list(entry.published_artifacts),
        "supported_versions": list(entry.supported_versions),
        "migration_guides": dict(entry.migration_guides),
        "last_updated": entry.last_updated,
        "owners": list(entry.owners),
        "dq_policy_ref": entry.dq_policy_ref,
        "rule_bundle_version": entry.rule_bundle_version,
        "normalization_profile_ref": entry.normalization_profile_ref,
        "normalization_profile_version": entry.normalization_profile_version,
        "normalization_profile_hash": entry.normalization_profile_hash,
    }


def build_existing_version_issue(
    existing: ContractRegistryEntry,
    candidate: ContractRegistryEntry,
) -> RegistryValidationIssue | None:
    """Return warning issue for same-version entry updates, if applicable."""
    if candidate.identity.contract_version != existing.identity.contract_version:
        return None
    if candidate == existing:
        return None
    return RegistryValidationIssue(
        message="Updating existing version with different content",
        severity=RegistryValidationSeverity.WARNING,
        contract_ref=candidate.identity.contract_ref,
    )


def resolve_path(reference: str, base_path: Path | None) -> Path:
    """Resolve possibly relative path against optional base directory."""
    candidate = Path(reference)
    if candidate.is_absolute() or base_path is None:
        return candidate
    return base_path / candidate


def build_version_regression_message(
    existing_version_label: str,
    candidate_version_label: str,
) -> str | None:
    """Return regression message if candidate semver is older, else None."""
    existing_version = parse_semver(existing_version_label)
    candidate_version = parse_semver(candidate_version_label)
    if candidate_version >= existing_version:
        return None
    if candidate_version[0] < existing_version[0]:
        level = "major"
    elif candidate_version[1] < existing_version[1]:
        level = "minor"
    else:
        level = "patch"
    return (
        f"Cannot register older {level} version: "
        f"{candidate_version_label} < {existing_version_label}"
    )
