"""Stage-5 comparison. An empty stage-0 set is not a quality measurement."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

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


def _same_classification(
    m_row: Mapping[str, str], python_row: Mapping[str, str]
) -> bool:
    """Compare class projections without inferring missing historical values."""
    classification_fields = (
        "effective_class",
        "effective_source",
        "decision_status",
        "match_status",
        "local_class",
        "local_status",
        "iuphar_annotation_status",
    )
    return _class(m_row) == _class(python_row) and all(
        m_row.get(field) == python_row.get(field) for field in classification_fields
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


def _group(
    rows: tuple[Mapping[str, str], ...],
) -> dict[tuple[tuple[str, str], ...], tuple[Mapping[str, str], ...]]:
    grouped: dict[tuple[tuple[str, str], ...], list[Mapping[str, str]]] = {}
    for row in rows:
        key = tuple(
            sorted(
                (name, value) for name, value in row.items() if name in _IDENTITY_FIELDS
            )
        )
        grouped.setdefault(key, []).append(row)
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
