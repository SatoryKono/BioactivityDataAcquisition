"""Pure rules for run evidence location locators (RF-002).

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

_OWNER_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
_SOURCE_ID = re.compile(r"^[0-9a-f]{64}$")
_RELATIVE_ROOT = re.compile(
    r"^(?!\.{1,2}(?:/|$))[A-Za-z0-9._-]+"
    r"(?:/(?!\.{1,2}(?:/|$))[A-Za-z0-9._-]+)*$"
)
_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:(?:/|$)")


def validate_runtime_source_id(value: object) -> str:
    """Return a canonical lowercase 64-hex source id or raise."""
    text = str(value or "").strip().lower()
    if not _SOURCE_ID.fullmatch(text):
        raise EvidenceLocationInvalidError(
            "runtime_source_id must be a 64-character lowercase hex digest"
        )
    return text


def _collapse_slashes(text: str) -> str:
    while "//" in text:
        text = text.replace("//", "/")
    return text


def _reject_absolute_relative_root(text: str) -> None:
    if text.startswith("/") or _DRIVE_ABSOLUTE.match(text):
        raise EvidenceLocationInvalidError(
            "relative_data_root must be relative to the alias base"
        )


def _reject_dot_segments(parts: list[str]) -> None:
    if any(part in {"", ".", ".."} for part in parts):
        raise EvidenceLocationInvalidError(
            "relative_data_root must not contain '.' or '..' segments"
        )


def _is_alias_base_relative(text: str) -> bool:
    return text in {"", ".", "./"}


def canonicalize_relative_data_root(value: object) -> str:
    """Normalize a relative data-root path; reject absolute / parent segments."""
    text = str(value or "").strip().replace("\\", "/")
    if _is_alias_base_relative(text):
        return "."
    text = _collapse_slashes(text)
    _reject_absolute_relative_root(text)
    text = text.strip("/")
    if _is_alias_base_relative(text):
        return "."
    _reject_dot_segments(text.split("/"))
    if not _RELATIVE_ROOT.fullmatch(text):
        raise EvidenceLocationInvalidError(
            "relative_data_root has unsupported characters or shape"
        )
    if len(text) > 512:
        raise EvidenceLocationInvalidError("relative_data_root exceeds max length 512")
    return text


def _require_nonempty_segment(text: str, *, field_name: str) -> str:
    if text in {".", ".."} or not text or not _OWNER_SEGMENT.fullmatch(text):
        raise EvidenceLocationInvalidError(
            f"{field_name} must be a non-empty safe path segment"
        )
    return text


def _require_segment(value: object, *, field_name: str) -> str:
    text = _require_nonempty_segment(str(value or "").strip(), field_name=field_name)
    if len(text) > 128:
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


def _payload_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    return str(value).strip()


def parse_run_evidence_location(payload: Mapping[str, object]) -> RunEvidenceLocation:
    """Parse and validate one location payload; recompute revision integrity."""
    if not isinstance(payload, Mapping):
        raise EvidenceLocationInvalidError("location payload must be a mapping")
    required = {
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
    missing = sorted(required - payload.keys())
    if missing:
        raise EvidenceLocationInvalidError(
            "location payload missing required fields: " + ", ".join(missing)
        )
    if (
        not isinstance(payload["relative_data_root"], str)
        or not str(payload["relative_data_root"]).strip()
    ):
        raise EvidenceLocationInvalidError(
            "relative_data_root must be a non-empty string"
        )
    schema = _payload_text(payload, "schema_version")
    if schema != EVIDENCE_LOCATION_SCHEMA_VERSION:
        raise EvidenceLocationInvalidError(
            f"unsupported schema_version: {schema or '<missing>'}"
        )
    location = build_run_evidence_location(
        kind=_payload_text(payload, "kind"),
        owner=_payload_text(payload, "owner"),
        run_id=_payload_text(payload, "run_id"),
        runtime_source_id=_payload_text(payload, "runtime_source_id"),
        root_alias=_payload_text(payload, "root_alias"),
        relative_data_root=_payload_text(payload, "relative_data_root"),
        workflow_run_id=payload.get("workflow_run_id"),  # type: ignore[arg-type]
    )
    recorded = _payload_text(payload, "revision").lower()
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
