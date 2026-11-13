"""TC-12: the stage-0 reference is empty, so quality counts stay unmeasured."""

from __future__ import annotations

import pytest

from iuphar_target_class.comparison import Stage0Reference, compare_stage0

pytestmark = pytest.mark.unit


def test_empty_stage0_set_is_not_a_measurement() -> None:
    reference = Stage0Reference("stage0-manifest", 0, ())
    report = compare_stage0(reference, ())
    assert report.measured is False
    assert report.metrics is None
    assert report.changes == ()
    assert report.residual == ()
    assert report.source_overwritten is False


def test_a_signed_change_is_explained_and_an_unsigned_one_remains() -> None:
    reference = Stage0Reference(
        "fixture",
        1,
        (
            {"input_row_id": "1", "legacy_iuphar_class": "Other Protein Target"},
            {"input_row_id": "2", "legacy_iuphar_class": "Receptor"},
        ),
    )
    before = tuple(dict(row) for row in reference.m_rows)
    report = compare_stage0(
        reference,
        (
            {
                "input_row_id": "1",
                "iuphar_class": "",
                "effective_class": "Enzyme",
                "match_status": "not_found",
                "effective_source": "local_rule",
                "decision_status": "resolved",
                "change_sign": "false_other_removed",
                "explanation": "старый Other не подтверждён свидетельством",
            },
            {
                "input_row_id": "2",
                "iuphar_class": "Enzyme",
                "effective_class": "Enzyme",
                "match_status": "matched",
                "effective_source": "iuphar_normalized",
                "decision_status": "resolved",
            },
        ),
    )
    assert reference.m_rows == before
    assert report.measured is True
    assert report.changes == (
        (
            "input_row_id=1",
            "false_other_removed",
            "старый Other не подтверждён свидетельством",
        ),
    )
    assert report.residual == ("input_row_id=2",)
    assert report.metrics is not None
    assert report.metrics["match_status:not_found"] == 1
    assert report.legacy_values == (
        ("input_row_id=1", "Other Protein Target"),
        ("input_row_id=2", "Receptor"),
    )
    assert report.source_overwritten is False


def test_selected_source_without_m_rows_is_not_measured() -> None:
    report = compare_stage0(
        Stage0Reference("fixture", 1, ()),
        ({"input_row_id": "1", "iuphar_class": "Receptor"},),
    )
    assert report.measured is False
    assert report.metrics is None


@pytest.mark.parametrize(
    ("python_rows", "expected_residual"),
    [
        ((), ("input_row_id=1",)),
        (({"input_row_id": "2"},), ("input_row_id=1", "input_row_id=2")),
    ],
)
def test_unmatched_rows_are_residuals(
    python_rows: tuple[dict[str, str], ...], expected_residual: tuple[str, ...]
) -> None:
    reference = Stage0Reference(
        "fixture", 1, ({"input_row_id": "1", "legacy_iuphar_class": "Receptor"},)
    )
    before = tuple(dict(row) for row in reference.m_rows)
    report = compare_stage0(reference, python_rows)
    assert report.measured is True
    assert report.changes == ()
    assert report.residual == expected_residual
    assert report.legacy_values == (("input_row_id=1", "Receptor"),)
    assert reference.m_rows == before


def test_computed_fields_do_not_break_the_identity_join() -> None:
    reference = Stage0Reference(
        "fixture", 1, ({"input_row_id": "1", "legacy_iuphar_class": "Receptor"},)
    )
    report = compare_stage0(
        reference,
        (
            {
                "input_row_id": "1",
                "iuphar_class": "Enzyme",
                "local_class": "Enzyme",
                "matched_target_id": "99",
                "iuphar_annotation_status": "available",
                "change_sign": "dictionary_change",
                "explanation": "fixture mapping changed",
            },
        ),
    )
    assert report.residual == ()
    assert report.changes == (
        ("input_row_id=1", "dictionary_change", "fixture mapping changed"),
    )


def test_composite_input_identity_is_preserved() -> None:
    reference = Stage0Reference(
        "fixture", 1, ({"input_row_id": "1", "target_id": "human-target"},)
    )
    report = compare_stage0(
        reference, ({"input_row_id": "1", "target_id": "mouse-target"},)
    )
    assert report.changes == ()
    assert report.residual == (
        "input_row_id=1|target_id=human-target",
        "input_row_id=1|target_id=mouse-target",
    )


def test_result_metadata_without_input_identity_is_not_a_match() -> None:
    report = compare_stage0(
        Stage0Reference("fixture", 1, ({"legacy_iuphar_class": "Receptor"},)),
        ({"iuphar_class": "Receptor"},),
    )
    assert report.residual == ("<missing identity>",)


def test_duplicate_python_rows_preserve_unambiguous_legacy_class() -> None:
    m_row = {"input_row_id": "1", "legacy_iuphar_class": "Receptor"}
    reference = Stage0Reference("stage0", 1, (m_row,))
    python_rows = (
        {"input_row_id": "1", "iuphar_class": "Receptor"},
        {"input_row_id": "1", "iuphar_class": "Enzyme"},
    )
    for rows in (python_rows, tuple(reversed(python_rows))):
        report = compare_stage0(reference, rows)
        assert report.legacy_values == (("input_row_id=1", "Receptor"),)
        assert report.residual == ("input_row_id=1",)
        assert report.changes == ()
        assert report.source_overwritten is False
    assert m_row == {"input_row_id": "1", "legacy_iuphar_class": "Receptor"}
    assert python_rows[0]["iuphar_class"] == "Receptor"
    assert python_rows[1]["iuphar_class"] == "Enzyme"


def test_duplicate_full_keys_stay_residual_in_either_order() -> None:
    reference = Stage0Reference(
        "fixture", 1, ({"input_row_id": "1", "legacy_iuphar_class": "Receptor"},)
    )
    rows = (
        {"input_row_id": "1", "iuphar_class": "Receptor"},
        {"input_row_id": "1", "iuphar_class": "Enzyme"},
    )
    forward = compare_stage0(reference, rows)
    reverse = compare_stage0(reference, tuple(reversed(rows)))
    assert forward == reverse
    assert forward.residual == ("input_row_id=1",)
    assert forward.changes == ()
    assert forward.metrics is not None
    assert forward.metrics["match_status:null"] == 2


@pytest.mark.parametrize("explained", [False, True])
@pytest.mark.parametrize(
    ("field", "old", "new"),
    [
        ("effective_class", "Receptor", "Enzyme"),
        ("decision_status", "resolved", "requires_review"),
        ("effective_source", "iuphar_normalized", "local_rule"),
        ("match_status", "matched", "ambiguous"),
    ],
)
def test_equal_iuphar_class_does_not_hide_a_changed_decision(
    field: str,
    old: str,
    new: str,
    explained: bool,
) -> None:
    previous = {"input_row_id": "1", "iuphar_class": "Receptor", field: old}
    current = {"input_row_id": "1", "iuphar_class": "Receptor", field: new}
    if explained:
        current.update(
            change_sign="direct_local_separation", explanation="fixture change"
        )
    reference = Stage0Reference("fixture", 1, (previous,))
    report = compare_stage0(reference, (current,))
    assert reference.m_rows == (previous,)
    if explained:
        assert report.changes == (
            ("input_row_id=1", "direct_local_separation", "fixture change"),
        )
        assert report.residual == ()
    else:
        assert report.changes == ()
        assert report.residual == ("input_row_id=1",)


def test_absent_historical_decision_is_not_invented_as_unchanged() -> None:
    report = compare_stage0(
        Stage0Reference(
            "fixture", 1, ({"input_row_id": "1", "iuphar_class": "Receptor"},)
        ),
        (
            {
                "input_row_id": "1",
                "iuphar_class": "Receptor",
                "effective_class": "Enzyme",
            },
        ),
    )
    assert report.changes == ()
    assert report.residual == ("input_row_id=1",)
