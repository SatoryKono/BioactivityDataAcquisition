"""Value objects and pure rules for run evidence location locators (RF-002).

A location record points at the data root used by one pipeline or workflow
run. It is intentionally **not** proof of READY, objects=true, or any replay
verdict. Manifest predecessor/successor chains and late workflow revisions
remain owned by RunManifestPort / report assessment — this locator must not
pin a permanent first-manifest id.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
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
    "binding_digest",
    "build_run_evidence_location",
    "canonicalize_relative_data_root",
    "compare_location_bindings",
    "decide_register_outcome",
    "ownership_key",
    "parse_run_evidence_location",
    "validate_runtime_source_id",
]

EVIDENCE_LOCATION_SCHEMA_VERSION = "run_evidence_location_v1"
DEFAULT_EVIDENCE_ROOT_ALIAS = "dashboard_data"

_OWNER_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
_SOURCE_ID = re.compile(r"^[0-9a-f]{64}$")
# Single-segment "." is allowed via the character class (not a separate
# alternative — that would be redundant with [A-Za-z0-9._-]+).
_RELATIVE_ROOT = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")


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


def validate_runtime_source_id(value: object) -> str:
    """Return a canonical lowercase 64-hex source id or raise."""
    text = str(value or "").strip().lower()
    if not _SOURCE_ID.fullmatch(text):
        raise EvidenceLocationInvalidError(
            "runtime_source_id must be a 64-character lowercase hex digest"
        )
    return text


def canonicalize_relative_data_root(value: object) -> str:
    """Normalize a relative data-root path; reject absolute / parent segments."""
    text = str(value or "").strip().replace("\\", "/")
    if not text or text in {".", "./"}:
        return "."
    while "//" in text:
        text = text.replace("//", "/")
    if text.startswith("/") or re.match(r"^[A-Za-z]:(?:/|$)", text):
        raise EvidenceLocationInvalidError(
            "relative_data_root must be relative to the alias base"
        )
    text = text.strip("/")
    if not text:
        return "."
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise EvidenceLocationInvalidError(
            "relative_data_root must not contain '.' or '..' segments"
        )
    if not _RELATIVE_ROOT.fullmatch(text):
        raise EvidenceLocationInvalidError(
            "relative_data_root has unsupported characters or shape"
        )
    return text


def _require_segment(value: object, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 128 or not _OWNER_SEGMENT.fullmatch(text):
        raise EvidenceLocationInvalidError(
            f"{field_name} must be a non-empty safe path segment"
        )
    if field_name == "owner" and len(text) > 120:
        raise EvidenceLocationInvalidError("owner exceeds max length 120")
    return text


def _optional_workflow_run_id(
    value: object,
    *,
    kind: EvidenceLocationKind,
) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if kind is EvidenceLocationKind.WORKFLOW:
        raise EvidenceLocationInvalidError(
            "workflow_run_id must be null for kind=workflow"
        )
    return _require_segment(text, field_name="workflow_run_id")


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def binding_digest(payload: Mapping[str, object]) -> str:
    """SHA-256 of the ownership/path binding body (no revision field)."""
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def ownership_key(
    *,
    kind: EvidenceLocationKind | str,
    owner: str,
    run_id: str,
) -> tuple[str, str, str]:
    """Stable ownership key matching catalog path segments."""
    kind_value = (
        kind.value if isinstance(kind, EvidenceLocationKind) else str(kind).strip()
    )
    return (kind_value, owner, run_id)


def build_run_evidence_location(
    *,
    kind: EvidenceLocationKind | str,
    owner: str,
    run_id: str,
    runtime_source_id: str,
    root_alias: str = DEFAULT_EVIDENCE_ROOT_ALIAS,
    relative_data_root: str = ".",
    workflow_run_id: str | None = None,
) -> RunEvidenceLocation:
    """Build a validated location record with a content revision digest."""
    kind_value = (
        kind
        if isinstance(kind, EvidenceLocationKind)
        else EvidenceLocationKind(str(kind).strip())
    )
    owner_text = _require_segment(owner, field_name="owner")
    if len(owner_text) > 120:
        raise EvidenceLocationInvalidError("owner exceeds max length 120")
    run_id_text = _require_segment(run_id, field_name="run_id")
    alias = _require_segment(root_alias, field_name="root_alias")
    if len(alias) > 64:
        raise EvidenceLocationInvalidError("root_alias exceeds max length 64")
    source_id = validate_runtime_source_id(runtime_source_id)
    relative = canonicalize_relative_data_root(relative_data_root)
    workflow = _optional_workflow_run_id(workflow_run_id, kind=kind_value)
    body = {
        "schema_version": EVIDENCE_LOCATION_SCHEMA_VERSION,
        "kind": kind_value.value,
        "owner": owner_text,
        "run_id": run_id_text,
        "workflow_run_id": workflow,
        "runtime_source_id": source_id,
        "root_alias": alias,
        "relative_data_root": relative,
    }
    revision = binding_digest(body)
    return RunEvidenceLocation(
        kind=kind_value,
        owner=owner_text,
        run_id=run_id_text,
        workflow_run_id=workflow,
        runtime_source_id=source_id,
        root_alias=alias,
        relative_data_root=relative,
        revision=revision,
    )


def parse_run_evidence_location(payload: Mapping[str, object]) -> RunEvidenceLocation:
    """Parse and validate one location payload; recompute revision integrity."""
    if not isinstance(payload, Mapping):
        raise EvidenceLocationInvalidError("location payload must be a mapping")
    schema = str(payload.get("schema_version") or "").strip()
    if schema != EVIDENCE_LOCATION_SCHEMA_VERSION:
        raise EvidenceLocationInvalidError(
            f"unsupported schema_version: {schema or '<missing>'}"
        )
    location = build_run_evidence_location(
        kind=str(payload.get("kind") or ""),
        owner=str(payload.get("owner") or ""),
        run_id=str(payload.get("run_id") or ""),
        runtime_source_id=str(payload.get("runtime_source_id") or ""),
        root_alias=str(payload.get("root_alias") or ""),
        relative_data_root=str(payload.get("relative_data_root") or ""),
        workflow_run_id=payload.get("workflow_run_id"),  # type: ignore[arg-type]
    )
    recorded = str(payload.get("revision") or "").strip().lower()
    if recorded != location.revision:
        raise EvidenceLocationInvalidError(
            "location revision digest does not match canonical binding body"
        )
    return location


def compare_location_bindings(
    left: RunEvidenceLocation,
    right: RunEvidenceLocation,
) -> bool:
    """Return True when ownership and path bindings are identical."""
    return left.binding_payload() == right.binding_payload()


def decide_register_outcome(
    *,
    candidate: RunEvidenceLocation,
    existing: RunEvidenceLocation | None,
) -> EvidenceLocationRegisterResult:
    """Decide idempotent register / conflict without mutating storage.

    Conflicting or foreign ownership never silently redirects to another run.
    """
    if existing is None:
        return EvidenceLocationRegisterResult(
            outcome=EvidenceLocationRegisterOutcome.REGISTERED,
            location=candidate,
        )
    if ownership_key(
        kind=existing.kind, owner=existing.owner, run_id=existing.run_id
    ) != ownership_key(
        kind=candidate.kind, owner=candidate.owner, run_id=candidate.run_id
    ):
        return EvidenceLocationRegisterResult(
            outcome=EvidenceLocationRegisterOutcome.CONFLICT,
            location=candidate,
            existing=existing,
            detail="ownership_mismatch",
        )
    if compare_location_bindings(existing, candidate):
        return EvidenceLocationRegisterResult(
            outcome=EvidenceLocationRegisterOutcome.ALREADY_IDENTICAL,
            location=existing,
            existing=existing,
        )
    return EvidenceLocationRegisterResult(
        outcome=EvidenceLocationRegisterOutcome.CONFLICT,
        location=candidate,
        existing=existing,
        detail="binding_conflict",
    )
