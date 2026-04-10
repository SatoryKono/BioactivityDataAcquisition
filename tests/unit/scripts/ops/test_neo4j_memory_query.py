from __future__ import annotations

from scripts.ops.neo4j_memory_query import (
    QUERY_PROFILES,
    _duplication_cluster_statement,
    _format_rows,
    _neighbors_statement,
    _ownership_statement,
    _promotion_candidates_statement,
)


def test_query_profiles_cover_operator_shortcuts() -> None:
    assert QUERY_PROFILES["owner-contract"]["target_label"] == "contract_surface"
    assert QUERY_PROFILES["owner-doc"]["target_label"] == "doc_source_surface"
    assert QUERY_PROFILES["owner-doc-artifact"]["target_label"] == "doc_artifact"
    assert QUERY_PROFILES["owner-pipeline"]["target_label"] == "pipeline_surface"
    assert QUERY_PROFILES["owner-alert"]["target_label"] == "alert_surface"
    assert QUERY_PROFILES["neighbors-pipeline"]["mode"] == "neighbors"
    assert QUERY_PROFILES["neighbors-alert"]["target_label"] == "alert_surface"
    assert QUERY_PROFILES["duplication-cluster"]["target_label"] == "duplication_cluster"
    assert QUERY_PROFILES["promotion-candidates"]["mode"] == "promotion_candidates"


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


def test_duplication_cluster_statement_uses_cluster_targets_members_and_tests() -> None:
    statement = _duplication_cluster_statement()

    assert "MATCH (cluster:duplication_cluster {name: $name})" in statement
    assert "(cluster)-[:CAN_PROMOTE_TO]->(target)" in statement
    assert "(cluster)-[:CONTAINS]->(member)" in statement
    assert "(cluster)-[:COVERED_BY_TEST]->(test)" in statement
    assert "collect(DISTINCT" in statement


def test_promotion_candidates_statement_filters_by_family_and_orders_by_score() -> None:
    statement = _promotion_candidates_statement()

    assert "MATCH (cluster:duplication_cluster)" in statement
    assert "$name = 'all' OR cluster.family_name = $name" in statement
    assert "count(DISTINCT member) AS member_count" in statement
    assert "count(DISTINCT test) AS test_count" in statement
    assert "ORDER BY cluster.promotion_score DESC, cluster.duplicate_count DESC" in statement


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


def test_format_rows_renders_duplication_cluster_summary() -> None:
    formatted = _format_rows(
        "duplication-cluster",
        "adapter_layer:method_surface:de487f71c608",
        [
            {
                "cluster_name": "adapter_layer:method_surface:de487f71c608",
                "family_name": "adapter_layer",
                "surface_kind": "method_surface",
                "duplicate_count": 4,
                "promotion_score": 0.99,
                "promotion_target": "src/bioetl/infrastructure/adapters/base.py",
                "promotion_target_labels": ["module_surface"],
                "members": [
                    {
                        "name": "src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count",
                        "labels": ["method_surface"],
                    }
                ],
                "tests": [
                    "tests/unit/infrastructure/adapters/test_pubmed_health.py",
                ],
            }
        ],
    )

    assert "Duplication cluster: `adapter_layer:method_surface:de487f71c608`" in formatted
    assert "family=adapter_layer | surface_kind=method_surface | duplicates=4 | promotion_score=0.99" in formatted
    assert "promotion_target=src/bioetl/infrastructure/adapters/base.py | labels=module_surface" in formatted
    assert "member=src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count | labels=method_surface" in formatted
    assert "covered_by_test=tests/unit/infrastructure/adapters/test_pubmed_health.py" in formatted


def test_format_rows_renders_promotion_candidates_summary() -> None:
    formatted = _format_rows(
        "promotion-candidates",
        "adapter_layer",
        [
            {
                "cluster_name": "adapter_layer:method_surface:d1c4b44398a1",
                "family_name": "adapter_layer",
                "surface_kind": "method_surface",
                "duplicate_count": 27,
                "promotion_score": 0.99,
                "promotion_target": "src/bioetl/infrastructure/adapters/base.py",
                "member_count": 27,
                "test_count": 80,
            }
        ],
    )

    assert "Promotion candidates: `adapter_layer`" in formatted
    assert "cluster=adapter_layer:method_surface:d1c4b44398a1 | family=adapter_layer" in formatted
    assert "duplicates=27 | members=27 | tests=80 | promotion_score=0.99" in formatted
    assert "target=src/bioetl/infrastructure/adapters/base.py" in formatted


def test_format_rows_handles_missing_results() -> None:
    formatted = _format_rows("owner-alert", "BioETLPipelineRunFailed", [])

    assert formatted == "Alert ownership path: no ownership path found for `BioETLPipelineRunFailed`."


def test_format_rows_handles_missing_neighbors() -> None:
    formatted = _format_rows("neighbors-alert", "BioETLPipelineRunFailed", [])

    assert formatted == "Alert semantic neighborhood: no semantic neighbors found for `BioETLPipelineRunFailed`."


def test_format_rows_handles_missing_duplication_cluster() -> None:
    formatted = _format_rows("duplication-cluster", "missing-cluster", [])

    assert formatted == "Duplication cluster: no duplication cluster found for `missing-cluster`."


def test_format_rows_handles_missing_promotion_candidates() -> None:
    formatted = _format_rows("promotion-candidates", "missing-family", [])

    assert formatted == "Promotion candidates: no promotion candidates found for `missing-family`."
