"""Step E resolution. The row table is data; the engine does not special-case a row number."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .policy import PLAN_SOURCE, PLAN_VERSION, compare_subclasses

ANNOTATION_STATUSES = frozenset(
    {"available", "partial", "unmapped_type", "conflicting", "not_available"}
)
LOCAL_STATUSES = frozenset(
    {"supported", "not_supported", "candidate_only", "conflicting"}
)
_NULL_ANNOTATION = frozenset(
    {
        "not_found",
        "ambiguous",
        "identity_conflict",
        "insufficient_input",
        "source_unavailable",
    }
)


@dataclass(frozen=True, slots=True)
class ResolutionInput:
    """One row entering the decision table. The function does not mutate it."""

    match_status: str
    iuphar_annotation_status: str | None
    local_status: str
    iuphar_class: str | None = None
    local_class: str | None = None
    iuphar_subclass: str | None = None
    local_subclasses: tuple[str, ...] = ()
    confirmed_subclasses: tuple[str, ...] = ()
    partial_basis: str | None = None
    target_kind: str = "protein"
    complex_direct_match: bool = False
    component_results: tuple[str, ...] = ()
    iuphar_class_candidates: tuple[str, ...] = ()
    local_candidates: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    raw_type: str | None = None
    matched_target_id: str | None = None
    candidate_target_ids: tuple[str, ...] = ()
    direct_vocabulary: frozenset[str] = frozenset()
    local_vocabulary: frozenset[str] = frozenset()
    same_pairs: frozenset[tuple[str, str]] = frozenset()
    class_subclass_pairs: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True, slots=True)
class Resolution:
    """Same fields for every branch, including contract_error."""

    effective_class: str | None
    effective_source: str
    decision_status: str
    conflict_codes: tuple[str, ...]
    effective_subclasses: tuple[str, ...]
    run_incomplete: bool
    rule_id: str
    iuphar_class: str | None
    iuphar_subclass: str | None
    local_class: str | None
    local_subclasses: tuple[str, ...]
    iuphar_class_candidates: tuple[str, ...]
    local_candidates: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    raw_type: str | None
    matched_target_id: str | None
    candidate_target_ids: tuple[str, ...]
    component_results: tuple[str, ...]
    partial_basis: str | None


@dataclass(frozen=True, slots=True)
class RowRule:
    """One versioned row of table E."""

    rule_id: str
    input_conditions: str
    output: str
    match_status: frozenset[str]
    annotation: frozenset[str | None]
    relation: str
    takes: str
    source: str
    decision: str
    codes: tuple[str, ...]
    code_mode: str
    run_incomplete: bool
    keep_local_candidate: bool
    limits: str
    justification_source: str = PLAN_SOURCE
    version: str = PLAN_VERSION


def resolution_rules() -> tuple[RowRule, ...]:
    """Rows 1–17 in priority order. The first match is the outcome."""
    source = "план v1 r8 шаг E"
    common = {
        "justification_source": source,
        "version": PLAN_VERSION,
        "limits": "первый совпавший ряд",
    }
    null = frozenset({None})
    return (
        _rule(
            "1",
            "source_unavailable и supported local",
            "предварительный local",
            {"source_unavailable"},
            null,
            "supported",
            "local",
            "requires_review",
            ("source_unavailable",),
            "literal",
            True,
            False,
            **common,
        ),
        _rule(
            "2",
            "source_unavailable и иной local",
            "null",
            {"source_unavailable"},
            null,
            "any",
            "null",
            "unresolved",
            ("source_unavailable",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "3",
            "ambiguous или identity_conflict",
            "null",
            {"ambiguous", "identity_conflict"},
            null,
            "any",
            "null",
            "requires_review",
            (),
            "match",
            False,
            False,
            **common,
        ),
        _rule(
            "4",
            "insufficient_input",
            "null",
            {"insufficient_input"},
            null,
            "any",
            "null",
            "unresolved",
            ("insufficient_input",),
            "literal",
            False,
            True,
            **common,
        ),
        _rule(
            "5",
            "matched available и согласный или отсутствующий local",
            "direct",
            {"matched"},
            frozenset({"available"}),
            "same_or_absent",
            "iuphar",
            "resolved",
            (),
            "empty",
            False,
            False,
            **common,
        ),
        _rule(
            "6",
            "matched available и иной supported local",
            "direct",
            {"matched"},
            frozenset({"available"}),
            "supported_different",
            "iuphar",
            "requires_review",
            ("direct_local_conflict",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "7",
            "matched available и conflicting local",
            "direct",
            {"matched"},
            frozenset({"available"}),
            "conflicting",
            "iuphar",
            "requires_review",
            ("local_conflict",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "8",
            "matched available и candidate_only",
            "direct",
            {"matched"},
            frozenset({"available"}),
            "candidate_only",
            "iuphar",
            "resolved",
            (),
            "empty",
            False,
            False,
            **common,
        ),
        _rule(
            "9б-1",
            "partial и supported local иного класса",
            "direct",
            {"matched"},
            frozenset({"partial"}),
            "supported_different",
            "iuphar",
            "requires_review",
            ("partial_annotation", "direct_local_conflict"),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "9б-2",
            "partial и conflicting local",
            "direct",
            {"matched"},
            frozenset({"partial"}),
            "conflicting",
            "iuphar",
            "requires_review",
            ("partial_annotation", "local_conflict"),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "9а",
            "partial без расхождения local",
            "direct",
            {"matched"},
            frozenset({"partial"}),
            "partial_agree",
            "iuphar",
            "resolved",
            ("partial_annotation",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "10",
            "unmapped_type и supported local",
            "local",
            {"matched"},
            frozenset({"unmapped_type"}),
            "supported",
            "local",
            "requires_review",
            ("unmapped_type",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "11",
            "unmapped_type и иной local",
            "null",
            {"matched"},
            frozenset({"unmapped_type"}),
            "any",
            "null",
            "unresolved",
            ("unmapped_type",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "12",
            "conflicting direct",
            "null",
            {"matched"},
            frozenset({"conflicting"}),
            "any",
            "null",
            "requires_review",
            ("direct_class_conflict",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "13",
            "not_available и supported local",
            "local",
            {"matched"},
            frozenset({"not_available"}),
            "supported",
            "local",
            "requires_review",
            ("annotation_not_available",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "14",
            "not_available и иной local",
            "null",
            {"matched"},
            frozenset({"not_available"}),
            "any",
            "null",
            "unresolved",
            ("annotation_not_available",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "15",
            "not_found и supported local",
            "local",
            {"not_found"},
            null,
            "supported",
            "local",
            "resolved",
            ("direct_not_found",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "16",
            "not_found и conflicting local",
            "null",
            {"not_found"},
            null,
            "conflicting",
            "null",
            "requires_review",
            ("local_conflict",),
            "literal",
            False,
            False,
            **common,
        ),
        _rule(
            "17",
            "not_found и candidate_only или not_supported",
            "null",
            {"not_found"},
            null,
            "candidate_or_absent",
            "null",
            "unresolved",
            (),
            "empty",
            False,
            False,
            **common,
        ),
    )


def validate_resolution_policy(rules: tuple[RowRule, ...]) -> None:
    """A row without a required field blocks the run."""
    for rule in rules:
        for field_name in (
            "rule_id",
            "input_conditions",
            "output",
            "justification_source",
            "version",
            "limits",
        ):
            if not getattr(rule, field_name):
                message = f"rule {rule.rule_id} missing {field_name}"
                raise ValueError(message)


def select_effective_class(
    row: ResolutionInput,
    rules: tuple[RowRule, ...] | None = None,
) -> Resolution:
    """Apply the complex rule, then the first matching row, then subclasses."""
    selected = resolution_rules() if rules is None else rules
    validate_resolution_policy(selected)
    if not _admissible(row):
        return _finish(
            row,
            None,
            "none",
            "requires_review",
            ("contract_error",),
            False,
            "contract_error",
        )
    complex_result = _complex_without_direct_match(row)
    if complex_result is not None:
        return complex_result
    for rule in selected:
        if _matches(rule, row):
            return _from_rule(row, rule)
    return _finish(
        row, None, "none", "requires_review", ("contract_error",), False, "uncovered"
    )


def detect_conflicts(row: ResolutionInput) -> tuple[str, ...]:
    """Conflict codes of the selected outcome, including subclass_conflict."""
    return select_effective_class(row).conflict_codes


def merge_records(
    rows: tuple[Mapping[str, str], ...],
) -> tuple[Mapping[str, str], ...]:
    """Keep every distinct full record. One chembl id does not drop another."""
    kept: list[Mapping[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for row in rows:
        key = tuple(sorted(row.items()))
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return tuple(kept)


def _rule(
    rule_id: str,
    conditions: str,
    output: str,
    match_status: set[str],
    annotation: frozenset[str | None],
    relation: str,
    takes: str,
    decision: str,
    codes: tuple[str, ...],
    code_mode: str,
    run_incomplete: bool,
    keep_local_candidate: bool,
    **common: str,
) -> RowRule:
    return RowRule(
        rule_id=rule_id,
        input_conditions=conditions,
        output=output,
        match_status=frozenset(match_status),
        annotation=annotation,
        relation=relation,
        takes=takes,
        source={"iuphar": "iuphar_normalized", "local": "local_rule", "null": "none"}[
            takes
        ],
        decision=decision,
        codes=codes,
        code_mode=code_mode,
        run_incomplete=run_incomplete,
        keep_local_candidate=keep_local_candidate,
        limits=common["limits"],
        justification_source=common["justification_source"],
        version=common["version"],
    )


def _admissible(row: ResolutionInput) -> bool:
    if row.local_status not in LOCAL_STATUSES:
        return False
    if row.match_status == "matched":
        return row.iuphar_annotation_status in ANNOTATION_STATUSES
    if row.match_status in _NULL_ANNOTATION:
        return row.iuphar_annotation_status is None
    return False


def _matches(rule: RowRule, row: ResolutionInput) -> bool:
    if row.match_status not in rule.match_status:
        return False
    if row.iuphar_annotation_status not in rule.annotation:
        return False
    return _relation(rule.relation, row)


def _relation(relation: str, row: ResolutionInput) -> bool:
    local = row.local_status
    different = local == "supported" and row.local_class != row.iuphar_class
    return {
        "any": True,
        "supported": local == "supported",
        "same_or_absent": local == "not_supported"
        or (local == "supported" and row.local_class == row.iuphar_class),
        "supported_different": different,
        "conflicting": local == "conflicting",
        "candidate_only": local == "candidate_only",
        "candidate_or_absent": local in {"candidate_only", "not_supported"},
        "partial_agree": not (different or local == "conflicting"),
    }.get(relation, False)


def _from_rule(row: ResolutionInput, rule: RowRule) -> Resolution:
    chosen = _taken_class(rule.takes, row)
    codes = _codes(rule, row)
    return _finish(
        row,
        chosen,
        rule.source,
        rule.decision,
        codes,
        rule.run_incomplete,
        rule.rule_id,
        keep_local_candidate=rule.keep_local_candidate,
    )


def _taken_class(takes: str, row: ResolutionInput) -> str | None:
    if takes == "iuphar":
        return row.iuphar_class
    if takes == "local":
        return row.local_class
    return None


def _codes(rule: RowRule, row: ResolutionInput) -> tuple[str, ...]:
    if rule.code_mode == "empty":
        return ()
    if rule.code_mode == "match":
        if row.match_status == "ambiguous":
            return ("ambiguous_match",)
        return (row.match_status,)
    return rule.codes


def _complex_without_direct_match(row: ResolutionInput) -> Resolution | None:
    if row.target_kind != "complex" or row.complex_direct_match:
        return None
    reason = (
        "component_only_match" if row.match_status == "matched" else row.match_status
    )
    return _finish(
        row,
        None,
        "none",
        "requires_review",
        ("complex_no_direct_match", reason),
        False,
        "complex",
    )


def _finish(
    row: ResolutionInput,
    effective_class: str | None,
    source: str,
    decision: str,
    codes: tuple[str, ...],
    run_incomplete: bool,
    rule_id: str,
    *,
    keep_local_candidate: bool = False,
) -> Resolution:
    subclasses = _effective_subclasses(source, row)
    if rule_id in {"complex", "contract_error", "uncovered"}:
        conflict = codes
    else:
        conflict = _with_subclass_conflict(row, source, subclasses, codes)
    if "subclass_conflict" in conflict:
        decision = "requires_review"
    if not effective_class and (source != "none" or decision == "resolved"):
        conflict = (*conflict, "contract_error")
    if "contract_error" in conflict:
        effective_class = None
        source = "none"
        subclasses = ()
        decision = "requires_review"
    candidates = row.local_candidates
    if keep_local_candidate and row.local_class and row.local_class not in candidates:
        candidates = (*candidates, row.local_class)
    return Resolution(
        effective_class=effective_class,
        effective_source=source,
        decision_status=decision,
        conflict_codes=conflict,
        effective_subclasses=subclasses,
        run_incomplete=run_incomplete,
        rule_id=rule_id,
        iuphar_class=row.iuphar_class,
        iuphar_subclass=row.iuphar_subclass,
        local_class=row.local_class,
        local_subclasses=row.local_subclasses,
        iuphar_class_candidates=row.iuphar_class_candidates,
        local_candidates=candidates,
        evidence_ids=row.evidence_ids,
        raw_type=row.raw_type,
        matched_target_id=row.matched_target_id,
        candidate_target_ids=row.candidate_target_ids,
        component_results=row.component_results,
        partial_basis=row.partial_basis,
    )


def _effective_subclasses(source: str, row: ResolutionInput) -> tuple[str, ...]:
    if source == "iuphar_normalized" and row.iuphar_annotation_status == "partial":
        return row.confirmed_subclasses
    if source == "iuphar_normalized" and row.iuphar_subclass:
        return (row.iuphar_subclass,)
    if source == "local_rule":
        return row.local_subclasses
    return ()


def _with_subclass_conflict(
    row: ResolutionInput,
    source: str,
    selected: tuple[str, ...],
    codes: tuple[str, ...],
) -> tuple[str, ...]:
    other = _unselected_subclasses(row, source)
    direct_side, local_side = (
        (selected, other) if source == "iuphar_normalized" else (other, selected)
    )
    if (
        not set(direct_side) <= row.direct_vocabulary
        or not set(local_side) <= row.local_vocabulary
    ):
        return (*codes, "contract_error")
    if not selected or not other:
        return codes
    compatible = _compatible_subclass_pairs(row, _pairs(source, selected, other))
    if {direct for direct, _ in compatible} == set(direct_side) and {
        local for _, local in compatible
    } == set(local_side):
        return codes
    return (*codes, "subclass_conflict")


def _compatible_subclass_pairs(
    row: ResolutionInput, pairs: tuple[tuple[str, str], ...]
) -> set[tuple[str, str]]:
    compatible: set[tuple[str, str]] = set()
    for direct, local in pairs:
        verdict = compare_subclasses(
            direct_subclass=direct,
            local_subclass=local,
            direct_vocabulary=row.direct_vocabulary,
            local_vocabulary=row.local_vocabulary,
            same_pairs=row.same_pairs,
            class_subclass_pairs=row.class_subclass_pairs,
        )
        if verdict in {"same", "class_subclass"}:
            compatible.add((direct, local))
    return compatible


def _unselected_subclasses(row: ResolutionInput, source: str) -> tuple[str, ...]:
    iuphar_side = _iuphar_supported_subclasses(row)
    local_side = row.local_subclasses if row.local_status == "supported" else ()
    if source == "iuphar_normalized":
        return local_side
    if source == "local_rule":
        return iuphar_side
    return ()


def _iuphar_supported_subclasses(row: ResolutionInput) -> tuple[str, ...]:
    if row.iuphar_annotation_status is None:
        return ()
    if row.iuphar_annotation_status == "partial":
        return row.confirmed_subclasses
    if row.iuphar_subclass:
        return (row.iuphar_subclass,)
    return ()


def _pairs(
    source: str,
    selected: tuple[str, ...],
    other: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    if source == "iuphar_normalized":
        return tuple((direct, local) for direct in selected for local in other)
    return tuple((direct, local) for local in selected for direct in other)
