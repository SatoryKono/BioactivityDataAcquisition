"""Explicit target migration profiles and the persisted journal contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from bioetl.infrastructure.storage.target_classification_guard import (
    contract_version_for_profile,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
)
from iuphar_target_class.stage0.io import sha256_bytes

_INVALID_TARGET_ID = "assay/target FK restoration RF-009 found an invalid target id"
_CANONICAL_CUTOVER = "RF-013"
# Physical transitions the driver can execute. 3.2.0 stays declared and
# refused until its field contract is installed and this set is updated.
_EXECUTABLE_TRANSITIONS = frozenset({("V30", "V31"), ("V31", "V31")})
_BLOCKED_TRANSITIONS = {
    ("V30", "V32"): (
        "destination contract 3.2.0 is not installed; "
        "refusing to treat it as a V31 promotion"
    ),
    ("V31", "V32"): (
        "destination contract 3.2.0 is not installed; "
        "refusing to treat it as a V31 promotion"
    ),
}


@dataclass(frozen=True, slots=True)
class TargetMigrationTransition:
    """One explicit source/destination pair, never an implicit enrich upgrade."""

    source_profile: str
    destination_profile: str
    source_contract_version: str
    destination_contract_version: str


def resolve_target_migration_transition(
    source_profile: str, destination_profile: str
) -> TargetMigrationTransition:
    """Accept only catalogued executable transitions; reject every other pair."""
    if (source_profile, destination_profile) in _BLOCKED_TRANSITIONS:
        raise ValueError(_BLOCKED_TRANSITIONS[(source_profile, destination_profile)])
    if (source_profile, destination_profile) not in _EXECUTABLE_TRANSITIONS:
        raise ValueError(
            "unsupported target migration transition "
            f"{source_profile} -> {destination_profile}"
        )
    return TargetMigrationTransition(
        source_profile,
        destination_profile,
        contract_version_for_profile(source_profile),
        contract_version_for_profile(destination_profile),
    )


def migration_status(state: Mapping[str, object]) -> dict[str, str]:
    """Report journal identity, including a schema-1 journal without V2 fields."""
    restoration = state.get("fk_restoration")
    status = "unrecorded"
    if isinstance(restoration, Mapping):
        value = restoration.get("status")
        if isinstance(value, str):
            status = value

    def text(key: str, default: str) -> str:
        value = state.get(key, default)
        return value if isinstance(value, str) else default

    return {
        "source_profile": text("source_profile", "V30"),
        "destination_profile": text("destination_profile", "V31"),
        "source_contract_version": text("source_contract_version", "3.0.0"),
        "destination_contract_version": text("destination_contract_version", "3.1.0"),
        "fk_restoration": status,
    }


def require_rf009_fk_restoration(
    assay_target_ids: set[str], gold_target_ids: set[str]
) -> dict[str, object]:
    """Block promotion until every current assay target exists in Gold."""
    missing = sorted(assay_target_ids - gold_target_ids)
    if missing:
        raise ValueError(
            "assay/target FK restoration RF-009 is required before promotion "
            f"({len(missing)} missing target ids)"
        )
    return {
        "dependency": "RF-009",
        "artifact": "bioetl_target_fk_repair_candidate",
        "status": "closed",
        "missing_target_ids": [],
        "assay_target_id_sha256": _id_digest(assay_target_ids),
        "gold_target_id_sha256": _id_digest(gold_target_ids),
    }


def _id_digest(ids: set[str]) -> str:
    return sha256_bytes("\n".join(sorted(ids)).encode())


def _assert_canonical_cutover(
    deployment: TargetDeploymentBinding | None, cutover_authority: str
) -> None:
    """Keep canonical deployment promotion behind RF-013."""
    if (
        deployment is not None
        and deployment.role == "deployment"
        and cutover_authority != _CANONICAL_CUTOVER
    ):
        raise ValueError("canonical table promotion is reserved for RF-013")


class TargetMigrationJournal(TypedDict):
    """Persisted occurrence state used by paired promotion and recovery."""

    artifact: str
    schema_version: int
    phase: str
    paths: dict[str, str]
    original_hashes: dict[str, dict[str, str]]
    candidate_hashes: dict[str, dict[str, str]]
    validation: dict[str, object]
    moved: list[str]
    activated: list[str]
    legacy_include_fields: list[str]
    assay_hashes: dict[str, str]
    restored: NotRequired[list[str]]
    deployment_binding: dict[str, str]
    dependencies: dict[str, str]
    dependency_backups: dict[str, str]
    restored_dependencies: NotRequired[list[str]]
    source_profile: str
    destination_profile: str
    source_contract_version: str
    destination_contract_version: str
    table_versions: dict[str, dict[str, object]]
    candidate_profiles: dict[str, str]
    config_contract_version: str
    destination_config_contract_version: str
    dependency_schema_versions: dict[str, int]
    fk_restoration: dict[str, object]
