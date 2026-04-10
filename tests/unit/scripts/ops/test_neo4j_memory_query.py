from __future__ import annotations

from scripts.ops.neo4j_memory_query import (
    _current_cycle_code_statement,
    _dead_code_candidates_statement,
    _fallback_pipelines_statement,
    _normalization_pipeline_statement,
    _overengineered_candidates_statement,
    _removable_complexity_statement,
    _simplification_blockers_statement,
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
    assert QUERY_PROFILES["normalization-pipeline"]["mode"] == "normalization_pipeline"
    assert QUERY_PROFILES["fallback-pipelines"]["mode"] == "fallback_pipelines"
    assert QUERY_PROFILES["duplication-cluster"]["target_label"] == "duplication_cluster"
    assert QUERY_PROFILES["promotion-candidates"]["mode"] == "promotion_candidates"
    assert QUERY_PROFILES["dead-code-candidates"]["target_label"] == "retirement_candidate"
    assert QUERY_PROFILES["current-cycle-code"]["mode"] == "current_cycle_code"
    assert QUERY_PROFILES["overengineered-candidates"]["target_label"] == "complexity_candidate"
    assert QUERY_PROFILES["removable-complexity"]["mode"] == "removable_complexity"
    assert QUERY_PROFILES["simplification-blockers"]["mode"] == "simplification_blockers"


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


def test_normalization_pipeline_statement_surfaces_profile_and_fallback_metrics() -> None:
    statement = _normalization_pipeline_statement()

    assert "MATCH (pipeline:pipeline_surface {name: $name})" in statement
    assert "pipeline.normalization_profile_registered AS normalization_profile_registered" in statement
    assert "pipeline.fallback_business_field_count AS fallback_business_field_count" in statement
    assert "collect(DISTINCT module.name) AS normalization_modules" in statement


def test_fallback_pipelines_statement_orders_by_fallback_business_count() -> None:
    statement = _fallback_pipelines_statement()

    assert "coalesce(pipeline.fallback_business_field_count, 0) > 0" in statement
    assert "$name = 'all' OR pipeline.name = $name" in statement
    assert "ORDER BY pipeline.fallback_business_field_count DESC" in statement


def test_promotion_candidates_statement_filters_by_family_and_orders_by_score() -> None:
    statement = _promotion_candidates_statement()

    assert "MATCH (cluster:duplication_cluster)" in statement
    assert "$name = 'all' OR cluster.family_name = $name" in statement
    assert "count(DISTINCT member) AS member_count" in statement
    assert "count(DISTINCT test) AS test_count" in statement
    assert "ORDER BY cluster.promotion_score DESC, cluster.duplicate_count DESC" in statement


def test_dead_code_candidates_statement_filters_family_and_blockers() -> None:
    statement = _dead_code_candidates_statement()

    assert "MATCH (candidate:retirement_candidate)" in statement
    assert "$name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name" in statement
    assert "(candidate)-[:CANDIDATE_FOR_REMOVAL]->(target)" in statement
    assert "candidate.blocked_by_current_cycle_target_name AS blocked_by_cycle" in statement
    assert "ORDER BY candidate.deletion_score DESC" in statement


def test_current_cycle_code_statement_filters_family_and_targets() -> None:
    statement = _current_cycle_code_statement()

    assert "MATCH (target)" in statement
    assert "coalesce(target.current_cycle_status, '') <> ''" in statement
    assert "$name = 'all' OR target.family_name = $name OR target.name = $name" in statement
    assert "ORDER BY target.current_cycle_score DESC" in statement


def test_overengineered_candidates_statement_filters_family_and_complexity_scores() -> None:
    statement = _overengineered_candidates_statement()

    assert "MATCH (candidate:complexity_candidate)" in statement
    assert "$name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name" in statement
    assert "(candidate)-[:CANDIDATE_FOR_SIMPLIFICATION]->(target)" in statement
    assert "candidate.blocked_by_current_cycle_target_name AS blocked_by_cycle" in statement
    assert "ORDER BY candidate.simplification_score DESC" in statement


def test_removable_complexity_statement_filters_classification() -> None:
    statement = _removable_complexity_statement()

    assert "MATCH (candidate:complexity_candidate)" in statement
    assert "candidate.classification = 'removable_complexity'" in statement
    assert "(candidate)-[:CANDIDATE_FOR_REMOVAL]->(target)" in statement
    assert "ORDER BY candidate.removable_score DESC" in statement


def test_simplification_blockers_statement_collects_cycles_and_blockers() -> None:
    statement = _simplification_blockers_statement()

    assert "MATCH (candidate:complexity_candidate)" in statement
    assert "[rel:JUSTIFIED_BY_RUNTIME|BLOCKED_BY_VARIANCE]" in statement
    assert "[candidate.blocked_by_current_cycle_target_name] AS cycle_blockers" in statement


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


def test_format_rows_renders_pipeline_normalization_evidence() -> None:
    formatted = _format_rows(
        "normalization-pipeline",
        "chembl_activity",
        [
            {
                "pipeline_name": "chembl_activity",
                "normalization_profile_registered": True,
                "normalization_profile_module_path": "src/bioetl/domain/normalization/profiles/chembl_activity.py",
                "profile_field_count": 12,
                "fallback_field_count": 1,
                "fallback_business_field_count": 1,
                "fallback_technical_passthrough_field_count": 0,
                "normalization_modules": [
                    "src/bioetl/application/core/record_normalization_processor.py",
                    "src/bioetl/domain/normalization/profiles/chembl_activity.py",
                ],
            }
        ],
    )

    assert "Pipeline normalization evidence: `chembl_activity`" in formatted
    assert "profile_registered=True | profile_fields=12 | fallback_fields=1 | fallback_business=1 | fallback_technical=0" in formatted
    assert "profile_module=src/bioetl/domain/normalization/profiles/chembl_activity.py" in formatted
    assert "normalization_module=src/bioetl/domain/normalization/profiles/chembl_activity.py" in formatted


def test_format_rows_renders_fallback_pipeline_summary() -> None:
    formatted = _format_rows(
        "fallback-pipelines",
        "all",
        [
            {
                "pipeline_name": "chembl_assay_parameters",
                "normalization_profile_registered": False,
                "profile_field_count": 0,
                "fallback_field_count": 22,
                "fallback_business_field_count": 22,
            }
        ],
    )

    assert "Fallback-heavy pipelines: `all`" in formatted
    assert "pipeline=chembl_assay_parameters | fallback_business=22 | fallback_total=22 | profile_registered=False | profile_fields=0" in formatted


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


def test_format_rows_renders_dead_code_candidates_summary() -> None:
    formatted = _format_rows(
        "dead-code-candidates",
        "adapter_layer",
        [
            {
                "candidate_name": "module_surface:src/bioetl/infrastructure/adapters/pubchem/client.py",
                "family_name": "adapter_layer",
                "target_label": "module_surface",
                "target_name": "src/bioetl/infrastructure/adapters/pubchem/client.py",
                "deletion_score": 8,
                "deletion_confidence": "high",
                "recent_age_days": 420,
                "only_test_referenced": True,
                "deprecation_markers": ["deprecated", "legacy"],
                "runtime_anchor_count": 0,
                "config_anchor_count": 0,
                "doc_anchor_count": 0,
                "test_anchor_count": 3,
                "blocked_by_cycle": "",
            }
        ],
    )

    assert "Dead code candidates: `adapter_layer`" in formatted
    assert "target=src/bioetl/infrastructure/adapters/pubchem/client.py | label=module_surface | family=adapter_layer" in formatted
    assert "deletion_score=8 | confidence=high | recent_age_days=420" in formatted
    assert "deprecation_markers=deprecated,legacy" in formatted


def test_format_rows_renders_current_cycle_code_summary() -> None:
    formatted = _format_rows(
        "current-cycle-code",
        "adapter_layer",
        [
            {
                "cycle_name": "module_surface:src/bioetl/infrastructure/adapters/common/new_runtime.py",
                "family_name": "adapter_layer",
                "target_label": "module_surface",
                "target_name": "src/bioetl/infrastructure/adapters/common/new_runtime.py",
                "cycle_status": "current_cycle",
                "cycle_score": 5,
                "recent_age_days": 3,
                "wip_markers": ["todo", "temporary"],
                "runtime_anchor_count": 0,
                "config_anchor_count": 0,
                "doc_anchor_count": 1,
                "test_anchor_count": 1,
            }
        ],
    )

    assert "Current-cycle code surfaces: `adapter_layer`" in formatted
    assert "target=src/bioetl/infrastructure/adapters/common/new_runtime.py | label=module_surface | family=adapter_layer" in formatted
    assert "cycle_status=current_cycle | cycle_score=5 | recent_age_days=3" in formatted
    assert "wip_markers=todo,temporary" in formatted


def test_format_rows_renders_overengineered_candidates_summary() -> None:
    formatted = _format_rows(
        "overengineered-candidates",
        "composite_layer",
        [
            {
                "candidate_name": "module_surface:src/bioetl/application/composite/runner_pkg/runner.py",
                "family_name": "composite_layer",
                "target_label": "module_surface",
                "target_name": "src/bioetl/application/composite/runner_pkg/runner.py",
                "classification": "overengineered_stale",
                "complexity_score": 6,
                "simplification_score": 6,
                "removable_score": 8,
                "branch_count": 7,
                "nesting_depth": 4,
                "helper_call_count": 3,
                "indirection_markers": ["compat", "runner"],
                "stateful_markers": ["runner"],
                "runtime_anchor_count": 0,
                "config_anchor_count": 0,
                "doc_anchor_count": 0,
                "test_anchor_count": 0,
                "blocked_by_cycle": "",
            }
        ],
    )

    assert "Overengineered candidates: `composite_layer`" in formatted
    assert "target=src/bioetl/application/composite/runner_pkg/runner.py | label=module_surface | family=composite_layer" in formatted
    assert "classification=overengineered_stale | complexity_score=6 | simplification_score=6 | removable_score=8" in formatted
    assert "indirection_markers=compat,runner" in formatted


def test_format_rows_renders_removable_complexity_summary() -> None:
    formatted = _format_rows(
        "removable-complexity",
        "composite_layer",
        [
            {
                "candidate_name": "module_surface:src/bioetl/application/composite/merger.py",
                "family_name": "composite_layer",
                "target_label": "module_surface",
                "target_name": "src/bioetl/application/composite/merger.py",
                "removable_score": 9,
                "removal_confidence": "high",
                "deprecation_markers": ["compat", "legacy"],
                "runtime_anchor_count": 0,
                "config_anchor_count": 0,
                "doc_anchor_count": 0,
                "test_anchor_count": 0,
            }
        ],
    )

    assert "Removable complexity candidates: `composite_layer`" in formatted
    assert "target=src/bioetl/application/composite/merger.py | label=module_surface | family=composite_layer" in formatted
    assert "removable_score=9 | removal_confidence=high" in formatted
    assert "deprecation_markers=compat,legacy" in formatted


def test_format_rows_renders_simplification_blockers_summary() -> None:
    formatted = _format_rows(
        "simplification-blockers",
        "adapter_layer",
        [
            {
                "candidate_name": "method_surface:src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count",
                "family_name": "adapter_layer",
                "target_label": "method_surface",
                "target_name": "src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count",
                "classification": "overengineered_active",
                "runtime_anchor_count": 2,
                "config_anchor_count": 1,
                "doc_anchor_count": 0,
                "test_anchor_count": 3,
                "cycle_blockers": ["method_surface:src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count"],
                "blockers": [
                    {
                        "name": "pubmed",
                        "labels": ["provider_surface"],
                        "relation": "BLOCKED_BY_VARIANCE",
                    }
                ],
            }
        ],
    )

    assert "Simplification blockers: `adapter_layer`" in formatted
    assert "target=src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count | label=method_surface | family=adapter_layer" in formatted
    assert "cycle_blocker=method_surface:src.bioetl.infrastructure.adapters.pubmed._health.PubMedHealthMixin.request_count" in formatted
    assert "blocker=pubmed | relation=BLOCKED_BY_VARIANCE | labels=provider_surface" in formatted


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


def test_format_rows_handles_missing_dead_code_candidates() -> None:
    formatted = _format_rows("dead-code-candidates", "missing-family", [])

    assert formatted == "Dead code candidates: no dead code candidates found for `missing-family`."


def test_format_rows_handles_missing_current_cycle_code() -> None:
    formatted = _format_rows("current-cycle-code", "missing-family", [])

    assert formatted == "Current-cycle code surfaces: no current-cycle code surfaces found for `missing-family`."


def test_format_rows_handles_missing_overengineered_candidates() -> None:
    formatted = _format_rows("overengineered-candidates", "missing-family", [])

    assert formatted == "Overengineered candidates: no overengineered candidates found for `missing-family`."


def test_format_rows_handles_missing_removable_complexity() -> None:
    formatted = _format_rows("removable-complexity", "missing-family", [])

    assert formatted == "Removable complexity candidates: no removable complexity candidates found for `missing-family`."


def test_format_rows_handles_missing_simplification_blockers() -> None:
    formatted = _format_rows("simplification-blockers", "missing-family", [])

    assert formatted == "Simplification blockers: no simplification blockers found for `missing-family`."
