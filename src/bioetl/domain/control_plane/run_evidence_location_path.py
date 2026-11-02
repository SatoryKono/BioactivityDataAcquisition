"""Path and identity segment rules for run evidence location locators."""

from __future__ import annotations

import re

from bioetl.domain.control_plane.run_evidence_location_models import (
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
)

__all__ = [
    "EVIDENCE_LOCATIONS_DIRNAME",
    "canonicalize_relative_data_root",
    "evidence_location_record_segments",
    "optional_workflow_run_id",
    "require_segment",
    "validate_runtime_source_id",
]

# Additive catalog directory beside pipeline/workflow report trees (RF-002).
EVIDENCE_LOCATIONS_DIRNAME = "_evidence-locations"

_OWNER_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
_SOURCE_ID = re.compile(r"^[0-9a-f]{64}$")
_RELATIVE_ROOT = re.compile(
    r"^(?!\.{1,2}(?:/|$))[A-Za-z0-9._-]+"
    r"(?:/(?!\.{1,2}(?:/|$))[A-Za-z0-9._-]+)*$"
)
_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:(?:/|$)")


def _as_stripped_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def validate_runtime_source_id(value: object) -> str:
    """Return a canonical lowercase 64-hex source id or raise."""
    text = _as_stripped_text(value).lower()
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


def _reject_relative_root_shape(text: str) -> None:
    if not _RELATIVE_ROOT.fullmatch(text):
        raise EvidenceLocationInvalidError(
            "relative_data_root has unsupported characters or shape"
        )
    if len(text) > 512:
        raise EvidenceLocationInvalidError("relative_data_root exceeds max length 512")


def canonicalize_relative_data_root(value: object) -> str:
    """Normalize a relative data-root path; reject absolute / parent segments."""
    text = _as_stripped_text(value).replace("\\", "/")
    if _is_alias_base_relative(text):
        return "."
    text = _collapse_slashes(text)
    _reject_absolute_relative_root(text)
    text = text.strip("/")
    if _is_alias_base_relative(text):
        return "."
    _reject_dot_segments(text.split("/"))
    _reject_relative_root_shape(text)
    return text


def _require_nonempty_segment(text: str, *, field_name: str) -> str:
    if text in {".", ".."} or not text or not _OWNER_SEGMENT.fullmatch(text):
        raise EvidenceLocationInvalidError(
            f"{field_name} must be a non-empty safe path segment"
        )
    return text


def _reject_segment_length(text: str, *, field_name: str) -> None:
    limits = {"owner": 120, "root_alias": 64}
    limit = limits.get(field_name, 128)
    if len(text) <= limit:
        return
    if field_name == "owner":
        raise EvidenceLocationInvalidError("owner exceeds max length 120")
    if field_name == "root_alias":
        raise EvidenceLocationInvalidError("root_alias exceeds max length 64")
    raise EvidenceLocationInvalidError(
        f"{field_name} must be a non-empty safe path segment"
    )


def require_segment(value: object, *, field_name: str) -> str:
    """Return a safe non-empty path segment with field-specific length caps."""
    text = _require_nonempty_segment(_as_stripped_text(value), field_name=field_name)
    _reject_segment_length(text, field_name=field_name)
    return text


def optional_workflow_run_id(
    value: object,
    *,
    kind: EvidenceLocationKind,
) -> str | None:
    """Normalize optional workflow_run_id; forbid it for kind=workflow."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if kind is EvidenceLocationKind.WORKFLOW:
        raise EvidenceLocationInvalidError(
            "workflow_run_id must be null for kind=workflow"
        )
    return require_segment(text, field_name="workflow_run_id")


def evidence_location_record_segments(
    *,
    kind: EvidenceLocationKind | str,
    owner: str,
    run_id: str,
) -> tuple[str, str, str]:
    """Return ``(kind, owner, run_id.json)`` segments for one catalog record."""
    kind_value = (
        kind.value if isinstance(kind, EvidenceLocationKind) else str(kind).strip()
    )
    if kind_value not in {
        EvidenceLocationKind.PIPELINE.value,
        EvidenceLocationKind.WORKFLOW.value,
    }:
        raise EvidenceLocationInvalidError(
            f"unsupported evidence location kind: {kind_value}"
        )
    owner_text = require_segment(owner, field_name="owner")
    run_id_text = require_segment(run_id, field_name="run_id")
    return (kind_value, owner_text, f"{run_id_text}.json")
