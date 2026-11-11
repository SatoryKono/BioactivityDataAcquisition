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
    before = reference.m_rows
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
