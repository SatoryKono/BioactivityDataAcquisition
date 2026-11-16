"""Validate run/row bindings before publishing classification evidence."""

from __future__ import annotations

from bioetl.domain.target_classification import TargetClassificationResult

from ._manifest import decode_json


def _known_evidence(value: object, run_id: str, row_id: str) -> set[str]:
    if not isinstance(value, list):
        raise ValueError("classification evidence must be a JSON array")
    identifiers: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("invalid classification evidence record")
        if item.get("run_id") != run_id or item.get("input_row_id") != row_id:
            raise ValueError("classification evidence belongs to another run or row")
        identifier = item.get("evidence_id")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
        ):
            raise ValueError("invalid or duplicate classification evidence identity")
        identifiers.add(identifier)
    return identifiers


def _classification_row(rows: object, row_id: str) -> dict[str, object]:
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("expected exactly one classification artifact row")
    row = rows[0]
    if row.get("input_row_id") != row_id:
        raise ValueError("classification artifact belongs to another source row")
    return row


def validate_row_artifacts(
    result: TargetClassificationResult, *, run_id: str, profile_sha256: str
) -> None:
    if result.projection.get("target_class_profile_sha256") != profile_sha256:
        raise ValueError("classification result belongs to another profile")
    contents = {
        artifact.name: decode_json(artifact.payload) for artifact in result.artifacts
    }
    row = _classification_row(contents["classification.json"], result.input_row_id)
    known = _known_evidence(contents["evidence.json"], run_id, result.input_row_id)
    for key in ("match_evidence_ids", "local_evidence_ids"):
        references = row.get(key, [])
        if not isinstance(references, list) or any(
            item not in known for item in references
        ):
            raise ValueError("unresolvable classification evidence reference")
