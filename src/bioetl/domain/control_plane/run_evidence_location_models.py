"""Enums, errors, and value objects for run evidence location locators."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "DEFAULT_EVIDENCE_ROOT_ALIAS",
    "EVIDENCE_LOCATION_SCHEMA_VERSION",
    "EvidenceLocationConflictError",
    "EvidenceLocationIdentityConflictError",
    "EvidenceLocationInvalidError",
    "EvidenceLocationKind",
    "EvidenceLocationLookupCode",
    "EvidenceLocationLookupResult",
    "EvidenceLocationRegisterOutcome",
    "EvidenceLocationRegisterResult",
    "RunEvidenceLocation",
]

EVIDENCE_LOCATION_SCHEMA_VERSION = "run_evidence_location_v1"
DEFAULT_EVIDENCE_ROOT_ALIAS = "dashboard_data"


class EvidenceLocationKind(StrEnum):
    """Catalog kind for one evidence-location record."""

    PIPELINE = "pipeline"
    WORKFLOW = "workflow"


class EvidenceLocationLookupCode(StrEnum):
    """Lookup discrimination for evidence location resolution.

    These codes are intentionally separate from replay readiness verdicts.
    ``MANIFEST_MISSING`` is reserved for the post-resolve manifest layer so
    callers never collapse location gaps into ``manifest_not_recorded`` /
    INCOMPLETE without an explicit second step.
    """

    FOUND = "found"
    LOCATION_MISSING = "location_missing"
    LOCATION_INVALID = "location_invalid"
    IDENTITY_CONFLICT = "identity_conflict"
    MANIFEST_MISSING = "manifest_missing"


class EvidenceLocationRegisterOutcome(StrEnum):
    """Outcome of an idempotent register attempt."""

    REGISTERED = "registered"
    ALREADY_IDENTICAL = "already_identical"
    CONFLICT = "conflict"


class EvidenceLocationInvalidError(ValueError):
    """Raised when a location payload fails contract validation."""


class EvidenceLocationConflictError(ValueError):
    """Raised when a register attempt conflicts with an existing binding."""


class EvidenceLocationIdentityConflictError(ValueError):
    """Raised when runtime/bind source identity does not match the locator."""


@dataclass(frozen=True, slots=True)
class RunEvidenceLocation:
    """Immutable locator for one run's data root under a trusted alias."""

    kind: EvidenceLocationKind
    owner: str
    run_id: str
    runtime_source_id: str
    root_alias: str
    relative_data_root: str
    revision: str
    workflow_run_id: str | None = None
    schema_version: str = EVIDENCE_LOCATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable canonical payload."""
        return {
            "schema_version": self.schema_version,
            "kind": self.kind.value,
            "owner": self.owner,
            "run_id": self.run_id,
            "workflow_run_id": self.workflow_run_id,
            "runtime_source_id": self.runtime_source_id,
            "root_alias": self.root_alias,
            "relative_data_root": self.relative_data_root,
            "revision": self.revision,
        }

    def binding_payload(self) -> dict[str, object]:
        """Return ownership + path binding fields used for conflict compares."""
        return {
            "schema_version": self.schema_version,
            "kind": self.kind.value,
            "owner": self.owner,
            "run_id": self.run_id,
            "workflow_run_id": self.workflow_run_id,
            "runtime_source_id": self.runtime_source_id,
            "root_alias": self.root_alias,
            "relative_data_root": self.relative_data_root,
        }


@dataclass(frozen=True, slots=True)
class EvidenceLocationLookupResult:
    """Bounded lookup result that never embeds a replay verdict."""

    code: EvidenceLocationLookupCode
    location: RunEvidenceLocation | None = None
    detail: str | None = None

    @property
    def is_found(self) -> bool:
        return (
            self.code is EvidenceLocationLookupCode.FOUND and self.location is not None
        )


@dataclass(frozen=True, slots=True)
class EvidenceLocationRegisterResult:
    """Result of evaluating one register attempt against existing state."""

    outcome: EvidenceLocationRegisterOutcome
    location: RunEvidenceLocation
    existing: RunEvidenceLocation | None = None
    detail: str | None = None
