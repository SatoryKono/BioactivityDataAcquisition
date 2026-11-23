"""RF-003 (#13311): composite post-join feature whitelist contract."""

from __future__ import annotations

import json
from pathlib import Path

from iuphar_target_class.bioetl_input import project_target_fields
from iuphar_target_class.composite_features import (
    CONTRACT_VERSION,
    FEATURE_CONTRACT_VERSION,
    build_classification_business_data,
    feature_availability,
    feature_completeness,
)


def test_feature_contract_artifact_pins_whitelist() -> None:
    root = Path("data/iuphar_target_class/rf003")
    payload = json.loads((root / "feature_whitelist.json").read_text(encoding="utf-8"))
    sidecar = json.loads(
        (root / "feature_whitelist.sha256.json").read_text(encoding="utf-8")
    )
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["surface"] == "composite_post_join"
    assert "keywords" in payload["whitelist_fields"]
    assert sidecar["sha256"]
    assert sidecar["contract_version"] == FEATURE_CONTRACT_VERSION


def test_keywords_and_l1_appear_only_after_join_shaped_row() -> None:
    seed_only = {
        "target_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "taxonomy_id": "9606",
        "organism": "Homo sapiens",
        "pref_name": "Example",
        "component_accessions": "P12345",
        "target_ec_numbers": "1.1.1.1",
    }
    assert feature_availability(seed_only)["keywords"] is False
    assert feature_availability(seed_only)["predicted_l1"] is False
    assert feature_completeness(seed_only) == "partial"

    after_join = {
        **seed_only,
        "keywords": "Kinase|ATP-binding",
        "target_protein_class_name_L1": "Enzyme",
        "target_protein_class_name_L2": "Kinase",
        "gene_primary": "GENE1",
        "uniprot_accession": "P12345",
    }
    availability = feature_availability(after_join)
    assert availability["keywords"] is True
    assert availability["predicted_l1"] is True
    assert availability["predicted_l2"] is True
    assert feature_completeness(after_join) == "complete"

    business = build_classification_business_data(after_join)
    assert business["keywords"] == "Kinase|ATP-binding"
    assert business["predicted_l1"] == "Enzyme"
    assert business["predicted_l2"] == "Kinase"
    assert business["gene_symbol"] == "GENE1"
    assert business["_classification_surface"] == "composite_post_join"
    assert "whitelist_sha256" in business["_classification_source_digests"]

    projected = project_target_fields(business, "9606")
    assert projected["keywords"] == "Kinase|ATP-binding"
    assert projected["predicted_l1"] == "Enzyme"
    assert projected["predicted_l2"] == "Kinase"
    assert "Enzyme" in (projected["source_business_data"] or "")
    assert "content_hash" not in (projected["source_business_data"] or "")


def test_predicted_layers_are_not_iuphar_identity_by_name() -> None:
    row = {
        "target_id": "CHEMBL2",
        "target_type": "SINGLE PROTEIN",
        "taxonomy_id": "9606",
        "organism": "Homo sapiens",
        "component_accessions": "Q9Y6K1",
        "target_protein_class_name_L1": "Other Protein Target",
    }
    business = build_classification_business_data(row)
    assert business["predicted_l1"] == "Other Protein Target"
    assert (
        business["_classification_l1_l2_provenance"]
        == "chembl_target_protein_classification_summary:predicted_layer_not_iuphar_identity"
    )


def test_idmapping_fills_primary_only_when_component_list_empty() -> None:
    fields = project_target_fields(
        {
            "target_id": "CHEMBL3",
            "uniprot_accession": "P99999",
            "target_xref_uniprot_ids": "P99999",
        },
        "9606",
    )
    assert fields["uniprot"] == "P99999"
    assert fields["uniprot_equivalent"] == "P99999"
