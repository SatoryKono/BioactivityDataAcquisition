"""RF-001 baseline: field layers, decision rows, and the pinned manifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from iuphar_target_class.baseline_manifest import (
    MANIFEST_RELATIVE_PATH,
    verify_baseline_manifest,
)
from iuphar_target_class.baseline_semantics import (
    CANONICAL_OTHER,
    COMMITTED_COMPOSITE_VERSION,
    COMMITTED_ENTITY_CONTRACT,
    COMMITTED_ENTITY_MODE,
    COMMITTED_TABLE_GENERATION,
    DROPPED_PARENTS,
    FALSE_OTHER,
    FIELD_DEFINITIONS,
    LEGACY_OTHER,
    LOCAL_INFERENCE_IN_IUPHAR,
    PROFILE_CHANGE_RULES,
    SNAPSHOT_ANNOTATION_CAPABILITY,
    UNDEFINED_TABLE_DISTINCT,
    UNCERTAINTY_STATUSES,
    BoundaryObservation,
    contract_document,
    covered_statuses,
    decide,
    field_layer,
)
from iuphar_target_class.policy import (
    BASE_MISSING_MARKERS,
    baseline_contract,
    policy_document,
)
from iuphar_target_class.stage0.io import canonical_json_bytes

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]


def test_v31_fields_keep_distinct_layers() -> None:
    layers = {item.name: item.layer for item in FIELD_DEFINITIONS}
    assert layers["target_type"] == "chembl_object_type"
    assert "target_type" not in TARGET_CLASSIFICATION_FIELDS
    assert len(TARGET_CLASSIFICATION_FIELDS) == 9
    for name in TARGET_CLASSIFICATION_FIELDS:
        assert layers[name] == field_layer(name)
    assert field_layer("iuphar_class") == "dictionary"
    assert field_layer("local_class") == "local_rule"
    assert field_layer("effective_class") == "decision"
    assert field_layer("effective_source") == "decision"
    with pytest.raises(ValueError, match="no RF-001 layer"):
        field_layer("pref_name")


def test_decision_table_covers_uncertainty_and_availability() -> None:
    covered = covered_statuses()
    assert set(UNCERTAINTY_STATUSES) <= covered
    assert {"source_unavailable", "not_found"} <= covered
    assert [rule.rule_id for rule in PROFILE_CHANGE_RULES]
    versions = contract_document()["contract_versions"]
    assert isinstance(versions, dict)
    assert all(versions.values())
    assert baseline_contract() == contract_document()


def test_missing_marker_version_stays_unapproved() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["missing_markers_version"] is None
    markers = contract_document()["missing_markers"]
    assert isinstance(markers, dict)
    assert markers["base"] == list(BASE_MISSING_MARKERS)
    assert markers["version"] is None
    assert markers["effect"] == "absence"
    assert "not_found" in markers["does_not_mean"]


def test_audit_counterexamples_follow_the_decision_table() -> None:
    mixed = decide(LOCAL_INFERENCE_IN_IUPHAR)
    assert mixed.rule_id == "layer_mix"
    assert mixed.decision_status == "contract_defect"
    assert mixed.iuphar_class is None
    assert mixed.local_class == "Enzyme"
    assert mixed.effective_class is None
    assert mixed.effective_source != "iuphar"

    parents = decide(DROPPED_PARENTS)
    assert parents.rule_id == "dropped_parents"
    assert parents.completeness == "partial"
    assert parents.effective_class is None
    assert parents.dropped_parent_ids == ("20",)
    assert parents.decision_status == "requires_review"

    other = decide(FALSE_OTHER)
    assert other.rule_id == "false_other"
    assert other.effective_class is None
    assert other.iuphar_class is None
    assert other.completeness == "unknown"

    distinct = decide(UNDEFINED_TABLE_DISTINCT)
    assert distinct.rule_id == "undefined_table_distinct"
    assert distinct.completeness == "ambiguous"
    assert distinct.effective_class is None
    assert distinct.decision_status == "requires_review"


def test_source_unavailable_is_not_rewritten_as_not_found() -> None:
    unavailable = decide(
        BoundaryObservation(case_id="gap", source_state="source_unavailable")
    )
    assert unavailable.rule_id == "source_unavailable"
    assert unavailable.completeness == "source_unavailable"
    assert "not_found" not in unavailable.codes

    found = decide(BoundaryObservation(case_id="absent", source_state="not_found"))
    assert found.rule_id == "confirmed_not_found"
    assert found.completeness == "not_found"
    assert "source_unavailable" not in found.codes


@pytest.mark.parametrize(
    ("uncertainty", "rule_id", "completeness"),
    [
        ("unknown", "unknown", "unknown"),
        ("partial", "partial_annotation", "partial"),
        ("ambiguous", "ambiguous_match", "ambiguous"),
        ("conflict", "layer_conflict", "conflict"),
    ],
)
def test_uncertainty_rows_do_not_invent_a_class(
    uncertainty: str, rule_id: str, completeness: str
) -> None:
    decision = decide(BoundaryObservation(case_id=uncertainty, uncertainty=uncertainty))
    assert decision.rule_id == rule_id
    assert decision.completeness == completeness
    assert decision.effective_class is None


def test_legacy_other_is_admissible_only_as_a_legacy_alias() -> None:
    rejected = decide(
        BoundaryObservation(
            case_id="other-in-dictionary",
            assigned_label=LEGACY_OTHER,
            approved_other_mapping=True,
            legacy_field=False,
        )
    )
    assert rejected.rule_id == "false_other"
    assert rejected.iuphar_class is None

    alias = decide(
        BoundaryObservation(
            case_id="legacy-alias",
            assigned_label=LEGACY_OTHER,
            approved_other_mapping=True,
            legacy_field=True,
        )
    )
    assert alias.rule_id == "legacy_other_alias"
    assert alias.iuphar_class == CANONICAL_OTHER
    assert alias.effective_source == "iuphar"

    direct = decide(
        BoundaryObservation(
            case_id="canonical-other",
            assigned_label=CANONICAL_OTHER,
            approved_other_mapping=True,
        )
    )
    assert direct.rule_id == "admissible_other"
    assert direct.effective_class == CANONICAL_OTHER


def test_partial_and_conflict_keep_a_dictionary_fact_apart_from_local() -> None:
    partial = decide(
        BoundaryObservation(
            case_id="partial-family",
            uncertainty="partial",
            dictionary_class="Receptor",
            local_class="Enzyme",
        )
    )
    assert partial.iuphar_class == "Receptor"
    assert partial.local_class == "Enzyme"
    assert partial.effective_source == "iuphar"
    assert partial.decision_status == "requires_review"

    conflict = decide(
        BoundaryObservation(
            case_id="direct-local",
            uncertainty="conflict",
            dictionary_class="Ion Channel",
            local_class="Transporter",
        )
    )
    assert conflict.rule_id == "layer_conflict"
    assert conflict.iuphar_class == "Ion Channel"
    assert conflict.local_class == "Transporter"
    assert conflict.effective_class == "Ion Channel"


def test_committed_configs_match_the_baseline_claim() -> None:
    entity = yaml.safe_load(
        (ROOT / "configs/entities/chembl/target.yaml").read_text(encoding="utf-8")
    )
    composite = yaml.safe_load(
        (ROOT / "configs/composites/target.yaml").read_text(encoding="utf-8")
    )
    classification = entity["pipeline"]["target_classification"]
    assert classification["mode"] == COMMITTED_ENTITY_MODE
    assert entity["contracts"]["active_version"] == COMMITTED_ENTITY_CONTRACT
    assert COMMITTED_TABLE_GENERATION == "V30"
    assert composite["composite"]["version"] == COMMITTED_COMPOSITE_VERSION
    snapshot = (
        ROOT / "src/bioetl/infrastructure/adapters/iuphar/snapshot_payload.py"
    ).read_text(encoding="utf-8")
    assert f'"annotation_capability": "{SNAPSHOT_ANNOTATION_CAPABILITY}"' in snapshot


def test_manifest_hashes_and_required_roles_hold() -> None:
    path = ROOT / MANIFEST_RELATIVE_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    problems = verify_baseline_manifest(ROOT, document)
    assert problems == ()
    materials = document["materials"]
    by_id = {row["material_id"]: row for row in materials}
    assert by_id["m_source"]["availability"] == "source_unavailable"
    assert by_id["m_source"]["semantics_bound"] is False
    assert by_id["m_source"]["version_id"] is None
    assert by_id["m_source"]["confirmed_absence"] is False
    assert by_id["result_cache"]["role"] == "result_cache"
    assert by_id["result_cache"]["fresh_recalculation"] is False
    assert by_id["result_cache"]["availability"] == "source_unavailable"
    assert by_id["iuphar_snapshot_bytes"]["availability"] == "source_unavailable"
    assert document["m_semantics_bound"] is False
    assert document["fresh_recalculation"] is False
    changed = {
        row["material_id"]
        for row in materials
        if row["delta"] == "content_changed_by_rf001"
    }
    assert changed == {"composite_config", "entity_config", "rules_source"}
    introduced = {
        row["material_id"] for row in materials if row["delta"] == "absent_on_baseline"
    }
    assert introduced == {"manifest_source", "semantics_source"}
    encoded = canonical_json_bytes(document)
    assert path.read_bytes() == encoded
