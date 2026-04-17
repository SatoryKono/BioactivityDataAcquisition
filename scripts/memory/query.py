#!/usr/bin/env python3
"""Operator-facing shortcuts for querying deterministic Neo4j memory paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Final, NotRequired, TypedDict

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))

try:
    from scripts.memory.sync import (
        JsonValue,
        Neo4jHttpClient,
        resolve_neo4j_connection,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from scripts.memory.sync import (
        JsonValue,
        Neo4jHttpClient,
        resolve_neo4j_connection,
    )

DEFAULT_NEIGHBOR_RELATION_TYPES: Final[tuple[str, ...]] = (
    "DEPENDS_ON",
    "TESTED_BY",
    "OBSERVED_BY",
    "RUNS_VIA",
    "VALIDATED_BY",
    "BACKED_BY",
    "GOVERNS",
)


class QueryProfile(TypedDict):
    mode: str
    target_label: str
    title: str
    relation_types: NotRequired[tuple[str, ...]]


QUERY_PROFILES: Final[dict[str, QueryProfile]] = {
    "owner-contract": {
        "mode": "owner",
        "target_label": "contract_surface",
        "title": "Contract ownership path",
    },
    "owner-doc": {
        "mode": "owner",
        "target_label": "doc_source_surface",
        "title": "Documentation ownership path",
    },
    "owner-doc-artifact": {
        "mode": "owner",
        "target_label": "doc_artifact",
        "title": "Documentation artifact ownership path",
    },
    "owner-pipeline": {
        "mode": "owner",
        "target_label": "pipeline_surface",
        "title": "Pipeline ownership path",
    },
    "owner-alert": {
        "mode": "owner",
        "target_label": "alert_surface",
        "title": "Alert ownership path",
    },
    "owner-storage": {
        "mode": "owner",
        "target_label": "storage_surface",
        "title": "Storage ownership path",
    },
    "owner-runtime-evidence": {
        "mode": "owner",
        "target_label": "runtime_evidence_surface",
        "title": "Runtime evidence ownership path",
    },
    "owner-runtime-state": {
        "mode": "owner",
        "target_label": "runtime_state_surface",
        "title": "Runtime state ownership path",
    },
    "owner-workflow": {
        "mode": "owner",
        "target_label": "workflow_surface",
        "title": "Workflow ownership path",
    },
    "owner-workflow-job": {
        "mode": "owner",
        "target_label": "workflow_job_surface",
        "title": "Workflow job ownership path",
    },
    "owner-workflow-call": {
        "mode": "owner",
        "target_label": "workflow_call_surface",
        "title": "Workflow call ownership path",
    },
    "owner-workflow-output": {
        "mode": "owner",
        "target_label": "workflow_output_surface",
        "title": "Workflow output ownership path",
    },
    "owner-cli-command": {
        "mode": "owner",
        "target_label": "cli_command_surface",
        "title": "CLI command ownership path",
    },
    "owner-cli-option": {
        "mode": "owner",
        "target_label": "cli_option_surface",
        "title": "CLI option ownership path",
    },
    "owner-schema-field": {
        "mode": "owner",
        "target_label": "schema_field_surface",
        "title": "Schema field ownership path",
    },
    "neighbors-contract": {
        "mode": "neighbors",
        "target_label": "contract_surface",
        "title": "Contract semantic neighborhood",
    },
    "neighbors-doc": {
        "mode": "neighbors",
        "target_label": "doc_source_surface",
        "title": "Documentation semantic neighborhood",
    },
    "neighbors-doc-artifact": {
        "mode": "neighbors",
        "target_label": "doc_artifact",
        "title": "Documentation artifact semantic neighborhood",
    },
    "neighbors-pipeline": {
        "mode": "neighbors",
        "target_label": "pipeline_surface",
        "title": "Pipeline semantic neighborhood",
    },
    "neighbors-alert": {
        "mode": "neighbors",
        "target_label": "alert_surface",
        "title": "Alert semantic neighborhood",
    },
    "neighbors-storage": {
        "mode": "neighbors",
        "target_label": "storage_surface",
        "title": "Storage semantic neighborhood",
        "relation_types": ("WRITES_TO", "PROMOTES_TO", "DEPENDS_ON", "DEFINED_BY"),
    },
    "neighbors-runtime-evidence": {
        "mode": "neighbors",
        "target_label": "runtime_evidence_surface",
        "title": "Runtime evidence semantic neighborhood",
        "relation_types": ("BACKED_BY", "DESCRIBED_IN", "WRITES_TO"),
    },
    "neighbors-runtime-state": {
        "mode": "neighbors",
        "target_label": "runtime_state_surface",
        "title": "Runtime state semantic neighborhood",
        "relation_types": ("DEPENDS_ON", "REFERENCES_ARTIFACT", "DESCRIBED_IN"),
    },
    "neighbors-workflow": {
        "mode": "neighbors",
        "target_label": "workflow_surface",
        "title": "Workflow semantic neighborhood",
        "relation_types": ("CONTAINS", "RUNS_VIA", "EXECUTES_GATE", "DEPENDS_ON"),
    },
    "neighbors-workflow-job": {
        "mode": "neighbors",
        "target_label": "workflow_job_surface",
        "title": "Workflow job semantic neighborhood",
        "relation_types": ("CONTAINS", "RUNS_VIA", "EXECUTES_GATE", "DEPENDS_ON"),
    },
    "neighbors-run-instance": {
        "mode": "neighbors",
        "target_label": "run_instance_surface",
        "title": "Run instance semantic neighborhood",
        "relation_types": ("REFERENCES_ARTIFACT", "DEPENDS_ON", "DESCRIBED_IN"),
    },
    "neighbors-cli-command": {
        "mode": "neighbors",
        "target_label": "cli_command_surface",
        "title": "CLI command semantic neighborhood",
        "relation_types": ("RUNS_VIA", "EXECUTES_GATE", "DEPENDS_ON"),
    },
    "docs-drift": {
        "mode": "docs_drift",
        "target_label": "doc_surface",
        "title": "Docs-to-code drift edges",
    },
    "workflow-gates": {
        "mode": "workflow_gates",
        "target_label": "workflow_surface",
        "title": "Workflow gates and executed targets",
    },
    "workflow-artifacts": {
        "mode": "workflow_artifacts",
        "target_label": "workflow_surface",
        "title": "Workflow actions, artifacts, and secrets",
    },
    "workflow-execution": {
        "mode": "workflow_execution",
        "target_label": "workflow_surface",
        "title": "Workflow execution semantics",
    },
    "storage-lineage": {
        "mode": "storage_lineage",
        "target_label": "storage_surface",
        "title": "Storage lineage path",
    },
    "field-lineage": {
        "mode": "field_lineage",
        "target_label": "schema_field_surface",
        "title": "Field lineage path",
    },
    "schema-drift": {
        "mode": "schema_drift",
        "target_label": "schema_field_surface",
        "title": "Schema drift evidence",
    },
    "run-artifacts": {
        "mode": "run_artifacts",
        "target_label": "run_instance_surface",
        "title": "Run instance artifact chain",
    },
    "runtime-state": {
        "mode": "runtime_state",
        "target_label": "runtime_state_surface",
        "title": "Runtime state summary",
    },
    "runtime-locks": {
        "mode": "runtime_locks",
        "target_label": "runtime_state_surface",
        "title": "Runtime lock state",
    },
    "claim-trace": {
        "mode": "claim_trace",
        "target_label": "doc_claim_surface",
        "title": "Claim-level documentation traceability",
    },
    "cli-semantics": {
        "mode": "cli_semantics",
        "target_label": "cli_command_surface",
        "title": "CLI options and side-effect semantics",
    },
    "normalization-pipeline": {
        "mode": "normalization_pipeline",
        "target_label": "pipeline_surface",
        "title": "Pipeline normalization evidence",
    },
    "fallback-pipelines": {
        "mode": "fallback_pipelines",
        "target_label": "pipeline_surface",
        "title": "Fallback-heavy pipelines",
    },
    "duplication-cluster": {
        "mode": "duplication_cluster",
        "target_label": "duplication_cluster",
        "title": "Duplication cluster",
    },
    "promotion-candidates": {
        "mode": "promotion_candidates",
        "target_label": "duplication_cluster",
        "title": "Promotion candidates",
    },
    "dead-code-candidates": {
        "mode": "dead_code_candidates",
        "target_label": "retirement_candidate",
        "title": "Dead code candidates",
    },
    "current-cycle-code": {
        "mode": "current_cycle_code",
        "target_label": "code_surface",
        "title": "Current-cycle code surfaces",
    },
    "overengineered-candidates": {
        "mode": "overengineered_candidates",
        "target_label": "complexity_candidate",
        "title": "Overengineered candidates",
    },
    "removable-complexity": {
        "mode": "removable_complexity",
        "target_label": "complexity_candidate",
        "title": "Removable complexity candidates",
    },
    "simplification-blockers": {
        "mode": "simplification_blockers",
        "target_label": "complexity_candidate",
        "title": "Simplification blockers",
    },
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query deterministic Neo4j memory with operator-facing ownership shortcuts.",
    )
    parser.add_argument(
        "profile",
        choices=sorted(QUERY_PROFILES),
        help="Shortcut profile to execute.",
    )
    parser.add_argument(
        "name",
        help=(
            "Exact surface name, duplication cluster name, or family name. "
            "Examples: `chembl.activity`, `BioETLPipelineRunFailed`, "
            "`adapter_layer`, `composite_layer:method_surface:d1c4b44398a1`, `all`."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--http-uri",
        type=str,
        help="Explicit Neo4j HTTP endpoint, e.g. http://localhost:7474.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON rows instead of a human summary.",
    )
    return parser


def _ownership_statement() -> str:
    return (
        "MATCH (target {name: $name}) "
        "UNWIND labels(target) AS target_label "
        "WITH target, target_label "
        "WHERE target_label = $target_label "
        "OPTIONAL MATCH (owner:directory_surface)-[houses:HOUSES]->(target) "
        "OPTIONAL MATCH (zone:repo_zone)-[:CONTAINS*1..8]->(owner) "
        "RETURN target.name AS target_name, "
        "target_label AS target_label, "
        "owner.name AS owner_directory, "
        "zone.name AS repo_zone, "
        "coalesce(houses.provenance, '') AS provenance "
        "ORDER BY "
        "CASE WHEN owner.name IS NULL THEN 1 ELSE 0 END, "
        "size(split(coalesce(owner.name, ''), '/')) ASC, "
        "owner.name ASC"
    )


def _neighbors_statement() -> str:
    return (
        "MATCH (target {name: $name}) "
        "UNWIND labels(target) AS target_label "
        "WITH target, target_label "
        "WHERE target_label = $target_label "
        "CALL { "
        "  WITH target "
        "  MATCH (target)-[rel]->(neighbor) "
        "  WHERE type(rel) IN $relation_types "
        "  RETURN 'outgoing' AS direction, "
        "         type(rel) AS relation_type, "
        "         neighbor.name AS neighbor_name, "
        "         labels(neighbor) AS neighbor_labels "
        "  UNION ALL "
        "  WITH target "
        "  MATCH (neighbor)-[rel]->(target) "
        "  WHERE type(rel) IN $relation_types "
        "  RETURN 'incoming' AS direction, "
        "         type(rel) AS relation_type, "
        "         neighbor.name AS neighbor_name, "
        "         labels(neighbor) AS neighbor_labels "
        "} "
        "RETURN target.name AS target_name, "
        "target_label AS target_label, "
        "direction, "
        "relation_type, "
        "neighbor_name, "
        "neighbor_labels "
        "ORDER BY direction ASC, relation_type ASC, neighbor_name ASC"
    )


def _duplication_cluster_statement() -> str:
    return (
        "MATCH (cluster:duplication_cluster {name: $name}) "
        "OPTIONAL MATCH (cluster)-[:CAN_PROMOTE_TO]->(target) "
        "OPTIONAL MATCH (cluster)-[:CONTAINS]->(direct_member) "
        "WITH cluster, target, collect(DISTINCT direct_member) AS direct_members "
        "CALL { "
        "  WITH cluster, direct_members "
        "  OPTIONAL MATCH (fallback) "
        "  WHERE size(direct_members) = 0 "
        "    AND cluster.surface_kind IN labels(fallback) "
        "    AND coalesce(fallback.family_name, '') = coalesce(cluster.family_name, '') "
        "    AND coalesce(fallback.ast_shape_hash, '') = coalesce(cluster.ast_shape_hash, '') "
        "  RETURN collect(DISTINCT CASE "
        "    WHEN fallback.name IS NULL THEN NULL "
        "    ELSE {name: fallback.name, labels: labels(fallback), package_family: coalesce(fallback.package_family, '')} "
        "  END) AS fallback_members "
        "} "
        "WITH cluster, target, CASE "
        "  WHEN size(direct_members) > 0 THEN [member IN direct_members "
        "    WHERE member.name IS NOT NULL | "
        "    {name: member.name, labels: labels(member), package_family: coalesce(member.package_family, '')}] "
        "  ELSE fallback_members "
        "END AS members "
        "CALL { "
        "  WITH cluster, members "
        "  OPTIONAL MATCH (cluster)-[:COVERED_BY_TEST]->(direct_test) "
        "  WITH members, collect(DISTINCT direct_test.name) AS direct_tests "
        "  CALL { "
        "    WITH members, direct_tests "
        "    UNWIND CASE WHEN size(direct_tests) = 0 THEN members ELSE [] END AS member "
        "    MATCH (test:test_artifact)-[:TESTS_PACKAGE_FAMILY]->(family:package_family {name: member.package_family}) "
        "    RETURN collect(DISTINCT test.name) AS fallback_tests "
        "  } "
        "  RETURN CASE WHEN size(direct_tests) > 0 THEN direct_tests ELSE fallback_tests END AS tests "
        "} "
        "RETURN cluster.name AS cluster_name, "
        "cluster.family_name AS family_name, "
        "cluster.surface_kind AS surface_kind, "
        "cluster.duplicate_count AS duplicate_count, "
        "cluster.promotion_score AS promotion_score, "
        "target.name AS promotion_target, "
        "labels(target) AS promotion_target_labels, "
        "members, "
        "tests"
    )


def _normalization_pipeline_statement() -> str:
    return (
        "MATCH (pipeline:pipeline_surface {name: $name}) "
        "WHERE pipeline.pipeline_kind = 'entity' "
        "OPTIONAL MATCH (pipeline)-[rel:DEPENDS_ON]->(module:module_surface) "
        "WHERE coalesce(rel.provenance, '') IN ['impact_normalization', 'normalization_registry'] "
        "RETURN pipeline.name AS pipeline_name, "
        "pipeline.provider AS provider, "
        "pipeline.entity AS entity, "
        "pipeline.normalization_profile_registered AS normalization_profile_registered, "
        "pipeline.normalization_profile_module_path AS normalization_profile_module_path, "
        "pipeline.profile_field_count AS profile_field_count, "
        "pipeline.fallback_field_count AS fallback_field_count, "
        "pipeline.fallback_business_field_count AS fallback_business_field_count, "
        "pipeline.fallback_technical_passthrough_field_count AS fallback_technical_passthrough_field_count, "
        "collect(DISTINCT module.name) AS normalization_modules"
    )


def _fallback_pipelines_statement() -> str:
    return (
        "MATCH (pipeline:pipeline_surface) "
        "WHERE pipeline.pipeline_kind = 'entity' "
        "AND coalesce(pipeline.fallback_business_field_count, 0) > 0 "
        "AND ($name = 'all' OR pipeline.name = $name) "
        "RETURN pipeline.name AS pipeline_name, "
        "pipeline.provider AS provider, "
        "pipeline.entity AS entity, "
        "pipeline.normalization_profile_registered AS normalization_profile_registered, "
        "pipeline.profile_field_count AS profile_field_count, "
        "pipeline.fallback_field_count AS fallback_field_count, "
        "pipeline.fallback_business_field_count AS fallback_business_field_count, "
        "pipeline.fallback_technical_passthrough_field_count AS fallback_technical_passthrough_field_count "
        "ORDER BY pipeline.fallback_business_field_count DESC, pipeline.fallback_field_count DESC, pipeline.name ASC "
        "LIMIT 25"
    )


def _promotion_candidates_statement() -> str:
    return (
        "MATCH (cluster:duplication_cluster) "
        "WHERE $name = 'all' OR cluster.family_name = $name "
        "OPTIONAL MATCH (cluster)-[:CAN_PROMOTE_TO]->(target) "
        "OPTIONAL MATCH (cluster)-[:CONTAINS]->(direct_member) "
        "WITH cluster, target, collect(DISTINCT direct_member) AS direct_members "
        "CALL { "
        "  WITH cluster, direct_members "
        "  OPTIONAL MATCH (fallback) "
        "  WHERE size(direct_members) = 0 "
        "    AND cluster.surface_kind IN labels(fallback) "
        "    AND coalesce(fallback.family_name, '') = coalesce(cluster.family_name, '') "
        "    AND coalesce(fallback.ast_shape_hash, '') = coalesce(cluster.ast_shape_hash, '') "
        "  RETURN collect(DISTINCT CASE "
        "    WHEN fallback.name IS NULL THEN NULL "
        "    ELSE {name: fallback.name, labels: labels(fallback), package_family: coalesce(fallback.package_family, '')} "
        "  END) AS fallback_members "
        "} "
        "WITH cluster, target, CASE "
        "  WHEN size(direct_members) > 0 THEN [member IN direct_members "
        "    WHERE member.name IS NOT NULL | "
        "    {name: member.name, labels: labels(member), package_family: coalesce(member.package_family, '')}] "
        "  ELSE fallback_members "
        "END AS members "
        "CALL { "
        "  WITH cluster, members "
        "  OPTIONAL MATCH (cluster)-[:COVERED_BY_TEST]->(direct_test) "
        "  WITH members, collect(DISTINCT direct_test.name) AS direct_tests "
        "  CALL { "
        "    WITH members, direct_tests "
        "    UNWIND CASE WHEN size(direct_tests) = 0 THEN members ELSE [] END AS member "
        "    MATCH (test:test_artifact)-[:TESTS_PACKAGE_FAMILY]->(family:package_family {name: member.package_family}) "
        "    RETURN collect(DISTINCT test.name) AS fallback_tests "
        "  } "
        "  RETURN CASE WHEN size(direct_tests) > 0 THEN direct_tests ELSE fallback_tests END AS tests "
        "} "
        "RETURN cluster.name AS cluster_name, "
        "cluster.family_name AS family_name, "
        "cluster.surface_kind AS surface_kind, "
        "cluster.duplicate_count AS duplicate_count, "
        "cluster.promotion_score AS promotion_score, "
        "target.name AS promotion_target, "
        "labels(target) AS promotion_target_labels, "
        "size(members) AS member_count, "
        "size(tests) AS test_count "
        "ORDER BY cluster.promotion_score DESC, cluster.duplicate_count DESC, cluster.name ASC"
    )


def _dead_code_candidates_statement() -> str:
    return (
        "MATCH (candidate:retirement_candidate) "
        "WHERE $name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name "
        "OPTIONAL MATCH (candidate)-[:CANDIDATE_FOR_REMOVAL]->(target) "
        "RETURN candidate.name AS candidate_name, "
        "candidate.family_name AS family_name, "
        "candidate.target_label AS target_label, "
        "candidate.target_name AS target_name, "
        "candidate.deletion_score AS deletion_score, "
        "candidate.deletion_confidence AS deletion_confidence, "
        "candidate.recent_age_days AS recent_age_days, "
        "candidate.only_test_referenced AS only_test_referenced, "
        "candidate.deprecation_markers AS deprecation_markers, "
        "candidate.runtime_anchor_count AS runtime_anchor_count, "
        "candidate.config_anchor_count AS config_anchor_count, "
        "candidate.doc_anchor_count AS doc_anchor_count, "
        "candidate.test_anchor_count AS test_anchor_count, "
        "target.name AS removal_target, "
        "labels(target) AS removal_target_labels, "
        "candidate.blocked_by_current_cycle_target_name AS blocked_by_cycle "
        "ORDER BY candidate.deletion_score DESC, candidate.target_name ASC"
    )


def _current_cycle_code_statement() -> str:
    return (
        "MATCH (target) "
        "WHERE any(label IN labels(target) WHERE label IN ['module_surface','class_surface','function_surface','method_surface']) "
        "AND coalesce(target.current_cycle_status, '') <> '' "
        "AND ($name = 'all' OR target.family_name = $name OR target.name = $name) "
        "RETURN target.name AS cycle_name, "
        "target.family_name AS family_name, "
        "head(labels(target)) AS target_label, "
        "target.name AS target_name, "
        "target.current_cycle_status AS cycle_status, "
        "target.current_cycle_score AS cycle_score, "
        "target.current_cycle_recent_age_days AS recent_age_days, "
        "target.current_cycle_wip_markers AS wip_markers, "
        "target.current_cycle_runtime_anchor_count AS runtime_anchor_count, "
        "target.current_cycle_config_anchor_count AS config_anchor_count, "
        "target.current_cycle_doc_anchor_count AS doc_anchor_count, "
        "target.current_cycle_test_anchor_count AS test_anchor_count, "
        "labels(target) AS target_labels "
        "ORDER BY target.current_cycle_score DESC, target.name ASC"
    )


def _overengineered_candidates_statement() -> str:
    return (
        "MATCH (candidate:complexity_candidate) "
        "WHERE $name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name "
        "OPTIONAL MATCH (candidate)-[:CANDIDATE_FOR_SIMPLIFICATION]->(target) "
        "RETURN candidate.name AS candidate_name, "
        "candidate.family_name AS family_name, "
        "candidate.target_label AS target_label, "
        "candidate.target_name AS target_name, "
        "candidate.classification AS classification, "
        "candidate.complexity_score AS complexity_score, "
        "candidate.simplification_score AS simplification_score, "
        "candidate.removable_score AS removable_score, "
        "candidate.branch_count AS branch_count, "
        "candidate.nesting_depth AS nesting_depth, "
        "candidate.helper_call_count AS helper_call_count, "
        "candidate.indirection_markers AS indirection_markers, "
        "candidate.stateful_markers AS stateful_markers, "
        "candidate.runtime_anchor_count AS runtime_anchor_count, "
        "candidate.config_anchor_count AS config_anchor_count, "
        "candidate.doc_anchor_count AS doc_anchor_count, "
        "candidate.test_anchor_count AS test_anchor_count, "
        "candidate.blocked_by_current_cycle_target_name AS blocked_by_cycle, "
        "labels(target) AS target_labels "
        "ORDER BY candidate.simplification_score DESC, candidate.removable_score DESC, candidate.target_name ASC "
        "LIMIT 50"
    )


def _removable_complexity_statement() -> str:
    return (
        "MATCH (candidate:complexity_candidate) "
        "WHERE ($name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name) "
        "AND candidate.classification = 'removable_complexity' "
        "OPTIONAL MATCH (candidate)-[:CANDIDATE_FOR_REMOVAL]->(target) "
        "RETURN candidate.name AS candidate_name, "
        "candidate.family_name AS family_name, "
        "candidate.target_label AS target_label, "
        "candidate.target_name AS target_name, "
        "candidate.removable_score AS removable_score, "
        "candidate.removal_confidence AS removal_confidence, "
        "candidate.deprecation_markers AS deprecation_markers, "
        "candidate.runtime_anchor_count AS runtime_anchor_count, "
        "candidate.config_anchor_count AS config_anchor_count, "
        "candidate.doc_anchor_count AS doc_anchor_count, "
        "candidate.test_anchor_count AS test_anchor_count, "
        "labels(target) AS target_labels "
        "ORDER BY candidate.removable_score DESC, candidate.target_name ASC "
        "LIMIT 50"
    )


def _simplification_blockers_statement() -> str:
    return (
        "MATCH (candidate:complexity_candidate) "
        "WHERE $name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name "
        "OPTIONAL MATCH (candidate)-[rel:JUSTIFIED_BY_RUNTIME|BLOCKED_BY_VARIANCE]->(blocker) "
        "RETURN candidate.name AS candidate_name, "
        "candidate.family_name AS family_name, "
        "candidate.target_label AS target_label, "
        "candidate.target_name AS target_name, "
        "candidate.classification AS classification, "
        "candidate.runtime_anchor_count AS runtime_anchor_count, "
        "candidate.config_anchor_count AS config_anchor_count, "
        "candidate.doc_anchor_count AS doc_anchor_count, "
        "candidate.test_anchor_count AS test_anchor_count, "
        "[candidate.blocked_by_current_cycle_target_name] AS cycle_blockers, "
        "collect(DISTINCT CASE "
        "  WHEN blocker.name IS NULL THEN NULL "
        "  ELSE {name: blocker.name, labels: labels(blocker), relation: type(rel)} "
        "END) AS blockers "
        "ORDER BY candidate.target_name ASC "
        "LIMIT 50"
    )


def _docs_drift_statement() -> str:
    return (
        "MATCH (doc)-[rel:DESCRIBES]->(target) "
        "WHERE any(label IN labels(doc) WHERE label IN ['doc_source_surface', 'doc_artifact', 'policy_surface']) "
        "AND ($name = 'all' OR doc.name = $name OR target.name = $name OR coalesce(doc.source_path, '') = $name) "
        "RETURN doc.name AS doc_name, "
        "labels(doc) AS doc_labels, "
        "coalesce(doc.source_path, '') AS doc_source_path, "
        "target.name AS target_name, "
        "labels(target) AS target_labels, "
        "coalesce(target.source_path, '') AS target_source_path, "
        "coalesce(rel.doc_reference, '') AS doc_reference, "
        "coalesce(rel.evidence_kind, '') AS evidence_kind, "
        "coalesce(rel.confidence, '') AS confidence, "
        "coalesce(rel.section_title, '') AS section_title, "
        "coalesce(rel.section_anchor, '') AS section_anchor, "
        "coalesce(rel.line_number, 0) AS line_number "
        "ORDER BY doc.name ASC, target.name ASC"
    )


def _workflow_gates_statement() -> str:
    return (
        "MATCH (workflow:workflow_surface) "
        "WHERE $name = 'all' OR workflow.name = $name "
        "MATCH (workflow)-[:CONTAINS]->(job:workflow_job_surface) "
        "OPTIONAL MATCH (job)-[:EXECUTES_GATE]->(gate:quality_gate) "
        "OPTIONAL MATCH (job)-[:RUNS_VIA]->(target) "
        "RETURN workflow.name AS workflow_name, "
        "job.name AS job_name, "
        "collect(DISTINCT gate.name) AS gates, "
        "collect(DISTINCT CASE "
        "  WHEN target.name IS NULL THEN NULL "
        "  ELSE {name: target.name, labels: labels(target)} "
        "END) AS run_targets "
        "ORDER BY workflow.name ASC, job.name ASC"
    )


def _workflow_artifacts_statement() -> str:
    return (
        "MATCH (workflow:workflow_surface) "
        "WHERE $name = 'all' OR workflow.name = $name "
        "MATCH (workflow)-[:CONTAINS]->(job:workflow_job_surface) "
        "OPTIONAL MATCH (job)-[:USES_ACTION]->(action:workflow_action_surface) "
        "OPTIONAL MATCH (job)-[artifact_rel:PUBLISHES_ARTIFACT|DEPENDS_ON]->(artifact:workflow_artifact_surface) "
        "OPTIONAL MATCH (job)-[:REQUIRES_SECRET]->(secret:workflow_secret_surface) "
        "RETURN workflow.name AS workflow_name, "
        "job.name AS job_name, "
        "collect(DISTINCT action.name) AS actions, "
        "collect(DISTINCT CASE "
        "  WHEN artifact.name IS NULL THEN NULL "
        "  ELSE {name: artifact.name, relation: type(artifact_rel)} "
        "END) AS artifacts, "
        "collect(DISTINCT secret.name) AS secrets "
        "ORDER BY workflow.name ASC, job.name ASC"
    )


def _workflow_execution_statement() -> str:
    return (
        "MATCH (workflow:workflow_surface) "
        "WHERE $name = 'all' OR workflow.name = $name "
        "OPTIONAL MATCH (workflow)-[:CONTAINS]->(job:workflow_job_surface) "
        "OPTIONAL MATCH (workflow)-[:CALLS_WORKFLOW]->(workflow_call:workflow_call_surface) "
        "OPTIONAL MATCH (job)-[:CALLS_WORKFLOW]->(job_call:workflow_call_surface) "
        "WITH workflow, job, collect(DISTINCT workflow_call) + collect(DISTINCT job_call) AS call_nodes "
        "UNWIND CASE WHEN size(call_nodes) = 0 THEN [NULL] ELSE call_nodes END AS call "
        "OPTIONAL MATCH (call)-[:DEPENDS_ON]->(target_workflow:workflow_surface) "
        "OPTIONAL MATCH (job)-[:HAS_MATRIX_VARIANT]->(variant:workflow_matrix_variant_surface) "
        "OPTIONAL MATCH (workflow)-[:EMITS_OUTPUT]->(workflow_output:workflow_output_surface) "
        "OPTIONAL MATCH (job)-[:EMITS_OUTPUT]->(job_output:workflow_output_surface) "
        "RETURN workflow.name AS workflow_name, "
        "coalesce(workflow.concurrency_group, '') AS workflow_concurrency_group, "
        "job.name AS job_name, "
        "coalesce(job.concurrency_group, '') AS job_concurrency_group, "
        "collect(DISTINCT CASE "
        "  WHEN call.name IS NULL THEN NULL "
        "  ELSE {name: call.name, target_workflow: coalesce(target_workflow.name, ''), reusable_kind: coalesce(call.reusable_kind, '')} "
        "END) AS reusable_calls, "
        "collect(DISTINCT CASE "
        "  WHEN variant.name IS NULL THEN NULL "
        "  ELSE {name: variant.name, variant_axes: coalesce(variant.variant_axes, {})} "
        "END) AS matrix_variants, "
        "collect(DISTINCT CASE "
        "  WHEN workflow_output.name IS NULL THEN NULL "
        "  ELSE {name: workflow_output.name, scope: coalesce(workflow_output.output_scope, ''), expression: coalesce(workflow_output.output_expression, '')} "
        "END) AS workflow_outputs, "
        "collect(DISTINCT CASE "
        "  WHEN job_output.name IS NULL THEN NULL "
        "  ELSE {name: job_output.name, scope: coalesce(job_output.output_scope, ''), expression: coalesce(job_output.output_expression, '')} "
        "END) AS job_outputs "
        "ORDER BY workflow.name ASC, job.name ASC"
    )


def _storage_lineage_statement() -> str:
    return (
        "MATCH (storage:storage_surface) "
        "WHERE $name = 'all' OR storage.name = $name "
        "OPTIONAL MATCH (producer)-[:WRITES_TO]->(storage) "
        "OPTIONAL MATCH (storage)-[:PROMOTES_TO]->(downstream:storage_surface) "
        "OPTIONAL MATCH (upstream:storage_surface)-[:PROMOTES_TO]->(storage) "
        "OPTIONAL MATCH (storage)-[:DEFINED_BY]->(config) "
        "RETURN storage.name AS storage_name, "
        "storage.layer AS layer, "
        "storage.storage_kind AS storage_kind, "
        "storage.storage_roles AS storage_roles, "
        "storage.format AS storage_format, "
        "storage.config_version AS config_version, "
        "storage.quality_version AS quality_version, "
        "storage.schema_present AS schema_present, "
        "storage.partition_by AS partition_by, "
        "storage.sort_by AS sort_by, "
        "storage.versioning_mode AS versioning_mode, "
        "storage.version_column AS version_column, "
        "collect(DISTINCT CASE "
        "  WHEN producer.name IS NULL THEN NULL "
        "  ELSE {name: producer.name, labels: labels(producer)} "
        "END) AS producers, "
        "collect(DISTINCT upstream.name) AS upstream_surfaces, "
        "collect(DISTINCT downstream.name) AS downstream_surfaces, "
        "collect(DISTINCT config.name) AS defining_configs "
        "ORDER BY storage.name ASC"
    )


def _field_lineage_statement() -> str:
    return (
        "MATCH (field:schema_field_surface) "
        "WHERE $name = 'all' OR field.name = $name OR field.field_name = $name OR field.storage_ref = $name OR field.contract_ref = $name "
        "OPTIONAL MATCH (storage:storage_surface)-[:HAS_SCHEMA_FIELD]->(field) "
        "OPTIONAL MATCH (contract:contract_surface)-[:HAS_SCHEMA_FIELD]->(field) "
        "OPTIONAL MATCH (field)-[:DERIVES_FIELD_FROM]->(upstream:schema_field_surface) "
        "OPTIONAL MATCH (field)-[:PROMOTES_FIELD_TO]->(downstream:schema_field_surface) "
        "RETURN field.name AS field_surface_name, "
        "field.field_name AS field_name, "
        "field.field_group AS field_group, "
        "field.storage_ref AS storage_ref, "
        "field.contract_ref AS contract_ref, "
        "field.required_in_quality AS required_in_quality, "
        "field.validation_types AS validation_types, "
        "field.drift_classification AS drift_classification, "
        "collect(DISTINCT storage.name) AS storage_surfaces, "
        "collect(DISTINCT contract.name) AS contracts, "
        "collect(DISTINCT upstream.name) AS upstream_fields, "
        "collect(DISTINCT downstream.name) AS downstream_fields "
        "ORDER BY field.storage_ref ASC, field.field_name ASC"
    )


def _schema_drift_statement() -> str:
    return (
        "MATCH (field:schema_field_surface) "
        "WHERE coalesce(field.drift_classification, '') <> '' "
        "AND ($name = 'all' OR field.storage_ref = $name OR field.contract_ref = $name OR field.field_name = $name) "
        "OPTIONAL MATCH (storage:storage_surface)-[:HAS_SCHEMA_FIELD]->(field) "
        "RETURN field.name AS field_surface_name, "
        "field.field_name AS field_name, "
        "field.field_group AS field_group, "
        "field.storage_ref AS storage_ref, "
        "field.contract_ref AS contract_ref, "
        "field.drift_classification AS drift_classification, "
        "field.required_in_quality AS required_in_quality, "
        "field.validation_types AS validation_types, "
        "collect(DISTINCT storage.name) AS storage_surfaces "
        "ORDER BY field.storage_ref ASC, field.field_name ASC"
    )


def _run_artifacts_statement() -> str:
    return (
        "MATCH (run:run_instance_surface) "
        "WHERE $name = 'all' OR run.name = $name OR run.manifest_id = $name OR run.run_id = $name "
        "OPTIONAL MATCH (run)-[:REFERENCES_ARTIFACT]->(artifact:control_plane_artifact_surface) "
        "OPTIONAL MATCH (run)-[:DEPENDS_ON]->(dependency) "
        "OPTIONAL MATCH (run)-[:DESCRIBED_IN]->(support) "
        "RETURN run.name AS run_instance_name, "
        "run.manifest_id AS manifest_id, "
        "run.run_id AS run_id, "
        "run.lifecycle_status AS lifecycle_status, "
        "run.contract_ref AS contract_ref, "
        "run.contract_version AS contract_version, "
        "run.effective_config_artifact_id AS effective_config_artifact_id, "
        "run.lineage_fragment_id AS lineage_fragment_id, "
        "collect(DISTINCT CASE "
        "  WHEN artifact.name IS NULL THEN NULL "
        "  ELSE {name: artifact.name, labels: labels(artifact), artifact_family: artifact.artifact_family} "
        "END) AS artifacts, "
        "collect(DISTINCT CASE "
        "  WHEN dependency.name IS NULL THEN NULL "
        "  ELSE {name: dependency.name, labels: labels(dependency)} "
        "END) AS dependencies, "
        "collect(DISTINCT CASE "
        "  WHEN support.name IS NULL THEN NULL "
        "  ELSE {name: support.name, labels: labels(support)} "
        "END) AS support_links "
        "ORDER BY run.name ASC"
    )


def _runtime_state_statement(*, locks_only: bool = False) -> str:
    filter_clause = (
        "AND state.state_kind = 'lock_state' "
        if locks_only
        else ""
    )
    return (
        "MATCH (state:runtime_state_surface) "
        "WHERE ($name = 'all' OR state.name = $name OR state.state_kind = $name OR state.lock_key = $name OR state.manifest_id = $name) "
        f"{filter_clause}"
        "OPTIONAL MATCH (owner)-[:HAS_RUNTIME_STATE]->(state) "
        "OPTIONAL MATCH (state)-[:DEPENDS_ON]->(dependency) "
        "OPTIONAL MATCH (state)-[:REFERENCES_ARTIFACT]->(artifact:control_plane_artifact_surface) "
        "RETURN state.name AS runtime_state_name, "
        "state.state_kind AS state_kind, "
        "state.state_status AS state_status, "
        "state.manifest_id AS manifest_id, "
        "state.retry_count AS retry_count, "
        "state.retry_strategy AS retry_strategy, "
        "state.lock_key AS lock_key, "
        "state.lock_scope AS lock_scope, "
        "state.owner_hint AS owner_hint, "
        "collect(DISTINCT CASE "
        "  WHEN owner.name IS NULL THEN NULL "
        "  ELSE {name: owner.name, labels: labels(owner)} "
        "END) AS owners, "
        "collect(DISTINCT CASE "
        "  WHEN dependency.name IS NULL THEN NULL "
        "  ELSE {name: dependency.name, labels: labels(dependency)} "
        "END) AS dependencies, "
        "collect(DISTINCT CASE "
        "  WHEN artifact.name IS NULL THEN NULL "
        "  ELSE {name: artifact.name, labels: labels(artifact), artifact_family: artifact.artifact_family} "
        "END) AS artifacts "
        "ORDER BY state.state_kind ASC, state.name ASC"
    )


def _claim_trace_statement() -> str:
    return (
        "MATCH (doc)-[:ASSERTS]->(claim:doc_claim_surface) "
        "WHERE any(label IN labels(doc) WHERE label IN ['doc_source_surface', 'doc_artifact', 'policy_surface']) "
        "AND ($name = 'all' OR claim.name = $name OR doc.name = $name OR coalesce(doc.source_path, '') = $name) "
        "OPTIONAL MATCH (claim)-[:ASSERTS_ABOUT]->(target) "
        "RETURN doc.name AS doc_name, "
        "coalesce(doc.source_path, '') AS doc_source_path, "
        "claim.name AS claim_name, "
        "coalesce(claim.claim_text, '') AS claim_text, "
        "coalesce(claim.modality, '') AS modality, "
        "coalesce(claim.section_title, '') AS section_title, "
        "coalesce(claim.section_anchor, '') AS section_anchor, "
        "coalesce(claim.line_number, 0) AS line_number, "
        "collect(DISTINCT CASE "
        "  WHEN target.name IS NULL THEN NULL "
        "  ELSE {name: target.name, labels: labels(target)} "
        "END) AS targets "
        "ORDER BY doc_name ASC, line_number ASC"
    )


def _cli_semantics_statement() -> str:
    return (
        "MATCH (command:cli_command_surface) "
        "WHERE $name = 'all' OR command.name = $name "
        "OPTIONAL MATCH (command)-[:ACCEPTS_OPTION]->(option:cli_option_surface) "
        "OPTIONAL MATCH (command)-[:SIDE_EFFECTS_ON]->(target) "
        "OPTIONAL MATCH (command)-[:EXECUTES_GATE]->(gate:quality_gate) "
        "RETURN command.name AS command_name, "
        "coalesce(command.side_effect_class, '') AS side_effect_class, "
        "collect(DISTINCT option.option_name) AS options, "
        "collect(DISTINCT CASE "
        "  WHEN target.name IS NULL THEN NULL "
        "  ELSE {name: target.name, labels: labels(target)} "
        "END) AS side_effect_targets, "
        "collect(DISTINCT gate.name) AS gates "
        "ORDER BY command.name ASC"
    )


def _run_query(
    root: Path,
    profile: str,
    name: str,
    http_uri: str | None,
) -> list[dict[str, JsonValue]]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    profile_config = QUERY_PROFILES[profile]
    params: dict[str, JsonValue] = {
        "name": name,
        "target_label": profile_config["target_label"],
    }
    if profile_config["mode"] == "neighbors":
        params["relation_types"] = list(profile_config.get("relation_types", DEFAULT_NEIGHBOR_RELATION_TYPES))
        statement = _neighbors_statement()
    elif profile_config["mode"] == "docs_drift":
        statement = _docs_drift_statement()
    elif profile_config["mode"] == "workflow_gates":
        statement = _workflow_gates_statement()
    elif profile_config["mode"] == "workflow_artifacts":
        statement = _workflow_artifacts_statement()
    elif profile_config["mode"] == "workflow_execution":
        statement = _workflow_execution_statement()
    elif profile_config["mode"] == "storage_lineage":
        statement = _storage_lineage_statement()
    elif profile_config["mode"] == "field_lineage":
        statement = _field_lineage_statement()
    elif profile_config["mode"] == "schema_drift":
        statement = _schema_drift_statement()
    elif profile_config["mode"] == "run_artifacts":
        statement = _run_artifacts_statement()
    elif profile_config["mode"] == "runtime_state":
        statement = _runtime_state_statement()
    elif profile_config["mode"] == "runtime_locks":
        statement = _runtime_state_statement(locks_only=True)
    elif profile_config["mode"] == "claim_trace":
        statement = _claim_trace_statement()
    elif profile_config["mode"] == "cli_semantics":
        statement = _cli_semantics_statement()
    elif profile_config["mode"] == "normalization_pipeline":
        statement = _normalization_pipeline_statement()
    elif profile_config["mode"] == "fallback_pipelines":
        statement = _fallback_pipelines_statement()
    elif profile_config["mode"] == "duplication_cluster":
        statement = _duplication_cluster_statement()
    elif profile_config["mode"] == "promotion_candidates":
        statement = _promotion_candidates_statement()
    elif profile_config["mode"] == "dead_code_candidates":
        statement = _dead_code_candidates_statement()
    elif profile_config["mode"] == "current_cycle_code":
        statement = _current_cycle_code_statement()
    elif profile_config["mode"] == "overengineered_candidates":
        statement = _overengineered_candidates_statement()
    elif profile_config["mode"] == "removable_complexity":
        statement = _removable_complexity_statement()
    elif profile_config["mode"] == "simplification_blockers":
        statement = _simplification_blockers_statement()
    else:
        statement = _ownership_statement()
    return client.query(
        statement,
        params,
    )


def _format_rows(profile: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    profile_config = QUERY_PROFILES[profile]
    title = profile_config["title"]
    if not rows:
        empty_suffix = {
            "owner": "no ownership path found",
            "neighbors": "no semantic neighbors found",
            "docs_drift": "no docs-to-code drift edges found",
            "workflow_gates": "no workflow gate coverage found",
            "workflow_artifacts": "no workflow action or artifact coverage found",
            "workflow_execution": "no reusable workflow, matrix, or output coverage found",
            "storage_lineage": "no storage lineage found",
            "field_lineage": "no field lineage found",
            "schema_drift": "no schema drift evidence found",
            "run_artifacts": "no run instance artifact chain found",
            "runtime_state": "no runtime state found",
            "runtime_locks": "no runtime lock state found",
            "claim_trace": "no claim-level traceability found",
            "cli_semantics": "no CLI semantic coverage found",
            "duplication_cluster": "no duplication cluster found",
            "normalization_pipeline": "no pipeline normalization evidence found",
            "fallback_pipelines": "no fallback-heavy pipelines found",
            "promotion_candidates": "no promotion candidates found",
            "dead_code_candidates": "no dead code candidates found",
            "current_cycle_code": "no current-cycle code surfaces found",
            "overengineered_candidates": "no overengineered candidates found",
            "removable_complexity": "no removable complexity candidates found",
            "simplification_blockers": "no simplification blockers found",
        }[profile_config["mode"]]
        return f"{title}: {empty_suffix} for `{name}`."

    if profile_config["mode"] == "neighbors":
        lines = [f"{title}: `{name}`"]
        seen: set[tuple[str, str, str, str]] = set()
        for row in rows:
            relation_type = str(row.get("relation_type") or "")
            neighbor_name = str(row.get("neighbor_name") or "")
            direction = str(row.get("direction") or "")
            if not relation_type or not neighbor_name:
                continue
            neighbor_labels = row.get("neighbor_labels")
            if isinstance(neighbor_labels, list):
                label_str = ",".join(str(label) for label in neighbor_labels)
            else:
                label_str = ""
            key = (direction, relation_type, neighbor_name, label_str)
            if key in seen:
                continue
            seen.add(key)
            label_suffix = f" | labels={label_str}" if label_str else ""
            lines.append(
                f"- direction={direction} | relation={relation_type} | neighbor={neighbor_name}{label_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no semantic edges found")
        return "\n".join(lines)

    if profile_config["mode"] == "docs_drift":
        lines = [f"{title}: `{name}`"]
        seen: set[tuple[str, str]] = set()
        for row in rows:
            doc_name = str(row.get("doc_name") or "")
            target_name = str(row.get("target_name") or "")
            if not doc_name or not target_name:
                continue
            key = (doc_name, target_name)
            if key in seen:
                continue
            seen.add(key)
            doc_labels = row.get("doc_labels")
            target_labels = row.get("target_labels")
            doc_label_str = ",".join(str(label) for label in doc_labels) if isinstance(doc_labels, list) else ""
            target_label_str = ",".join(str(label) for label in target_labels) if isinstance(target_labels, list) else ""
            doc_path = str(row.get("doc_source_path") or "")
            target_path = str(row.get("target_source_path") or "")
            doc_reference = str(row.get("doc_reference") or "")
            evidence_kind = str(row.get("evidence_kind") or "")
            confidence = str(row.get("confidence") or "")
            section_title = str(row.get("section_title") or "")
            section_anchor = str(row.get("section_anchor") or "")
            line_number = int(row.get("line_number") or 0)
            path_suffix = f" | doc_path={doc_path}" if doc_path else ""
            target_path_suffix = f" | target_path={target_path}" if target_path else ""
            evidence_suffix = f" | ref={doc_reference}" if doc_reference else ""
            evidence_suffix += f" | evidence_kind={evidence_kind}" if evidence_kind else ""
            evidence_suffix += f" | confidence={confidence}" if confidence else ""
            evidence_suffix += f" | section={section_title}" if section_title else ""
            evidence_suffix += f" | anchor={section_anchor}" if section_anchor else ""
            evidence_suffix += f" | line={line_number}" if line_number else ""
            lines.append(
                f"- doc={doc_name} | doc_labels={doc_label_str} | target={target_name} | "
                f"target_labels={target_label_str}{path_suffix}{target_path_suffix}{evidence_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no docs-to-code drift edges found")
        return "\n".join(lines)

    if profile_config["mode"] == "workflow_gates":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            workflow_name = str(row.get("workflow_name") or "")
            job_name = str(row.get("job_name") or "")
            if not workflow_name or not job_name:
                continue
            lines.append(f"- workflow={workflow_name} | job={job_name}")
            gates = row.get("gates")
            if isinstance(gates, list):
                for gate_name in sorted({str(item) for item in gates if item}):
                    lines.append(f"  gate={gate_name}")
            run_targets = row.get("run_targets")
            if isinstance(run_targets, list):
                normalized_targets: set[str] = set()
                for target in run_targets:
                    if not isinstance(target, dict):
                        continue
                    target_name = str(target.get("name") or "")
                    if not target_name:
                        continue
                    labels = target.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    label_suffix = f" | labels={label_str}" if label_str else ""
                    normalized_targets.add(f"  runs_via={target_name}{label_suffix}")
                lines.extend(sorted(normalized_targets))
        if len(lines) == 1:
            lines.append("- no workflow gate coverage found")
        return "\n".join(lines)

    if profile_config["mode"] == "workflow_artifacts":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            workflow_name = str(row.get("workflow_name") or "")
            job_name = str(row.get("job_name") or "")
            if not workflow_name or not job_name:
                continue
            lines.append(f"- workflow={workflow_name} | job={job_name}")
            actions = row.get("actions")
            if isinstance(actions, list):
                for action_name in sorted({str(item) for item in actions if item}):
                    lines.append(f"  action={action_name}")
            artifacts = row.get("artifacts")
            if isinstance(artifacts, list):
                normalized_artifacts: set[str] = set()
                for artifact in artifacts:
                    if not isinstance(artifact, dict):
                        continue
                    artifact_name = str(artifact.get("name") or "")
                    if not artifact_name:
                        continue
                    relation_name = str(artifact.get("relation") or "")
                    relation_suffix = f" | relation={relation_name}" if relation_name else ""
                    normalized_artifacts.add(f"  artifact={artifact_name}{relation_suffix}")
                lines.extend(sorted(normalized_artifacts))
            secrets = row.get("secrets")
            if isinstance(secrets, list):
                for secret_name in sorted({str(item) for item in secrets if item}):
                    lines.append(f"  secret={secret_name}")
        if len(lines) == 1:
            lines.append("- no workflow action or artifact coverage found")
        return "\n".join(lines)

    if profile_config["mode"] == "workflow_execution":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            workflow_name = str(row.get("workflow_name") or "")
            if not workflow_name:
                continue
            job_name = str(row.get("job_name") or "")
            workflow_concurrency = str(row.get("workflow_concurrency_group") or "")
            job_concurrency = str(row.get("job_concurrency_group") or "")
            lines.append(
                f"- workflow={workflow_name}"
                + (f" | job={job_name}" if job_name else "")
                + (f" | workflow_concurrency={workflow_concurrency}" if workflow_concurrency else "")
                + (f" | job_concurrency={job_concurrency}" if job_concurrency else "")
            )
            for field_name, prefix in (
                ("reusable_calls", "call"),
                ("matrix_variants", "matrix"),
                ("workflow_outputs", "workflow_output"),
                ("job_outputs", "job_output"),
            ):
                values = row.get(field_name)
                if not isinstance(values, list):
                    continue
                normalized: set[str] = set()
                for value in values:
                    if not isinstance(value, dict):
                        continue
                    item_name = str(value.get("name") or "")
                    if not item_name:
                        continue
                    suffix_parts: list[str] = []
                    if field_name == "reusable_calls":
                        target_workflow = str(value.get("target_workflow") or "")
                        reusable_kind = str(value.get("reusable_kind") or "")
                        if target_workflow:
                            suffix_parts.append(f"target_workflow={target_workflow}")
                        if reusable_kind:
                            suffix_parts.append(f"kind={reusable_kind}")
                    elif field_name == "matrix_variants":
                        variant_axes = value.get("variant_axes")
                        if isinstance(variant_axes, dict):
                            suffix_parts.append(
                                "axes="
                                + ",".join(
                                    f"{key}={variant_axes[key]!s}" for key in sorted(variant_axes)
                                )
                            )
                    else:
                        output_scope = str(value.get("scope") or "")
                        expression = str(value.get("expression") or "")
                        if output_scope:
                            suffix_parts.append(f"scope={output_scope}")
                        if expression:
                            suffix_parts.append(f"expression={expression}")
                    suffix = f" | {' | '.join(suffix_parts)}" if suffix_parts else ""
                    normalized.add(f"  {prefix}={item_name}{suffix}")
                lines.extend(sorted(normalized))
        if len(lines) == 1:
            lines.append("- no reusable workflow, matrix, or output coverage found")
        return "\n".join(lines)

    if profile_config["mode"] == "storage_lineage":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            storage_name = str(row.get("storage_name") or "")
            if not storage_name:
                continue
            storage_roles = row.get("storage_roles")
            roles_str = ",".join(str(item) for item in storage_roles) if isinstance(storage_roles, list) else ""
            partition_by = row.get("partition_by")
            partition_str = ",".join(str(item) for item in partition_by) if isinstance(partition_by, list) else ""
            sort_by = row.get("sort_by")
            sort_str = ",".join(str(item) for item in sort_by) if isinstance(sort_by, list) else ""
            lines.append(
                f"- storage={storage_name} | layer={row.get('layer') or ''!s} | storage_kind={row.get('storage_kind') or ''!s} "
                f"| format={row.get('storage_format') or ''!s} | roles={roles_str or ''} | schema_present={row.get('schema_present') or False!s}"
            )
            versioning_mode = str(row.get("versioning_mode") or "")
            version_column = str(row.get("version_column") or "")
            config_version = str(row.get("config_version") or "")
            quality_version = str(row.get("quality_version") or "")
            detail_parts = [
                f"config_version={config_version}" if config_version else "",
                f"quality_version={quality_version}" if quality_version else "",
                f"partition_by={partition_str}" if partition_str else "",
                f"sort_by={sort_str}" if sort_str else "",
                f"versioning_mode={versioning_mode}" if versioning_mode else "",
                f"version_column={version_column}" if version_column else "",
            ]
            detail_line = " | ".join(part for part in detail_parts if part)
            if detail_line:
                lines.append(f"  {detail_line}")
            producers = row.get("producers")
            if isinstance(producers, list):
                normalized_producers: set[str] = set()
                for producer in producers:
                    if not isinstance(producer, dict):
                        continue
                    producer_name = str(producer.get("name") or "")
                    if not producer_name:
                        continue
                    labels = producer.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    label_suffix = f" | labels={label_str}" if label_str else ""
                    normalized_producers.add(f"  producer={producer_name}{label_suffix}")
                lines.extend(sorted(normalized_producers))
            for field_name, prefix in (
                ("upstream_surfaces", "upstream"),
                ("downstream_surfaces", "downstream"),
                ("defining_configs", "defined_by"),
            ):
                values = row.get(field_name)
                if isinstance(values, list):
                    for value in sorted({str(item) for item in values if item}):
                        lines.append(f"  {prefix}={value}")
        if len(lines) == 1:
            lines.append("- no storage lineage found")
        return "\n".join(lines)

    if profile_config["mode"] == "field_lineage":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            field_name = str(row.get("field_name") or "")
            storage_ref = str(row.get("storage_ref") or "")
            if not field_name or not storage_ref:
                continue
            lines.append(
                f"- storage={storage_ref} | field={field_name} | group={row.get('field_group') or ''!s} "
                f"| drift={row.get('drift_classification') or ''!s} | required={row.get('required_in_quality')!s}"
            )
            validation_types = row.get("validation_types")
            if isinstance(validation_types, list) and validation_types:
                lines.append(f"  validations={','.join(str(item) for item in validation_types if item)}")
            for field_name_key, prefix in (
                ("upstream_fields", "upstream"),
                ("downstream_fields", "downstream"),
                ("contracts", "contract"),
            ):
                values = row.get(field_name_key)
                if isinstance(values, list):
                    for value in sorted({str(item) for item in values if item}):
                        lines.append(f"  {prefix}={value}")
        if len(lines) == 1:
            lines.append("- no field lineage found")
        return "\n".join(lines)

    if profile_config["mode"] == "schema_drift":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            field_name = str(row.get("field_name") or "")
            storage_ref = str(row.get("storage_ref") or "")
            drift = str(row.get("drift_classification") or "")
            if not field_name or not storage_ref:
                continue
            validation_types = row.get("validation_types")
            validation_suffix = (
                f" | validations={','.join(str(item) for item in validation_types if item)}"
                if isinstance(validation_types, list) and validation_types
                else ""
            )
            lines.append(
                f"- storage={storage_ref} | field={field_name} | drift={drift} | required={row.get('required_in_quality')!s}{validation_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no schema drift evidence found")
        return "\n".join(lines)

    if profile_config["mode"] == "run_artifacts":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            run_instance_name = str(row.get("run_instance_name") or "")
            if not run_instance_name:
                continue
            lines.append(
                f"- run_instance={run_instance_name} | lifecycle_status={row.get('lifecycle_status') or ''!s} "
                f"| manifest_id={row.get('manifest_id') or ''!s} | run_id={row.get('run_id') or ''!s}"
            )
            detail_parts = [
                f"contract_ref={row.get('contract_ref') or ''!s}" if row.get("contract_ref") else "",
                f"contract_version={row.get('contract_version') or ''!s}" if row.get("contract_version") else "",
                f"effective_config_artifact_id={row.get('effective_config_artifact_id') or ''!s}"
                if row.get("effective_config_artifact_id")
                else "",
                f"lineage_fragment_id={row.get('lineage_fragment_id') or ''!s}" if row.get("lineage_fragment_id") else "",
            ]
            detail_line = " | ".join(part for part in detail_parts if part)
            if detail_line:
                lines.append(f"  {detail_line}")
            for field_name, prefix in (
                ("artifacts", "artifact"),
                ("dependencies", "depends_on"),
                ("support_links", "support"),
            ):
                values = row.get(field_name)
                if not isinstance(values, list):
                    continue
                normalized: set[str] = set()
                for value in values:
                    if not isinstance(value, dict):
                        continue
                    value_name = str(value.get("name") or "")
                    if not value_name:
                        continue
                    labels = value.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    artifact_family = str(value.get("artifact_family") or "")
                    extras = []
                    if label_str:
                        extras.append(f"labels={label_str}")
                    if artifact_family:
                        extras.append(f"artifact_family={artifact_family}")
                    suffix = f" | {' | '.join(extras)}" if extras else ""
                    normalized.add(f"  {prefix}={value_name}{suffix}")
                lines.extend(sorted(normalized))
        if len(lines) == 1:
            lines.append("- no run instance artifact chain found")
        return "\n".join(lines)

    if profile_config["mode"] in {"runtime_state", "runtime_locks"}:
        lines = [f"{title}: `{name}`"]
        for row in rows:
            state_name = str(row.get("runtime_state_name") or "")
            if not state_name:
                continue
            lines.append(
                f"- state={state_name} | kind={row.get('state_kind') or ''!s} | status={row.get('state_status') or ''!s} "
                f"| manifest_id={row.get('manifest_id') or ''!s} | retry_count={row.get('retry_count')!s} | lock_key={row.get('lock_key') or ''!s}"
            )
            for field_name_key, prefix in (("owners", "owner"), ("dependencies", "dependency"), ("artifacts", "artifact")):
                values = row.get(field_name_key)
                if not isinstance(values, list):
                    continue
                normalized: set[str] = set()
                for value in values:
                    if not isinstance(value, dict):
                        continue
                    value_name = str(value.get("name") or "")
                    if not value_name:
                        continue
                    labels = value.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    artifact_family = str(value.get("artifact_family") or "")
                    extras = []
                    if label_str:
                        extras.append(f"labels={label_str}")
                    if artifact_family:
                        extras.append(f"artifact_family={artifact_family}")
                    suffix = f" | {' | '.join(extras)}" if extras else ""
                    normalized.add(f"  {prefix}={value_name}{suffix}")
                lines.extend(sorted(normalized))
        if len(lines) == 1:
            lines.append("- no runtime state found")
        return "\n".join(lines)

    if profile_config["mode"] == "claim_trace":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            claim_name = str(row.get("claim_name") or "")
            if not claim_name:
                continue
            lines.append(
                f"- doc={row.get('doc_name') or ''!s} | claim={claim_name} | modality={row.get('modality') or ''!s} "
                f"| section={row.get('section_title') or ''!s} | anchor={row.get('section_anchor') or ''!s} "
                f"| line={row.get('line_number') or 0!s}"
            )
            claim_text = str(row.get("claim_text") or "")
            if claim_text:
                lines.append(f"  text={claim_text}")
            targets = row.get("targets")
            if isinstance(targets, list):
                normalized_targets: set[str] = set()
                for target in targets:
                    if not isinstance(target, dict):
                        continue
                    target_name = str(target.get("name") or "")
                    if not target_name:
                        continue
                    labels = target.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    label_suffix = f" | labels={label_str}" if label_str else ""
                    normalized_targets.add(f"  target={target_name}{label_suffix}")
                lines.extend(sorted(normalized_targets))
        if len(lines) == 1:
            lines.append("- no claim-level traceability found")
        return "\n".join(lines)

    if profile_config["mode"] == "cli_semantics":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            command_name = str(row.get("command_name") or "")
            if not command_name:
                continue
            lines.append(
                f"- command={command_name} | side_effect_class={row.get('side_effect_class') or ''!s}"
            )
            options = row.get("options")
            if isinstance(options, list):
                for option_name in sorted({str(item) for item in options if item}):
                    lines.append(f"  option={option_name}")
            gates = row.get("gates")
            if isinstance(gates, list):
                for gate_name in sorted({str(item) for item in gates if item}):
                    lines.append(f"  gate={gate_name}")
            targets = row.get("side_effect_targets")
            if isinstance(targets, list):
                normalized_targets: set[str] = set()
                for target in targets:
                    if not isinstance(target, dict):
                        continue
                    target_name = str(target.get("name") or "")
                    if not target_name:
                        continue
                    labels = target.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    label_suffix = f" | labels={label_str}" if label_str else ""
                    normalized_targets.add(f"  side_effect_target={target_name}{label_suffix}")
                lines.extend(sorted(normalized_targets))
        if len(lines) == 1:
            lines.append("- no CLI semantic coverage found")
        return "\n".join(lines)

    if profile_config["mode"] == "duplication_cluster":
        row = rows[0]
        family_name = str(row.get("family_name") or "")
        surface_kind = str(row.get("surface_kind") or "")
        duplicate_count = str(row.get("duplicate_count") or "")
        promotion_score = str(row.get("promotion_score") or "")
        promotion_target = str(row.get("promotion_target") or "")
        target_labels = row.get("promotion_target_labels")
        members = row.get("members")
        tests = row.get("tests")
        lines = [f"{title}: `{name}`"]
        lines.append(
            f"- family={family_name} | surface_kind={surface_kind} | duplicates={duplicate_count} | promotion_score={promotion_score}"
        )
        if promotion_target:
            if isinstance(target_labels, list):
                label_str = ",".join(str(label) for label in target_labels)
            else:
                label_str = ""
            label_suffix = f" | labels={label_str}" if label_str else ""
            lines.append(f"- promotion_target={promotion_target}{label_suffix}")
        if isinstance(members, list):
            normalized_members = []
            for member in members:
                if not isinstance(member, dict):
                    continue
                member_name = str(member.get("name") or "")
                if not member_name:
                    continue
                labels = member.get("labels")
                if isinstance(labels, list):
                    label_str = ",".join(str(label) for label in labels)
                else:
                    label_str = ""
                label_suffix = f" | labels={label_str}" if label_str else ""
                normalized_members.append(f"- member={member_name}{label_suffix}")
            lines.extend(sorted(normalized_members))
        if isinstance(tests, list):
            normalized_tests = sorted(
                {
                    f"- covered_by_test={test_name!s}"
                    for test_name in tests
                    if test_name is not None and str(test_name)
                }
            )
            lines.extend(normalized_tests)
        return "\n".join(lines)

    if profile_config["mode"] == "normalization_pipeline":
        row = rows[0]
        lines = [f"{title}: `{name}`"]
        lines.append(
            "- "
            f"profile_registered={bool(row.get('normalization_profile_registered'))} | "
            f"profile_fields={int(row.get('profile_field_count') or 0)} | "
            f"fallback_fields={int(row.get('fallback_field_count') or 0)} | "
            f"fallback_business={int(row.get('fallback_business_field_count') or 0)} | "
            f"fallback_technical={int(row.get('fallback_technical_passthrough_field_count') or 0)}"
        )
        module_path = str(row.get("normalization_profile_module_path") or "")
        if module_path:
            lines.append(f"- profile_module={module_path}")
        modules = row.get("normalization_modules")
        if isinstance(modules, list):
            for module in sorted({str(item) for item in modules if str(item)}):
                lines.append(f"- normalization_module={module}")
        return "\n".join(lines)

    if profile_config["mode"] == "fallback_pipelines":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            pipeline_name = str(row.get("pipeline_name") or "")
            if not pipeline_name:
                continue
            lines.append(
                "- "
                f"pipeline={pipeline_name} | "
                f"fallback_business={int(row.get('fallback_business_field_count') or 0)} | "
                f"fallback_total={int(row.get('fallback_field_count') or 0)} | "
                f"profile_registered={bool(row.get('normalization_profile_registered'))} | "
                f"profile_fields={int(row.get('profile_field_count') or 0)}"
            )
        return "\n".join(lines)

    if profile_config["mode"] == "promotion_candidates":
        lines = [f"{title}: `{name}`"]
        seen: set[str] = set()
        for row in rows:
            cluster_name = str(row.get("cluster_name") or "")
            if not cluster_name or cluster_name in seen:
                continue
            seen.add(cluster_name)
            family_name = str(row.get("family_name") or "")
            surface_kind = str(row.get("surface_kind") or "")
            duplicate_count = str(row.get("duplicate_count") or "")
            promotion_score = str(row.get("promotion_score") or "")
            promotion_target = str(row.get("promotion_target") or "")
            member_count = str(row.get("member_count") or "")
            test_count = str(row.get("test_count") or "")
            lines.append(
                f"- cluster={cluster_name} | family={family_name} | surface_kind={surface_kind} | "
                f"duplicates={duplicate_count} | members={member_count} | tests={test_count} | "
                f"promotion_score={promotion_score} | target={promotion_target}"
            )
        if len(lines) == 1:
            lines.append("- no promotion candidates found")
        return "\n".join(lines)

    if profile_config["mode"] == "dead_code_candidates":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            family_name = str(row.get("family_name") or "")
            target_label = str(row.get("target_label") or "")
            deletion_score = str(row.get("deletion_score") or "")
            deletion_confidence = str(row.get("deletion_confidence") or "")
            recent_age_days = str(row.get("recent_age_days") or "")
            only_test_referenced = str(row.get("only_test_referenced") or "")
            runtime_anchor_count = str(row.get("runtime_anchor_count") or "")
            config_anchor_count = str(row.get("config_anchor_count") or "")
            doc_anchor_count = str(row.get("doc_anchor_count") or "")
            test_anchor_count = str(row.get("test_anchor_count") or "")
            blocked_by_cycle = str(row.get("blocked_by_cycle") or "")
            deprecation_markers = row.get("deprecation_markers")
            if isinstance(deprecation_markers, list):
                marker_str = ",".join(str(marker) for marker in deprecation_markers)
            else:
                marker_str = ""
            blocked_suffix = f" | blocked_by={blocked_by_cycle}" if blocked_by_cycle else ""
            marker_suffix = f" | deprecation_markers={marker_str}" if marker_str else ""
            lines.append(
                f"- target={target_name} | label={target_label} | family={family_name} | deletion_score={deletion_score} "
                f"| confidence={deletion_confidence} | recent_age_days={recent_age_days} | only_test_referenced={only_test_referenced} "
                f"| runtime={runtime_anchor_count} | config={config_anchor_count} | docs={doc_anchor_count} | tests={test_anchor_count}"
                f"{marker_suffix}{blocked_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no dead code candidates found")
        return "\n".join(lines)

    if profile_config["mode"] == "current_cycle_code":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            family_name = str(row.get("family_name") or "")
            target_label = str(row.get("target_label") or "")
            cycle_status = str(row.get("cycle_status") or "")
            cycle_score = str(row.get("cycle_score") or "")
            recent_age_days = str(row.get("recent_age_days") or "")
            runtime_anchor_count = str(row.get("runtime_anchor_count") or "")
            config_anchor_count = str(row.get("config_anchor_count") or "")
            doc_anchor_count = str(row.get("doc_anchor_count") or "")
            test_anchor_count = str(row.get("test_anchor_count") or "")
            wip_markers = row.get("wip_markers")
            if isinstance(wip_markers, list):
                marker_str = ",".join(str(marker) for marker in wip_markers)
            else:
                marker_str = ""
            marker_suffix = f" | wip_markers={marker_str}" if marker_str else ""
            lines.append(
                f"- target={target_name} | label={target_label} | family={family_name} | cycle_status={cycle_status} "
                f"| cycle_score={cycle_score} | recent_age_days={recent_age_days} | runtime={runtime_anchor_count} "
                f"| config={config_anchor_count} | docs={doc_anchor_count} | tests={test_anchor_count}{marker_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no current-cycle code surfaces found")
        return "\n".join(lines)

    if profile_config["mode"] == "overengineered_candidates":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            blocked_by_cycle = str(row.get("blocked_by_cycle") or "")
            indirection_markers = row.get("indirection_markers")
            stateful_markers = row.get("stateful_markers")
            indirection_str = ",".join(str(marker) for marker in indirection_markers) if isinstance(indirection_markers, list) else ""
            stateful_str = ",".join(str(marker) for marker in stateful_markers) if isinstance(stateful_markers, list) else ""
            blocked_suffix = f" | blocked_by={blocked_by_cycle}" if blocked_by_cycle else ""
            lines.append(
                f"- target={target_name} | label={row.get('target_label') or ''!s} | family={row.get('family_name') or ''!s} "
                f"| classification={row.get('classification') or ''!s} | complexity_score={row.get('complexity_score') or ''!s} "
                f"| simplification_score={row.get('simplification_score') or ''!s} | removable_score={row.get('removable_score') or ''!s} "
                f"| branches={row.get('branch_count') or ''!s} | nesting={row.get('nesting_depth') or ''!s} "
                f"| helper_calls={row.get('helper_call_count') or ''!s}{blocked_suffix}"
            )
            if indirection_str:
                lines.append(f"  indirection_markers={indirection_str}")
            if stateful_str:
                lines.append(f"  stateful_markers={stateful_str}")
        if len(lines) == 1:
            lines.append("- no overengineered candidates found")
        return "\n".join(lines)

    if profile_config["mode"] == "removable_complexity":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            deprecation_markers = row.get("deprecation_markers")
            marker_str = ",".join(str(marker) for marker in deprecation_markers) if isinstance(deprecation_markers, list) else ""
            marker_suffix = f" | deprecation_markers={marker_str}" if marker_str else ""
            lines.append(
                f"- target={target_name} | label={row.get('target_label') or ''!s} | family={row.get('family_name') or ''!s} "
                f"| removable_score={row.get('removable_score') or ''!s} | removal_confidence={row.get('removal_confidence') or ''!s} "
                f"| runtime={row.get('runtime_anchor_count') or ''!s} | config={row.get('config_anchor_count') or ''!s} "
                f"| docs={row.get('doc_anchor_count') or ''!s} | tests={row.get('test_anchor_count') or ''!s}{marker_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no removable complexity candidates found")
        return "\n".join(lines)

    if profile_config["mode"] == "simplification_blockers":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            lines.append(
                f"- target={target_name} | label={row.get('target_label') or ''!s} | family={row.get('family_name') or ''!s} "
                f"| classification={row.get('classification') or ''!s} | runtime={row.get('runtime_anchor_count') or ''!s} "
                f"| config={row.get('config_anchor_count') or ''!s} | docs={row.get('doc_anchor_count') or ''!s} "
                f"| tests={row.get('test_anchor_count') or ''!s}"
            )
            cycle_blockers = row.get("cycle_blockers")
            if isinstance(cycle_blockers, list):
                for blocker in sorted({str(item) for item in cycle_blockers if item}):
                    lines.append(f"  cycle_blocker={blocker}")
            blockers = row.get("blockers")
            if isinstance(blockers, list):
                normalized: set[str] = set()
                for blocker in blockers:
                    if not isinstance(blocker, dict):
                        continue
                    blocker_name = str(blocker.get("name") or "")
                    if not blocker_name:
                        continue
                    relation_name = str(blocker.get("relation") or "")
                    labels = blocker.get("labels")
                    label_str = ",".join(str(label) for label in labels) if isinstance(labels, list) else ""
                    normalized.add(
                        f"  blocker={blocker_name} | relation={relation_name}" + (f" | labels={label_str}" if label_str else "")
                    )
                lines.extend(sorted(normalized))
        if len(lines) == 1:
            lines.append("- no simplification blockers found")
        return "\n".join(lines)

    lines = [f"{title}: `{name}`"]
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        owner = str(row.get("owner_directory") or "")
        if not owner:
            continue
        zone = str(row.get("repo_zone") or "")
        provenance = str(row.get("provenance") or "")
        key = (zone, owner, provenance, "")
        if key in seen:
            continue
        seen.add(key)
        provenance_suffix = f" | provenance={provenance}" if provenance else ""
        lines.append(f"- zone={zone} | owner={owner}{provenance_suffix}")
    if len(lines) == 1:
        lines.append("- no directory ownership edges found")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    rows = _run_query(args.root, args.profile, args.name, args.http_uri)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(_format_rows(args.profile, args.name, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
