"""Load the stage-0 survey. Placeholder values are rejected."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from .constants import RECORDED_AT_PATTERN, REQUIRED_FIELD_IDS
from .io import optional_sha256
from .models import (
    CandidateFile,
    ExpectedMaterial,
    LocalObservation,
    MCodeVersion,
    ProvenanceClaim,
    Stage0Survey,
)

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RECORDED_AT = re.compile(RECORDED_AT_PATTERN)
_PLACEHOLDER = "[...]"


def load_survey(path: Path) -> Stage0Survey:
    """Load a survey object from JSON."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = "survey must be a JSON object"
        raise TypeError(message)
    return survey_from_object(cast(dict[str, Any], payload))


def survey_from_object(payload: dict[str, Any]) -> Stage0Survey:
    """Validate a survey object. Unknown keys and ``[...]`` values fail."""
    _exact_keys(
        payload,
        {
            "candidate_files",
            "expected_materials",
            "gold_standard_reviewer",
            "issued_on",
            "local_observations",
            "m_code_versions",
            "module_executor",
            "plan_revision",
            "plan_version",
            "provenance_claims",
            "recorded_at_utc",
            "result_owner_name",
            "result_owner_source",
        },
        "survey",
    )
    recorded_at = _required_text(payload["recorded_at_utc"], "recorded_at_utc")
    if _RECORDED_AT.fullmatch(recorded_at) is None:
        message = f"recorded_at_utc must match {RECORDED_AT_PATTERN}"
        raise ValueError(message)
    issued_on = _required_text(payload["issued_on"], "issued_on")
    if _DATE.fullmatch(issued_on) is None:
        message = "issued_on must be YYYY-MM-DD"
        raise ValueError(message)
    claims = tuple(
        _claim(item)
        for item in _object_list(payload["provenance_claims"], "provenance_claims")
    )
    claim_ids = [claim.field_id for claim in claims]
    if sorted(claim_ids) != sorted(REQUIRED_FIELD_IDS) or len(claim_ids) != len(
        set(claim_ids)
    ):
        message = f"provenance_claims must list each of {REQUIRED_FIELD_IDS} once"
        raise ValueError(message)
    return Stage0Survey(
        recorded_at_utc=recorded_at,
        plan_version=_required_text(payload["plan_version"], "plan_version"),
        plan_revision=_required_text(payload["plan_revision"], "plan_revision"),
        plan_issued_on=issued_on,
        result_owner_name=_required_text(
            payload["result_owner_name"], "result_owner_name"
        ),
        result_owner_source=_required_text(
            payload["result_owner_source"],
            "result_owner_source",
        ),
        module_executor=_optional_role(payload["module_executor"], "module_executor"),
        gold_standard_reviewer=_optional_role(
            payload["gold_standard_reviewer"],
            "gold_standard_reviewer",
        ),
        candidate_files=tuple(
            _candidate(item)
            for item in _object_list(payload["candidate_files"], "candidate_files")
        ),
        expected_materials=tuple(
            _material(item)
            for item in _object_list(
                payload["expected_materials"], "expected_materials"
            )
        ),
        provenance_claims=claims,
        m_code_versions=tuple(
            _m_code(item)
            for item in _object_list(payload["m_code_versions"], "m_code_versions")
        ),
        local_observations=tuple(
            _observation(item)
            for item in _object_list(
                payload["local_observations"], "local_observations"
            )
        ),
    )


def _claim(payload: dict[str, Any]) -> ProvenanceClaim:
    _exact_keys(
        payload,
        {
            "confirmation_owner",
            "field_id",
            "rule_or_process",
            "source_ref",
            "source_sha256",
        },
        "provenance_claims",
    )
    return ProvenanceClaim(
        field_id=_required_text(payload["field_id"], "field_id"),
        source_ref=_optional_text(payload["source_ref"], "source_ref"),
        source_sha256=optional_sha256(payload["source_sha256"]),
        rule_or_process=_optional_text(payload["rule_or_process"], "rule_or_process"),
        confirmation_owner=_optional_text(
            payload["confirmation_owner"],
            "confirmation_owner",
        ),
    )


def _candidate(payload: dict[str, Any]) -> CandidateFile:
    _exact_keys(payload, {"relative_path", "select_as_source"}, "candidate_files")
    if not isinstance(payload["select_as_source"], bool):
        message = "select_as_source must be a boolean"
        raise TypeError(message)
    return CandidateFile(
        relative_path=_relative_path(payload["relative_path"]),
        select_as_source=payload["select_as_source"],
    )


def _material(payload: dict[str, Any]) -> ExpectedMaterial:
    _exact_keys(payload, {"material_id", "note", "relative_path"}, "expected_materials")
    relative = payload["relative_path"]
    return ExpectedMaterial(
        material_id=_required_text(payload["material_id"], "material_id"),
        relative_path=None if relative is None else _relative_path(relative),
        note=_required_text(payload["note"], "note"),
    )


def _m_code(payload: dict[str, Any]) -> MCodeVersion:
    _exact_keys(
        payload,
        {"source_ref", "source_sha256", "version_id"},
        "m_code_versions",
    )
    sha = optional_sha256(payload["source_sha256"])
    if sha is None:
        message = "m_code_versions.source_sha256 is required when a version is listed"
        raise ValueError(message)
    return MCodeVersion(
        version_id=_required_text(payload["version_id"], "version_id"),
        source_ref=_required_text(payload["source_ref"], "source_ref"),
        source_sha256=sha,
    )


def _observation(payload: dict[str, Any]) -> LocalObservation:
    _exact_keys(
        payload,
        {"ci_recheck", "location", "method", "result"},
        "local_observations",
    )
    if not isinstance(payload["ci_recheck"], bool):
        message = "ci_recheck must be a boolean"
        raise TypeError(message)
    return LocalObservation(
        location=_required_text(payload["location"], "location"),
        method=_required_text(payload["method"], "method"),
        result=_required_text(payload["result"], "result"),
        ci_recheck=payload["ci_recheck"],
    )


def _optional_role(value: object, label: str) -> str | None:
    text = _optional_text(value, label)
    if text is not None and _PLACEHOLDER in text:
        message = f"{label} still contains {_PLACEHOLDER}; refusing to invent it"
        raise ValueError(message)
    return text


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, label)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        message = f"{label} must be a non-empty string"
        raise TypeError(message)
    if _PLACEHOLDER in value:
        message = f"{label} still contains {_PLACEHOLDER}; refusing to invent it"
        raise ValueError(message)
    return value.strip()


def _relative_path(value: object) -> str:
    text = _required_text(value, "relative_path")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or "\\" in text:
        message = f"relative posix path required: {text}"
        raise ValueError(message)
    return path.as_posix()


def _object_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        message = f"{label} must be a list"
        raise TypeError(message)
    items: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            message = f"{label} items must be objects"
            raise TypeError(message)
        items.append(cast(dict[str, Any], item))
    return items


def _exact_keys(payload: dict[str, Any], keys: set[str], label: str) -> None:
    extra = sorted(set(payload) - keys)
    missing = sorted(keys - set(payload))
    if extra or missing:
        message = f"{label} keys extra={extra} missing={missing}"
        raise ValueError(message)
