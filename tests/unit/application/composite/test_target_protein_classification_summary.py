"""Tests for target protein-classification pre-join summary projection."""

from __future__ import annotations

import json

import polars as pl
import pytest

from bioetl.application.composite.target_protein_classification_summary import (
    summarize_target_protein_classification_dependency,
)
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
    initialize_protein_class_target_type_mapping,
)


@pytest.fixture(autouse=True)
def _init_protein_class_mapping() -> None:
    initialize_protein_class_target_type_mapping(
        ProteinClassTargetTypeMappingData(
            mapping_version="protein_class_l1_map_v1",
            entries=(
                ProteinClassTopLevelMappingEntry("Enzyme", "enzyme", True),
                ProteinClassTopLevelMappingEntry("Ion channel", "ion_channel", True),
                ProteinClassTopLevelMappingEntry("Transporter", "transporter", True),
                ProteinClassTopLevelMappingEntry(
                    "Unclassified protein",
                    "unclassified_protein",
                    False,
                ),
                ProteinClassTopLevelMappingEntry(
                    "Membrane receptor",
                    "membrane_receptor",
                    True,
                ),
            ),
        )
    )


@pytest.mark.unit
def test_summary_copies_single_resolved_hierarchy_levels() -> None:
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1"],
            "component_id": [10],
            "leaf_id": [231],
            "l1_id": [1],
            "l1_name": ["Enzyme"],
            "l1_desc": ["Root"],
            "l2_id": [2],
            "l2_name": ["Kinase"],
            "l2_desc": ["Branch"],
            "l3_id": [231],
            "l3_name": ["Protein kinase"],
            "l3_desc": ["Leaf"],
            "classification_status": ["resolved"],
        }
    )

    result = summarize_target_protein_classification_dependency(df)
    row = result.to_dicts()[0]

    assert row["target_protein_class_id_L1"] == "1"
    assert row["target_protein_class_name_L1"] == "Enzyme"
    assert row["target_protein_class_desc_L1"] == "Root"
    assert row["target_protein_class_type"] == "enzyme"
    assert row["top_level_count"] == 1
    assert row["canonical_top_levels"] == '["enzyme"]'
    assert row["counted_top_levels"] == '["enzyme"]'
    assert row["ignored_top_levels"] == "[]"
    assert row["primary_top_level"] == "enzyme"
    assert row["target_type_reason_code"] == "single_informative_top_level"
    assert row["target_protein_class_id_L3"] == "231"
    assert row["target_protein_class_name_L3"] == "Protein kinase"
    payload = json.loads(row["protein_classifications"])
    assert payload[0]["leaf_id"] == 231
    assert payload[0]["classification_status"] == "resolved"


@pytest.mark.unit
def test_summary_marks_multiple_informative_l1_values_as_multifunctional() -> None:
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL1"],
            "component_id": [10, 11],
            "leaf_id": [300, 200],
            "l1_id": [3, 1],
            "l1_name": ["Transporter", "Enzyme"],
            "l2_id": [4, 2],
            "l2_name": ["Ion channel", "Kinase"],
            "classification_status": ["resolved", "resolved"],
        }
    )

    result = summarize_target_protein_classification_dependency(df)
    row = result.to_dicts()[0]

    assert row["target_protein_class_id_L1"] is None
    assert row["target_protein_class_id_L5"] is None
    assert row["target_protein_class_name_L1"] == "Multifunctional target"
    assert row["target_protein_class_name_L2"] == "Multifunctional target"
    assert row["target_protein_class_name_L3"] == ""
    assert row["target_protein_class_name_L4"] == ""
    assert row["target_protein_class_name_L5"] == ""
    assert row["target_protein_class_type"] == "multifunctional"
    assert row["top_level_count"] == 2
    assert row["counted_top_levels"] == '["enzyme","transporter"]'
    assert row["primary_top_level"] is None
    assert row["multifunctional_origin"] == "multi_component_heterogeneity"
    payload = json.loads(row["protein_classifications"])
    assert [item["leaf_id"] for item in payload] == [200, 300]


@pytest.mark.unit
def test_summary_does_not_mark_duplicate_top_level_branches_multifunctional() -> None:
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL1"],
            "component_id": [10, 11],
            "leaf_id": [300, 200],
            "l1_id": [1, 1],
            "l1_name": ["Enzyme", "Enzyme"],
            "l2_id": [4, 2],
            "l2_name": ["Hydrolase", "Kinase"],
            "classification_status": ["resolved", "resolved"],
        }
    )

    result = summarize_target_protein_classification_dependency(df)
    row = result.to_dicts()[0]

    assert row["target_protein_class_type"] == "enzyme"
    assert row["top_level_count"] == 1
    assert row["target_protein_class_name_L1"] == "Enzyme"
    assert row["target_protein_class_name_L2"] == "Kinase"
    assert row["protein_classifications"] is not None


@pytest.mark.unit
def test_summary_ignores_unclassified_top_level_for_target_type() -> None:
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL1"],
            "component_id": [10, 11],
            "leaf_id": [300, 200],
            "l1_id": [9, 3],
            "l1_name": ["Unclassified protein", "Ion channel"],
            "classification_status": ["resolved", "resolved"],
        }
    )

    result = summarize_target_protein_classification_dependency(df)
    row = result.to_dicts()[0]

    assert row["target_protein_class_type"] == "ion_channel"
    assert row["top_level_count"] == 1
    assert row["ignored_top_levels"] == '["unclassified_protein"]'
    assert row["target_protein_class_name_L1"] == "Ion channel"


@pytest.mark.unit
def test_summary_ignores_missing_and_quarantined_classifications() -> None:
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL1"],
            "leaf_id": [None, 9],
            "classification_status": ["missing_classification", "quarantined"],
        }
    )

    result = summarize_target_protein_classification_dependency(df)
    row = result.to_dicts()[0]

    assert row["protein_classifications"] is None
    assert row["target_protein_class_name_L1"] is None
    assert row["target_protein_class_id_L1"] is None
    assert row["target_protein_class_type"] == "unknown"
    assert row["top_level_count"] == 0
    assert row["target_type_reason_code"] == "no_informative_top_level"


@pytest.mark.unit
def test_summary_deduplicates_leaf_ids_deterministically() -> None:
    df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL1"],
            "leaf_id": [42, 42],
            "component_id": [11, 10],
            "l1_id": [99, 1],
            "l1_name": ["Late", "First"],
            "classification_status": ["resolved", "resolved"],
        }
    )

    result = summarize_target_protein_classification_dependency(df)
    row = result.to_dicts()[0]

    assert row["target_protein_class_id_L1"] == "1"
    assert row["target_protein_class_name_L1"] == "First"
    assert row["target_protein_class_type"] == "other_classified_protein"
    assert json.loads(row["protein_classifications"])[0]["l1_id"] == 1
