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
_RESULT_FIELDS = frozenset(
    {
        "change_sign",
        "decision_status",
        "effective_class",
        "effective_source",
        "explanation",
        "iuphar_class",
        "legacy_iuphar_class",
        "match_status",
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
    """Counts stay null until the reference actually contains M rows."""

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
    """Join on the full identity key and leave the M rows untouched."""
    if reference.selected_source_count == 0 and not reference.m_rows:
        return ComparisonReport(
            False,
            "эталонный набор этапа 0 не содержит выбранного источника и строк M",
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
        label = _label(key)
        m_group = grouped_m.get(key, ())
        python_group = grouped_python.get(key, ())
        if len(m_group) > 1 or len(python_group) > 1:
            residual.append(label)
            continue
        m_row = m_group[0] if m_group else None
        python_row = python_group[0] if python_group else None
        if m_row is not None and "legacy_iuphar_class" in m_row:
            legacy.append((label, m_row["legacy_iuphar_class"]))
        if m_row is None or python_row is None or _class(m_row) == _class(python_row):
            continue
        sign = python_row.get("change_sign", "")
        explanation = python_row.get("explanation", "")
        if sign in CHANGE_CATEGORIES and explanation:
            changes.append((label, sign, explanation))
        else:
            residual.append(label)
    return ComparisonReport(
        True,
        "строки M и Python сопоставлены по полному ключу",
        tuple(sorted(changes)),
        tuple(sorted(set(residual))),
        _metrics(python_rows),
        False,
        tuple(sorted(legacy)),
    )


def _group(
    rows: tuple[Mapping[str, str], ...],
) -> dict[tuple[tuple[str, str], ...], tuple[Mapping[str, str], ...]]:
    grouped: dict[tuple[tuple[str, str], ...], list[Mapping[str, str]]] = {}
    for row in rows:
        key = tuple(
            sorted(
                (name, value)
                for name, value in row.items()
                if name not in _RESULT_FIELDS
            )
        )
        grouped.setdefault(key, []).append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _class(row: Mapping[str, str]) -> str:
    return row.get("iuphar_class", row.get("legacy_iuphar_class", ""))


def _label(key: tuple[tuple[str, str], ...]) -> str:
    return "|".join(f"{name}={value}" for name, value in key)


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
