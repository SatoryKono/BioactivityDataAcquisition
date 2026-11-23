"""TC-12 and M parity: class agreement is not biological accuracy."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from iuphar_target_class.comparison import (
    COMPARED_FIELDS,
    FIELD_GROUPS,
    M_PARITY_REPORT_FILENAME,
    PROOF_VERIFICATION_ARTIFACTS,
    BasisSeal,
    DifferenceBasis,
    ParityInputs,
    Stage0Reference,
    build_m_parity_report,
    compare_stage0,
    register_difference_basis,
    recompute_m_copy,
    seal_difference_bases,
    write_m_parity_report,
)
from iuphar_target_class.rf008_qualification import evaluate_categories

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
_STAGE0_FIELDS = tuple(
    field for field in COMPARED_FIELDS if field != "legacy_iuphar_class"
)
_HISTORICAL_CORPUS_SHA256 = (
    "540826dde55a4afa530acab67149d808383c74bea4d803fce249e92c6ab859d2"
)


def _old_value(field: str) -> str:
    if field in _LIST_FIELDS:
        return json.dumps(["Hydrolase", "alpha"], separators=(",", ":"))
    if field == "iuphar_subclass":
        return "Hydrolase"
    return "historical-value"


def _new_value(field: str) -> str:
    if field in _LIST_FIELDS:
        return json.dumps(["beta", "Transferase"], separators=(",", ":"))
    if field == "iuphar_subclass":
        return "Transferase"
    return "new-value"


def _identity(**fields: str) -> dict[str, str]:
    row = {"input_row_id": "1", "target_id": "T1"}
    row.update(fields)
    return row


def _basis(
    field: str, *, source_pair: str = "original_m:new_result"
) -> DifferenceBasis:
    return register_difference_basis(
        basis_id=f"basis-{field}",
        category="ec_fix",
        statement=f"основание {field} зафиксировано до запуска",
        field=field,
        source_pair=source_pair,
        target_id="T1",
    )


def _comparison(report: dict[str, object], pair: str) -> dict[str, object]:
    comparisons = report["comparisons"]
    assert isinstance(comparisons, list)
    matches = [
        item
        for item in comparisons
        if isinstance(item, dict) and item.get("pair") == pair
    ]
    assert len(matches) == 1
    found = matches[0]
    assert isinstance(found, dict)
    return found


def _differences(comparison: dict[str, object]) -> list[dict[str, object]]:
    differences = comparison["differences"]
    assert isinstance(differences, list)
    typed = [item for item in differences if isinstance(item, dict)]
    assert len(typed) == len(differences)
    return typed


def _field_diff(comparison: dict[str, object], field: str) -> dict[str, object] | None:
    matches = [item for item in _differences(comparison) if item["field"] == field]
    if not matches:
        return None
    assert len(matches) == 1
    return matches[0]


def _availability(comparison: dict[str, object], field: str) -> dict[str, object]:
    rows = comparison["field_availability"]
    assert isinstance(rows, list)
    found = next(
        item for item in rows if isinstance(item, dict) and item["field"] == field
    )
    assert isinstance(found, dict)
    return found


def _report(
    historical: tuple[dict[str, str], ...],
    current: tuple[dict[str, str], ...],
    bases: tuple[DifferenceBasis, ...] = (),
    *,
    basis_seal: BasisSeal | None = None,
    **sources: tuple[dict[str, str], ...] | None,
) -> dict[str, object]:
    seal = basis_seal
    if seal is None and bases:
        seal = seal_difference_bases(bases)
    return build_m_parity_report(
        ParityInputs(
            original_m=historical,
            new_result=current,
            basis_seal=seal,
            saved_excel=sources.get("saved_excel"),
            independent_reference=sources.get("independent_reference"),
            control_run=sources.get("control_run"),
        )
    )


@pytest.mark.parametrize(
    ("field", "old", "new"),
    [
        ("iuphar_subclass", "Hydrolase", "Transferase"),
        ("iuphar_family_paths", "Enzyme/Hydrolase", "Enzyme/Transferase"),
    ],
)
def test_same_class_different_subclass_or_path_is_detected(
    field: str, old: str, new: str
) -> None:
    historical = _identity(iuphar_class="Enzyme", **{field: old})
    current = _identity(iuphar_class="Enzyme", **{field: new})
    stage0 = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert stage0.changes == ()
    assert stage0.residual == ("input_row_id=1|target_id=T1",)
    report = _report((historical,), (current,))
    comparison = _comparison(report, "original_m:new_result")
    difference = _field_diff(comparison, field)
    assert difference is not None
    assert difference["old_value"] == old
    assert difference["new_value"] == new
    assert difference["disposition"] == "unexplained"
    assert difference["target_id"] == "T1"
    assert difference["basis_sha256"] is None
    assert comparison["class_agreement_count"] == 1
    assert comparison["class_disagreement_count"] == 0
    assert report["biological_accuracy"] is None
    assert report["biological_accuracy_accepted"] is False
    assert report["class_agreement_is_biological_accuracy"] is False


@pytest.mark.parametrize("field", _STAGE0_FIELDS)
def test_stage0_detects_every_compared_field(field: str) -> None:
    historical = _identity()
    current = _identity()
    historical[field] = _old_value(field)
    current[field] = _new_value(field)
    if field != "iuphar_class":
        historical["iuphar_class"] = "Enzyme"
        current["iuphar_class"] = "Enzyme"
    before = dict(historical)
    report = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert historical == before
    assert report.changes == ()
    assert report.residual == ("input_row_id=1|target_id=T1",)


def test_stage0_legacy_class_alias_does_not_require_the_legacy_column() -> None:
    historical = {"input_row_id": "1", "legacy_iuphar_class": "Enzyme"}
    current = {"input_row_id": "1", "iuphar_class": "Enzyme"}
    report = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert report.changes == ()
    assert report.residual == ()


def test_identical_semantic_rows_are_not_residual() -> None:
    row = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Hydrolase",
        iuphar_family_paths="Enzyme/Hydrolase",
        effective_class="Enzyme",
        decision_status="resolved",
    )
    report = compare_stage0(Stage0Reference("fixture", 1, (row,)), (dict(row),))
    assert report.changes == ()
    assert report.residual == ()
    assert report.metrics is not None
    assert all(
        "biological" not in key and "class_agreement" not in key
        for key in report.metrics
    )


@pytest.mark.parametrize("field", COMPARED_FIELDS)
def test_each_field_difference_records_target_old_and_new(field: str) -> None:
    historical = _identity(**{field: _old_value(field)})
    current = _identity(**{field: _new_value(field)})
    if field != "iuphar_class":
        historical["iuphar_class"] = "Enzyme"
        current["iuphar_class"] = "Enzyme"
    report = _report((historical,), (current,))
    difference = _field_diff(_comparison(report, "original_m:new_result"), field)
    assert difference is not None
    assert difference["group"] == FIELD_GROUPS[field]
    assert difference["target_id"] == "T1"
    assert difference["old_value"] != difference["new_value"]
    assert difference["disposition"] == "unexplained"
    assert difference["historical_availability"] == "present"
    assert difference["new_availability"] == "present"
    assert "explanation" not in difference
    assert "statement" not in difference


@pytest.mark.parametrize("field", COMPARED_FIELDS)
def test_equal_present_field_is_not_a_difference(field: str) -> None:
    row = _identity(**{field: _old_value(field)})
    comparison = _comparison(_report((row,), (dict(row),)), "original_m:new_result")
    assert _field_diff(comparison, field) is None
    availability = _availability(comparison, field)
    assert availability["historical_present"] == 1
    assert availability["new_present"] == 1
    assert availability["historical_unavailable"] == 0


@pytest.mark.parametrize("field", COMPARED_FIELDS)
def test_missing_historical_field_is_not_invented(field: str) -> None:
    historical = _identity()
    current = _identity(**{field: _new_value(field)})
    report = _report((historical,), (current,), (_basis(field),))
    comparison = _comparison(report, "original_m:new_result")
    difference = _field_diff(comparison, field)
    assert difference is not None
    assert difference["disposition"] == "historical_unavailable"
    assert difference["old_value"] is None
    assert difference["new_value"] == _canonical_expected(field, _new_value(field))
    assert difference["basis_id"] is None
    assert difference["basis_sha256"] is None
    assert comparison["class_agreement_count"] == 0
    payload = json.dumps(report, ensure_ascii=False)
    assert "resolved" not in payload
    assert "requires_review" not in payload
    assert "family_only" not in payload


@pytest.mark.parametrize("field", COMPARED_FIELDS)
def test_missing_new_field_is_not_filled_from_history(field: str) -> None:
    historical = _identity(**{field: _old_value(field)})
    current = _identity()
    comparison = _comparison(
        _report((historical,), (current,), (_basis(field),)),
        "original_m:new_result",
    )
    difference = _field_diff(comparison, field)
    assert difference is not None
    assert difference["disposition"] == "new_unavailable"
    assert difference["new_value"] is None
    assert difference["old_value"] == _canonical_expected(field, _old_value(field))
    assert difference["basis_id"] is None


@pytest.mark.parametrize("field", COMPARED_FIELDS)
def test_field_missing_on_both_sides_has_no_invented_status(field: str) -> None:
    row = _identity()
    comparison = _comparison(_report((row,), (dict(row),)), "original_m:new_result")
    assert _field_diff(comparison, field) is None
    availability = _availability(comparison, field)
    assert availability["historical_unavailable"] == 1
    assert availability["new_unavailable"] == 1
    assert availability["historical_present"] == 0
    assert availability["new_present"] == 0


@pytest.mark.parametrize("field", COMPARED_FIELDS)
def test_empty_string_is_present_historical_value(field: str) -> None:
    historical = _identity(**{field: ""})
    current = _identity(**{field: _new_value(field)})
    difference = _field_diff(
        _comparison(_report((historical,), (current,)), "original_m:new_result"),
        field,
    )
    assert difference is not None
    assert difference["historical_availability"] == "present"
    assert difference["old_value"] == ""
    assert difference["disposition"] == "unexplained"


def test_path_order_is_stable_and_a_different_path_is_kept() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            ["Enzyme/Transferase", "Enzyme/Hydrolase"], separators=(",", ":")
        ),
    )
    reordered = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            ["Enzyme/Hydrolase", "Enzyme/Transferase"], separators=(",", ":")
        ),
    )
    changed = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(["Enzyme/Isomerase"], separators=(",", ":")),
    )
    same = _comparison(_report((historical,), (reordered,)), "original_m:new_result")
    assert _field_diff(same, "iuphar_family_paths") is None
    difference = _field_diff(
        _comparison(_report((historical,), (changed,)), "original_m:new_result"),
        "iuphar_family_paths",
    )
    assert difference is not None
    assert difference["disposition"] == "unexplained"
    assert difference["new_value"] == '["Enzyme/Isomerase"]'


def test_post_hoc_explanation_does_not_qualify_a_difference() -> None:
    historical = _identity(iuphar_class="Enzyme", iuphar_subclass="Hydrolase")
    current = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Transferase",
        change_sign="ec_fix",
        explanation="свободная постфактум строка не является основанием",
    )
    report = _report((historical,), (current,))
    difference = _field_diff(
        _comparison(report, "original_m:new_result"), "iuphar_subclass"
    )
    assert difference is not None
    assert difference["disposition"] == "unexplained"
    assert difference["post_hoc_explanation_ignored"] is True
    assert difference["basis_sha256"] is None
    payload = json.dumps(report, ensure_ascii=False)
    assert "свободная постфактум строка" not in payload


def test_preregistered_basis_qualifies_and_its_hash_is_stable() -> None:
    historical = _identity(iuphar_class="Enzyme", iuphar_subclass="Hydrolase")
    current = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Transferase",
        explanation="эта строка остаётся неквалифицирующей",
    )
    basis = register_difference_basis(
        basis_id="ec-subclass",
        category="ec_fix",
        statement="EC-исправление подкласса зафиксировано до запуска",
        field="iuphar_subclass",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    again = register_difference_basis(
        basis_id="ec-subclass",
        category="ec_fix",
        statement="EC-исправление подкласса зафиксировано до запуска",
        field="iuphar_subclass",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    assert again.basis_sha256 == basis.basis_sha256
    report = _report((historical,), (current,), (basis,))
    difference = _field_diff(
        _comparison(report, "original_m:new_result"), "iuphar_subclass"
    )
    assert difference is not None
    assert difference["disposition"] == "allowed"
    assert difference["basis_id"] == "ec-subclass"
    assert difference["basis_sha256"] == basis.basis_sha256
    assert difference["post_hoc_explanation_ignored"] is True
    payload = json.dumps(report, ensure_ascii=False)
    assert "эта строка остаётся неквалифицирующей" not in payload
    assert "EC-исправление подкласса зафиксировано до запуска" in payload


def test_forged_basis_hash_is_rejected() -> None:
    basis = _basis("iuphar_subclass")
    forged = replace(basis, basis_sha256="0" * 64)
    with pytest.raises(ValueError, match="хеш основания"):
        _report((_identity(),), (_identity(),), (forged,))


def test_unknown_basis_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="категория"):
        register_difference_basis(
            basis_id="free",
            category="post-hoc",
            statement="свободная категория",
            field="iuphar_subclass",
            source_pair="original_m:new_result",
        )


def test_sources_stay_separated_and_bases_do_not_cross_pairs() -> None:
    original = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Hydrolase",
        iuphar_family_paths="Enzyme/Hydrolase",
    )
    excel = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Transferase",
        iuphar_family_paths="Enzyme/Hydrolase",
    )
    current = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Hydrolase",
        iuphar_family_paths="Enzyme/Transferase",
    )
    reference = _identity(
        iuphar_class="Enzyme",
        iuphar_subclass="Isomerase",
        iuphar_family_paths="Enzyme/Isomerase",
    )
    before = dict(original)
    basis = register_difference_basis(
        basis_id="path-release",
        category="dictionary_release",
        statement="выпуск словаря для пути зафиксирован до запуска",
        field="iuphar_family_paths",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    report = _report(
        (original,),
        (current,),
        (basis,),
        saved_excel=(excel,),
        independent_reference=(reference,),
    )
    assert original == before
    original_pair = _comparison(report, "original_m:new_result")
    excel_pair = _comparison(report, "saved_excel:new_result")
    reference_pair = _comparison(report, "independent_reference:new_result")
    original_path = _field_diff(original_pair, "iuphar_family_paths")
    excel_subclass = _field_diff(excel_pair, "iuphar_subclass")
    reference_subclass = _field_diff(reference_pair, "iuphar_subclass")
    assert original_path is not None and original_path["disposition"] == "allowed"
    assert excel_subclass is not None and excel_subclass["disposition"] == "unexplained"
    assert excel_subclass["basis_id"] is None
    assert reference_subclass is not None
    assert reference_subclass["old_value"] == "Isomerase"
    assert reference_subclass["disposition"] == "unexplained"
    assert _field_diff(original_pair, "iuphar_subclass") is None


def test_duplicate_identity_is_not_silently_deduplicated() -> None:
    historical = (
        _identity(iuphar_subclass="Hydrolase"),
        _identity(iuphar_subclass="Transferase"),
    )
    current = (_identity(iuphar_subclass="Hydrolase"),)
    forward = _report(historical, current)
    reverse = _report(tuple(reversed(historical)), current)
    assert forward == reverse
    comparison = _comparison(forward, "original_m:new_result")
    assert comparison["class_agreement_count"] == 0
    identity = _field_diff(comparison, "identity")
    assert identity is not None
    assert identity["disposition"] == "unexplained"
    assert _field_diff(comparison, "iuphar_subclass") is None
    basis = register_difference_basis(
        basis_id="dedup",
        category="nondeterministic_dedup_removed",
        statement="устранение недетерминированного dedup зафиксировано до запуска",
        field="identity",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    allowed = _comparison(
        _report(historical, current, (basis,)), "original_m:new_result"
    )
    identity = _field_diff(allowed, "identity")
    assert identity is not None
    assert identity["disposition"] == "allowed"
    assert identity["basis_sha256"] == basis.basis_sha256
    assert _field_diff(allowed, "iuphar_subclass") is None
    changed_class = (
        _identity(iuphar_class="Enzyme"),
        _identity(iuphar_class="Enzyme"),
    )
    receptor = (_identity(iuphar_class="Receptor"),)
    hidden = _comparison(
        _report(changed_class, receptor, (basis,)), "original_m:new_result"
    )
    hidden_identity = _field_diff(hidden, "identity")
    hidden_class = _field_diff(hidden, "iuphar_class")
    assert hidden_identity is not None and hidden_identity["disposition"] == "allowed"
    assert hidden_class is not None
    assert hidden_class["disposition"] == "unexplained"
    assert hidden_class["basis_id"] is None
    assert hidden_class["old_value"] == "Enzyme"
    assert hidden_class["new_value"] == "Receptor"
    assert hidden["unexplained_count"] == 1
    assert hidden["allowed_count"] == 1
    lost = _comparison(_report(historical, (), (basis,)), "original_m:new_result")
    lost_identity = _field_diff(lost, "identity")
    assert lost_identity is not None
    assert lost_identity["disposition"] == "unexplained"
    assert lost_identity["basis_id"] is None
    assert lost["class_agreement_count"] == 0


def test_tied_historical_duplicates_use_a_stable_signature() -> None:
    enzyme = _identity(iuphar_class="Enzyme", iuphar_subclass="Hydrolase")
    receptor = _identity(iuphar_class="Receptor", iuphar_subclass="Transferase")
    survivor = (_identity(iuphar_class="Enzyme", iuphar_subclass="Transferase"),)
    dedup = register_difference_basis(
        basis_id="dedup-tie",
        category="nondeterministic_dedup_removed",
        statement="устранение недетерминированного dedup зафиксировано до запуска",
        field="identity",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    subclass = register_difference_basis(
        basis_id="subclass-tie",
        category="ec_fix",
        statement="смена подкласса зафиксирована до запуска",
        field="iuphar_subclass",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    seal = seal_difference_bases((dedup, subclass))
    forward = _comparison(
        _report((enzyme, receptor), survivor, basis_seal=seal),
        "original_m:new_result",
    )
    reverse = _comparison(
        _report((receptor, enzyme), survivor, basis_seal=seal),
        "original_m:new_result",
    )
    assert forward == reverse
    assert forward["unexplained_count"] == reverse["unexplained_count"] == 0
    subclass_diff = _field_diff(forward, "iuphar_subclass")
    assert subclass_diff is not None
    assert subclass_diff["disposition"] == "allowed"
    assert subclass_diff["old_value"] == "Hydrolase"
    assert subclass_diff["new_value"] == "Transferase"
    assert _field_diff(forward, "iuphar_class") is None


def test_rows_without_identity_are_not_a_class_match() -> None:
    historical = {"iuphar_class": "Enzyme"}
    current = {"iuphar_class": "Enzyme"}
    comparison = _comparison(
        _report((historical,), (current,)), "original_m:new_result"
    )
    assert comparison["measured"] is True
    assert comparison["class_agreement_count"] == 0
    assert comparison["semantic_mismatch_count"] == 1
    identity = _field_diff(comparison, "identity")
    assert identity is not None
    assert identity["disposition"] == "unexplained"
    assert identity["target_id"] == ""


def test_provenance_object_formatting_is_not_a_difference() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        provenance=json.dumps({"b": "2", "a": "1"}, indent=2),
    )
    current = _identity(
        iuphar_class="Enzyme",
        provenance=json.dumps(
            {"a": "1", "b": "2"}, sort_keys=True, separators=(",", ":")
        ),
    )
    changed = _identity(
        iuphar_class="Enzyme",
        provenance=json.dumps({"a": "9", "b": "2"}, separators=(",", ":")),
    )
    stage0 = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert stage0.residual == ()
    assert stage0.changes == ()
    same = _comparison(_report((historical,), (current,)), "original_m:new_result")
    assert _field_diff(same, "provenance") is None
    assert same["semantic_mismatch_count"] == 0
    difference = _field_diff(
        _comparison(_report((historical,), (changed,)), "original_m:new_result"),
        "provenance",
    )
    assert difference is not None
    assert difference["disposition"] == "unexplained"
    assert difference["old_value"] == '{"a":"1","b":"2"}'
    assert difference["new_value"] == '{"a":"9","b":"2"}'
    plain = _identity(iuphar_class="Enzyme", provenance="rule-a")
    other = _identity(iuphar_class="Enzyme", provenance="rule-b")
    text = _field_diff(
        _comparison(_report((plain,), (other,)), "original_m:new_result"),
        "provenance",
    )
    assert text is not None
    assert text["old_value"] == "rule-a"
    assert text["new_value"] == "rule-b"


def test_structured_family_paths_ignore_key_and_record_order() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            [
                {
                    "family_id": "b",
                    "leaf_to_root": "b",
                    "root_to_leaf": ["root", "b"],
                },
                {
                    "root_to_leaf": ["root", "a"],
                    "family_id": "a",
                    "leaf_to_root": "a",
                },
            ]
        ),
    )
    current = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            [
                {
                    "leaf_to_root": "a",
                    "root_to_leaf": ["root", "a"],
                    "family_id": "a",
                },
                {
                    "family_id": "b",
                    "root_to_leaf": ["root", "b"],
                    "leaf_to_root": "b",
                },
            ],
            indent=2,
        ),
    )
    stage0 = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert stage0.residual == ()
    assert stage0.changes == ()
    comparison = _comparison(
        _report((historical,), (current,)), "original_m:new_result"
    )
    assert _field_diff(comparison, "iuphar_family_paths") is None
    assert comparison["semantic_mismatch_count"] == 0


def test_family_path_node_order_is_a_difference() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            [
                {
                    "family_id": "a",
                    "leaf_to_root": "a",
                    "root_to_leaf": ["root", "a"],
                }
            ],
            separators=(",", ":"),
        ),
    )
    current = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            [
                {
                    "root_to_leaf": ["a", "root"],
                    "leaf_to_root": "a",
                    "family_id": "a",
                }
            ]
        ),
    )
    stage0 = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert stage0.residual == ("input_row_id=1|target_id=T1",)
    difference = _field_diff(
        _comparison(_report((historical,), (current,)), "original_m:new_result"),
        "iuphar_family_paths",
    )
    assert difference is not None
    assert difference["disposition"] == "unexplained"
    assert difference["old_value"] == (
        '[{"family_id":"a","leaf_to_root":"a","root_to_leaf":["root","a"]}]'
    )
    assert difference["new_value"] == (
        '[{"family_id":"a","leaf_to_root":"a","root_to_leaf":["a","root"]}]'
    )


def test_input_validation_errors_are_compared() -> None:
    historical = _identity(
        input_validation_status="invalid_input",
        input_errors=json.dumps(["beta", "alpha"], separators=(",", ":")),
    )
    reordered = _identity(
        input_validation_status="invalid_input",
        input_errors=json.dumps(["alpha", "beta"], separators=(",", ":")),
    )
    changed = _identity(
        input_validation_status="invalid_input",
        input_errors=json.dumps(["gamma"], separators=(",", ":")),
    )
    same = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (reordered,))
    different = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (changed,))
    assert same.residual == ()
    assert different.residual == ("input_row_id=1|target_id=T1",)
    same_report = _comparison(
        _report((historical,), (reordered,)), "original_m:new_result"
    )
    changed_report = _comparison(
        _report((historical,), (changed,)), "original_m:new_result"
    )
    assert _field_diff(same_report, "input_errors") is None
    assert same_report["semantic_mismatch_count"] == 0
    difference = _field_diff(changed_report, "input_errors")
    assert difference is not None
    assert difference["group"] == "local_effective"
    assert difference["disposition"] == "unexplained"
    assert difference["old_value"] == '["alpha","beta"]'
    assert difference["new_value"] == '["gamma"]'
    assert _field_diff(changed_report, "input_validation_status") is None


def test_conflict_codes_change_is_detected() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        decision_status="requires_review",
        conflict_codes=json.dumps(["beta", "alpha"], separators=(",", ":")),
    )
    reordered = _identity(
        iuphar_class="Enzyme",
        decision_status="requires_review",
        conflict_codes=json.dumps(["alpha", "beta"], separators=(",", ":")),
    )
    changed = _identity(
        iuphar_class="Enzyme",
        decision_status="requires_review",
        conflict_codes=json.dumps(["gamma"], separators=(",", ":")),
    )
    same = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (reordered,))
    different = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (changed,))
    assert same.residual == ()
    assert different.residual == ("input_row_id=1|target_id=T1",)
    same_report = _comparison(
        _report((historical,), (reordered,)), "original_m:new_result"
    )
    changed_report = _comparison(
        _report((historical,), (changed,)), "original_m:new_result"
    )
    assert _field_diff(same_report, "conflict_codes") is None
    assert same_report["semantic_mismatch_count"] == 0
    difference = _field_diff(changed_report, "conflict_codes")
    assert difference is not None
    assert difference["group"] == "local_effective"
    assert difference["disposition"] == "unexplained"
    assert difference["old_value"] == '["alpha","beta"]'
    assert difference["new_value"] == '["gamma"]'
    assert _field_diff(changed_report, "decision_status") is None
    assert _field_diff(changed_report, "iuphar_class") is None


def test_reordered_family_paths_are_not_a_stage0_residual() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            ["Enzyme/Transferase", "Enzyme/Hydrolase"], separators=(",", ":")
        ),
    )
    reordered = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(
            ["Enzyme/Hydrolase", "Enzyme/Transferase"], separators=(",", ":")
        ),
    )
    changed = _identity(
        iuphar_class="Enzyme",
        iuphar_family_paths=json.dumps(["Enzyme/Isomerase"], separators=(",", ":")),
    )
    same = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (reordered,))
    different = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (changed,))
    assert same.residual == ()
    assert same.changes == ()
    assert different.residual == ("input_row_id=1|target_id=T1",)
    candidates = _identity(
        iuphar_class="Enzyme",
        candidate_target_ids=json.dumps(["1", "2"], separators=(",", ":")),
    )
    reordered_candidates = _identity(
        iuphar_class="Enzyme",
        candidate_target_ids=json.dumps(["2", "1"], separators=(",", ":")),
    )
    stage0 = compare_stage0(
        Stage0Reference("fixture", 1, (candidates,)), (reordered_candidates,)
    )
    assert stage0.residual == ()
    assert stage0.changes == ()


@pytest.mark.parametrize(
    "field",
    ("iuphar_mapping_rule_id", "local_rule_ids", "rules_version", "snapshot_id"),
)
def test_same_class_different_rule_provenance_is_detected(field: str) -> None:
    historical = _identity(iuphar_class="Enzyme", **{field: _old_value(field)})
    current = _identity(iuphar_class="Enzyme", **{field: _new_value(field)})
    stage0 = compare_stage0(Stage0Reference("fixture", 1, (historical,)), (current,))
    assert stage0.residual == ("input_row_id=1|target_id=T1",)
    difference = _field_diff(
        _comparison(_report((historical,), (current,)), "original_m:new_result"),
        field,
    )
    assert difference is not None
    assert difference["group"] == "provenance"
    assert difference["disposition"] == "unexplained"
    comparison = _comparison(
        _report((historical,), (current,)), "original_m:new_result"
    )
    assert comparison["class_agreement_count"] == 1
    assert comparison["class_disagreement_count"] == 0


def test_selected_target_and_published_family_ids_are_compared() -> None:
    historical = _identity(
        iuphar_class="Enzyme",
        matched_target_id="1",
        candidate_target_ids=json.dumps(["1", "2"], separators=(",", ":")),
        iuphar_family_ids=json.dumps(["10"], separators=(",", ":")),
    )
    current = _identity(
        iuphar_class="Enzyme",
        matched_target_id="2",
        candidate_target_ids=json.dumps(["2", "1"], separators=(",", ":")),
        iuphar_family_ids=json.dumps(["20"], separators=(",", ":")),
    )
    comparison = _comparison(
        _report((historical,), (current,)), "original_m:new_result"
    )
    selected = _field_diff(comparison, "matched_target_id")
    families = _field_diff(comparison, "iuphar_family_ids")
    assert selected is not None and selected["old_value"] == "1"
    assert selected["new_value"] == "2"
    assert selected["disposition"] == "unexplained"
    assert families is not None and families["old_value"] == '["10"]'
    assert families["new_value"] == '["20"]'
    assert _field_diff(comparison, "candidate_target_ids") is None
    assert comparison["class_agreement_count"] == 1
    assert comparison["semantic_mismatch_count"] == 2


def test_parity_report_refuses_to_follow_a_symlink(tmp_path: Path) -> None:
    proof = tmp_path / "classification.json"
    proof.write_text("proof-original", encoding="utf-8")
    link = tmp_path / M_PARITY_REPORT_FILENAME
    link.symlink_to(proof.name)
    report = _report((), ())
    with pytest.raises(ValueError, match="symlink"):
        write_m_parity_report(report, tmp_path)
    assert proof.read_text(encoding="utf-8") == "proof-original"
    assert link.is_symlink()


def test_basis_added_after_the_seal_is_rejected() -> None:
    historical = _identity(iuphar_class="Enzyme", iuphar_subclass="Hydrolase")
    seal = seal_difference_bases(
        (
            register_difference_basis(
                basis_id="sealed-ec",
                category="ec_fix",
                statement="EC-исправление зафиксировано до сравнения",
                field="iuphar_subclass",
                source_pair="original_m:new_result",
                target_id="T1",
            ),
        )
    )
    current = _identity(iuphar_class="Enzyme", iuphar_subclass="Transferase")
    extra = register_difference_basis(
        basis_id="late-path",
        category="dictionary_release",
        statement="позднее основание не входит в печать",
        field="iuphar_family_paths",
        source_pair="original_m:new_result",
        target_id="T1",
    )
    tampered = replace(seal, bases=(*seal.bases, extra))
    with pytest.raises(ValueError, match="печать оснований"):
        _report((historical,), (current,), basis_seal=tampered)
    report = _report((historical,), (current,), basis_seal=seal)
    assert report["basis_set_sha256"] == seal.basis_set_sha256
    difference = _field_diff(
        _comparison(report, "original_m:new_result"), "iuphar_subclass"
    )
    assert difference is not None
    assert difference["disposition"] == "allowed"
    assert difference["basis_id"] == "sealed-ec"


def test_recompute_uses_a_copy_and_restores_originals() -> None:
    original = ({"target_id": "T1", "iuphar_class": "Enzyme"},)

    def flip(rows: tuple[dict[str, str], ...]) -> tuple[dict[str, str], ...]:
        rows[0]["iuphar_class"] = "Receptor"
        return rows

    produced = recompute_m_copy(original, flip)
    assert original[0]["iuphar_class"] == "Enzyme"
    assert produced[0]["iuphar_class"] == "Receptor"

    def corrupt(rows: tuple[dict[str, str], ...]) -> tuple[dict[str, str], ...]:
        original[0]["iuphar_class"] = "Receptor"
        return rows

    with pytest.raises(RuntimeError, match="исходные строки M"):
        recompute_m_copy(original, corrupt)
    assert original[0]["iuphar_class"] == "Enzyme"


def test_empty_historical_set_is_not_class_agreement(tmp_path: Path) -> None:
    report = _report((), ({"input_row_id": "1", "iuphar_class": "Enzyme"},))
    comparison = _comparison(report, "original_m:new_result")
    assert comparison["measured"] is False
    assert comparison["class_agreement_count"] is None
    assert comparison["differences"] == []
    assert report["biological_accuracy"] is None
    sources = report["sources"]
    assert isinstance(sources, dict)
    excel = sources["saved_excel"]
    assert isinstance(excel, dict)
    assert excel["available"] is False
    assert all(
        isinstance(item, dict) and item["pair"] != "saved_excel:new_result"
        for item in report["comparisons"]
        if isinstance(report["comparisons"], list)
    )
    proof = tmp_path / "stages_0_3_report.json"
    proof.write_text("proof-original", encoding="utf-8")
    destination = write_m_parity_report(report, tmp_path)
    assert destination.name == M_PARITY_REPORT_FILENAME
    assert destination.name not in PROOF_VERIFICATION_ARTIFACTS
    assert proof.read_text(encoding="utf-8") == "proof-original"
    assert (
        write_m_parity_report(report, tmp_path).read_bytes() == destination.read_bytes()
    )
    with pytest.raises(ValueError, match="m-parity-report"):
        write_m_parity_report({"artifact": "stages_0_3_report"}, tmp_path)


def test_fixed_1960_historical_rows_and_control_intersection_use_separate_bases() -> (
    None
):
    historical = _historical_1960()
    seal = seal_difference_bases(_corpus_bases())
    current = _new_result(historical)
    control = _control_run(historical)
    before = tuple(dict(row) for row in historical)
    forward = _report(historical, current, basis_seal=seal, control_run=control)
    backward = _report(
        tuple(reversed(historical)),
        tuple(reversed(current)),
        basis_seal=seal,
        control_run=tuple(reversed(control)),
    )
    assert forward["basis_set_sha256"] == seal.basis_set_sha256
    assert historical == before
    assert forward == backward
    sources = forward["sources"]
    assert isinstance(sources, dict)
    original_source = sources["original_m"]
    assert isinstance(original_source, dict)
    assert original_source["row_count"] == 1960
    assert original_source["sha256"] == _HISTORICAL_CORPUS_SHA256
    pair = _comparison(forward, "original_m:new_result")
    assert pair["class_agreement_count"] == 1960
    assert pair["class_disagreement_count"] == 0
    assert pair["unexplained_count"] != pair["class_agreement_count"]
    assert forward["biological_accuracy"] is None
    assert forward["class_agreement_is_biological_accuracy"] is False
    subclass = [
        item for item in _differences(pair) if item["field"] == "iuphar_subclass"
    ]
    allowed = [item for item in subclass if item["disposition"] == "allowed"]
    unexplained = [item for item in subclass if item["disposition"] == "unexplained"]
    assert [item["target_id"] for item in allowed] == ["T0000"]
    assert allowed[0]["basis_id"] == "t0000-ec-subclass"
    assert (
        len(unexplained) == len([index for index in range(1960) if index % 11 == 0]) - 1
    )
    assert all(item["basis_sha256"] is None for item in unexplained)
    paths = [
        item for item in _differences(pair) if item["field"] == "iuphar_family_paths"
    ]
    path_indexes = [
        index for index in range(1960) if index % 13 == 0 and index % 11 != 0
    ]
    assert len(paths) == len(path_indexes)
    assert all(item["disposition"] == "unexplained" for item in paths)
    assert all(item["old_value"] != item["new_value"] for item in paths)
    for field_name, basis_id in (
        ("iuphar_type_raw", "ec-raw-type"),
        ("family_ids", "dictionary-release"),
        ("effective_source", "direct-local"),
    ):
        matched = [item for item in _differences(pair) if item["field"] == field_name]
        assert matched
        assert all(
            item["disposition"] == "allowed" and item["basis_id"] == basis_id
            for item in matched
        )
    row_11 = next(item for item in unexplained if item["target_id"] == "T0011")
    assert row_11["post_hoc_explanation_ignored"] is True
    provenance = [
        item
        for item in _differences(pair)
        if item["field"] == "provenance"
        and item["disposition"] == "historical_unavailable"
    ]
    assert len(provenance) == len([index for index in range(1960) if index % 5 == 0])
    assert all(item["old_value"] is None for item in provenance)
    payload = json.dumps(forward, ensure_ascii=False)
    assert "постфактум причина не должна пройти" not in payload
    control_pair = _comparison(forward, "original_m:control_run")
    assert control_pair["intersection_only"] is True
    control_subclass = [
        item
        for item in _differences(control_pair)
        if item["field"] == "iuphar_subclass"
    ]
    assert control_subclass
    assert all(item["disposition"] == "allowed" for item in control_subclass)
    assert all(item["basis_id"] == "control-dedup" for item in control_subclass)
    assert all(item["basis_id"] != "t0000-ec-subclass" for item in control_subclass)
    outside = control_pair["outside_intersection"]
    assert isinstance(outside, list)
    assert "input_row_id=11|target_id=T0011" in outside


def _canonical_expected(field: str, value: str) -> str:
    if field not in _LIST_FIELDS:
        return value
    loaded = json.loads(value)
    assert isinstance(loaded, list)
    return json.dumps(sorted(loaded), ensure_ascii=False, separators=(",", ":"))


def _historical_1960() -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for index in range(1960):
        target_id = f"T{index:04d}"
        subclass = "Hydrolase" if index % 2 == 0 else "Transferase"
        row = {
            "candidate_target_ids": json.dumps([target_id], separators=(",", ":")),
            "capability": "family_only",
            "decision_status": "resolved",
            "effective_class": "Enzyme",
            "effective_source": "iuphar_normalized",
            "effective_subclasses": json.dumps([subclass], separators=(",", ":")),
            "family_ids": json.dumps([str(index % 50)], separators=(",", ":")),
            "input_row_id": str(index),
            "iuphar_annotation_status": "available",
            "iuphar_class": "Enzyme",
            "iuphar_class_candidates": json.dumps(["Enzyme"], separators=(",", ":")),
            "iuphar_family_paths": json.dumps(
                [f"Enzyme/{subclass}/{index}"], separators=(",", ":")
            ),
            "iuphar_subclass": subclass,
            "iuphar_type_raw": "enzyme",
            "local_candidates": "[]",
            "local_class": "Enzyme",
            "local_status": "supported",
            "local_subclasses": json.dumps([subclass], separators=(",", ":")),
            "match_status": "matched",
            "target_id": target_id,
        }
        if index % 5 != 0:
            row["provenance"] = f"m-snapshot:{index}"
        rows.append(row)
    return tuple(rows)


def _new_result(
    historical: tuple[dict[str, str], ...],
) -> tuple[dict[str, str], ...]:
    produced: list[dict[str, str]] = []
    for index, row in enumerate(historical):
        current = dict(row)
        if "provenance" not in current:
            current["provenance"] = "run-fixed"
        if index % 11 == 0:
            current["iuphar_subclass"] = (
                "Transferase" if row["iuphar_subclass"] == "Hydrolase" else "Hydrolase"
            )
        if index % 13 == 0 and index % 11 != 0:
            current["iuphar_family_paths"] = json.dumps(
                [f"Enzyme/{row['iuphar_subclass']}/{index}/extra"],
                separators=(",", ":"),
            )
        if index % 17 == 0:
            current["iuphar_type_raw"] = "ec:3.1"
        if index % 19 == 0:
            current["family_ids"] = json.dumps(["released"], separators=(",", ":"))
        if index % 23 == 0:
            current["effective_source"] = "local_rule"
        if index == 11:
            current["explanation"] = "постфактум причина не должна пройти"
            current["change_sign"] = "ec_fix"
        produced.append(current)
    return tuple(produced)


def _control_run(
    historical: tuple[dict[str, str], ...],
) -> tuple[dict[str, str], ...]:
    selected: list[dict[str, str]] = []
    for index, row in enumerate(historical):
        if index % 29 != 0:
            continue
        current = dict(row)
        current["iuphar_subclass"] = (
            "Transferase" if row["iuphar_subclass"] == "Hydrolase" else "Hydrolase"
        )
        selected.append(current)
    return tuple(selected)


def _corpus_bases() -> tuple[DifferenceBasis, ...]:
    return (
        register_difference_basis(
            basis_id="t0000-ec-subclass",
            category="ec_fix",
            statement="EC-исправление подкласса T0000 зафиксировано до запуска",
            field="iuphar_subclass",
            source_pair="original_m:new_result",
            target_id="T0000",
        ),
        register_difference_basis(
            basis_id="ec-raw-type",
            category="ec_fix",
            statement="EC-исправление raw type зафиксировано до запуска",
            field="iuphar_type_raw",
            source_pair="original_m:new_result",
            target_id="",
        ),
        register_difference_basis(
            basis_id="dictionary-release",
            category="dictionary_release",
            statement="выпуск словаря family ids зафиксирован до запуска",
            field="family_ids",
            source_pair="original_m:new_result",
            target_id="",
        ),
        register_difference_basis(
            basis_id="direct-local",
            category="direct_local_separation",
            statement="разделение direct и local зафиксировано до запуска",
            field="effective_source",
            source_pair="original_m:new_result",
            target_id="",
        ),
        register_difference_basis(
            basis_id="control-dedup",
            category="nondeterministic_dedup_removed",
            statement="устранение недетерминированного dedup контрольного пересечения зафиксировано до запуска",
            field="iuphar_subclass",
            source_pair="original_m:control_run",
            target_id="",
        ),
    )


def test_rf008_direct_class_changes_require_evidence() -> None:
    report = evaluate_categories(("comparison_evidence",))
    assert report["unexplained_error_count"] == 0
    cases = report["cases"]
    assert isinstance(cases, list)
    by_id = {str(item["case_id"]): item for item in cases if isinstance(item, dict)}
    unexplained = by_id["cmp-unexplained-direct-class"]["observed"]
    explained = by_id["cmp-explained-direct-class"]["observed"]
    assert unexplained == {"change_count": 0, "residual_count": 1}
    assert explained == {"change_count": 1, "residual_count": 0}
    assert by_id["cmp-unexplained-direct-class"]["claim"] == "engineering_rule"
