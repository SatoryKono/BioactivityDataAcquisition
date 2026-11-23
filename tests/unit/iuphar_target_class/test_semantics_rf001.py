"""RF-001 (#13309): field layers, statuses, and baseline manifest contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bioetl.domain.config.target_classification import (
    FIELD_LAYER_BY_NAME,
    RF001_SEMANTICS_CONTRACT,
    TARGET_CLASSIFICATION_FIELDS,
    TargetClassificationConfig,
)
from iuphar_target_class.policy import (
    BASE_MISSING_MARKERS,
    WORKING_CLASSES,
    policy_document,
)
from iuphar_target_class.semantics import (
    ANNOTATION_STATUSES,
    CAPABILITY_MATRIX,
    DECISION_STATUSES,
    FIELD_LAYERS,
    LEGACY_OTHER_POLICY,
    LOCAL_STATUSES,
    MATCH_STATUSES,
    MISSING_MARKER_POLICY,
    PATH_POLICY,
    RF001_CONTRACT_VERSION,
    UNCERTAINTY_TOKENS,
    semantics_document,
)
from iuphar_target_class.resolution import ResolutionInput, select_effective_class
from iuphar_target_class.stage0.io import canonical_json_bytes

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "data" / "iuphar_target_class" / "rf001" / "baseline_manifest.json"
RECEIPT = (
    REPO / "data" / "iuphar_target_class" / "rf001" / "baseline_manifest.sha256.json"
)
DOC = (
    REPO
    / "docs"
    / "04-reference"
    / "pipelines"
    / "chembl"
    / "16-iuphar-target-classification-semantics.md"
)


def test_rf001_contract_identity_and_no_biological_admission() -> None:
    document = semantics_document()
    assert document["contract_version"] == RF001_CONTRACT_VERSION == "rf001-2026-11-23"
    assert document["biological_accuracy_accepted"] is False
    assert TargetClassificationConfig().semantics_contract_version == (
        RF001_SEMANTICS_CONTRACT
    )
    embedded = policy_document()["rf001_semantics"]
    assert embedded == document
    assert policy_document()["biological_accuracy_accepted"] is False


def test_field_layers_separate_chembl_iuphar_local_effective() -> None:
    assert FIELD_LAYERS["target_type"]["layer"] == "chembl_object"
    assert FIELD_LAYER_BY_NAME["target_type"] == "chembl_object"
    for name in (
        "iuphar_target_id",
        "iuphar_class",
        "iuphar_match_status",
        "iuphar_annotation_status",
    ):
        assert FIELD_LAYERS[name]["layer"] == "iuphar_reference"
        assert FIELD_LAYER_BY_NAME[name] == "iuphar_reference"
    assert FIELD_LAYERS["local_class"]["layer"] == "local_rules"
    for name in (
        "effective_class",
        "effective_source",
        "decision_status",
        "target_class_profile_sha256",
    ):
        assert FIELD_LAYERS[name]["layer"] == "effective"
        assert name in TARGET_CLASSIFICATION_FIELDS
    meaning = FIELD_LAYERS["effective_source"]["meaning"]
    assert "iuphar_normalized" in meaning
    assert "local_rule" in meaning
    assert "none" in meaning


def test_source_unavailable_stays_distinct_from_not_found() -> None:
    assert "source_unavailable" in MATCH_STATUSES
    assert "not_found" in MATCH_STATUSES
    assert MATCH_STATUSES["source_unavailable"] != MATCH_STATUSES["not_found"]
    assert semantics_document()["source_unavailable_vs_not_found"][
        "must_remain_distinct"
    ]
    for token in ("unknown", "partial", "ambiguous", "conflict"):
        assert token in UNCERTAINTY_TOKENS
    assert set(ANNOTATION_STATUSES) >= {
        "available",
        "partial",
        "unmapped_type",
        "conflicting",
        "not_available",
    }
    assert set(LOCAL_STATUSES) >= {
        "supported",
        "not_supported",
        "candidate_only",
        "conflicting",
    }
    assert set(DECISION_STATUSES) == {"resolved", "requires_review", "unresolved"}


def test_capability_matrix_prefers_composite_after_joins() -> None:
    standalone = CAPABILITY_MATRIX["standalone_chembl_target"]
    composite = CAPABILITY_MATRIX["enriched_composite_target"]
    assert composite["priority"] == 1
    assert standalone["priority"] == 2
    assert composite["full_features_available"] is True
    assert standalone["full_features_available"] is False
    assert "uniprot_protein" in composite["available_after_dependency_joins"]
    assert (
        "uniprot_protein annotations/keywords" in standalone["unavailable_until_joins"]
    )


def test_path_missing_marker_and_other_policies() -> None:
    assert PATH_POLICY["canonical_direction"] == "root_to_leaf"
    assert PATH_POLICY["legacy_text_field"] == "leaf_to_root"
    assert PATH_POLICY["multiple_parents_allowed"] is True
    assert list(MISSING_MARKER_POLICY["base_markers"]) == list(BASE_MISSING_MARKERS)
    assert MISSING_MARKER_POLICY["version"] is None
    assert (
        "unmapped_type or name/path text containing 'Other'"
        in LEGACY_OTHER_POLICY["forbidden_when"]
    )
    assert WORKING_CLASSES == tuple(semantics_document()["working_classes"])
    assert "Other Protein Target" in WORKING_CLASSES


def test_baseline_manifest_hashes_and_receipt() -> None:
    payload = MANIFEST.read_bytes()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert hashlib.sha256(payload).hexdigest() == receipt["sha256"]
    manifest = json.loads(payload.decode("utf-8"))
    assert manifest["artifact"] == "iuphar_rf001_baseline_manifest"
    assert manifest["schema_version"] == 2
    assert manifest["biological_accuracy_accepted"] is False
    assert manifest["immutability"]["hash_lock_scope"] == "pinned_artifacts_only"
    assert manifest["m_code"]["status"] == "не установлено"
    assert manifest["m_code"]["excel_cache_confirms_fresh_recalc"] is False
    assert manifest["upstream_iuphar"]["annotation_capability"] == "family_only"
    assert (
        manifest["audit_2026_11_23_control_counts"]["matched"]
        != manifest["audit_2026_11_23_control_counts"][
            "counterfactual_matched_not_accuracy"
        ]
    )
    # Only immutable stage-0 / acceptance bytes are hash-locked.
    pinned = manifest["pinned_artifacts"]
    assert pinned
    for relative, meta in pinned.items():
        path = REPO / relative
        assert path.is_file(), relative
        assert meta["pin_policy"] == "immutable_hash_locked"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == meta["sha256"], relative
    # Live configs/docs/source stay listed but not CI-hash-locked.
    mutable = manifest["mutable_surfaces"]
    assert "configs/entities/chembl/target.yaml" in mutable
    assert (
        "docs/04-reference/pipelines/chembl/16-iuphar-target-classification-semantics.md"
        in mutable
    )
    for relative, meta in mutable.items():
        assert (REPO / relative).is_file(), relative
        assert meta["pin_policy"] in {"not_hash_locked", "versioned_separately"}
    assert DOC.is_file()
    assert "source_unavailable" in DOC.read_text(encoding="utf-8")


def test_matched_available_path_uses_iuphar_normalized_source() -> None:
    """RF-001 dictionary must name the live resolution token, not a short alias."""
    outcome = select_effective_class(
        ResolutionInput(
            match_status="matched",
            iuphar_annotation_status="available",
            local_status="not_supported",
            iuphar_class="Receptor",
        )
    )
    assert outcome.effective_class == "Receptor"
    assert outcome.effective_source == "iuphar_normalized"
    assert outcome.decision_status == "resolved"
    assert "iuphar_normalized" in FIELD_LAYERS["effective_source"]["meaning"]
    assert "iuphar_normalized" in DOC.read_text(encoding="utf-8")


def test_profile_schema_version_is_not_conflated_with_table_contract() -> None:
    rules = semantics_document()["profile_change_rules"]
    assert isinstance(rules, dict)
    schema_rule = str(rules["classification_schema_version"])
    table_rule = str(rules["table_contract"])
    assert "3.1.0" in schema_rule
    assert "shadow and enrich" in schema_rule or "shadow" in schema_rule
    assert "chembl_target_v3.0" in table_rule and "chembl_target_v3.1" in table_rule
    assert "3.0.0" in table_rule
    assert TargetClassificationConfig().contract_version == "3.0.0"
    assert (
        TargetClassificationConfig(
            mode="shadow",
            snapshot_manifest="snapshot.json",
            snapshot_manifest_sha256="a" * 64,
        ).contract_version
        == "3.0.0"
    )
    assert (
        TargetClassificationConfig(
            mode="enrich",
            snapshot_manifest="snapshot.json",
            snapshot_manifest_sha256="a" * 64,
        ).contract_version
        == "3.1.0"
    )


def test_semantics_document_is_canonical_json_stable() -> None:
    first = canonical_json_bytes(semantics_document())
    second = canonical_json_bytes(semantics_document())
    assert first == second
