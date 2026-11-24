"""Classify missing assay targets without publishing candidate tables."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Protocol, cast

import orjson

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.target_migration_row_ops import by_id, hash_input


class GoldRowFilter(Protocol):
    """Structural Gold filter used without a domain import at runtime."""

    def should_include(self, record: JsonDict) -> bool:
        """Return whether one Gold row passes the active filter."""


ADMISSIBLE_ABSENCE_REASONS = frozenset({"limited_sample", "incomplete_load"})
BLOCKING_ABSENCE_REASONS = frozenset({"gold_filter", "contract_mismatch", "unresolved"})
_SOURCE_KINDS = frozenset({"verified_pipeline_output", "persisted_silver"})
ASSAY_TARGET_CLOSURE_ERROR = "baseline assay/target foreign-key closure failed"


@dataclass(frozen=True, slots=True)
class TargetRecoveryInput:
    """One verified source file and the full Silver/Gold rows it supports."""

    target_id: str
    source_kind: str
    source_path: str
    source_file: Path
    source_sha256: str
    silver_row: Mapping[str, object] | None
    gold_row: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class TargetAbsenceFinding:
    """Why one assay target is absent, and whether a full row may be published."""

    target_id: str
    absence_reason: str
    disposition: str
    source_kind: str | None = None
    source_path: str | None = None
    source_sha256: str | None = None
    silver_row: Mapping[str, object] | None = None
    gold_row: Mapping[str, object] | None = None

    @property
    def layers(self) -> tuple[str, ...]:
        """Return the candidate layers that gain this target."""
        if self.disposition != "restore":
            return ()
        if self.absence_reason == "limited_sample":
            return ("silver", "gold")
        return ("gold",)


@dataclass(frozen=True, slots=True)
class TargetFKRestorationPlan:
    """Deterministic closure plan. Blockers publish no candidate rows."""

    missing_ids: tuple[str, ...]
    existing_target_ids: tuple[str, ...]
    assay_target_ids: tuple[str, ...]
    findings: tuple[TargetAbsenceFinding, ...]

    @property
    def blockers(self) -> tuple[TargetAbsenceFinding, ...]:
        """Return findings that must keep the migration blocked."""
        return tuple(item for item in self.findings if item.disposition == "block")

    @property
    def restorations(self) -> tuple[TargetAbsenceFinding, ...]:
        """Return findings whose full rows may be added."""
        return tuple(item for item in self.findings if item.disposition == "restore")


def current_target_ids(rows: Sequence[Mapping[str, object]]) -> set[str]:
    """Return target IDs whose persisted row is current."""
    return {key[0] for key, row in by_id(rows).items() if row.get("_is_current", True)}


def current_assay_target_ids(rows: Sequence[Mapping[str, object]]) -> set[str]:
    """Return non-null target IDs referenced by current assay rows."""
    return {
        str(row["target_id"])
        for row in rows
        if row.get("target_id") is not None and row.get("_is_current", True)
    }


def classify_target_absence(
    *,
    in_silver: bool,
    business_equal: bool,
    filter_allows: bool,
    source_kind: str,
    has_silver_record: bool,
) -> str:
    """Assign one absence cause without relaxing the Gold filter."""
    if not filter_allows:
        return "gold_filter"
    if in_silver and not business_equal:
        return "contract_mismatch"
    if in_silver and business_equal:
        return "incomplete_load"
    if (
        source_kind == "verified_pipeline_output"
        and has_silver_record
        and business_equal
    ):
        return "limited_sample"
    return "unresolved"


def plan_target_fk_restoration(
    *,
    silver_rows: Sequence[Mapping[str, object]],
    gold_rows: Sequence[Mapping[str, object]],
    assay_rows: Sequence[Mapping[str, object]],
    recoveries: Sequence[TargetRecoveryInput],
    gold_filter: GoldRowFilter,
) -> TargetFKRestorationPlan:
    """Classify every missing assay FK. Incomplete rows stay unresolved."""
    if not gold_rows or not silver_rows:
        raise ValueError("empty target cohort cannot explain an assay foreign key")
    missing = tuple(
        sorted(current_assay_target_ids(assay_rows) - current_target_ids(gold_rows))
    )
    if not missing:
        raise ValueError("Baseline has no missing target references")
    gold_columns = _column_set(gold_rows)
    silver_columns = _column_set(silver_rows)
    all_gold_ids = {key[0] for key in by_id(gold_rows)}
    silver_current = {
        key[0]: row
        for key, row in by_id(silver_rows).items()
        if row.get("_is_current", True)
    }
    by_source = _recovery_index(recoveries, missing)
    findings = tuple(
        _finding_for(
            target_id,
            recovery=by_source.get(target_id),
            gold_columns=gold_columns,
            silver_columns=silver_columns,
            all_gold_ids=all_gold_ids,
            silver_current=silver_current,
            gold_filter=gold_filter,
        )
        for target_id in missing
    )
    return TargetFKRestorationPlan(
        missing,
        tuple(sorted(all_gold_ids)),
        tuple(sorted(current_assay_target_ids(assay_rows))),
        findings,
    )


def _recovery_index(
    recoveries: Sequence[TargetRecoveryInput], missing: Sequence[str]
) -> dict[str, TargetRecoveryInput]:
    indexed: dict[str, TargetRecoveryInput] = {}
    allowed = set(missing)
    for item in recoveries:
        if item.target_id in indexed:
            raise ValueError("duplicate target recovery source")
        if item.target_id not in allowed:
            raise ValueError("recovery source includes a target that is not missing")
        if item.source_kind not in _SOURCE_KINDS:
            raise ValueError("unsupported target recovery source kind")
        indexed[item.target_id] = item
    return indexed


def _finding_for(
    target_id: str,
    *,
    recovery: TargetRecoveryInput | None,
    gold_columns: set[str],
    silver_columns: set[str],
    all_gold_ids: set[str],
    silver_current: Mapping[str, Mapping[str, object]],
    gold_filter: GoldRowFilter,
) -> TargetAbsenceFinding:
    if recovery is None:
        return TargetAbsenceFinding(target_id, "unresolved", "block")
    payload = _source_payload(recovery)
    source_gold = _bound_source_row(recovery, "gold", payload)
    if source_gold is None:
        raise ValueError(
            "target recovery source does not contain the restored gold row"
        )
    recovery = replace(
        recovery,
        silver_row=_bound_source_row(recovery, "silver", payload),
        gold_row=source_gold,
    )
    if target_id in all_gold_ids:
        return _blocked(recovery, "contract_mismatch")
    if not _complete_gold_row(recovery.gold_row, gold_columns, target_id):
        return _blocked(recovery, "unresolved")
    silver_row = _silver_record(recovery, silver_current, silver_columns, target_id)
    reason = classify_target_absence(
        in_silver=target_id in silver_current,
        business_equal=silver_row is not None
        and _business_compatible(silver_row, recovery.gold_row),
        filter_allows=gold_filter.should_include(
            cast(JsonDict, dict(recovery.gold_row))
        ),
        source_kind=recovery.source_kind,
        has_silver_record=silver_row is not None,
    )
    if reason not in ADMISSIBLE_ABSENCE_REASONS:
        return _blocked(recovery, reason)
    if reason == "limited_sample" and (
        recovery.silver_row is None or set(recovery.silver_row) != silver_columns
    ):
        return _blocked(recovery, "unresolved")
    published_silver = recovery.silver_row if reason == "limited_sample" else None
    return TargetAbsenceFinding(
        target_id,
        reason,
        "restore",
        recovery.source_kind,
        recovery.source_path,
        recovery.source_sha256,
        published_silver,
        dict(recovery.gold_row),
    )


def _blocked(recovery: TargetRecoveryInput, reason: str) -> TargetAbsenceFinding:
    return TargetAbsenceFinding(
        recovery.target_id,
        reason,
        "block",
        recovery.source_kind,
        recovery.source_path,
        recovery.source_sha256,
    )


def _silver_record(
    recovery: TargetRecoveryInput,
    silver_current: Mapping[str, Mapping[str, object]],
    silver_columns: set[str],
    target_id: str,
) -> Mapping[str, object] | None:
    persisted = silver_current.get(target_id)
    if persisted is not None:
        return persisted
    supplied = recovery.silver_row
    if supplied is None:
        return None
    if supplied.get("target_id") != target_id:
        raise ValueError("recovery silver row target_id mismatch")
    if set(supplied) != silver_columns:
        return None
    return supplied


def _bound_source_row(
    recovery: TargetRecoveryInput, layer: str, payload: Mapping[str, object]
) -> dict[str, object] | None:
    """Return the row stored in the pinned source, not a parallel caller object."""
    declared = recovery.gold_row if layer == "gold" else recovery.silver_row
    stored = payload.get(layer)
    if declared is None:
        if stored is not None:
            raise ValueError(
                f"target recovery source contains an undeclared {layer} row"
            )
        return None
    if not isinstance(stored, dict):
        raise ValueError(
            f"target recovery source does not contain the restored {layer} row"
        )
    row = dict(stored)
    identity = row.get("target_id", row.get("target_chembl_id", recovery.target_id))
    if identity != recovery.target_id:
        raise ValueError("target recovery source row does not match the missing target")
    row["target_id"] = recovery.target_id
    if canonical_row_sha256(row) != canonical_row_sha256(declared):
        raise ValueError(f"target recovery {layer} row is not the verified source row")
    return row


def _source_payload(recovery: TargetRecoveryInput) -> dict[str, object]:
    raw = recovery.source_file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != recovery.source_sha256:
        raise ValueError("target recovery source digest mismatch")
    payload = orjson.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("target recovery source must be a JSON object")
    identity = payload.get("target_id", payload.get("target_chembl_id"))
    if identity != recovery.target_id:
        raise ValueError("target recovery source does not identify the missing target")
    return payload


def _complete_gold_row(
    row: Mapping[str, object], columns: set[str], target_id: str
) -> bool:
    if set(row) != columns or row.get("target_id") != target_id:
        return False
    if row.get("_is_current", True) is not True:
        return False
    return all(
        isinstance(row.get(field), str) and str(row.get(field)).strip()
        for field in ("pref_name", "organism", "target_type")
    )


def _column_set(rows: Sequence[Mapping[str, object]]) -> set[str]:
    columns = {frozenset(row) for row in rows}
    if len(columns) != 1:
        raise ValueError("target physical cohort has inconsistent columns")
    return set(next(iter(columns)))


def _business_compatible(
    silver: Mapping[str, object], gold: Mapping[str, object]
) -> bool:
    left = _business_view(silver)
    right = _business_view(gold)
    if any(
        key not in right and not _empty(value) for key, value in left.items()
    ) or any(
        key in right and not _values_equal(right[key], value)
        for key, value in left.items()
    ):
        return False
    return all(_empty(value) for key, value in right.items() if key not in left)


def _business_view(row: Mapping[str, object]) -> dict[str, object]:
    record = {
        key: value
        for key, value in hash_input(row).items()
        if key not in TARGET_CLASSIFICATION_FIELDS
    }
    if "description" not in record:
        return record
    description = record["description"]
    canonical = record.get("target_description", description)
    if _values_equal(description, canonical) or _empty(description):
        record.pop("description")
        if "target_description" not in record and not _empty(canonical):
            record["target_description"] = canonical
    return record


def _empty(value: object) -> bool:
    return value is None or value in ("", [], {})


def _values_equal(left: object, right: object) -> bool:
    if type(left) is type(right):
        return left == right
    if (
        isinstance(left, int | float)
        and isinstance(right, int | float)
        and not isinstance(left, bool)
        and not isinstance(right, bool)
    ):
        return float(left) == float(right)
    return False


def canonical_row_sha256(row: Mapping[str, object]) -> str:
    """Hash one persisted row with stable key order and ISO timestamps."""
    payload = orjson.dumps(
        dict(row), option=orjson.OPT_SORT_KEYS, default=_json_default
    )
    return hashlib.sha256(payload).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    raise TypeError(f"target row value is not canonical JSON: {type(value).__name__}")


__all__ = [
    "ADMISSIBLE_ABSENCE_REASONS",
    "ASSAY_TARGET_CLOSURE_ERROR",
    "BLOCKING_ABSENCE_REASONS",
    "TargetAbsenceFinding",
    "TargetFKRestorationPlan",
    "TargetRecoveryInput",
    "canonical_row_sha256",
    "classify_target_absence",
    "current_assay_target_ids",
    "current_target_ids",
    "plan_target_fk_restoration",
]
