"""Pure rules for run evidence location locators (RF-002).

A location record points at one run's data root. It is not READY / objects /
replay proof; manifest chains stay on RunManifestPort / report assessment.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from bioetl.domain.control_plane.run_evidence_location_models import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EVIDENCE_LOCATION_SCHEMA_VERSION,
    EvidenceLocationConflictError,
    EvidenceLocationIdentityConflictError,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    EvidenceLocationLookupResult,
    EvidenceLocationRegisterOutcome,
    EvidenceLocationRegisterResult,
    RunEvidenceLocation,
)
from bioetl.domain.control_plane.run_evidence_location_path import (
    EVIDENCE_LOCATIONS_DIRNAME,
    canonicalize_relative_data_root,
    evidence_location_record_segments,
    optional_workflow_run_id,
    require_segment,
    validate_runtime_source_id,
)

__all__ = [
    "DEFAULT_EVIDENCE_ROOT_ALIAS",
    "EVIDENCE_LOCATIONS_DIRNAME",
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
    "evidence_location_record_segments",
    "ownership_key",
    "parse_run_evidence_location",
    "validate_runtime_source_id",
]

_REQUIRED_LOCATION_FIELDS = frozenset(
    {
        "schema_version",
        "kind",
        "owner",
        "run_id",
        "workflow_run_id",
        "runtime_source_id",
        "root_alias",
        "relative_data_root",
        "revision",
    }
)


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


def _coerce_kind(kind: EvidenceLocationKind | str) -> EvidenceLocationKind:
    if isinstance(kind, EvidenceLocationKind):
        return kind
    try:
        return EvidenceLocationKind(str(kind).strip())
    except ValueError as exc:
        raise EvidenceLocationInvalidError(
            f"unsupported evidence location kind: {kind}"
        ) from exc


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
    kind_value = _coerce_kind(kind)
    owner_text = require_segment(owner, field_name="owner")
    run_id_text = require_segment(run_id, field_name="run_id")
    alias = require_segment(root_alias, field_name="root_alias")
    source_id = validate_runtime_source_id(runtime_source_id)
    relative = canonicalize_relative_data_root(relative_data_root)
    workflow = optional_workflow_run_id(workflow_run_id, kind=kind_value)
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


def _payload_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _require_location_mapping(payload: object) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise EvidenceLocationInvalidError("location payload must be a mapping")
    return payload


def _require_location_fields(payload: Mapping[str, object]) -> None:
    missing = sorted(_REQUIRED_LOCATION_FIELDS - payload.keys())
    if missing:
        raise EvidenceLocationInvalidError(
            "location payload missing required fields: " + ", ".join(missing)
        )


def _require_relative_root_string(payload: Mapping[str, object]) -> None:
    value = payload["relative_data_root"]
    if isinstance(value, str) and value.strip():
        return
    raise EvidenceLocationInvalidError("relative_data_root must be a non-empty string")


def _require_supported_schema(payload: Mapping[str, object]) -> None:
    schema = _payload_text(payload, "schema_version")
    if schema == EVIDENCE_LOCATION_SCHEMA_VERSION:
        return
    label = schema if schema else "<missing>"
    raise EvidenceLocationInvalidError(f"unsupported schema_version: {label}")


def _build_from_payload(payload: Mapping[str, object]) -> RunEvidenceLocation:
    return build_run_evidence_location(
        kind=_payload_text(payload, "kind"),
        owner=_payload_text(payload, "owner"),
        run_id=_payload_text(payload, "run_id"),
        runtime_source_id=_payload_text(payload, "runtime_source_id"),
        root_alias=_payload_text(payload, "root_alias"),
        relative_data_root=_payload_text(payload, "relative_data_root"),
        workflow_run_id=payload.get("workflow_run_id"),  # type: ignore[arg-type]  # tracked(#12721): type safety debt
    )


def _require_matching_revision(
    payload: Mapping[str, object],
    location: RunEvidenceLocation,
) -> None:
    recorded = _payload_text(payload, "revision").lower()
    if recorded != location.revision:
        raise EvidenceLocationInvalidError(
            "location revision digest does not match canonical binding body"
        )


def parse_run_evidence_location(payload: Mapping[str, object]) -> RunEvidenceLocation:
    """Parse and validate one location payload; recompute revision integrity."""
    mapping = _require_location_mapping(payload)
    _require_location_fields(mapping)
    _require_relative_root_string(mapping)
    _require_supported_schema(mapping)
    location = _build_from_payload(mapping)
    _require_matching_revision(mapping, location)
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
