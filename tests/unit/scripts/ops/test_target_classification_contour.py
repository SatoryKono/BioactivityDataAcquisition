"""Main-contour acceptance keeps shadow, enrich, migration, and biology apart."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from openpyxl import Workbook

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from scripts.ops.target_classification_contour import (
    PHYSICAL_CONTRACT,
    ContourEvidenceError,
    ContourMeasurementPaths,
    ContourObservations,
    apply_measurements,
    classification_sha256,
    compare_xlsx_round_trip,
    evaluate_main_contour,
    file_sha256,
    inspect_repository,
    logical_projection_sha256,
    parse_evidence,
    status_distributions,
    unresolved_assay_targets,
    write_contour_report,
)
from scripts.ops.target_classification_migration import main

pytestmark = pytest.mark.unit

_PROFILE = "a" * 64
_CONFIG = "b" * 64
_CANONICAL = "c" * 64
_OTHER = "d" * 64
_COMMIT = "e" * 40
_ROWS = (
    {
        "target_id": "CHEMBL1",
        "pref_name": "alpha",
        "iuphar_target_id": "1",
        "iuphar_class": "enzyme",
        "iuphar_match_status": "matched",
        "iuphar_annotation_status": "partial",
        "local_class": "enzyme",
        "effective_class": "enzyme",
        "effective_source": "iuphar",
        "decision_status": "direct",
        "target_class_profile_sha256": _PROFILE,
    },
    {
        "target_id": "CHEMBL2",
        "pref_name": "beta",
        "iuphar_target_id": None,
        "iuphar_class": None,
        "iuphar_match_status": "ambiguous",
        "iuphar_annotation_status": "source_unavailable",
        "local_class": "unresolved",
        "effective_class": "unresolved",
        "effective_source": "local",
        "decision_status": "conflict",
        "target_class_profile_sha256": _PROFILE,
    },
)


def _phase(report: dict[str, object], name: str) -> str:
    phases = report["phases"]
    assert isinstance(phases, dict)
    phase = phases[name]
    assert isinstance(phase, dict)
    status = phase["status"]
    assert isinstance(status, str)
    return status


def _not_run_evidence() -> dict[str, object]:
    empty_counts = {
        field: {}
        for field in (
            "iuphar_match_status",
            "local_class",
            "effective_class",
            "decision_status",
        )
    }
    return {
        "schema_version": "bioetl_iuphar_main_contour_evidence_v1",
        "shadow": {
            "executed": False,
            "run_id": None,
            "separate_directory": False,
            "contract_version": None,
            "business_rows_unchanged": False,
            "profile_sha256": None,
            "config_sha256": None,
            "cohort_sha256": None,
            "discrepancy_report_sha256": None,
            "independent_expectations_sha256": None,
            "row_count": 0,
            "status_counts": empty_counts,
            "source_completeness": "not_recorded",
        },
        "isolated_enrich": _enrich_body(executed=False),
        "composite_enrich": {
            "executed": False,
            "separate_directory": False,
            "agreed_cohort_sha256": None,
            "same_cohort_as_shadow": False,
            "classification_columns_present": False,
        },
        "migration": {
            "rehearsal_rollback": "NOT_RUN",
            "fk_unresolved": None,
            "writers_quiesced": False,
            "promoted": False,
            "source_identity_matches": False,
            "effective_config_sha256": None,
            "effective_profile_sha256": None,
            "physical_contract": None,
            "backup_retained": False,
            "full_cohort": False,
        },
        "live": {
            "readback": False,
            "next_run_executed": False,
            "next_run_id": None,
            "tables_match_promoted": False,
            "classification_reproduced": False,
            "observed_profile_sha256": None,
            "observed_config_sha256": None,
        },
        "biological": {
            "biological_accuracy_accepted": False,
            "matched_count": None,
            "matched_count_used_as_qualification": False,
            "scientific_status": None,
            "rf008_receipt_status": "NOT_RUN",
            "rf008_receipt_sha256": None,
            "independent_reference_sha256": None,
            "reviewer_reference": None,
        },
        "local": {"status": "NOT_RUN", "evidence_sha256": None},
        "ci": {"status": "NOT_RUN", "commit_sha": None},
    }


def _enrich_body(*, executed: bool) -> dict[str, object]:
    return {
        "executed": executed,
        "separate_directory": executed,
        "limit": 1000 if executed else None,
        "full_table_proof": False,
        "silver_contract": "3.1.0" if executed else None,
        "gold_contract": "3.1.0" if executed else None,
        "profile_sha256": _PROFILE if executed else None,
        "config_sha256": _CONFIG if executed else None,
        "evidence_manifest_sha256": _OTHER if executed else None,
        "persisted_silver_sha256": None,
        "persisted_gold_sha256": None,
        "repeat": {
            "same_inputs": executed,
            "same_versions": executed,
            "classification_sha256": None,
            "repeat_classification_sha256": None,
        },
        "xlsx": {
            "table_sha256": None,
            "xlsx_sha256": None,
            "historical_columns": ["pref_name"] if executed else [],
        },
    }


def _write_csv(
    path: Path, rows: tuple[dict[str, object], ...] | list[dict[str, object]]
) -> None:
    import csv

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_xlsx(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    headers = list(rows[0])
    sheet.append(headers)
    for row in rows:
        sheet.append([row[header] for header in headers])
    workbook.save(path)
    workbook.close()


def _ready_case(tmp_path: Path) -> tuple[dict[str, object], ContourObservations]:
    table = tmp_path / "enrich.csv"
    repeat = tmp_path / "repeat.csv"
    silver = tmp_path / "silver.csv"
    gold = tmp_path / "gold.csv"
    assay = tmp_path / "assay.csv"
    workbook = tmp_path / "targets.xlsx"
    discrepancy = tmp_path / "discrepancy.json"
    expectations = tmp_path / "expectations.json"
    shadow_business = tmp_path / "shadow-business.csv"
    shadow_classification = tmp_path / "shadow-classification.csv"
    _write_csv(
        shadow_business,
        tuple(
            {"target_id": row["target_id"], "pref_name": row["pref_name"]}
            for row in _ROWS
        ),
    )
    _write_csv(shadow_classification, _ROWS)
    _write_csv(table, _ROWS)
    _write_csv(repeat, _ROWS)
    _write_csv(silver, _ROWS)
    _write_csv(gold, _ROWS)
    _write_csv(
        assay,
        ({"target_id": "CHEMBL1"}, {"target_id": "CHEMBL2"}, {"target_id": ""}),
    )
    _write_xlsx(workbook, _ROWS)
    discrepancy.write_text('{"compared": true}\n', encoding="utf-8")
    expectations.write_text('{"independent": true}\n', encoding="utf-8")
    cohort = "1" * 64
    evidence = _not_run_evidence()
    counts = status_distributions(_ROWS)
    evidence["shadow"] = {
        "executed": True,
        "run_id": "shadow-1000",
        "separate_directory": True,
        "contract_version": "3.0.0",
        "business_rows_unchanged": True,
        "profile_sha256": _PROFILE,
        "config_sha256": _OTHER,
        "cohort_sha256": cohort,
        "discrepancy_report_sha256": file_sha256(discrepancy),
        "independent_expectations_sha256": file_sha256(expectations),
        "row_count": len(_ROWS),
        "status_counts": counts,
        "source_completeness": "admission_complete",
    }
    enrich = _enrich_body(executed=True)
    enrich["persisted_silver_sha256"] = file_sha256(silver)
    enrich["persisted_gold_sha256"] = file_sha256(gold)
    enrich["repeat"] = {
        "same_inputs": True,
        "same_versions": True,
        "classification_sha256": classification_sha256(_ROWS),
        "repeat_classification_sha256": classification_sha256(_ROWS),
    }
    enrich["xlsx"] = {
        "table_sha256": file_sha256(table),
        "xlsx_sha256": file_sha256(workbook),
        "historical_columns": ["pref_name"],
    }
    evidence["isolated_enrich"] = enrich
    evidence["composite_enrich"] = {
        "executed": True,
        "separate_directory": True,
        "agreed_cohort_sha256": cohort,
        "same_cohort_as_shadow": True,
        "classification_columns_present": True,
    }
    evidence["migration"] = {
        "rehearsal_rollback": "PASS",
        "fk_unresolved": 0,
        "writers_quiesced": True,
        "promoted": False,
        "source_identity_matches": True,
        "effective_config_sha256": _CONFIG,
        "effective_profile_sha256": _PROFILE,
        "physical_contract": PHYSICAL_CONTRACT,
        "backup_retained": True,
        "full_cohort": True,
    }
    evidence["biological"] = {
        "biological_accuracy_accepted": False,
        "matched_count": 1,
        "matched_count_used_as_qualification": False,
        "scientific_status": "bounded_reference_cases_only",
        "rf008_receipt_status": "PASS",
        "rf008_receipt_sha256": _OTHER,
        "independent_reference_sha256": _CANONICAL,
        "reviewer_reference": None,
    }
    evidence["local"] = {"status": "PASS", "evidence_sha256": _OTHER}
    evidence["ci"] = {"status": "PASS", "commit_sha": _COMMIT}
    parsed = parse_evidence(evidence)
    fields = ("target_type", *TARGET_CLASSIFICATION_FIELDS)
    observations = apply_measurements(
        ContourObservations(
            canonical_mode="off",
            canonical_config_sha256=_CANONICAL,
            composite_classification_fields=fields,
            entity_classification_fields=fields,
            composite_contract_properties=frozenset(TARGET_CLASSIFICATION_FIELDS),
        ),
        parsed,
        ContourMeasurementPaths(
            discrepancy_report=discrepancy,
            expectations=expectations,
            shadow_table=shadow_business,
            shadow_classification=shadow_classification,
            table=table,
            repeat_table=repeat,
            xlsx=workbook,
            isolated_silver=silver,
            isolated_gold=gold,
            silver=silver,
            gold=gold,
            assay=assay,
        ),
    )
    return parsed, observations


def test_repository_contour_stays_blocked_and_keeps_mode_off() -> None:
    observations = inspect_repository()
    report = evaluate_main_contour(_not_run_evidence(), observations)

    assert observations.canonical_mode == "off"
    assert observations.composite_classification_fields == (
        observations.entity_classification_fields
    )
    assert set(TARGET_CLASSIFICATION_FIELDS).issubset(
        observations.composite_classification_fields
    )
    assert set(TARGET_CLASSIFICATION_FIELDS).issubset(
        observations.composite_contract_properties
    )
    assert report["promotion_decision"] == "BLOCKED"
    assert report["biological_accuracy_accepted"] is False
    assert report["matched_count_substitutes_biological_qualification"] is False
    assert _phase(report, "shadow") == "NOT_RUN"
    assert _phase(report, "isolated_enrich") == "NOT_RUN"
    assert _phase(report, "composite_enrich") == "NOT_RUN"
    assert _phase(report, "migration") == "NOT_RUN"
    assert _phase(report, "live") == "NOT_RUN"
    axes = report["axes"]
    assert isinstance(axes, dict)
    assert axes["local"]["status"] == "NOT_RUN"
    assert axes["ci"]["status"] == "NOT_RUN"
    assert axes["biological"]["status"] == "NOT_ACCEPTED"
    assert axes["biological"]["rf008_admitted"] is False


def test_ready_report_does_not_treat_matched_count_as_biological_acceptance(
    tmp_path: Path,
) -> None:
    evidence, observations = _ready_case(tmp_path)
    report = evaluate_main_contour(evidence, observations)

    assert report["promotion_decision"] == "READY"
    assert report["biological_accuracy_accepted"] is False
    assert report["rf008_admitted"] is True
    assert report["matched_count"] == 1
    assert _phase(report, "shadow") == "PASS"
    assert _phase(report, "isolated_enrich") == "PASS"
    assert _phase(report, "composite_enrich") == "PASS"
    assert _phase(report, "migration") == "PASS"
    assert _phase(report, "live") == "NOT_RUN"
    assert report["distributions"]["iuphar_match_status"] == {
        "ambiguous": 1,
        "matched": 1,
    }
    assert report["distribution_source"] == "shadow_classification"


def test_shadow_pass_does_not_pass_enrich(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    enrich = dict(evidence["isolated_enrich"])
    enrich["executed"] = False
    evidence["isolated_enrich"] = enrich
    report = evaluate_main_contour(evidence, observations)

    assert _phase(report, "shadow") == "PASS"
    assert _phase(report, "isolated_enrich") == "NOT_RUN"
    assert report["promotion_decision"] == "BLOCKED"


def test_matched_count_cannot_qualify_biology(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    biological = dict(evidence["biological"])
    biological["matched_count_used_as_qualification"] = True
    biological["biological_accuracy_accepted"] = True
    evidence["biological"] = biological
    report = evaluate_main_contour(evidence, observations)
    axes = report["axes"]
    assert isinstance(axes, dict)

    assert axes["biological"]["status"] == "FAIL"
    assert report["promotion_decision"] == "BLOCKED"
    assert "matched_count_used_as_qualification" in axes["biological"]["reasons"]


def test_bounded_reference_is_not_biological_pass(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    biological = dict(evidence["biological"])
    biological["biological_accuracy_accepted"] = True
    biological["reviewer_reference"] = "reviewer-1"
    evidence["biological"] = biological
    report = evaluate_main_contour(evidence, observations)
    axes = report["axes"]
    assert isinstance(axes, dict)

    assert axes["biological"]["status"] == "FAIL"
    assert (
        "bounded_reference_is_not_biological_acceptance"
        in axes["biological"]["reasons"]
    )


def test_unresolved_fk_and_xlsx_mismatch_fail_their_own_phases(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    fk_report = evaluate_main_contour(evidence, replace(observations, fk_unresolved=37))
    assert _phase(fk_report, "migration") == "FAIL"
    assert _phase(fk_report, "isolated_enrich") == "PASS"
    assert fk_report["promotion_decision"] == "BLOCKED"

    broken = tmp_path / "broken.xlsx"
    _write_xlsx(
        broken,
        (
            {**_ROWS[0], "iuphar_class": "truncated"},
            _ROWS[1],
        ),
    )
    mismatched = apply_measurements(
        observations,
        evidence,
        ContourMeasurementPaths(table=tmp_path / "enrich.csv", xlsx=broken),
    )
    xlsx_report = evaluate_main_contour(evidence, mismatched)
    assert _phase(xlsx_report, "isolated_enrich") == "FAIL"
    assert _phase(xlsx_report, "shadow") == "PASS"


def test_repeat_mismatch_fails_enrich_only(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    changed = tmp_path / "changed.csv"
    _write_csv(changed, ({**_ROWS[0], "decision_status": "other"}, _ROWS[1]))
    measured = apply_measurements(
        observations,
        evidence,
        ContourMeasurementPaths(
            table=tmp_path / "enrich.csv",
            repeat_table=changed,
        ),
    )
    report = evaluate_main_contour(evidence, measured)

    assert _phase(report, "isolated_enrich") == "FAIL"
    assert (
        "repeat_classification_mismatch"
        in report["phases"]["isolated_enrich"]["reasons"]
    )


def test_promoted_failure_requires_rollback(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    report = evaluate_main_contour(
        evidence,
        replace(observations, canonical_mode="off"),
    )

    assert report["promotion_decision"] == "ROLLBACK_REQUIRED"
    assert report["rollback_required"] is True


def test_contour_report_cli_writes_blocked_report_without_promoting(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "evidence.json"
    output = tmp_path / "contour-report.json"
    evidence_path.write_text(
        json.dumps(_not_run_evidence(), sort_keys=True),
        encoding="utf-8",
    )
    exit_code = main(
        [
            "contour-report",
            "--evidence",
            str(evidence_path),
            "--output",
            str(output),
            "--repo-root",
            str(Path(__file__).resolve().parents[4]),
        ]
    )
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["canonical"]["mode"] == "off"
    assert report["promotion_decision"] == "BLOCKED"
    ready_code = main(
        [
            "contour-report",
            "--evidence",
            str(evidence_path),
            "--output",
            str(tmp_path / "required.json"),
            "--repo-root",
            str(Path(__file__).resolve().parents[4]),
            "--require-ready",
        ]
    )
    assert ready_code == 1


def test_contour_report_cli_rejects_invalid_evidence(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        main(
            [
                "contour-report",
                "--evidence",
                str(evidence_path),
                "--output",
                str(tmp_path / "report.json"),
            ]
        )
    assert caught.value.code == 2


def test_claimed_profile_must_match_each_current_row(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    other = "f" * 64
    enrich = dict(evidence["isolated_enrich"])
    enrich["profile_sha256"] = other
    evidence["isolated_enrich"] = enrich
    migration = dict(evidence["migration"])
    migration["effective_profile_sha256"] = other
    evidence["migration"] = migration
    report = evaluate_main_contour(evidence, observations)

    assert _phase(report, "isolated_enrich") == "FAIL"
    assert (
        "enrich_profile_row_mismatch" in report["phases"]["isolated_enrich"]["reasons"]
    )
    assert report["promotion_decision"] == "BLOCKED"


def test_closed_gold_version_does_not_close_a_current_assay_fk() -> None:
    current_assay = [{"target_id": "CHEMBL1", "_is_current": True}]
    closed_gold = [{"target_id": "CHEMBL1", "_is_current": False}]
    current_gold = [{"target_id": "CHEMBL1", "_is_current": True}]
    closed_assay = [{"target_id": "CHEMBL9", "_is_current": False}]

    assert unresolved_assay_targets(current_assay, closed_gold) == 1
    assert unresolved_assay_targets(current_assay, current_gold) == 0
    assert unresolved_assay_targets(closed_assay, current_gold) == 0
    assert unresolved_assay_targets([{"target_id": "CHEMBL1"}], current_gold) == 0
    assert (
        unresolved_assay_targets(
            [{"target_id": "CHEMBL9", "_is_current": 0}],
            current_gold,
        )
        == 0
    )
    assert (
        unresolved_assay_targets(
            [{"target_id": "CHEMBL9", "_is_current": None}],
            current_gold,
        )
        == 0
    )


def test_shadow_counts_come_from_classification_not_the_business_table(
    tmp_path: Path,
) -> None:
    evidence, observations = _ready_case(tmp_path)
    business = tmp_path / "v30.csv"
    _write_csv(
        business,
        tuple(
            {"target_id": row["target_id"], "pref_name": row["pref_name"]}
            for row in _ROWS
        ),
    )
    shorter = tmp_path / "smoke.csv"
    _write_csv(shorter, (_ROWS[0],))
    measured = apply_measurements(
        observations,
        evidence,
        ContourMeasurementPaths(
            shadow_table=business,
            shadow_classification=tmp_path / "shadow-classification.csv",
            table=shorter,
            repeat_table=shorter,
        ),
    )
    report = evaluate_main_contour(evidence, measured)

    assert _phase(report, "shadow") == "PASS"
    assert report["distribution_source"] == "shadow_classification"
    assert report["distributions"]["iuphar_match_status"] == {
        "ambiguous": 1,
        "matched": 1,
    }
    assert _phase(report, "isolated_enrich") == "FAIL"

    business_only = apply_measurements(
        replace(observations, shadow_classification_rows=None),
        evidence,
        ContourMeasurementPaths(shadow_table=business),
    )
    business_report = evaluate_main_contour(evidence, business_only)
    reasons = business_report["phases"]["shadow"]["reasons"]
    assert isinstance(reasons, list)
    assert "shadow_classification_not_read" in reasons
    assert "status_count_conflict" not in reasons


def test_directory_identity_is_measured_for_silver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence, observations = _ready_case(tmp_path)
    directory = tmp_path / "silver-delta"
    directory.mkdir()
    monkeypatch.setattr(
        "scripts.ops.target_classification_contour.load_table",
        lambda _path: list(_ROWS),
    )
    measured = apply_measurements(
        observations,
        evidence,
        ContourMeasurementPaths(isolated_silver=directory),
    )
    assert measured.silver_sha256 == logical_projection_sha256(list(_ROWS))
    report = evaluate_main_contour(evidence, measured)
    assert "silver_hash_conflict" in report["phases"]["isolated_enrich"]["reasons"]


def test_live_matches_current_silver_rather_than_the_smoke_table(
    tmp_path: Path,
) -> None:
    evidence, observations = _ready_case(tmp_path)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["live"] = {
        "readback": True,
        "next_run_executed": True,
        "next_run_id": "next-run",
        "tables_match_promoted": True,
        "classification_reproduced": True,
        "observed_profile_sha256": _PROFILE,
        "observed_config_sha256": _CONFIG,
    }
    observations = replace(
        observations,
        canonical_mode="enrich",
        canonical_config_sha256=_CONFIG,
        live_projection_match=True,
    )
    report = evaluate_main_contour(evidence, observations)

    assert _phase(report, "live") == "PASS"
    assert report["promotion_decision"] == "LIVE_ACCEPTED"


def test_ci_failure_after_promotion_requires_rollback(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["ci"] = {"status": "FAIL", "commit_sha": _COMMIT}
    evidence["live"] = {
        "readback": True,
        "next_run_executed": True,
        "next_run_id": "next-run",
        "tables_match_promoted": True,
        "classification_reproduced": True,
        "observed_profile_sha256": _PROFILE,
        "observed_config_sha256": _CONFIG,
    }
    report = evaluate_main_contour(
        evidence,
        replace(
            observations,
            canonical_mode="enrich",
            canonical_config_sha256=_CONFIG,
        ),
    )

    assert report["promotion_decision"] == "ROLLBACK_REQUIRED"
    assert "ci" in report["promotion_reasons"]


def test_not_run_ci_after_promotion_does_not_request_rollback(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["ci"] = {"status": "NOT_RUN", "commit_sha": None}
    report = evaluate_main_contour(
        evidence,
        replace(observations, canonical_mode="enrich", canonical_config_sha256=_CONFIG),
    )

    assert report["rollback_required"] is False
    assert report["promotion_decision"] == "BLOCKED"


def test_report_refuses_to_replace_an_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "contour-report.json"
    write_contour_report({"artifact": "bioetl_iuphar_main_contour_report"}, output)
    with pytest.raises(ContourEvidenceError, match="refusing to replace"):
        write_contour_report({"artifact": "bioetl_iuphar_main_contour_report"}, output)
    assert json.loads(output.read_text(encoding="utf-8"))["artifact"] == (
        "bioetl_iuphar_main_contour_report"
    )


def test_relative_path_escape_is_rejected() -> None:
    with pytest.raises(ValueError, match="refusing path outside"):
        file_sha256(Path("../outside-the-repository"))


def test_csv_closed_flags_stay_out_of_current_checks(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    rows: list[dict[str, object]] = []
    for row in _ROWS:
        current = dict(row)
        current["_is_current"] = "True"
        rows.append(current)
    for target_id, flag in (
        ("CHEMBL7", "False"),
        ("CHEMBL8", "false"),
        ("CHEMBL9", "0"),
    ):
        closed = dict(_ROWS[0])
        closed["target_id"] = target_id
        closed["_is_current"] = flag
        closed["iuphar_class"] = "ion channel"
        closed["target_class_profile_sha256"] = "f" * 64
        rows.append(closed)
    table = tmp_path / "history.csv"
    repeat = tmp_path / "history-repeat.csv"
    workbook = tmp_path / "history.xlsx"
    _write_csv(table, rows)
    _write_csv(repeat, rows)
    _write_xlsx(workbook, _ROWS)
    current_hash = classification_sha256(_ROWS)
    enrich = dict(evidence["isolated_enrich"])
    enrich["repeat"] = {
        "same_inputs": True,
        "same_versions": True,
        "classification_sha256": current_hash,
        "repeat_classification_sha256": current_hash,
    }
    enrich["xlsx"] = {
        "table_sha256": file_sha256(table),
        "xlsx_sha256": file_sha256(workbook),
        "historical_columns": ["pref_name"],
    }
    evidence["isolated_enrich"] = enrich
    measured = apply_measurements(
        observations,
        evidence,
        ContourMeasurementPaths(table=table, repeat_table=repeat, xlsx=workbook),
    )
    report = evaluate_main_contour(evidence, measured)

    assert _phase(report, "isolated_enrich") == "PASS"


def test_live_readback_rejects_missing_classification_fields(
    tmp_path: Path,
) -> None:
    evidence, observations = _ready_case(tmp_path)
    thin = tuple(
        {
            "target_id": row["target_id"],
            "target_class_profile_sha256": _PROFILE,
        }
        for row in _ROWS
    )
    silver = tmp_path / "silver-thin.csv"
    gold = tmp_path / "gold-thin.csv"
    _write_csv(silver, thin)
    _write_csv(gold, thin)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["live"] = {
        "readback": True,
        "next_run_executed": True,
        "next_run_id": "next-run",
        "tables_match_promoted": True,
        "classification_reproduced": True,
        "observed_profile_sha256": _PROFILE,
        "observed_config_sha256": _CONFIG,
    }
    measured = apply_measurements(
        replace(
            observations,
            canonical_mode="enrich",
            canonical_config_sha256=_CONFIG,
        ),
        evidence,
        ContourMeasurementPaths(silver=silver, gold=gold),
    )
    report = evaluate_main_contour(evidence, measured)
    phases = report["phases"]
    assert isinstance(phases, dict)
    live = phases["live"]
    assert isinstance(live, dict)

    assert measured.live_projection_match is False
    assert measured.silver_sha256 == observations.silver_sha256
    assert _phase(report, "isolated_enrich") == "PASS"
    assert _phase(report, "live") == "FAIL"
    assert "classification_not_reproduced" in live["reasons"]
    assert report["promotion_decision"] == "ROLLBACK_REQUIRED"


def test_main_contour_readback_does_not_replace_isolated_hashes(
    tmp_path: Path,
) -> None:
    evidence, observations = _ready_case(tmp_path)
    extra = dict(_ROWS[0])
    extra["target_id"] = "CHEMBL3"
    rows = (*_ROWS, extra)
    silver = tmp_path / "main-silver.csv"
    gold = tmp_path / "main-gold.csv"
    _write_csv(silver, rows)
    _write_csv(gold, rows)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["live"] = {
        "readback": True,
        "next_run_executed": True,
        "next_run_id": "next-run",
        "tables_match_promoted": True,
        "classification_reproduced": True,
        "observed_profile_sha256": _PROFILE,
        "observed_config_sha256": _CONFIG,
    }
    measured = apply_measurements(
        replace(
            observations,
            canonical_mode="enrich",
            canonical_config_sha256=_CONFIG,
        ),
        evidence,
        ContourMeasurementPaths(silver=silver, gold=gold),
    )
    report = evaluate_main_contour(evidence, measured)

    assert measured.silver_sha256 == observations.silver_sha256
    assert measured.gold_sha256 == observations.gold_sha256
    assert _phase(report, "isolated_enrich") == "PASS"
    assert _phase(report, "live") == "PASS"
    assert report["promotion_decision"] == "LIVE_ACCEPTED"


def test_live_readback_rejects_matching_but_wrong_row_profiles(
    tmp_path: Path,
) -> None:
    """Live Silver/Gold may match each other yet disagree with the promoted digest."""
    evidence, observations = _ready_case(tmp_path)
    wrong = tuple({**row, "target_class_profile_sha256": _OTHER} for row in _ROWS)
    silver = tmp_path / "live-wrong-silver.csv"
    gold = tmp_path / "live-wrong-gold.csv"
    _write_csv(silver, wrong)
    _write_csv(gold, wrong)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["live"] = {
        "readback": True,
        "next_run_executed": True,
        "next_run_id": "next-run",
        "tables_match_promoted": True,
        "classification_reproduced": True,
        "observed_profile_sha256": _PROFILE,
        "observed_config_sha256": _CONFIG,
    }
    measured = apply_measurements(
        replace(
            observations,
            canonical_mode="enrich",
            canonical_config_sha256=_CONFIG,
        ),
        evidence,
        ContourMeasurementPaths(silver=silver, gold=gold),
    )
    report = evaluate_main_contour(evidence, measured)
    phases = report["phases"]
    assert isinstance(phases, dict)
    live = phases["live"]
    assert isinstance(live, dict)

    assert measured.silver_profile_values == observations.silver_profile_values
    assert measured.gold_profile_values == observations.gold_profile_values
    assert measured.live_silver_profile_values == (_OTHER, _OTHER)
    assert measured.live_gold_profile_values == (_OTHER, _OTHER)
    assert measured.live_projection_match is True
    assert _phase(report, "isolated_enrich") == "PASS"
    assert _phase(report, "live") == "FAIL"
    assert "live_silver_profile_row_mismatch" in live["reasons"]
    assert "live_gold_profile_row_mismatch" in live["reasons"]
    assert report["promotion_decision"] != "LIVE_ACCEPTED"


def test_duplicate_current_target_id_blocks_live_acceptance(
    tmp_path: Path,
) -> None:
    evidence, observations = _ready_case(tmp_path)
    conflict = dict(_ROWS[0])
    conflict["effective_class"] = "gpcr"
    silver_rows = (conflict, *_ROWS)
    silver = tmp_path / "duplicate-silver.csv"
    _write_csv(silver, silver_rows)
    migration = dict(evidence["migration"])
    migration["promoted"] = True
    evidence["migration"] = migration
    evidence["live"] = {
        "readback": True,
        "next_run_executed": True,
        "next_run_id": "next-run",
        "tables_match_promoted": True,
        "classification_reproduced": True,
        "observed_profile_sha256": _PROFILE,
        "observed_config_sha256": _CONFIG,
    }
    measured = apply_measurements(
        replace(
            observations,
            canonical_mode="enrich",
            canonical_config_sha256=_CONFIG,
        ),
        evidence,
        ContourMeasurementPaths(silver=silver, gold=tmp_path / "gold.csv"),
    )
    report = evaluate_main_contour(evidence, measured)
    phases = report["phases"]
    assert isinstance(phases, dict)
    live = phases["live"]
    assert isinstance(live, dict)

    assert measured.duplicate_current_target_ids is True
    assert _phase(report, "live") == "FAIL"
    assert "duplicate_current_target_id" in live["reasons"]
    assert report["promotion_decision"] == "ROLLBACK_REQUIRED"


def test_standard_xlsx_rejoins_split_historical_text(tmp_path: Path) -> None:
    import pyarrow as pa

    from bioetl.infrastructure.export.xlsx_text_parts import write_arrow_xlsx

    rows = [dict(row) for row in _ROWS]
    rows[0]["pref_name"] = "n" * 32768
    workbook = tmp_path / "split.xlsx"
    write_arrow_xlsx(
        pa.Table.from_pylist(rows),
        workbook,
        table_name="target",
        layer="gold",
    )
    status, preserved = compare_xlsx_round_trip(rows, workbook, ("pref_name",))

    assert status == "PASS"
    assert preserved is True


def test_smoke_limit_cannot_claim_full_table_proof(tmp_path: Path) -> None:
    evidence, observations = _ready_case(tmp_path)
    enrich = dict(evidence["isolated_enrich"])
    enrich["full_table_proof"] = True
    evidence["isolated_enrich"] = enrich
    report = evaluate_main_contour(evidence, observations)

    assert _phase(report, "isolated_enrich") == "FAIL"
    assert (
        "smoke_cannot_prove_full_table"
        in report["phases"]["isolated_enrich"]["reasons"]
    )
    assert _phase(report, "migration") == "PASS"
