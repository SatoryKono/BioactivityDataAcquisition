"""RF-000 contract checks that do not claim biological acceptance."""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.application.services.target_runtime.classification import (
    equivalent_target_binding,
)
from bioetl.application.services.target_runtime.post_join_classification import (
    apply_post_join_classification,
    occurrence_id,
    project_enriched_features,
)
from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TargetClassificationConfig,
)
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v32_normalization_profile,
)
from bioetl.domain.schemas.chembl.target import TargetSchemaV32
from bioetl.infrastructure.export.export_writer_adapter import (
    _write_xlsx_file,
    restore_xlsx_text,
)
from bioetl.infrastructure.export.xlsx_workbook import restore_xlsx_table
from bioetl.infrastructure.storage.target_contract_transition import (
    assert_live_promotion_allowed,
    plan_target_contract_transition,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    reject_unverified_fk_addition,
)
from iuphar_target_class.bioetl_input import project_target_fields
from iuphar_target_class.comparison import (
    Stage0Reference,
    _same_classification,
    build_m_parity_report,
)
from iuphar_target_class.enablement import contour_status
from iuphar_target_class.policy import (
    classification_local_rules,
    local_rule_catalog_sha256,
)
from iuphar_target_class.qualification import (
    DIAGNOSTIC_NOT_KPI,
    Admission,
    assert_not_self_certified,
    legacy_receipt_does_not_admit,
)
from iuphar_target_class.semantics import (
    FIELD_ROLES,
    build_input_manifest,
)

pytestmark = pytest.mark.unit
_DIGEST = "a" * 64


def test_primary_uniprot_is_separate_from_auxiliary_xref() -> None:
    fields = project_target_fields(
        {
            "component_accessions": ["P11111"],
            "target_xref_uniprot_ids": ["P11111", "Q99999"],
        },
        "9606",
    )
    assert fields["uniprot"] == "P11111"
    assert fields["uniprot_equivalent"] == "P11111"
    assert fields["uniprot_xref"] == "Q99999"


def test_input_manifest_does_not_mutate_the_original() -> None:
    payload = b"target-bytes"
    manifest = build_input_manifest(payload)
    assert manifest["mutated"] is False
    assert manifest["byte_length"] == len(payload)
    assert payload == b"target-bytes"
    assert FIELD_ROLES["target_type"] == "chembl"
    assert FIELD_ROLES["local_class"] == "local"


def test_ec7_is_a_local_enzyme_subclass_and_the_catalog_hash_is_order_independent() -> (
    None
):
    rules = classification_local_rules()
    translocase = rules[-1]
    assert translocase.output == "Translocase"
    assert translocase.parent_class == "Enzyme"
    assert translocase.output != "Transporter"
    assert local_rule_catalog_sha256() == local_rule_catalog_sha256(
        tuple(reversed(rules))
    )


def test_enrich_defaults_to_v31_and_off_cannot_select_v32() -> None:
    enrich = TargetClassificationConfig(
        mode="enrich",
        snapshot_manifest="profile.json",
        snapshot_manifest_sha256=_DIGEST,
    )
    assert enrich.contract_version == "3.1.0"
    selected = TargetClassificationConfig(
        mode="enrich",
        snapshot_manifest="profile.json",
        snapshot_manifest_sha256=_DIGEST,
        table_contract="3.2.0",
    )
    assert selected.contract_version == "3.2.0"
    with pytest.raises(ValueError, match="off/shadow"):
        TargetClassificationConfig(mode="off", table_contract="3.2.0")


def test_v32_schema_keeps_detail_fields_nullable() -> None:
    columns = TargetSchemaV32.to_schema().columns
    for name in TARGET_CLASSIFICATION_DETAIL_FIELDS:
        assert name in columns
        assert columns[name].nullable
    target_v32_normalization_profile()


def test_subclass_disagreement_is_not_class_agreement(tmp_path) -> None:
    del tmp_path
    shared = {
        "input_row_id": "1",
        "iuphar_class": "Enzyme",
        "effective_class": "Enzyme",
        "effective_source": "iuphar_normalized",
        "decision_status": "resolved",
        "match_status": "matched",
        "local_class": "",
        "local_status": "",
        "iuphar_annotation_status": "available",
    }
    reference = Stage0Reference(
        "fixture",
        1,
        ({**shared, "iuphar_subclasses": "Hydrolase"},),
    )
    report = build_m_parity_report(
        reference,
        ({**shared, "iuphar_subclasses": "Transferase", "basis_sha256": ""},),
    )
    assert report["biological_accuracy_metric"] is False
    assert report["unexplained"] == ["input_row_id=1"]
    assert report["qualified_changes"] == []
    partial = build_m_parity_report(
        reference,
        (
            {
                **shared,
                "iuphar_subclasses": "Transferase",
                "effective_class": "Receptor",
                "basis_sha256": "a" * 64,
                "change_sign": "direct_local_separation",
                "explanation": "recorded class split",
            },
        ),
        allowed=(
            {
                "target_id": "1",
                "field": "effective_class",
                "category": "direct_local_separation",
                "basis_sha256": "a" * 64,
            },
        ),
    )
    assert partial["qualified_changes"] == []
    assert partial["unexplained"] == ["input_row_id=1"]


def test_expectations_cannot_be_the_classifier_output() -> None:
    with pytest.raises(ValueError, match="cannot certify"):
        assert_not_self_certified(frozenset({"row-1"}), frozenset({"row-1"}))
    with pytest.raises(ValueError, match="cannot certify"):
        Admission(
            True,
            True,
            {"verified": 1},
            "classifier",
        )
    assert legacy_receipt_does_not_admit(6, "3.2.0") is True
    assert DIAGNOSTIC_NOT_KPI == (633, 374)


def test_main_contour_stays_refused_without_biological_acceptance() -> None:
    status = contour_status(
        {
            "fk_closure": True,
            "xlsx_round_trip": True,
            "rehearsal_rollback_passed": True,
        }
    )
    assert status["main_contour"] == "refused"
    assert status["biological_accuracy_accepted"] is False
    assert status["ci_status"] == "NOT_RUN"
    assert status["production_configs"] == "unchanged"


def test_post_join_features_are_whitelisted_and_not_overwritten() -> None:
    import polars as pl

    absent = project_enriched_features({"unrelated": "x"})
    assert absent["feature_provenance"] == "absent"
    present = project_enriched_features({"target_ec_numbers": "3.4.21.1", "extra": 1})
    assert present["feature_provenance"] == "post_join"
    assert present["features"] == {"target_ec_numbers": "3.4.21.1"}
    first = occurrence_id("run", 0, present["features"])
    assert first == occurrence_id("run", 0, present["features"])
    frame = pl.DataFrame({"seed_priority": ["old"], "target_ec_numbers": ["1.1.1.1"]})

    def classify(features, run_id, index):
        return {"seed_priority": f"{run_id}:{index}:{features['target_ec_numbers']}"}

    result = apply_post_join_classification(frame, "run", classify)
    assert result["seed_priority"].to_list() == ["run:0:1.1.1.1"]


def test_xlsx_round_trip_restores_only_verified_parts(tmp_path) -> None:
    original = "enzyme-" * 8000
    token_like = "bioetl-xlsx-part:" + ("b" * 64) + ":1"
    path = tmp_path / "classification.xlsx"
    _write_xlsx_file(
        pa.table({"note": [original, token_like, "short"]}),
        path,
    )
    restored = restore_xlsx_table(str(path))
    assert restored.column("note").to_pylist() == [original, token_like, "short"]
    assert restore_xlsx_text(token_like, ("nope",)) is None


def test_unverified_target_rows_and_live_v32_promotion_are_refused() -> None:
    with pytest.raises(ValueError, match="unverified target addition"):
        reject_unverified_fk_addition(
            {"placeholder": True, "absence_reason": "limited_sample"}
        )
    with pytest.raises(ValueError, match="unresolved target contract mismatch"):
        reject_unverified_fk_addition(
            {
                "source_sha256": _DIGEST,
                "absence_reason": "contract_mismatch",
                "contract_decision": "open",
            }
        )
    plan = plan_target_contract_transition("3.1.0", "3.2.0")
    assert plan["main_tables"] == "unchanged"
    with pytest.raises(ValueError, match="unsupported"):
        plan_target_contract_transition("3.2.0", "9.9.9")
    with pytest.raises(ValueError, match="live 3.2.0"):
        assert_live_promotion_allowed({"table_contract": "3.2.0"})
    assert_live_promotion_allowed({})


def test_family_paths_count_only_when_both_rows_carry_them() -> None:
    shared = {"iuphar_class": "Enzyme", "iuphar_family_paths": '[["Enzyme"]]'}
    other = {"iuphar_class": "Enzyme", "iuphar_family_paths": '[["Receptor"]]'}
    missing = {"iuphar_class": "Enzyme"}
    contract_name = {"iuphar_class": "Enzyme", "iuphar_paths": '[["Receptor"]]'}
    same_contract_name = {"iuphar_class": "Enzyme", "iuphar_paths": '[["Enzyme"]]'}
    assert not _same_classification(shared, other)
    assert not _same_classification(shared, contract_name)
    assert _same_classification(shared, same_contract_name)
    assert _same_classification(shared, missing)


def test_missing_table_contract_matches_an_explicit_null() -> None:
    stored = {"target_config": {"target_classification": {"mode": "off"}}}
    current = {
        "target_config": {
            "target_classification": {"mode": "off", "table_contract": None}
        }
    }
    changed = {
        "target_config": {
            "target_classification": {"mode": "enrich", "table_contract": None}
        }
    }
    assert equivalent_target_binding(stored, current)
    assert not equivalent_target_binding(stored, changed)
