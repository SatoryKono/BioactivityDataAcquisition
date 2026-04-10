from __future__ import annotations

from scripts.ops.neo4j_memory_query import (
    QUERY_PROFILES,
    _format_rows,
    _neighbors_statement,
    _ownership_statement,
)


def test_query_profiles_cover_operator_shortcuts() -> None:
    assert QUERY_PROFILES["owner-contract"]["target_label"] == "contract_surface"
    assert QUERY_PROFILES["owner-doc"]["target_label"] == "doc_source_surface"
    assert QUERY_PROFILES["owner-doc-artifact"]["target_label"] == "doc_artifact"
    assert QUERY_PROFILES["owner-pipeline"]["target_label"] == "pipeline_surface"
    assert QUERY_PROFILES["owner-alert"]["target_label"] == "alert_surface"
    assert QUERY_PROFILES["neighbors-pipeline"]["mode"] == "neighbors"
    assert QUERY_PROFILES["neighbors-alert"]["target_label"] == "alert_surface"


def test_ownership_statement_uses_target_label_and_directory_houses_edges() -> None:
    statement = _ownership_statement()

    assert "target_label = $target_label" in statement
    assert "(owner:directory_surface)-[houses:HOUSES]->(target)" in statement
    assert "(zone:repo_zone)-[:CONTAINS*1..8]->(owner)" in statement
    assert "parent_directory" not in statement


def test_neighbors_statement_uses_relation_filter_and_bidirectional_search() -> None:
    statement = _neighbors_statement()

    assert "target_label = $target_label" in statement
    assert "type(rel) IN $relation_types" in statement
    assert "MATCH (target)-[rel]->(neighbor)" in statement
    assert "MATCH (neighbor)-[rel]->(target)" in statement
    assert "direction" in statement


def test_format_rows_renders_operator_summary() -> None:
    formatted = _format_rows(
        "owner-contract",
        "chembl.activity",
        [
            {
                "target_name": "chembl.activity",
                "target_label": "contract_surface",
                "owner_directory": "configs/contracts/chembl",
                "repo_zone": "configs",
                "provenance": "file_structure_inferred",
            }
        ],
    )

    assert "Contract ownership path: `chembl.activity`" in formatted
    assert "zone=configs | owner=configs/contracts/chembl" in formatted
    assert "provenance=file_structure_inferred" in formatted


def test_format_rows_renders_neighbors_summary() -> None:
    formatted = _format_rows(
        "neighbors-pipeline",
        "chembl_activity",
        [
            {
                "target_name": "chembl_activity",
                "target_label": "pipeline_surface",
                "direction": "outgoing",
                "relation_type": "DEPENDS_ON",
                "neighbor_name": "chembl.activity",
                "neighbor_labels": ["contract_surface"],
            }
        ],
    )

    assert "Pipeline semantic neighborhood: `chembl_activity`" in formatted
    assert "direction=outgoing | relation=DEPENDS_ON | neighbor=chembl.activity" in formatted
    assert "labels=contract_surface" in formatted


def test_format_rows_handles_missing_results() -> None:
    formatted = _format_rows("owner-alert", "BioETLPipelineRunFailed", [])

    assert formatted == "Alert ownership path: no ownership path found for `BioETLPipelineRunFailed`."


def test_format_rows_handles_missing_neighbors() -> None:
    formatted = _format_rows("neighbors-alert", "BioETLPipelineRunFailed", [])

    assert formatted == "Alert semantic neighborhood: no semantic neighbors found for `BioETLPipelineRunFailed`."
