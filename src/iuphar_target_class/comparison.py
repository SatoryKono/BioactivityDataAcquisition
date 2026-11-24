"""Stage-5 comparison and the separate M parity report.

An empty stage-0 set is not a quality measurement. ``m-parity-report.json``
compares the full result semantics. A matching top-level class is not a
biological-accuracy metric, and a free explanation string does not justify a
difference. Original M rows are never rewritten by this module.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

CHANGE_CATEGORIES: tuple[str, ...] = (
    "ec_fix",
    "false_other_removed",
    "ambiguity_found",
    "dictionary_change",
    "direct_local_separation",
    "new_or_unverified_logic",
)
# Raw identity columns shared by the input normalization contract. Result and
# provenance projections must not change the identity of an input row.
_IDENTITY_FIELDS = frozenset(
    {
        "input_row_id",
        "target_id",
        "uniprot",
        "gene_id",
        "gene_symbol",
        "organism",
        "isoform_id",
        "isoform_suffix",
        "target_kind",
    }
)


@dataclass(frozen=True, slots=True)
class Stage0Reference:
    """Rows named by the stage-0 manifest. This module does not replace them."""

    manifest_id: str
    selected_source_count: int
    m_rows: tuple[Mapping[str, str], ...]


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Counts stay null until M rows exist; metrics cover the whole Python run."""

    measured: bool
    reason: str
    changes: tuple[tuple[str, str, str], ...]
    residual: tuple[str, ...]
    metrics: dict[str, int] | None
    source_overwritten: bool
    legacy_values: tuple[tuple[str, str], ...]


def compare_stage0(
    reference: Stage0Reference,
    python_rows: tuple[Mapping[str, str], ...],
) -> ComparisonReport:
    """Join on the full identity key and leave the M rows untouched.

    Metrics describe every supplied Python row, including duplicate and orphan
    rows. Changes and residuals describe the identity join separately; missing
    historical decision fields are not invented as unchanged values.
    """
    if not reference.m_rows:
        return ComparisonReport(
            False,
            "эталонный набор этапа 0 не содержит строк M",
            (),
            (),
            None,
            False,
            (),
        )
    grouped_m = _group(reference.m_rows)
    grouped_python = _group(python_rows)
    changes: list[tuple[str, str, str]] = []
    residual: list[str] = []
    legacy: list[tuple[str, str]] = []
    for key in sorted(set(grouped_m) | set(grouped_python)):
        _classify_key(
            key,
            grouped_m.get(key, ()),
            grouped_python.get(key, ()),
            changes,
            residual,
            legacy,
        )
    return ComparisonReport(
        True,
        "строки M и Python сопоставлены по полному ключу",
        tuple(sorted(changes)),
        tuple(sorted(set(residual))),
        _metrics(python_rows),
        False,
        tuple(sorted(legacy)),
    )


def _classify_key(
    key: tuple[tuple[str, str], ...],
    m_group: tuple[Mapping[str, str], ...],
    python_group: tuple[Mapping[str, str], ...],
    changes: list[tuple[str, str, str]],
    residual: list[str],
    legacy: list[tuple[str, str]],
) -> None:
    """Record one identity key. Duplicates and unexplained gaps stay residual."""
    label = _label(key)
    m_row = m_group[0] if len(m_group) == 1 else None
    _record_legacy(label, m_row, legacy)
    if len(m_group) > 1 or len(python_group) > 1:
        residual.append(label)
        return
    python_row = python_group[0] if python_group else None
    if not key or m_row is None or python_row is None:
        residual.append(label)
        return
    if _same_classification(m_row, python_row):
        return
    _record_difference(label, python_row, changes, residual)


# Stage-5 equality. The legacy class alias stays in ``_class``; a missing
# historical column is not treated as equal to a present value.
_STAGE0_FIELDS: tuple[str, ...] = (
    "candidate_target_ids",
    "capability",
    "conflict_codes",
    "decision_status",
    "effective_class",
    "effective_source",
    "effective_subclasses",
    "family_ids",
    "iuphar_annotation_status",
    "iuphar_class_candidates",
    "iuphar_family_ids",
    "iuphar_family_paths",
    "iuphar_subclass",
    "matched_target_id",
    "iuphar_type_raw",
    "input_errors",
    "input_validation_status",
    "local_candidates",
    "local_class",
    "local_status",
    "iuphar_mapping_rule_id",
    "iuphar_mapping_version",
    "local_rule_ids",
    "local_subclasses",
    "match_status",
    "normalization_version",
    "provenance",
    "rules_version",
    "schema_version",
    "snapshot_id",
)


def _same_classification(
    m_row: Mapping[str, str], python_row: Mapping[str, str]
) -> bool:
    """Compare class, subclass, path, and decision projections.

    Missing historical values stay missing. They are not filled in from the
    Python row, and a shared top-level class does not hide another field.
    JSON lists compare in canonical order, so a path permutation is not a change.
    """
    return _class(m_row) == _class(python_row) and all(
        _observe(m_row, field) == _observe(python_row, field)
        for field in _STAGE0_FIELDS
    )


def _record_legacy(
    label: str,
    row: Mapping[str, str] | None,
    legacy: list[tuple[str, str]],
) -> None:
    if row is not None and "legacy_iuphar_class" in row:
        legacy.append((label, row["legacy_iuphar_class"]))


def _record_difference(
    label: str,
    python_row: Mapping[str, str],
    changes: list[tuple[str, str, str]],
    residual: list[str],
) -> None:
    """Keep an explained category. Anything else is residual, not a metric."""
    sign = python_row.get("change_sign", "")
    explanation = python_row.get("explanation", "")
    if sign in CHANGE_CATEGORIES and explanation:
        changes.append((label, sign, explanation))
        return
    residual.append(label)


def _identity_key(row: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted((name, value) for name, value in row.items() if name in _IDENTITY_FIELDS)
    )


def _group(
    rows: tuple[Mapping[str, str], ...],
) -> dict[tuple[tuple[str, str], ...], tuple[Mapping[str, str], ...]]:
    grouped: dict[tuple[tuple[str, str], ...], list[Mapping[str, str]]] = {}
    for row in rows:
        grouped.setdefault(_identity_key(row), []).append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _class(row: Mapping[str, str]) -> str:
    return row.get("iuphar_class", row.get("legacy_iuphar_class", ""))


def _label(key: tuple[tuple[str, str], ...]) -> str:
    return "|".join(f"{name}={value}" for name, value in key) or "<missing identity>"


def _metrics(rows: tuple[Mapping[str, str], ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for field_name in ("match_status", "effective_source", "decision_status"):
            value = row.get(field_name, "")
            name = f"{field_name}:{value or 'null'}"
            counts[name] = counts.get(name, 0) + 1
        if not row.get("effective_class"):
            status = row.get("decision_status", "") or "null"
            name = f"null_class:{status}"
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


M_PARITY_SCHEMA_VERSION = "iuphar-m-parity-report-v1"
M_PARITY_REPORT_ARTIFACT = "m-parity-report"
M_PARITY_REPORT_FILENAME = "m-parity-report.json"
PARITY_BASIS_CATEGORIES: tuple[str, ...] = (
    "ambiguity_found",
    "dictionary_change",
    "dictionary_release",
    "direct_local_separation",
    "ec_fix",
    "false_other_removed",
    "new_or_unverified_logic",
    "nondeterministic_dedup_removed",
)
FIELD_GROUPS: dict[str, str] = {
    "candidate_target_ids": "candidates",
    "capability": "capability",
    "conflict_codes": "local_effective",
    "decision_status": "local_effective",
    "effective_class": "local_effective",
    "effective_source": "local_effective",
    "effective_subclasses": "subclasses",
    "family_ids": "families_paths",
    "iuphar_annotation_status": "local_effective",
    "iuphar_class": "class",
    "iuphar_class_candidates": "candidates",
    "iuphar_family_ids": "families_paths",
    "iuphar_family_paths": "families_paths",
    "matched_target_id": "matched_target",
    "iuphar_mapping_rule_id": "provenance",
    "iuphar_mapping_version": "provenance",
    "iuphar_subclass": "subclasses",
    "iuphar_type_raw": "raw_type",
    "input_errors": "local_effective",
    "input_validation_status": "local_effective",
    "legacy_iuphar_class": "class",
    "local_candidates": "candidates",
    "local_class": "local_effective",
    "local_rule_ids": "provenance",
    "local_status": "local_effective",
    "local_subclasses": "subclasses",
    "match_status": "local_effective",
    "normalization_version": "provenance",
    "provenance": "provenance",
    "rules_version": "provenance",
    "schema_version": "provenance",
    "snapshot_id": "provenance",
}
COMPARED_FIELDS: tuple[str, ...] = tuple(sorted(FIELD_GROUPS))
PROOF_VERIFICATION_ARTIFACTS: frozenset[str] = frozenset(
    {
        "acceptance.json",
        "candidates.json",
        "classification.json",
        "components.json",
        "diagnostics.json",
        "evidence.json",
        "execution-config.json",
        "metrics.json",
        "stage_report.json",
        "stages_0_3_report.json",
        "volume-result.json",
    }
)
_LIST_FIELDS = frozenset(
    {
        "candidate_target_ids",
        "conflict_codes",
        "effective_subclasses",
        "family_ids",
        "iuphar_class_candidates",
        "iuphar_family_ids",
        "iuphar_family_paths",
        "input_errors",
        "local_candidates",
        "local_rule_ids",
        "local_subclasses",
    }
)
_SOURCE_PAIRS = frozenset(
    {
        "independent_reference:new_result",
        "original_m:control_run",
        "original_m:new_result",
        "saved_excel:new_result",
    }
)
_DIFF_SORT = (
    "target_id",
    "input_row_id",
    "field",
    "old_value",
    "new_value",
    "disposition",
    "basis_id",
)


@dataclass(frozen=True, slots=True)
class DifferenceBasis:
    """One allowable difference registered before the run.

    ``basis_sha256`` is the canonical hash of the registration. A later free
    text reason cannot stand in for this record.
    """

    basis_id: str
    category: str
    statement: str
    field: str
    source_pair: str
    target_id: str
    basis_sha256: str


@dataclass(frozen=True, slots=True)
class BasisSeal:
    """Allowable differences fixed before result rows are compared.

    ``basis_set_sha256`` covers the canonical basis list. A basis added or
    edited after the seal does not match and cannot qualify a difference.
    """

    basis_set_sha256: str
    bases: tuple[DifferenceBasis, ...]


@dataclass(frozen=True, slots=True)
class ParityInputs:
    """Separated M, Excel, new result, reference, and optional control run."""

    original_m: tuple[Mapping[str, str], ...]
    new_result: tuple[Mapping[str, str], ...]
    saved_excel: tuple[Mapping[str, str], ...] | None = None
    independent_reference: tuple[Mapping[str, str], ...] | None = None
    control_run: tuple[Mapping[str, str], ...] | None = None
    basis_seal: BasisSeal | None = None


@dataclass(frozen=True, slots=True)
class ParityPublication:
    """Historical rows and the seal fixed before a pipeline run.

    The new result is the batch the pipeline just classified. This record does
    not carry that batch, so the seal cannot be assembled from its output.
    """

    original_m: tuple[Mapping[str, str], ...]
    basis_seal: BasisSeal
    saved_excel: tuple[Mapping[str, str], ...] | None = None
    independent_reference: tuple[Mapping[str, str], ...] | None = None
    control_run: tuple[Mapping[str, str], ...] | None = None


@dataclass(slots=True)
class _Availability:
    historical_present: int = 0
    historical_unavailable: int = 0
    new_present: int = 0
    new_unavailable: int = 0


@dataclass(frozen=True, slots=True)
class _KeyOutcome:
    differences: tuple[dict[str, object], ...]
    class_agreement: int
    class_disagreement: int
    availability: tuple[tuple[str, str, str], ...]


def register_difference_basis(
    *,
    basis_id: str,
    category: str,
    statement: str,
    field: str,
    source_pair: str,
    target_id: str = "",
) -> DifferenceBasis:
    """Register one pre-run ground and return its content hash."""
    _require_basis_text(basis_id, statement, source_pair)
    if source_pair not in _SOURCE_PAIRS:
        message = f"пара источников не входит в перечень: {source_pair}"
        raise ValueError(message)
    if category not in PARITY_BASIS_CATEGORIES:
        message = f"категория не входит в перечень: {category}"
        raise ValueError(message)
    if field not in set(COMPARED_FIELDS) | {"identity"}:
        message = f"поле не сравнивается: {field}"
        raise ValueError(message)
    payload = {
        "basis_id": basis_id,
        "category": category,
        "field": field,
        "source_pair": source_pair,
        "statement": statement,
        "target_id": target_id,
    }
    return DifferenceBasis(
        basis_id=basis_id,
        category=category,
        statement=statement,
        field=field,
        source_pair=source_pair,
        target_id=target_id,
        basis_sha256=_sha256_bytes(_canonical_json_bytes(payload)),
    )


def seal_difference_bases(bases: tuple[DifferenceBasis, ...]) -> BasisSeal:
    """Seal a basis list. Later additions are rejected against this hash."""
    verified = _verified_bases(bases)
    digest = _sha256_bytes(
        _canonical_json_bytes([_basis_document(basis) for basis in verified])
    )
    return BasisSeal(basis_set_sha256=digest, bases=verified)


def recompute_m_copy(
    rows: tuple[Mapping[str, str], ...],
    transform: Callable[[tuple[dict[str, str], ...]], tuple[Mapping[str, str], ...]],
) -> tuple[dict[str, str], ...]:
    """Run ``transform`` on a copy. Original row objects are restored on mutation."""
    before = _freeze_rows(rows)
    copied = _freeze_rows(rows)
    mutated = False
    try:
        produced = transform(copied)
    finally:
        if _freeze_rows(rows) != before:
            _restore_rows(rows, before)
            mutated = True
    if mutated:
        message = "исходные строки M изменены"
        raise RuntimeError(message)
    return _freeze_rows(produced)


def build_m_parity_report(inputs: ParityInputs) -> dict[str, object]:
    """Build a deterministic parity document. Original rows stay untouched."""
    bases = _bases_from_seal(inputs.basis_seal)
    comparisons = [
        _compare_named(
            "original_m",
            inputs.original_m,
            "new_result",
            inputs.new_result,
            bases,
            intersection_only=False,
        )
    ]
    comparisons.extend(_optional_comparisons(inputs, bases))
    ordered = sorted(comparisons, key=lambda item: str(item["pair"]))
    return {
        "artifact": M_PARITY_REPORT_ARTIFACT,
        "basis_set_sha256": None
        if inputs.basis_seal is None
        else inputs.basis_seal.basis_set_sha256,
        "bases": [_basis_document(basis) for basis in bases],
        "biological_accuracy": None,
        "biological_accuracy_accepted": False,
        "class_agreement_is_biological_accuracy": False,
        "comparisons": ordered,
        "schema_version": M_PARITY_SCHEMA_VERSION,
        "sources": {
            "control_run": _source_record(inputs.control_run),
            "independent_reference": _source_record(inputs.independent_reference),
            "new_result": _source_record(inputs.new_result),
            "original_m": _source_record(inputs.original_m),
            "saved_excel": _source_record(inputs.saved_excel),
        },
    }


def write_m_parity_report(report: Mapping[str, object], directory: Path) -> Path:
    """Atomically write ``m-parity-report.json`` without replacing proof artifacts."""
    if report.get("artifact") != M_PARITY_REPORT_ARTIFACT:
        message = "документ не является m-parity-report"
        raise ValueError(message)
    if M_PARITY_REPORT_FILENAME in PROOF_VERIFICATION_ARTIFACTS:
        message = "имя отчёта пересекается с proof verification"
        raise RuntimeError(message)
    destination = directory / M_PARITY_REPORT_FILENAME
    if destination.name in PROOF_VERIFICATION_ARTIFACTS:
        message = "m-parity report must not replace a proof artifact"
        raise ValueError(message)
    _atomic_write_bytes(destination, _canonical_json_bytes(report), root=directory)
    return destination


def _require_basis_text(basis_id: str, statement: str, source_pair: str) -> None:
    if basis_id.strip() and statement.strip() and source_pair.strip():
        return
    message = "основание должно быть задано до запуска"
    raise ValueError(message)


def _optional_comparisons(
    inputs: ParityInputs, bases: tuple[DifferenceBasis, ...]
) -> list[dict[str, object]]:
    comparisons: list[dict[str, object]] = []
    if inputs.saved_excel is not None:
        comparisons.append(
            _compare_named(
                "saved_excel",
                inputs.saved_excel,
                "new_result",
                inputs.new_result,
                bases,
                intersection_only=False,
            )
        )
    if inputs.independent_reference is not None:
        comparisons.append(
            _compare_named(
                "independent_reference",
                inputs.independent_reference,
                "new_result",
                inputs.new_result,
                bases,
                intersection_only=False,
            )
        )
    if inputs.control_run is not None:
        comparisons.append(
            _compare_named(
                "original_m",
                inputs.original_m,
                "control_run",
                inputs.control_run,
                bases,
                intersection_only=True,
            )
        )
    return comparisons


def _bases_from_seal(seal: BasisSeal | None) -> tuple[DifferenceBasis, ...]:
    if seal is None:
        return ()
    verified = _verified_bases(seal.bases)
    digest = _sha256_bytes(
        _canonical_json_bytes([_basis_document(basis) for basis in verified])
    )
    if digest != seal.basis_set_sha256:
        message = "печать оснований не совпадает с каноническим перечнем"
        raise ValueError(message)
    return verified


def _verified_bases(
    bases: tuple[DifferenceBasis, ...],
) -> tuple[DifferenceBasis, ...]:
    verified: list[DifferenceBasis] = []
    seen: set[str] = set()
    for basis in bases:
        fresh = register_difference_basis(
            basis_id=basis.basis_id,
            category=basis.category,
            statement=basis.statement,
            field=basis.field,
            source_pair=basis.source_pair,
            target_id=basis.target_id,
        )
        if fresh.basis_sha256 != basis.basis_sha256:
            message = "хеш основания не совпадает с канонической записью"
            raise ValueError(message)
        if basis.basis_id in seen:
            message = "повторяющийся идентификатор основания"
            raise ValueError(message)
        seen.add(basis.basis_id)
        verified.append(basis)
    return tuple(sorted(verified, key=lambda item: item.basis_id))


def _basis_document(basis: DifferenceBasis) -> dict[str, object]:
    return {
        "basis_id": basis.basis_id,
        "basis_sha256": basis.basis_sha256,
        "category": basis.category,
        "field": basis.field,
        "source_pair": basis.source_pair,
        "statement": basis.statement,
        "target_id": basis.target_id,
    }


def _compare_named(
    left_name: str,
    left_rows: tuple[Mapping[str, str], ...] | None,
    right_name: str,
    right_rows: tuple[Mapping[str, str], ...] | None,
    bases: tuple[DifferenceBasis, ...],
    *,
    intersection_only: bool,
) -> dict[str, object]:
    pair = f"{left_name}:{right_name}"
    if left_rows is None or right_rows is None:
        return _unmeasured(pair, "источник не предоставлен", intersection_only, ())
    left = _freeze_rows(left_rows)
    right = _freeze_rows(right_rows)
    outside: tuple[str, ...] = ()
    if intersection_only:
        left, right, outside = _intersection(left, right)
    if not left and not right:
        return _unmeasured(
            pair, "пересечение источников пусто", intersection_only, outside
        )
    if not left:
        return _unmeasured(
            pair, "эталонный набор не содержит строк", intersection_only, outside
        )
    return _measure(pair, left, right, bases, intersection_only, outside)


def _intersection(
    left: tuple[dict[str, str], ...], right: tuple[dict[str, str], ...]
) -> tuple[tuple[dict[str, str], ...], tuple[dict[str, str], ...], tuple[str, ...]]:
    shared = set(_group(left)) & set(_group(right))
    outside = tuple(
        sorted(_label(key) for key in (set(_group(left)) | set(_group(right))) - shared)
    )
    left_shared = tuple(row for row in left if _identity_key(row) in shared)
    right_shared = tuple(row for row in right if _identity_key(row) in shared)
    return left_shared, right_shared, outside


def _measure(
    pair: str,
    left: tuple[dict[str, str], ...],
    right: tuple[dict[str, str], ...],
    bases: tuple[DifferenceBasis, ...],
    intersection_only: bool,
    outside: tuple[str, ...],
) -> dict[str, object]:
    grouped_left = _group(left)
    grouped_right = _group(right)
    differences: list[dict[str, object]] = []
    class_agreement = 0
    class_disagreement = 0
    counts = {field: _Availability() for field in COMPARED_FIELDS}
    for key in sorted(set(grouped_left) | set(grouped_right)):
        outcome = _classify_parity_key(key, grouped_left, grouped_right, pair, bases)
        differences.extend(outcome.differences)
        class_agreement += outcome.class_agreement
        class_disagreement += outcome.class_disagreement
        _note_availability(counts, outcome.availability)
    return _measured_document(
        pair,
        differences,
        class_agreement,
        class_disagreement,
        counts,
        intersection_only,
        outside,
    )


def _classify_parity_key(
    key: tuple[tuple[str, str], ...],
    grouped_left: Mapping[tuple[tuple[str, str], ...], tuple[Mapping[str, str], ...]],
    grouped_right: Mapping[tuple[tuple[str, str], ...], tuple[Mapping[str, str], ...]],
    pair: str,
    bases: tuple[DifferenceBasis, ...],
) -> _KeyOutcome:
    left_group = grouped_left.get(key, ())
    right_group = grouped_right.get(key, ())
    target_id = _key_value(key, "target_id")
    input_row_id = _key_value(key, "input_row_id")
    if key and len(left_group) == 1 and len(right_group) == 1:
        return _compare_singleton(
            left_group[0],
            right_group[0],
            pair,
            bases,
            target_id,
            input_row_id,
        )
    return _irregular_key(
        key, left_group, right_group, pair, bases, target_id, input_row_id
    )


def _compare_singleton(
    left: Mapping[str, str],
    right: Mapping[str, str],
    pair: str,
    bases: tuple[DifferenceBasis, ...],
    target_id: str,
    input_row_id: str,
) -> _KeyOutcome:
    post_hoc = _post_hoc(right)
    differences: list[dict[str, object]] = []
    availability: list[tuple[str, str, str]] = []
    for field in COMPARED_FIELDS:
        left_availability, left_value = _observe(left, field)
        right_availability, right_value = _observe(right, field)
        availability.append((field, left_availability, right_availability))
        difference = _field_difference(
            field,
            left_availability,
            left_value,
            right_availability,
            right_value,
            pair,
            bases,
            target_id,
            input_row_id,
            post_hoc,
        )
        if difference is not None:
            differences.append(difference)
    agreement, disagreement = _class_counts(left, right)
    return _KeyOutcome(tuple(differences), agreement, disagreement, tuple(availability))


def _field_difference(
    field: str,
    left_availability: str,
    left_value: str | None,
    right_availability: str,
    right_value: str | None,
    pair: str,
    bases: tuple[DifferenceBasis, ...],
    target_id: str,
    input_row_id: str,
    post_hoc: bool,
) -> dict[str, object] | None:
    if left_availability == "unavailable" and right_availability == "unavailable":
        return None
    if (
        left_availability == "present"
        and right_availability == "present"
        and left_value == right_value
    ):
        return None
    basis: DifferenceBasis | None = None
    if left_availability == "unavailable":
        disposition = "historical_unavailable"
    elif right_availability == "unavailable":
        disposition = "new_unavailable"
    else:
        basis = _select_basis(bases, pair, field, target_id)
        disposition = "allowed" if basis is not None else "unexplained"
    return _difference_record(
        field=field,
        group=FIELD_GROUPS[field],
        old_value=left_value,
        new_value=right_value,
        historical_availability=left_availability,
        new_availability=right_availability,
        disposition=disposition,
        basis=basis,
        target_id=target_id,
        input_row_id=input_row_id,
        post_hoc=post_hoc,
    )


def _irregular_key(
    key: tuple[tuple[str, str], ...],
    left_group: tuple[Mapping[str, str], ...],
    right_group: tuple[Mapping[str, str], ...],
    pair: str,
    bases: tuple[DifferenceBasis, ...],
    target_id: str,
    input_row_id: str,
) -> _KeyOutcome:
    duplicate = len(left_group) > 1 or len(right_group) > 1
    old_value, new_value = _irregular_values(
        left_group, right_group, _label(key), duplicate
    )
    basis = _identity_basis(bases, pair, target_id, left_group, right_group)
    disposition = "allowed" if basis is not None else "unexplained"
    difference = _difference_record(
        field="identity",
        group="identity",
        old_value=old_value,
        new_value=new_value,
        historical_availability="present" if left_group else "unavailable",
        new_availability="present" if right_group else "unavailable",
        disposition=disposition,
        basis=basis,
        target_id=target_id,
        input_row_id=input_row_id,
        post_hoc=_group_post_hoc(right_group),
    )
    differences = [difference]
    availability: tuple[tuple[str, str, str], ...] = ()
    if len(left_group) > 1 and len(right_group) == 1:
        survivor = _compare_singleton(
            _closest_historical_row(left_group, right_group[0]),
            right_group[0],
            pair,
            bases,
            target_id,
            input_row_id,
        )
        differences.extend(survivor.differences)
        availability = survivor.availability
    return _KeyOutcome(tuple(differences), 0, 0, availability)


def _irregular_values(
    left_group: tuple[Mapping[str, str], ...],
    right_group: tuple[Mapping[str, str], ...],
    label: str,
    duplicate: bool,
) -> tuple[str | None, str | None]:
    if duplicate:
        old_value = _group_signature(left_group) if left_group else None
        new_value = _group_signature(right_group) if right_group else None
        return old_value, new_value
    old_value = label if left_group else None
    new_value = label if right_group else None
    return old_value, new_value


def _class_counts(left: Mapping[str, str], right: Mapping[str, str]) -> tuple[int, int]:
    """Count a class match only when both sides actually carry ``iuphar_class``."""
    if "iuphar_class" not in left or "iuphar_class" not in right:
        return 0, 0
    left_value = _canonical_field_value("iuphar_class", left["iuphar_class"])
    right_value = _canonical_field_value("iuphar_class", right["iuphar_class"])
    if left_value == right_value:
        return 1, 0
    return 0, 1


def _identity_basis(
    bases: tuple[DifferenceBasis, ...],
    pair: str,
    target_id: str,
    left_group: tuple[Mapping[str, str], ...],
    right_group: tuple[Mapping[str, str], ...],
) -> DifferenceBasis | None:
    """A dedup basis covers a collapse to one surviving row, not a lost target."""
    basis = _select_basis(bases, pair, "identity", target_id)
    if basis is None:
        return None
    if basis.category != "nondeterministic_dedup_removed":
        return basis
    if len(left_group) > 1 and len(right_group) == 1:
        return basis
    return None


def _select_basis(
    bases: tuple[DifferenceBasis, ...], pair: str, field: str, target_id: str
) -> DifferenceBasis | None:
    matches = [
        basis
        for basis in bases
        if basis.source_pair == pair
        and basis.field == field
        and basis.target_id in ("", target_id)
    ]
    if not matches:
        return None
    return min(matches, key=lambda item: (item.target_id == "", item.basis_id))


def _difference_record(
    *,
    field: str,
    group: str,
    old_value: str | None,
    new_value: str | None,
    historical_availability: str,
    new_availability: str,
    disposition: str,
    basis: DifferenceBasis | None,
    target_id: str,
    input_row_id: str,
    post_hoc: bool,
) -> dict[str, object]:
    return {
        "basis_id": None if basis is None else basis.basis_id,
        "basis_sha256": None if basis is None else basis.basis_sha256,
        "disposition": disposition,
        "field": field,
        "group": group,
        "historical_availability": historical_availability,
        "input_row_id": input_row_id,
        "new_availability": new_availability,
        "new_value": new_value,
        "old_value": old_value,
        "post_hoc_explanation_ignored": post_hoc,
        "target_id": target_id,
    }


def _observe(row: Mapping[str, str], field: str) -> tuple[str, str | None]:
    if field not in row:
        return "unavailable", None
    return "present", _canonical_field_value(field, row[field])


def _canonical_field_value(field: str, value: str) -> str:
    if field == "provenance":
        return _canonical_object(value)
    if field not in _LIST_FIELDS:
        return value
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return value
    if not isinstance(loaded, list):
        return value
    if all(isinstance(item, str) for item in loaded):
        return json.dumps(sorted(loaded), ensure_ascii=False, separators=(",", ":"))
    if field == "iuphar_family_paths" and all(
        isinstance(item, dict) for item in loaded
    ):
        return _canonical_family_paths(loaded)
    return value


def _canonical_object(value: str) -> str:
    """Sort object keys. A non-object provenance string stays exact."""
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return value
    if not isinstance(loaded, dict):
        return value
    return json.dumps(loaded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _closest_historical_row(
    rows: tuple[Mapping[str, str], ...], survivor: Mapping[str, str]
) -> Mapping[str, str]:
    """Pick the nearest historical duplicate. Equal distances use a stable signature."""

    def rank(row: Mapping[str, str]) -> tuple[int, str]:
        distance = sum(
            _observe(row, field) != _observe(survivor, field)
            for field in COMPARED_FIELDS
        )
        signature = json.dumps(
            sorted(row.items()), ensure_ascii=False, separators=(",", ":")
        )
        return distance, signature

    return min(rows, key=rank)


def _canonical_family_paths(loaded: list[object]) -> str:
    """Sort path records and object keys. Node order inside ``root_to_leaf`` stays."""
    records = [_family_path_record(item) for item in loaded if isinstance(item, dict)]
    records.sort(key=_family_path_sort_key)
    return json.dumps(
        records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _family_path_record(item: dict[object, object]) -> dict[str, object]:
    return {str(key): item[key] for key in sorted(item, key=str)}


def _family_path_sort_key(record: Mapping[str, object]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _note_availability(
    counts: dict[str, _Availability], observed: tuple[tuple[str, str, str], ...]
) -> None:
    for field, left_availability, right_availability in observed:
        bucket = counts[field]
        if left_availability == "present":
            bucket.historical_present += 1
        else:
            bucket.historical_unavailable += 1
        if right_availability == "present":
            bucket.new_present += 1
        else:
            bucket.new_unavailable += 1


def _measured_document(
    pair: str,
    differences: list[dict[str, object]],
    class_agreement: int,
    class_disagreement: int,
    counts: dict[str, _Availability],
    intersection_only: bool,
    outside: tuple[str, ...],
) -> dict[str, object]:
    ordered = sorted(differences, key=_diff_sort_key)
    unexplained = _count_disposition(ordered, "unexplained")
    allowed = _count_disposition(ordered, "allowed")
    return {
        "allowed_count": allowed,
        "class_agreement_count": class_agreement,
        "class_compared_count": class_agreement + class_disagreement,
        "class_disagreement_count": class_disagreement,
        "differences": ordered,
        "field_availability": _availability_document(counts),
        "historical_unavailable_count": _count_disposition(
            ordered, "historical_unavailable"
        ),
        "intersection_only": intersection_only,
        "measured": True,
        "new_unavailable_count": _count_disposition(ordered, "new_unavailable"),
        "outside_intersection": list(outside),
        "pair": pair,
        "reason": "строки сопоставлены по полному ключу",
        "semantic_mismatch_count": unexplained + allowed,
        "unexplained_count": unexplained,
    }


def _unmeasured(
    pair: str, reason: str, intersection_only: bool, outside: tuple[str, ...]
) -> dict[str, object]:
    return {
        "allowed_count": None,
        "class_agreement_count": None,
        "class_compared_count": None,
        "class_disagreement_count": None,
        "differences": [],
        "field_availability": [],
        "historical_unavailable_count": None,
        "intersection_only": intersection_only,
        "measured": False,
        "new_unavailable_count": None,
        "outside_intersection": list(outside),
        "pair": pair,
        "reason": reason,
        "semantic_mismatch_count": None,
        "unexplained_count": None,
    }


def _availability_document(
    counts: Mapping[str, _Availability],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for field in COMPARED_FIELDS:
        item = counts[field]
        rows.append(
            {
                "field": field,
                "group": FIELD_GROUPS[field],
                "historical_present": item.historical_present,
                "historical_unavailable": item.historical_unavailable,
                "new_present": item.new_present,
                "new_unavailable": item.new_unavailable,
            }
        )
    return rows


def _count_disposition(differences: list[dict[str, object]], name: str) -> int:
    return sum(1 for item in differences if item["disposition"] == name)


def _diff_sort_key(item: Mapping[str, object]) -> tuple[str, ...]:
    return tuple("" if item[name] is None else str(item[name]) for name in _DIFF_SORT)


def _post_hoc(row: Mapping[str, str]) -> bool:
    return bool(row.get("explanation") or row.get("change_sign"))


def _group_post_hoc(rows: tuple[Mapping[str, str], ...]) -> bool:
    return any(_post_hoc(row) for row in rows)


def _group_signature(rows: tuple[Mapping[str, str], ...]) -> str:
    signatures = sorted(
        json.dumps(sorted(row.items()), ensure_ascii=False, separators=(",", ":"))
        for row in rows
    )
    return json.dumps(signatures, ensure_ascii=False, separators=(",", ":"))


def _key_value(key: tuple[tuple[str, str], ...], name: str) -> str:
    for item_name, value in key:
        if item_name == name:
            return value
    return ""


def _source_record(rows: tuple[Mapping[str, str], ...] | None) -> dict[str, object]:
    if rows is None:
        return {"available": False, "row_count": None, "sha256": None}
    frozen = _freeze_rows(rows)
    ordered = sorted(tuple(sorted(row.items())) for row in frozen)
    return {
        "available": True,
        "row_count": len(frozen),
        "sha256": _sha256_bytes(_canonical_json_bytes(ordered)),
    }


def _freeze_rows(rows: tuple[Mapping[str, str], ...]) -> tuple[dict[str, str], ...]:
    return tuple(_copy_row(row) for row in rows)


def _copy_row(row: object) -> dict[str, str]:
    if not isinstance(row, Mapping):
        message = "строка M должна быть отображением"
        raise TypeError(message)
    copied: dict[str, str] = {}
    for key, value in row.items():
        if not isinstance(key, str) or not isinstance(value, str):
            message = "поля строки M должны быть строками"
            raise TypeError(message)
        copied[key] = value
    return copied


def _restore_rows(
    rows: tuple[Mapping[str, str], ...], snapshot: tuple[dict[str, str], ...]
) -> None:
    if len(rows) != len(snapshot):
        return
    for original, saved in zip(rows, snapshot, strict=True):
        if not isinstance(original, dict):
            continue
        original.clear()
        original.update(saved)


def _canonical_json_bytes(payload: object) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write_bytes(path: Path, payload: bytes, *, root: Path) -> None:
    if path.is_symlink() or path.name in PROOF_VERIFICATION_ARTIFACTS:
        message = (
            "m-parity report must not follow a symlink or replace a proof artifact"
        )
        raise ValueError(message)
    root_resolved = root.resolve()
    parent = path.parent.resolve()
    if not parent.is_relative_to(root_resolved):
        message = "path escapes root"
        raise ValueError(message)
    destination = parent / path.name
    if destination.is_symlink():
        message = "m-parity report must not follow a symlink"
        raise ValueError(message)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
