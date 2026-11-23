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
    assert "uniprot_protein annotations/keywords" in standalone["unavailable_until_joins"]


def test_path_missing_marker_and_other_policies() -> None:
    assert PATH_POLICY["canonical_direction"] == "root_to_leaf"
    assert PATH_POLICY["legacy_text_field"] == "leaf_to_root"
    assert PATH_POLICY["multiple_parents_allowed"] is True
    assert list(MISSING_MARKER_POLICY["base_markers"]) == list(BASE_MISSING_MARKERS)
    assert MISSING_MARKER_POLICY["version"] is None
    assert "unmapped_type or name/path text containing 'Other'" in LEGACY_OTHER_POLICY[
        "forbidden_when"
    ]
    assert WORKING_CLASSES == tuple(semantics_document()["working_classes"])
    assert "Other Protein Target" in WORKING_CLASSES


def test_baseline_manifest_hashes_and_receipt() -> None:
    payload = MANIFEST.read_bytes()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert hashlib.sha256(payload).hexdigest() == receipt["sha256"]
    manifest = json.loads(payload.decode("utf-8"))
    assert manifest["artifact"] == "iuphar_rf001_baseline_manifest"
    assert manifest["biological_accuracy_accepted"] is False
    assert manifest["m_code"]["status"] == "не установлено"
    assert manifest["m_code"]["excel_cache_confirms_fresh_recalc"] is False
    assert manifest["upstream_iuphar"]["annotation_capability"] == "family_only"
    assert (
        manifest["audit_2026_11_23_control_counts"]["matched"]
        != manifest["audit_2026_11_23_control_counts"]["counterfactual_matched_not_accuracy"]
    )
    for relative, meta in manifest["artifacts"].items():
        path = REPO / relative
        assert path.is_file(), relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == meta["sha256"], relative
    assert DOC.is_file()
    assert "source_unavailable" in DOC.read_text(encoding="utf-8")


def test_semantics_document_is_canonical_json_stable() -> None:
    first = canonical_json_bytes(semantics_document())
    second = canonical_json_bytes(semantics_document())
    assert first == second
