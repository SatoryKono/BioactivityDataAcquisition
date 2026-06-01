"""Tests for target protein-classification pre-join summary projection."""

from __future__ import annotations

import json

import polars as pl
import pytest

from bioetl.application.composite.target_protein_classification_summary import (
    summarize_target_protein_classification_dependency,
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
    assert row["target_protein_class_id_L3"] == "231"
    assert row["target_protein_class_name_L3"] == "Protein kinase"
    payload = json.loads(row["protein_classifications"])
    assert payload[0]["leaf_id"] == 231
    assert payload[0]["classification_status"] == "resolved"


@pytest.mark.unit
def test_summary_marks_multiple_leaf_ids_as_multifunctional() -> None:
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
    payload = json.loads(row["protein_classifications"])
    assert [item["leaf_id"] for item in payload] == [200, 300]


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
    assert json.loads(row["protein_classifications"])[0]["l1_id"] == 1
