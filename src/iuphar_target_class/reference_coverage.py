"""Pinned V2 reviewed-case scope and mandatory scenario dispositions.

This checks the supplied reviewed evidence, never creates a reviewer decision or
infers expected labels from a classifier result. Acceptance remains bounded.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote, urlsplit

from .stage0.io import sha256_file

if TYPE_CHECKING:
    from .models import RunProvenance
    from .pipeline import BatchResult, RowResult
    from .pipeline_acceptance import AdmittedCohort

REQUIRED_REFERENCE_CATEGORIES = (
    "direct_type",
    "direct_family",
    "partial_direct",
    "ambiguous",
    "unmatched",
    "identity_conflict",
    "taxonomy_boundary",
    "local_vs_direct",
    "non_applicable",
)
REQUIRED_REFERENCE_FIELDS = frozenset(
    {
        "match_status",
        "matched_target_id",
        "iuphar_class",
        "iuphar_annotation_status",
        "decision_status",
    }
)
SUPPORTED_REFERENCE_FIELDS = REQUIRED_REFERENCE_FIELDS | frozenset(
    {
        "local_class",
        "effective_class",
        "effective_source",
        "local_status",
        "iuphar_mapping_rule_id",
        "input_validation_status",
        "conflict_codes",
    }
)
_DISPOSITIONS = frozenset({"real_reference", "engineering_only", "out_of_scope"})


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("reference coverage requires a JSON object")
    return cast("Mapping[str, object]", value)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or "[...]" in value:
        raise ValueError("explicit reviewed reference text required")
    return value


def _sha(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("reference coverage requires pinned SHA-256 values")
    return value


def _strings(value: object, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("reference coverage requires an explicit string list")
    result = tuple(_text(item) for item in value)
    if len(result) != len(set(result)) or (nonempty and not result):
        raise ValueError(
            "reference coverage list must be distinct and explicitly populated"
        )
    return result


def _references(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(
            "scenario disposition needs independently supplied proof references"
        )
    references = tuple(_mapping(item) for item in value)
    for reference in references:
        _text(reference.get("path"))
        _sha(reference.get("sha256"))
    return references


def _scope(value: object) -> Mapping[str, object]:
    scope = _mapping(value)
    for key in ("scope_id", "approval_reference"):
        _text(scope.get(key))
    if scope.get("kind") != "bounded_reviewed_reference":
        raise ValueError(
            "reference acceptance needs an explicitly bounded reviewed scope"
        )
    _strings(scope.get("limitations"), nonempty=True)
    return scope


def _matrix(value: object) -> Mapping[str, object]:
    matrix = _mapping(value)
    if set(matrix) != set(REQUIRED_REFERENCE_CATEGORIES):
        raise ValueError(
            "all mandatory reference categories need a reviewed disposition"
        )
    for category in REQUIRED_REFERENCE_CATEGORIES:
        _disposition(category, _mapping(matrix[category]))
    return matrix


def _disposition(category: str, item: Mapping[str, object]) -> None:
    if item.get("status") not in _DISPOSITIONS:
        raise ValueError(f"unknown reference disposition: {category}")
    _text(item.get("rationale"))
    ids = _strings(item.get("case_row_ids"))
    _references(item.get("source_references"))
    if item["status"] == "real_reference" and not ids:
        raise ValueError("real reference category needs reviewed cases")
    if item["status"] == "out_of_scope" and ids:
        raise ValueError(
            "out-of-scope categories cannot claim executed reference cases"
        )


def validate_reference_coverage_receipt(document: Mapping[str, object]) -> None:
    """Validate the pure frozen V2 receipt contract for enrich admission."""
    _validate_bounded_coverage(document)
    _validate_artifact_references(document)


def _validate_bounded_coverage(document: Mapping[str, object]) -> None:
    if document.get("schema_version") != 2:
        raise ValueError("bounded reference acceptance requires receipt schema 2")
    for key in ("cohort_manifest_sha256", "conversion_ledger_sha256"):
        _sha(document.get(key))
    scope = _scope(document.get("scope_declaration"))
    coverage = _mapping(document.get("reference_coverage"))
    if coverage.get("schema_version") != 2:
        raise ValueError("reference coverage schema must be 2")
    reviewed = _strings(coverage.get("reviewed_row_ids"), nonempty=True)
    unreviewed = _strings(coverage.get("unreviewed_row_ids"))
    if (reviewed, unreviewed) != (
        _strings(scope.get("reviewed_row_ids"), nonempty=True),
        _strings(scope.get("unreviewed_row_ids")),
    ):
        raise ValueError(
            "executed reference coverage differs from the frozen pre-run scope"
        )
    _coverage_partition(coverage.get("cohort_row_count"), reviewed, unreviewed)
    matrix = _matrix(coverage.get("categories"))
    real_ids = set().union(
        *(
            set(_strings(_mapping(item)["case_row_ids"]))
            for item in matrix.values()
            if _mapping(item)["status"] == "real_reference"
        )
    )
    if real_ids != set(reviewed):
        raise ValueError(
            "reviewed reference coverage differs from the declared real cases"
        )
    if (
        document.get("scientific_status") != "bounded_reference_cases_only"
        or document.get("biological_accuracy_accepted") is not False
    ):
        raise ValueError("reference receipt cannot claim broad biological accuracy")


def _coverage_partition(
    count: object, reviewed: tuple[str, ...], unreviewed: tuple[str, ...]
) -> None:
    if type(count) is not int or count <= 0:
        raise ValueError("reference cohort row count must be positive")
    if set(reviewed).intersection(unreviewed) or count != len(reviewed) + len(
        unreviewed
    ):
        raise ValueError(
            "reference scope must account for the complete cohort without overlaps"
        )


def validate_reference_specification(
    spec: Mapping[str, object],
    *,
    cohort: AdmittedCohort,
    provenance: RunProvenance,
    root: Path,
) -> dict[str, object]:
    """Verify the pre-run scope, identities and all independently supplied proofs."""
    if cohort.schema_version != 2:
        raise ValueError("reference specification V2 requires Stage-0 V2 admission")
    _same_versions(spec, provenance)
    if (spec.get("cohort_manifest_sha256"), spec.get("conversion_ledger_sha256")) != (
        cohort.cohort_manifest_sha256,
        cohort.conversion_ledger_sha256,
    ):
        raise ValueError(
            "reference cases belong to another canonical cohort or conversion"
        )
    scope = _scope(spec.get("scope_declaration"))
    matrix = _matrix(spec.get("reference_matrix"))
    cases = _case_index(spec.get("cases"))
    reviewed = _strings(scope.get("reviewed_row_ids"), nonempty=True)
    unreviewed = _strings(scope.get("unreviewed_row_ids"))
    ids = {row.input_row_id for row in cohort.rows}
    if set(reviewed) | set(unreviewed) != ids or not set(cases).issubset(ids):
        raise ValueError("declared reference scope differs from the admitted cohort")
    _verify_matrix_cases(matrix, cases, root)
    receipt: dict[str, object] = {
        "schema_version": 2,
        "cohort_manifest_sha256": cohort.cohort_manifest_sha256,
        "conversion_ledger_sha256": cohort.conversion_ledger_sha256,
        "scope_declaration": dict(scope),
        "scientific_status": "bounded_reference_cases_only",
        "biological_accuracy_accepted": False,
        "reference_coverage": {
            "schema_version": 2,
            "cohort_row_count": len(ids),
            "reviewed_row_ids": list(reviewed),
            "unreviewed_row_ids": list(unreviewed),
            "categories": dict(matrix),
        },
    }
    _validate_bounded_coverage(receipt)
    return receipt


def _validate_artifact_references(document: Mapping[str, object]) -> None:
    references = document.get("artifact_references")
    if not isinstance(references, list):
        raise ValueError("reference receipt needs replayable artifact references")
    indexed: dict[str, list[Mapping[str, object]]] = {}
    for item in references:
        reference = _mapping(item)
        kind = _text(reference.get("kind"))
        uri = urlsplit(_text(reference.get("immutable_uri")))
        if uri.scheme != "file" or uri.netloc not in {"", "localhost"} or not uri.path:
            raise ValueError(
                "reference artifacts require actual local immutable file URIs"
            )
        if any(
            part.lower() == ".env"
            or part.lower().startswith(".env.")
            or part.lower().endswith(".env")
            for part in PurePosixPath(unquote(uri.path)).parts
        ):
            raise ValueError(
                "environment files cannot enter a replayable acceptance bundle"
            )
        _sha(reference.get("sha256"))
        indexed.setdefault(kind, []).append(reference)
    _required_artifact_identities(document, indexed)


def _required_artifact_identities(
    document: Mapping[str, object], indexed: Mapping[str, list[Mapping[str, object]]]
) -> None:
    bindings = {
        "stage0_manifest": "stage0_manifest_sha256",
        "expected_labels": "expected_labels_sha256",
        "cohort_manifest": "cohort_manifest_sha256",
        "conversion_ledger": "conversion_ledger_sha256",
        "pipeline_proof": "pipeline_proof_sha256",
        "pipeline_report": "pipeline_report_sha256",
    }
    for kind, key in bindings.items():
        _single_bound_reference(indexed, kind, _sha(document.get(key)))
    outputs = _mapping(document.get("output_sha256"))
    names = {
        "classification.json",
        "evidence.json",
        "candidates.json",
        "components.json",
        "diagnostics.json",
        "metrics.json",
    }
    if set(outputs) != names:
        raise ValueError("reference receipt must bind all six output byte files")
    for name in names:
        _single_bound_reference(indexed, name, _sha(outputs[name]))


def _single_bound_reference(
    indexed: Mapping[str, list[Mapping[str, object]]], kind: str, digest: str
) -> None:
    matches = indexed.get(kind, [])
    if len(matches) != 1 or matches[0]["sha256"] != digest:
        raise ValueError(f"missing or mismatched replayable reference: {kind}")


def _same_versions(spec: Mapping[str, object], provenance: RunProvenance) -> None:
    observed = tuple(
        spec.get(key)
        for key in (
            "normalization_version",
            "rules_version",
            "classification_schema_version",
            "matching_policy_version",
        )
    )
    if observed != (
        provenance.normalization_version,
        provenance.rules_version,
        provenance.schema_version,
        provenance.matching_policy_version,
    ):
        raise ValueError("reference profile versions differ from executing code")


def _case_index(value: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("reference specification needs explicit reviewed cases")
    result: dict[str, Mapping[str, object]] = {}
    for raw in value:
        case = _mapping(raw)
        key = _text(case.get("input_row_id"))
        if key in result:
            raise ValueError("duplicate reference case identity")
        result[key] = case
    return result


def _verify_matrix_cases(
    matrix: Mapping[str, object], cases: Mapping[str, Mapping[str, object]], root: Path
) -> None:
    for category, raw in matrix.items():
        item = _mapping(raw)
        _verify_proof_bytes(_references(item["source_references"]), root)
        for row_id in _strings(item["case_row_ids"]):
            if row_id not in cases:
                raise ValueError("scenario matrix refers to an absent case")
            case = cases[row_id]
            _verify_case_fields(case, category, _text(item["status"]))
            _verify_proof_bytes(_references(case.get("source_references")), root)


def _verify_case_fields(case: Mapping[str, object], category: str, status: str) -> None:
    if (
        category not in _strings(case.get("categories"))
        or case.get("reference_status") != status
    ):
        raise ValueError(
            "reference case disposition differs from its pre-run scenario matrix"
        )
    expected = _mapping(case.get("expected"))
    if not set(expected).issubset(SUPPORTED_REFERENCE_FIELDS):
        raise ValueError("unsupported reference expectation field")
    if status == "real_reference" and not REQUIRED_REFERENCE_FIELDS.issubset(expected):
        raise ValueError(
            "real reference cases need complete direct/match/annotation/decision expectations"
        )
    _category_expectations(category, status, expected)


def _category_expectations(
    category: str, status: str, expected: Mapping[str, object]
) -> None:
    if status != "real_reference":
        return
    fields = {
        "local_vs_direct": frozenset(
            {"local_class", "effective_class", "effective_source"}
        ),
        "non_applicable": frozenset({"input_validation_status"}),
    }.get(category, frozenset())
    if not fields.issubset(expected):
        raise ValueError(
            "real reference case lacks its mandatory category-specific expectations"
        )


def _verify_proof_bytes(
    references: tuple[Mapping[str, object], ...], root: Path
) -> None:
    for reference in references:
        path = (root / _text(reference["path"])).resolve()
        if not path.is_relative_to(root.resolve()) or path == root.resolve():
            raise ValueError("reviewed reference proof escapes its specification root")
        if sha256_file(path) != reference["sha256"]:
            raise ValueError("reviewed reference proof digest mismatch")


def validate_executed_reference_coverage(
    batch: BatchResult, spec: Mapping[str, object]
) -> None:
    """Require each declared scenario to occur, rather than trusting case tags."""
    rows = {row.result.input_row_id: row for row in batch.rows}
    matrix = _matrix(spec.get("reference_matrix"))
    for category, raw in matrix.items():
        item = _mapping(raw)
        for row_id in _strings(item["case_row_ids"]):
            if row_id not in rows or not _scenario_occurs(category, rows[row_id], spec):
                raise AssertionError(
                    f"declared reference scenario did not execute: {category}/{row_id}"
                )


def _scenario_occurs(category: str, row: RowResult, spec: Mapping[str, object]) -> bool:
    result = row.result
    rules = {
        "direct_type": bool(
            (result.iuphar_mapping_rule_id or "").startswith("iuphar_type:")
        ),
        "direct_family": bool(
            (result.iuphar_mapping_rule_id or "").startswith("iuphar_family:")
        ),
        "partial_direct": result.iuphar_annotation_status == "partial"
        and result.iuphar_class is not None,
        "ambiguous": result.match_status == "ambiguous",
        "unmatched": result.match_status in {"not_found", "source_unavailable"},
        "identity_conflict": result.match_status == "identity_conflict",
        "local_vs_direct": result.local_class is not None
        and result.iuphar_class is not None,
        "non_applicable": result.input_validation_status == "invalid_input",
    }
    if category == "taxonomy_boundary":
        taxa = _strings(spec.get("taxonomy_scope"), nonempty=True)
        return row.validated.taxon not in taxa or any(
            "taxon" in item.code or "species" in item.code
            for item in result.diagnostics
        )
    return rules[category]


__all__ = [
    "REQUIRED_REFERENCE_CATEGORIES",
    "REQUIRED_REFERENCE_FIELDS",
    "SUPPORTED_REFERENCE_FIELDS",
    "validate_executed_reference_coverage",
    "validate_reference_coverage_receipt",
    "validate_reference_specification",
]
