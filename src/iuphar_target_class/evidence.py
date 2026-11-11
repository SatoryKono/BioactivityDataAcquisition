"""Deterministic evidence ids, reference checks, and class-chain defects."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import ClassificationResult, Evidence, RunProvenance

EVIDENCE_TYPE_ORDER: tuple[str, ...] = (
    "match",
    "iuphar_raw",
    "iuphar_mapping",
    "local_rule",
)
_NAME_ONLY = frozenset({"exact_name", "exact_synonym"})
_SEPARATOR = "/"


@dataclass(frozen=True, slots=True)
class EvidenceDraft:
    """One witness before numbering. Arrival order is ignored."""

    input_row_id: str
    evidence_type: str
    source_id: str
    content: str
    list_name: str


@dataclass(frozen=True, slots=True)
class EvidenceTable:
    """Child table for one run. Ids are assigned in canonical order."""

    run_id: str
    records: tuple[Evidence, ...]
    match_evidence_ids: tuple[str, ...]
    local_evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoredRun:
    """One finished run. A later rules version does not replace these bytes."""

    rules_version: str
    provenance: RunProvenance
    table: EvidenceTable
    payload: bytes


class ContractDefect(ValueError):
    """A reference or class chain does not meet the evidence contract."""


def build_evidence_table(
    drafts: tuple[EvidenceDraft, ...], *, run_id: str
) -> EvidenceTable:
    """Number unique witnesses. The same content keeps the same id."""
    _reject_bad_parts(drafts)
    order = {name: index for index, name in enumerate(EVIDENCE_TYPE_ORDER)}
    ranked = sorted(
        drafts,
        key=lambda draft: (order[draft.evidence_type], draft.source_id, draft.content),
    )
    assigned: dict[tuple[str, str, str], Evidence] = {}
    records: list[Evidence] = []
    for draft in ranked:
        key = (draft.evidence_type, draft.source_id, draft.content)
        if key in assigned:
            continue
        ordinal = len(records) + 1
        evidence_id = _SEPARATOR.join(
            (draft.input_row_id, draft.evidence_type, draft.source_id, f"{ordinal:04d}")
        )
        record = Evidence(
            evidence_id,
            draft.input_row_id,
            draft.evidence_type,
            draft.source_id,
            draft.content,
            run_id,
        )
        assigned[key] = record
        records.append(record)
    by_key = assigned
    match_ids = _list_ids(ranked, by_key, "match")
    local_ids = _list_ids(ranked, by_key, "local")
    return EvidenceTable(run_id, tuple(records), match_ids, local_ids)


def unresolved_references(table: EvidenceTable) -> tuple[str, ...]:
    """Ids in either list that do not resolve inside this run."""
    known = {
        record.evidence_id for record in table.records if record.run_id == table.run_id
    }
    missing = [
        evidence_id
        for evidence_id in (*table.match_evidence_ids, *table.local_evidence_ids)
        if evidence_id not in known
    ]
    return tuple(sorted(set(missing)))


def require_resolvable(table: EvidenceTable) -> None:
    """Raise when a list id has no child record in the same run."""
    missing = unresolved_references(table)
    if missing:
        message = "unresolvable evidence reference: " + ", ".join(missing)
        raise ContractDefect(message)
    _reject_duplicate_ids(table.match_evidence_ids)
    _reject_duplicate_ids(table.local_evidence_ids)


def class_chain_defects(row: ClassificationResult) -> tuple[str, ...]:
    """Invariant 9. A class needs every link from the matched target."""
    if not row.iuphar_class:
        return ()
    defects: list[str] = []
    if row.match_status != "matched" or not row.matched_target_id:
        defects.append("matched_target_id")
    if not row.snapshot_id or not row.iuphar_type_raw:
        defects.append("raw_annotation")
    if not row.iuphar_mapping_rule_id or not row.iuphar_mapping_version:
        defects.append("mapping_rule")
    return tuple(defects)


def require_class_chain(row: ClassificationResult) -> None:
    """Raise when a non-empty IUPHAR class has a broken provenance chain."""
    defects = class_chain_defects(row)
    if defects:
        message = "class chain is incomplete: " + ", ".join(defects)
        raise ContractDefect(message)


def content_equal(left: StoredRun, right: StoredRun) -> bool:
    """Invariant 5. Timestamps may differ; evidence bytes may not."""
    return (
        left.rules_version == right.rules_version
        and left.payload == right.payload
        and left.table == right.table
        and _without_timestamps(left.provenance)
        == _without_timestamps(right.provenance)
    )


def rerun_with_new_rules(previous: StoredRun, rules_version: str) -> StoredRun:
    """A new rules version is a new run. The previous payload stays in place."""
    if not rules_version or rules_version == previous.rules_version:
        message = "a new rules version requires its own run"
        raise ValueError(message)
    provenance = replace(previous.provenance, rules_version=rules_version)
    return StoredRun(rules_version, provenance, previous.table, previous.payload)


def local_only_violation(row: ClassificationResult) -> bool:
    """Invariant 1. A local-only row has no IUPHAR class, id, or path."""
    local_only = row.effective_source == "local_rule" and row.match_status != "matched"
    if not local_only:
        return False
    return bool(row.iuphar_class or row.matched_target_id or row.iuphar_type_raw)


def trace_violation(row: ClassificationResult, methods: tuple[str, ...]) -> bool:
    """Invariant 2. A class needs a matched id and a non-name method."""
    if not row.iuphar_class:
        return False
    name_only = bool(methods) and set(methods) <= _NAME_ONLY
    return (
        row.match_status != "matched"
        or not row.matched_target_id
        or not methods
        or name_only
        or bool(class_chain_defects(row))
    )


def unsupported_class(row: ClassificationResult) -> bool:
    """Invariant 3. A class without a rule and an evidence id stays empty."""
    if row.local_class and (not row.local_rule_ids or not row.local_evidence_ids):
        return True
    if row.effective_class and row.effective_source == "local_rule":
        return not row.local_rule_ids or not row.local_evidence_ids
    if row.effective_class and row.effective_source == "iuphar_normalized":
        return not row.iuphar_mapping_rule_id or not row.match_evidence_ids
    return False


def match_id_violation(row: ClassificationResult) -> bool:
    """Invariant 8. ``matched`` and the target id appear together."""
    matched = row.match_status == "matched"
    return matched != bool(row.matched_target_id)


def _list_ids(
    ranked: list[EvidenceDraft],
    assigned: dict[tuple[str, str, str], Evidence],
    list_name: str,
) -> tuple[str, ...]:
    found: set[str] = set()
    for draft in ranked:
        if draft.list_name != list_name:
            continue
        key = (draft.evidence_type, draft.source_id, draft.content)
        found.add(assigned[key].evidence_id)
    return tuple(sorted(found))


def _reject_bad_parts(drafts: tuple[EvidenceDraft, ...]) -> None:
    known = set(EVIDENCE_TYPE_ORDER)
    for draft in drafts:
        if draft.evidence_type not in known:
            message = f"unknown evidence type: {draft.evidence_type}"
            raise ValueError(message)
        if draft.list_name not in {"match", "local"}:
            message = f"unknown evidence list: {draft.list_name}"
            raise ValueError(message)
        for label, value in (
            ("input_row_id", draft.input_row_id),
            ("source_id", draft.source_id),
        ):
            if not value or _SEPARATOR in value or "\n" in value:
                message = f"{label} is empty or contains the id separator"
                raise ValueError(message)


def _reject_duplicate_ids(evidence_ids: tuple[str, ...]) -> None:
    if len(evidence_ids) != len(set(evidence_ids)):
        message = "duplicate evidence id"
        raise ContractDefect(message)
    if tuple(sorted(evidence_ids)) != evidence_ids:
        message = "evidence ids are not in canonical order"
        raise ContractDefect(message)


def _without_timestamps(provenance: RunProvenance) -> tuple[str | None, ...]:
    return (
        provenance.snapshot_id,
        provenance.normalization_version,
        provenance.rules_version,
        provenance.schema_version,
    )
