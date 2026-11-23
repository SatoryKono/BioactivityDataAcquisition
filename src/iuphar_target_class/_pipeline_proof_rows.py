"""Validate persisted row artifacts without importing the BioETL runtime."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields
from typing import cast

from .models import ClassificationResult, RunProvenance

_CLASSIFICATION_JSON = "classification.json"
_METRICS_JSON = "metrics.json"
OUTPUT_NAMES = frozenset(
    {
        _CLASSIFICATION_JSON,
        "evidence.json",
        "candidates.json",
        "components.json",
        "diagnostics.json",
        _METRICS_JSON,
    }
)


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate proof JSON key")
        result[key] = value
    return result


def mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("proof JSON object required")
    return cast("dict[str, object]", value)


def document(raw: bytes) -> dict[str, object]:
    return mapping(json.loads(raw, object_pairs_hook=_pairs))


def records(raw: bytes) -> list[dict[str, object]]:
    value = json.loads(raw, object_pairs_hook=_pairs)
    if not isinstance(value, list):
        raise ValueError("proof JSON array required")
    return [mapping(item) for item in value]


def require_values(
    actual: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    if any(actual.get(key) != value for key, value in expected.items()):
        raise ValueError("integration proof identity or version mismatch")


def version_identity(provenance: RunProvenance) -> dict[str, object]:
    result: dict[str, object] = {
        "normalization_version": provenance.normalization_version,
        "rules_version": provenance.rules_version,
        "classification_schema_version": provenance.schema_version,
        "matching_policy_version": provenance.matching_policy_version,
    }
    if any(
        not isinstance(value, str) or not value.strip() for value in result.values()
    ):
        raise ValueError("integration proof requires executed version identities")
    return result


def _known_evidence(
    items: list[dict[str, object]], row_id: str, run_id: str
) -> dict[str, dict[str, object]]:
    indexed: dict[str, dict[str, object]] = {}
    for item in items:
        require_values(item, {"input_row_id": row_id, "run_id": run_id})
        key = item.get("evidence_id")
        if not isinstance(key, str) or not key or key in indexed:
            raise ValueError("invalid or duplicate pipeline evidence ID")
        indexed[key] = item
    return indexed


def _check_links(row: Mapping[str, object], known: Mapping[str, object]) -> None:
    for name in ("match_evidence_ids", "local_evidence_ids"):
        links = row.get(name, [])
        if not isinstance(links, list) or any(
            not isinstance(key, str) or key not in known for key in links
        ):
            raise ValueError("unresolvable pipeline classification evidence reference")


def _check_diagnostics(
    items: list[dict[str, object]], known: Mapping[str, object]
) -> None:
    for item in items:
        link = item.get("evidence_id")
        if link is not None and (not isinstance(link, str) or link not in known):
            raise ValueError("unresolvable pipeline diagnostic evidence reference")


def _check_direct(
    row: Mapping[str, object], known: Mapping[str, dict[str, object]]
) -> None:
    if not row.get("iuphar_class"):
        return
    candidates = [
        item for item in known.values() if item.get("evidence_type") == "iuphar_raw"
    ]
    for item in candidates:
        content = item.get("content")
        if (
            isinstance(content, str)
            and item.get("source_id") == row.get("matched_target_id")
            and hashlib.sha256(content.encode()).hexdigest()
            == row.get("payload_sha256")
        ):
            return
    raise ValueError("direct pipeline class lacks its matching provider payload")


def _check_classification_provenance(
    row: Mapping[str, object], expected: RunProvenance
) -> None:
    if row.get("status") == "not_applicable":
        if not row.get("reason"):
            raise ValueError("unclassified pipeline row has no reason")
        return
    if not {field.name for field in fields(ClassificationResult)}.issubset(row):
        raise ValueError("incomplete pipeline classification result schema")
    require_values(
        mapping(row.get("provenance")),
        {
            "snapshot_id": expected.snapshot_id,
            "normalization_version": expected.normalization_version,
            "rules_version": expected.rules_version,
            "schema_version": expected.schema_version,
            "retrieved_at": expected.retrieved_at,
        },
    )


def validate_row_outputs(
    outputs: Mapping[str, bytes], *, row_id: str, run_id: str, provenance: RunProvenance
) -> None:
    """Require exactly one row, its children, executed versions and resolved links."""
    classification = records(outputs[_CLASSIFICATION_JSON])
    if len(classification) != 1:
        raise ValueError("pipeline artifact needs exactly one classification row")
    row = classification[0]
    require_values(row, {"input_row_id": row_id})
    children = {
        name: records(outputs[name])
        for name in OUTPUT_NAMES - {_CLASSIFICATION_JSON, _METRICS_JSON}
    }
    for items in children.values():
        for item in items:
            require_values(item, {"input_row_id": row_id})
    metrics = document(outputs[_METRICS_JSON])
    if type(metrics.get("rows")) is not int or metrics["rows"] != 1:
        raise ValueError("pipeline row metrics count differs")
    known = _known_evidence(children["evidence.json"], row_id, run_id)
    _check_links(row, known)
    _check_diagnostics(children["diagnostics.json"], known)
    embedded = row.get("diagnostics", [])
    if not isinstance(embedded, list):
        raise ValueError("invalid embedded pipeline diagnostics")
    _check_diagnostics([mapping(item) for item in embedded], known)
    _check_direct(row, known)
    _check_classification_provenance(row, provenance)
