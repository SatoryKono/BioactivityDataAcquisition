"""TC-08 decision table, including the named coverage-matrix cases."""

from __future__ import annotations

from dataclasses import fields, replace

import pytest

from iuphar_target_class.resolution import (
    ResolutionInput,
    merge_records,
    select_effective_class,
)
from iuphar_target_class.resolution import resolution_rules

pytestmark = pytest.mark.unit

_VOCAB = frozenset({"alpha", "beta"})


def _row(**overrides: object) -> ResolutionInput:
    payload: dict[str, object] = {
        "match_status": "matched",
        "iuphar_annotation_status": "available",
        "local_status": "not_supported",
        "iuphar_class": "Receptor",
        "local_class": None,
        "iuphar_subclass": None,
        "local_subclasses": (),
        "confirmed_subclasses": (),
        "partial_basis": None,
        "target_kind": "protein",
        "complex_direct_match": False,
        "component_results": (),
        "iuphar_class_candidates": (),
        "local_candidates": (),
        "evidence_ids": ("evidence-1",),
        "raw_type": "gpcr",
        "matched_target_id": "1",
        "candidate_target_ids": (),
        "direct_vocabulary": frozenset(),
        "local_vocabulary": frozenset(),
        "same_pairs": frozenset(),
        "class_subclass_pairs": frozenset(),
    }
    payload.update(overrides)
    return ResolutionInput(**payload)  # type: ignore[arg-type]


_CASES = (
    (
        "1",
        _row(
            match_status="source_unavailable",
            iuphar_annotation_status=None,
            local_status="supported",
            local_class="Enzyme",
        ),
        "Enzyme",
        "local_rule",
        "requires_review",
        ("source_unavailable",),
        True,
        (),
    ),
    (
        "2",
        _row(
            match_status="source_unavailable",
            iuphar_annotation_status=None,
            local_status="not_supported",
        ),
        None,
        "none",
        "unresolved",
        ("source_unavailable",),
        False,
        (),
    ),
    (
        "3-ambiguous",
        _row(
            match_status="ambiguous",
            iuphar_annotation_status=None,
            candidate_target_ids=("2", "1"),
        ),
        None,
        "none",
        "requires_review",
        ("ambiguous_match",),
        False,
        (),
    ),
    (
        "3-identity",
        _row(
            match_status="identity_conflict",
            iuphar_annotation_status=None,
            candidate_target_ids=("1", "2"),
        ),
        None,
        "none",
        "requires_review",
        ("identity_conflict",),
        False,
        (),
    ),
    (
        "4",
        _row(
            match_status="insufficient_input",
            iuphar_annotation_status=None,
            local_status="supported",
            local_class="Enzyme",
        ),
        None,
        "none",
        "unresolved",
        ("insufficient_input",),
        False,
        (),
    ),
    (
        "5а-same",
        _row(
            local_status="supported",
            local_class="Receptor",
            iuphar_subclass="alpha",
            local_subclasses=("alpha",),
            direct_vocabulary=_VOCAB,
            local_vocabulary=_VOCAB,
        ),
        "Receptor",
        "iuphar_normalized",
        "resolved",
        (),
        False,
        ("alpha",),
    ),
    ("5а-absent", _row(), "Receptor", "iuphar_normalized", "resolved", (), False, ()),
    (
        "5б",
        _row(
            local_status="supported",
            local_class="Receptor",
            iuphar_subclass="alpha",
            local_subclasses=("beta",),
            direct_vocabulary=_VOCAB,
            local_vocabulary=_VOCAB,
        ),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("subclass_conflict",),
        False,
        ("alpha",),
    ),
    (
        "6",
        _row(local_status="supported", local_class="Enzyme"),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("direct_local_conflict",),
        False,
        (),
    ),
    (
        "7",
        _row(local_status="conflicting", local_candidates=("Enzyme", "Receptor")),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("local_conflict",),
        False,
        (),
    ),
    (
        "8",
        _row(local_status="candidate_only", local_candidates=("Enzyme",)),
        "Receptor",
        "iuphar_normalized",
        "resolved",
        (),
        False,
        (),
    ),
    (
        "9а-type",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="type",
            confirmed_subclasses=("type-sub",),
            local_status="not_supported",
        ),
        "Receptor",
        "iuphar_normalized",
        "resolved",
        ("partial_annotation",),
        False,
        ("type-sub",),
    ),
    (
        "9а-family",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="family_mapping",
            confirmed_subclasses=("family-sub",),
            local_status="supported",
            local_class="Receptor",
        ),
        "Receptor",
        "iuphar_normalized",
        "resolved",
        ("partial_annotation",),
        False,
        ("family-sub",),
    ),
    (
        "9б-1-type",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="type",
            confirmed_subclasses=("type-sub",),
            local_status="supported",
            local_class="Enzyme",
        ),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("partial_annotation", "direct_local_conflict"),
        False,
        ("type-sub",),
    ),
    (
        "9б-1-family",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="family_mapping",
            confirmed_subclasses=("family-sub",),
            local_status="supported",
            local_class="Enzyme",
        ),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("partial_annotation", "direct_local_conflict"),
        False,
        ("family-sub",),
    ),
    (
        "9б-2-type",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="type",
            confirmed_subclasses=("type-sub",),
            local_status="conflicting",
        ),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("partial_annotation", "local_conflict"),
        False,
        ("type-sub",),
    ),
    (
        "9б-2-family",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="family_mapping",
            confirmed_subclasses=("family-sub",),
            local_status="conflicting",
        ),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("partial_annotation", "local_conflict"),
        False,
        ("family-sub",),
    ),
    (
        "10",
        _row(
            iuphar_annotation_status="unmapped_type",
            iuphar_class=None,
            local_status="supported",
            local_class="Enzyme",
        ),
        "Enzyme",
        "local_rule",
        "requires_review",
        ("unmapped_type",),
        False,
        (),
    ),
    (
        "11",
        _row(
            iuphar_annotation_status="unmapped_type",
            iuphar_class=None,
            local_status="not_supported",
        ),
        None,
        "none",
        "unresolved",
        ("unmapped_type",),
        False,
        (),
    ),
    (
        "12",
        _row(
            iuphar_annotation_status="conflicting",
            iuphar_class=None,
            iuphar_class_candidates=("Enzyme", "Receptor"),
        ),
        None,
        "none",
        "requires_review",
        ("direct_class_conflict",),
        False,
        (),
    ),
    (
        "13",
        _row(
            iuphar_annotation_status="not_available",
            iuphar_class=None,
            local_status="supported",
            local_class="Enzyme",
        ),
        "Enzyme",
        "local_rule",
        "requires_review",
        ("annotation_not_available",),
        False,
        (),
    ),
    (
        "14",
        _row(iuphar_annotation_status="not_available", iuphar_class=None),
        None,
        "none",
        "unresolved",
        ("annotation_not_available",),
        False,
        (),
    ),
    (
        "15",
        _row(
            match_status="not_found",
            iuphar_annotation_status=None,
            iuphar_class=None,
            iuphar_subclass="alpha",
            local_status="supported",
            local_class="Enzyme",
            local_subclasses=("beta",),
        ),
        "Enzyme",
        "local_rule",
        "resolved",
        ("direct_not_found",),
        False,
        ("beta",),
    ),
    (
        "16",
        _row(
            match_status="not_found",
            iuphar_annotation_status=None,
            iuphar_class=None,
            local_status="conflicting",
        ),
        None,
        "none",
        "requires_review",
        ("local_conflict",),
        False,
        (),
    ),
    (
        "17-candidate",
        _row(
            match_status="not_found",
            iuphar_annotation_status=None,
            iuphar_class=None,
            local_status="candidate_only",
            local_candidates=("Enzyme",),
        ),
        None,
        "none",
        "unresolved",
        (),
        False,
        (),
    ),
    (
        "17-absent",
        _row(
            match_status="not_found", iuphar_annotation_status=None, iuphar_class=None
        ),
        None,
        "none",
        "unresolved",
        (),
        False,
        (),
    ),
    (
        "П-Комплекс",
        _row(
            target_kind="complex",
            local_status="supported",
            local_class="Enzyme",
            component_results=("component-a",),
        ),
        None,
        "none",
        "requires_review",
        ("complex_no_direct_match", "component_only_match"),
        False,
        (),
    ),
    (
        "П-Допуст.",
        _row(match_status="not_found", iuphar_annotation_status="available"),
        None,
        "none",
        "requires_review",
        ("contract_error",),
        False,
        (),
    ),
    (
        "П-Подкл.-совместимо",
        _row(
            local_status="supported",
            local_class="Receptor",
            iuphar_subclass="alpha",
            local_subclasses=("beta",),
            direct_vocabulary=_VOCAB,
            local_vocabulary=_VOCAB,
            class_subclass_pairs=frozenset({("alpha", "beta")}),
        ),
        "Receptor",
        "iuphar_normalized",
        "resolved",
        (),
        False,
        ("alpha",),
    ),
    (
        "9а-подкласс",
        _row(
            iuphar_annotation_status="partial",
            partial_basis="type",
            confirmed_subclasses=("alpha",),
            local_status="supported",
            local_class="Receptor",
            local_subclasses=("beta",),
            direct_vocabulary=_VOCAB,
            local_vocabulary=_VOCAB,
        ),
        "Receptor",
        "iuphar_normalized",
        "requires_review",
        ("partial_annotation", "subclass_conflict"),
        False,
        ("alpha",),
    ),
)


@pytest.mark.parametrize(
    (
        "name",
        "row",
        "effective_class",
        "source",
        "decision",
        "codes",
        "incomplete",
        "subclasses",
    ),
    _CASES,
    ids=[case[0] for case in _CASES],
)
def test_resolution_matrix(
    name: str,
    row: ResolutionInput,
    effective_class: str | None,
    source: str,
    decision: str,
    codes: tuple[str, ...],
    incomplete: bool,
    subclasses: tuple[str, ...],
) -> None:
    del name
    before = (
        row.iuphar_class,
        row.raw_type,
        row.evidence_ids,
        row.iuphar_class_candidates,
        row.candidate_target_ids,
    )
    result = select_effective_class(row)
    assert result.effective_class == effective_class
    assert result.effective_source == source
    assert result.decision_status == decision
    assert result.conflict_codes == codes
    assert result.run_incomplete is incomplete
    assert result.effective_subclasses == subclasses
    assert result.evidence_ids == row.evidence_ids
    assert result.partial_basis == row.partial_basis
    assert result.iuphar_class == row.iuphar_class
    assert (
        row.iuphar_class,
        row.raw_type,
        row.evidence_ids,
        row.iuphar_class_candidates,
        row.candidate_target_ids,
    ) == before


def test_branches_share_one_output_schema() -> None:
    names = [field.name for field in fields(select_effective_class(_CASES[0][1]))]
    for case in _CASES:
        assert [
            field.name for field in fields(select_effective_class(case[1]))
        ] == names


def test_candidate_order_does_not_change_the_decision() -> None:
    forward = select_effective_class(
        _row(
            match_status="ambiguous",
            iuphar_annotation_status=None,
            candidate_target_ids=("1", "2"),
        )
    )
    reverse = select_effective_class(
        _row(
            match_status="ambiguous",
            iuphar_annotation_status=None,
            candidate_target_ids=("2", "1"),
        )
    )
    assert forward.decision_status == reverse.decision_status
    assert forward.conflict_codes == reverse.conflict_codes
    assert forward.effective_class == reverse.effective_class
    assert reverse.candidate_target_ids == ("2", "1")


def test_same_chembl_id_does_not_drop_a_different_annotation() -> None:
    kept = merge_records(
        (
            {"target_chembl_id": "CHEMBL1", "iuphar_class": "Receptor"},
            {"target_chembl_id": "CHEMBL1", "iuphar_class": "Enzyme"},
            {"target_chembl_id": "CHEMBL1", "iuphar_class": "Receptor"},
        )
    )
    assert kept == (
        {"target_chembl_id": "CHEMBL1", "iuphar_class": "Receptor"},
        {"target_chembl_id": "CHEMBL1", "iuphar_class": "Enzyme"},
    )


def test_insufficient_input_keeps_the_local_class_as_a_candidate() -> None:
    result = select_effective_class(_CASES[4][1])
    assert result.local_candidates == ("Enzyme",)
    assert result.effective_class is None


def test_broken_resolution_rule_blocks_the_run() -> None:
    damaged = replace(resolution_rules()[0], version="")
    with pytest.raises(ValueError, match="missing version"):
        select_effective_class(_CASES[0][1], (damaged,))
