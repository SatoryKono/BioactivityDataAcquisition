"""RF-008: independent expectations, separate from the old 6-case receipt."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iuphar_target_class.rf008_qualification import (
    REQUIRED_CATEGORIES,
    qualification_materials,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE = _ROOT / "data" / "iuphar_target_class" / "acceptance" / "rf008"


def _document(name: str) -> dict[str, object]:
    payload = json.loads((_PACKAGE / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = f"{name} is not an object"
        raise TypeError(message)
    return payload


def test_committed_materials_match_the_offline_rebuild() -> None:
    rebuilt = qualification_materials()
    for name, payload in rebuilt.items():
        assert (_PACKAGE / name).read_bytes() == payload


def test_expectations_are_not_classifier_output() -> None:
    expectations = _document("independent_expectations.json")
    assert expectations["built_from_classifier_output"] is False
    cases = expectations["cases"]
    assert isinstance(cases, list)
    assert cases
    for case in cases:
        assert isinstance(case, dict)
        assert "observed" not in case
        assert case["evidence"]


def test_engineering_and_biological_acceptance_stay_separate() -> None:
    receipt = _document("qualification_receipt.json")
    engineering = receipt["engineering_acceptance"]
    biological = receipt["biological_acceptance"]
    assert isinstance(engineering, dict)
    assert isinstance(biological, dict)
    assert engineering["status"] == "PASS"
    assert engineering["unexplained_error_count"] == 0
    assert engineering["independent_case_count"] == 37
    assert biological["biological_accuracy_accepted"] is False
    assert receipt["enrich_admitted"] is False
    assert receipt["admitted_identity_or_direct_class_changes"] == []
    assert receipt["unexplained_case_ids"] == []


def test_old_receipt_and_diagnostic_counts_are_not_acceptance_kpis() -> None:
    receipt = _document("qualification_receipt.json")
    historical = receipt["historical_acceptance_not_reused"]
    diagnostic = receipt["diagnostic_observations_not_acceptance_kpis"]
    assert isinstance(historical, dict)
    assert isinstance(diagnostic, dict)
    assert historical["reviewed_case_count"] == 6
    assert historical["unreviewed_case_count"] == 994
    assert historical["reused_as_new_semantics_admission"] is False
    assert diagnostic["acceptance_kpi"] is False
    assert diagnostic["counterfactual_matched"] == 633
    assert diagnostic["intersection_matches"] == 374
    engineering = receipt["engineering_acceptance"]
    assert isinstance(engineering, dict)
    assert 633 not in engineering.values()
    assert 374 not in engineering.values()


def test_control_registry_keeps_unreviewed_rows_unverified() -> None:
    partition = _document("cohort_partition.json")
    verified = partition["verified_expectations"]
    acceptable = partition["acceptable_incompleteness"]
    unsupported = partition["unsupported"]
    unreviewed = partition["unreviewed"]
    assert isinstance(verified, dict)
    assert isinstance(acceptable, dict)
    assert isinstance(unsupported, dict)
    assert isinstance(unreviewed, dict)
    assert partition["inputs"] == 1000
    assert partition["row_identities_in_repository"] is False
    assert verified["count"] == 0
    assert acceptable["count"] == 189
    assert unsupported["count"] == 147
    assert unreviewed["count"] == 664
    assert unreviewed["declared_verified"] is False
    assert (
        verified["count"]
        + acceptable["count"]
        + unsupported["count"]
        + unreviewed["count"]
        == 1000
    )


def test_coverage_matrix_names_every_required_category() -> None:
    receipt = _document("qualification_receipt.json")
    coverage = receipt["coverage"]
    assert isinstance(coverage, list)
    present = {item["category"] for item in coverage if isinstance(item, dict)}
    assert present == set(REQUIRED_CATEGORIES)


def test_profile_pins_materials_and_stays_unadmitted() -> None:
    profile = _document("profile.json")
    pins = _document("material_sha256.json")
    assert profile["admitted_for_enrich"] is False
    assert profile["acceptance"] is None
    assert profile["biological_accuracy_accepted"] is False
    retained = profile["retained_profile"]
    assert isinstance(retained, dict)
    assert retained["mode"] == "off"
    files = pins["files"]
    assert isinstance(files, dict)
    assert set(files) == {
        "cohort_partition.json",
        "independent_expectations.json",
        "profile.json",
        "qualification_receipt.json",
    }
