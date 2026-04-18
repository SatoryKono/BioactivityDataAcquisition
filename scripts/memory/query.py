#!/usr/bin/env python3
"""Operator-facing shortcuts for querying deterministic Neo4j memory paths."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
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


QUERY_STATEMENTS: dict[str, Callable[[], str]] = {
    "neighbors": _neighbors_statement,
    "docs_drift": _docs_drift_statement,
    "workflow_gates": _workflow_gates_statement,
    "workflow_artifacts": _workflow_artifacts_statement,
    "workflow_execution": _workflow_execution_statement,
    "storage_lineage": _storage_lineage_statement,
    "field_lineage": _field_lineage_statement,
    "schema_drift": _schema_drift_statement,
    "run_artifacts": _run_artifacts_statement,
    "runtime_state": _runtime_state_statement,
    "runtime_locks": lambda: _runtime_state_statement(locks_only=True),
    "claim_trace": _claim_trace_statement,
    "cli_semantics": _cli_semantics_statement,
    "normalization_pipeline": _normalization_pipeline_statement,
    "fallback_pipelines": _fallback_pipelines_statement,
    "duplication_cluster": _duplication_cluster_statement,
    "promotion_candidates": _promotion_candidates_statement,
    "dead_code_candidates": _dead_code_candidates_statement,
    "current_cycle_code": _current_cycle_code_statement,
    "overengineered_candidates": _overengineered_candidates_statement,
    "removable_complexity": _removable_complexity_statement,
    "simplification_blockers": _simplification_blockers_statement,
}


def _statement_for_profile_mode(mode: str) -> str:
    statement_builder = QUERY_STATEMENTS.get(mode, _ownership_statement)
    return statement_builder()


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
    statement = _statement_for_profile_mode(str(profile_config["mode"]))
    return client.query(
        statement,
        params,
    )


EMPTY_SUFFIXES: dict[str, str] = {
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
}


def _empty_result(title: str, mode: str, name: str) -> str:
    return f"{title}: {EMPTY_SUFFIXES[mode]} for `{name}`."


def _optional_row_part(
    row: dict[str, JsonValue],
    field_name: str,
    *,
    label: str | None = None,
    formatter: Callable[[JsonValue], str] | None = None,
) -> str:
    value = row.get(field_name)
    if value in (None, ""):
        return ""
    rendered = formatter(value) if formatter is not None else str(value)
    return f"{label or field_name}={rendered}" if rendered else ""


def _optional_joined_list_part(
    row: dict[str, JsonValue],
    field_name: str,
    *,
    label: str | None = None,
) -> str:
    return _optional_row_part(
        row,
        field_name,
        label=label,
        formatter=lambda value: _join_string_list(value),
    )


def _append_prefixed_row_values(
    lines: list[str],
    row: dict[str, JsonValue],
    field_mappings: list[tuple[str, str]],
) -> None:
    for field_name, prefix in field_mappings:
        lines.extend(_sorted_prefixed_values(row.get(field_name), prefix))


def _format_neighbors_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        relation_type = str(row.get("relation_type") or "")
        neighbor_name = str(row.get("neighbor_name") or "")
        direction = str(row.get("direction") or "")
        if not relation_type or not neighbor_name:
            continue
        neighbor_labels = row.get("neighbor_labels")
        label_str = ",".join(str(label) for label in neighbor_labels) if isinstance(neighbor_labels, list) else ""
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


def _docs_drift_row_line(row: dict[str, JsonValue]) -> str | None:
    doc_name = str(row.get("doc_name") or "")
    target_name = str(row.get("target_name") or "")
    if not doc_name or not target_name:
        return None
    detail_parts = [
        f"doc={doc_name}",
        _optional_joined_list_part(row, "doc_labels", label="doc_labels"),
        f"target={target_name}",
        _optional_joined_list_part(row, "target_labels", label="target_labels"),
        _optional_row_part(row, "doc_source_path", label="doc_path"),
        _optional_row_part(row, "target_source_path", label="target_path"),
        _optional_row_part(row, "doc_reference", label="ref"),
        _optional_row_part(row, "evidence_kind"),
        _optional_row_part(row, "confidence"),
        _optional_row_part(row, "section_title", label="section"),
        _optional_row_part(row, "section_anchor", label="anchor"),
        _optional_row_part(
            row,
            "line_number",
            label="line",
            formatter=lambda value: str(int(value or 0)) if int(value or 0) else "",
        ),
    ]
    return "- " + " | ".join(part for part in detail_parts if part)


def _format_docs_drift_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    seen: set[str] = set()
    for row in rows:
        rendered = _docs_drift_row_line(row)
        if not rendered or rendered in seen:
            continue
        seen.add(rendered)
        lines.append(rendered)
    if len(lines) == 1:
        lines.append("- no docs-to-code drift edges found")
    return "\n".join(lines)


def _workflow_job_header(row: dict[str, JsonValue]) -> str | None:
    workflow_name = str(row.get("workflow_name") or "")
    job_name = str(row.get("job_name") or "")
    if not workflow_name or not job_name:
        return None
    return f"- workflow={workflow_name} | job={job_name}"


def _format_workflow_gates_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        header = _workflow_job_header(row)
        if not header:
            continue
        lines.append(header)
        lines.extend(_sorted_prefixed_values(row.get("gates"), "gate"))
        lines.extend(_format_surface_dict_list(row.get("run_targets"), "runs_via"))
    if len(lines) == 1:
        lines.append("- no workflow gate coverage found")
    return "\n".join(lines)


def _format_workflow_artifacts_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        header = _workflow_job_header(row)
        if not header:
            continue
        lines.append(header)
        lines.extend(_sorted_prefixed_values(row.get("actions"), "action"))
        artifacts = row.get("artifacts")
        if isinstance(artifacts, list):
            lines.extend(_format_surface_dict_list(artifacts, "artifact"))
        lines.extend(_sorted_prefixed_values(row.get("secrets"), "secret"))
    if len(lines) == 1:
        lines.append("- no workflow action or artifact coverage found")
    return "\n".join(lines)


def _workflow_execution_suffix_parts(
    field_name: str,
    value: dict[str, JsonValue],
) -> list[str]:
    if field_name == "reusable_calls":
        return [
            part
            for part in (
                _optional_row_part(value, "target_workflow"),
                _optional_row_part(value, "reusable_kind", label="kind"),
            )
            if part
        ]
    if field_name == "matrix_variants":
        variant_axes = value.get("variant_axes")
        if isinstance(variant_axes, dict):
            return [
                "axes="
                + ",".join(f"{key}={variant_axes[key]!s}" for key in sorted(variant_axes))
            ]
        return []
    return [
        part
        for part in (
            _optional_row_part(value, "scope"),
            _optional_row_part(value, "expression"),
        )
        if part
    ]


def _format_workflow_execution_value(field_name: str, prefix: str, value: dict[str, JsonValue]) -> str | None:
    item_name = str(value.get("name") or "")
    if not item_name:
        return None
    suffix_parts = _workflow_execution_suffix_parts(field_name, value)
    suffix = f" | {' | '.join(suffix_parts)}" if suffix_parts else ""
    return f"  {prefix}={item_name}{suffix}"


def _workflow_execution_header(row: dict[str, JsonValue]) -> str | None:
    workflow_name = str(row.get("workflow_name") or "")
    if not workflow_name:
        return None
    suffix_parts = [
        part
        for part in (
            _optional_row_part(row, "job_name", label="job"),
            _optional_row_part(
                row,
                "workflow_concurrency_group",
                label="workflow_concurrency",
            ),
            _optional_row_part(row, "job_concurrency_group", label="job_concurrency"),
        )
        if part
    ]
    suffix = f" | {' | '.join(suffix_parts)}" if suffix_parts else ""
    return f"- workflow={workflow_name}{suffix}"


def _format_workflow_execution_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        header = _workflow_execution_header(row)
        if not header:
            continue
        lines.append(header)
        for field_name, prefix in (
            ("reusable_calls", "call"),
            ("matrix_variants", "matrix"),
            ("workflow_outputs", "workflow_output"),
            ("job_outputs", "job_output"),
        ):
            values = row.get(field_name)
            if not isinstance(values, list):
                continue
            normalized = {
                rendered
                for value in values
                if isinstance(value, dict)
                for rendered in [_format_workflow_execution_value(field_name, prefix, value)]
                if rendered
            }
            lines.extend(sorted(normalized))
    if len(lines) == 1:
        lines.append("- no reusable workflow, matrix, or output coverage found")
    return "\n".join(lines)


def _join_string_list(values: JsonValue) -> str:
    return ",".join(str(item) for item in values) if isinstance(values, list) else ""


def _label_suffix(labels: JsonValue) -> str:
    label_str = _join_string_list(labels)
    return f" | labels={label_str}" if label_str else ""


def _sorted_prefixed_values(values: JsonValue, prefix: str) -> list[str]:
    if not isinstance(values, list):
        return []
    return [f"  {prefix}={value}" for value in sorted({str(item) for item in values if item})]


def _storage_summary_line(row: dict[str, JsonValue], storage_name: str) -> str:
    roles_str = _join_string_list(row.get("storage_roles"))
    return (
        f"- storage={storage_name} | layer={row.get('layer') or ''!s} | storage_kind={row.get('storage_kind') or ''!s} "
        f"| format={row.get('storage_format') or ''!s} | roles={roles_str or ''} | schema_present={row.get('schema_present') or False!s}"
    )


def _storage_detail_line(row: dict[str, JsonValue]) -> str | None:
    detail_parts = [
        _optional_row_part(row, "config_version"),
        _optional_row_part(row, "quality_version"),
        _optional_joined_list_part(row, "partition_by"),
        _optional_joined_list_part(row, "sort_by"),
        _optional_row_part(row, "versioning_mode"),
        _optional_row_part(row, "version_column"),
    ]
    detail_line = " | ".join(part for part in detail_parts if part)
    return f"  {detail_line}" if detail_line else None


def _storage_producer_lines(producers: JsonValue) -> list[str]:
    if not isinstance(producers, list):
        return []
    normalized: set[str] = set()
    for producer in producers:
        if not isinstance(producer, dict):
            continue
        producer_name = str(producer.get("name") or "")
        if not producer_name:
            continue
        normalized.add(f"  producer={producer_name}{_label_suffix(producer.get('labels'))}")
    return sorted(normalized)


def _format_storage_lineage_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        storage_name = str(row.get("storage_name") or "")
        if not storage_name:
            continue
        lines.append(_storage_summary_line(row, storage_name))
        detail_line = _storage_detail_line(row)
        if detail_line:
            lines.append(detail_line)
        lines.extend(_storage_producer_lines(row.get("producers")))
        lines.extend(_sorted_prefixed_values(row.get("upstream_surfaces"), "upstream"))
        lines.extend(_sorted_prefixed_values(row.get("downstream_surfaces"), "downstream"))
        lines.extend(_sorted_prefixed_values(row.get("defining_configs"), "defined_by"))
    if len(lines) == 1:
        lines.append("- no storage lineage found")
    return "\n".join(lines)


def _format_field_lineage_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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
        _append_prefixed_row_values(
            lines,
            row,
            [
            ("upstream_fields", "upstream"),
            ("downstream_fields", "downstream"),
            ("contracts", "contract"),
            ],
        )
    if len(lines) == 1:
        lines.append("- no field lineage found")
    return "\n".join(lines)


def _format_schema_drift_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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


def _format_surface_dict_list(values: object, prefix: str) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        value_name = str(value.get("name") or "")
        if not value_name:
            continue
        extras = [
            part
            for part in (
                _optional_joined_list_part(value, "labels"),
                _optional_row_part(value, "artifact_family"),
                _optional_row_part(value, "relation"),
            )
            if part
        ]
        suffix = f" | {' | '.join(extras)}" if extras else ""
        normalized.add(f"  {prefix}={value_name}{suffix}")
    return sorted(normalized)


def _format_run_artifacts_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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
            _optional_row_part(row, "contract_ref"),
            _optional_row_part(row, "contract_version"),
            _optional_row_part(row, "effective_config_artifact_id"),
            _optional_row_part(row, "lineage_fragment_id"),
        ]
        detail_line = " | ".join(part for part in detail_parts if part)
        if detail_line:
            lines.append(f"  {detail_line}")
        lines.extend(_format_surface_dict_list(row.get("artifacts"), "artifact"))
        lines.extend(_format_surface_dict_list(row.get("dependencies"), "depends_on"))
        lines.extend(_format_surface_dict_list(row.get("support_links"), "support"))
    if len(lines) == 1:
        lines.append("- no run instance artifact chain found")
    return "\n".join(lines)


def _format_runtime_state_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        state_name = str(row.get("runtime_state_name") or "")
        if not state_name:
            continue
        lines.append(
            f"- state={state_name} | kind={row.get('state_kind') or ''!s} | status={row.get('state_status') or ''!s} "
            f"| manifest_id={row.get('manifest_id') or ''!s} | retry_count={row.get('retry_count')!s} | lock_key={row.get('lock_key') or ''!s}"
        )
        lines.extend(_format_surface_dict_list(row.get("owners"), "owner"))
        lines.extend(_format_surface_dict_list(row.get("dependencies"), "dependency"))
        lines.extend(_format_surface_dict_list(row.get("artifacts"), "artifact"))
    if len(lines) == 1:
        lines.append("- no runtime state found")
    return "\n".join(lines)


def _format_claim_trace_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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
        lines.extend(_format_surface_dict_list(row.get("targets"), "target"))
    if len(lines) == 1:
        lines.append("- no claim-level traceability found")
    return "\n".join(lines)


def _format_cli_semantics_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        command_name = str(row.get("command_name") or "")
        if not command_name:
            continue
        lines.append(f"- command={command_name} | side_effect_class={row.get('side_effect_class') or ''!s}")
        lines.extend(_sorted_prefixed_values(row.get("options"), "option"))
        lines.extend(_sorted_prefixed_values(row.get("gates"), "gate"))
        lines.extend(_format_surface_dict_list(row.get("side_effect_targets"), "side_effect_target"))
    if len(lines) == 1:
        lines.append("- no CLI semantic coverage found")
    return "\n".join(lines)


def _format_duplication_cluster_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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
        lines.append(f"- promotion_target={promotion_target}{_label_suffix(target_labels)}")
    if isinstance(members, list):
        lines.extend(line.replace("  member=", "- member=", 1) for line in _format_surface_dict_list(members, "member"))
    if isinstance(tests, list):
        normalized_tests = sorted(
            {f"- covered_by_test={test_name!s}" for test_name in tests if test_name is not None and str(test_name)}
        )
        lines.extend(normalized_tests)
    return "\n".join(lines)


def _format_normalization_pipeline_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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


def _format_fallback_pipelines_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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


def _format_promotion_candidates_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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


def _marker_suffix(row: dict[str, JsonValue], field_name: str, suffix_name: str) -> str:
    marker_str = _join_string_list(row.get(field_name))
    return f" | {suffix_name}={marker_str}" if marker_str else ""


def _target_identity_parts(row: dict[str, JsonValue]) -> list[str]:
    return [
        f"target={row.get('target_name') or ''!s}",
        f"label={row.get('target_label') or ''!s}",
        f"family={row.get('family_name') or ''!s}",
    ]


def _anchor_count_parts(row: dict[str, JsonValue]) -> list[str]:
    return [
        f"runtime={row.get('runtime_anchor_count') or ''!s}",
        f"config={row.get('config_anchor_count') or ''!s}",
        f"docs={row.get('doc_anchor_count') or ''!s}",
        f"tests={row.get('test_anchor_count') or ''!s}",
    ]


def _target_row_line(row: dict[str, JsonValue], extra_parts: list[str], suffix: str = "") -> str:
    return "- " + " | ".join([*_target_identity_parts(row), *extra_parts]) + suffix


def _blocker_detail_lines(blockers: JsonValue) -> list[str]:
    if not isinstance(blockers, list):
        return []
    normalized: set[str] = set()
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        blocker_name = str(blocker.get("name") or "")
        if not blocker_name:
            continue
        relation_name = str(blocker.get("relation") or "")
        normalized.add(f"  blocker={blocker_name} | relation={relation_name}{_label_suffix(blocker.get('labels'))}")
    return sorted(normalized)


def _format_dead_code_candidates_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        if not row.get("target_name"):
            continue
        suffix = _marker_suffix(row, "deprecation_markers", "deprecation_markers")
        if row.get("blocked_by_cycle"):
            suffix += f" | blocked_by={row.get('blocked_by_cycle') or ''!s}"
        lines.append(
            _target_row_line(
                row,
                [
                    f"deletion_score={row.get('deletion_score') or ''!s}",
                    f"confidence={row.get('deletion_confidence') or ''!s}",
                    f"recent_age_days={row.get('recent_age_days') or ''!s}",
                    f"only_test_referenced={row.get('only_test_referenced') or ''!s}",
                    *_anchor_count_parts(row),
                ],
                suffix,
            )
        )
    if len(lines) == 1:
        lines.append("- no dead code candidates found")
    return "\n".join(lines)


def _format_current_cycle_code_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        if not row.get("target_name"):
            continue
        lines.append(
            _target_row_line(
                row,
                [
                    f"cycle_status={row.get('cycle_status') or ''!s}",
                    f"cycle_score={row.get('cycle_score') or ''!s}",
                    f"recent_age_days={row.get('recent_age_days') or ''!s}",
                    *_anchor_count_parts(row),
                ],
                _marker_suffix(row, "wip_markers", "wip_markers"),
            )
        )
    if len(lines) == 1:
        lines.append("- no current-cycle code surfaces found")
    return "\n".join(lines)


def _format_overengineered_candidates_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        if not row.get("target_name"):
            continue
        blocked_suffix = f" | blocked_by={row.get('blocked_by_cycle') or ''!s}" if row.get("blocked_by_cycle") else ""
        lines.append(
            _target_row_line(
                row,
                [
                    f"classification={row.get('classification') or ''!s}",
                    f"complexity_score={row.get('complexity_score') or ''!s}",
                    f"simplification_score={row.get('simplification_score') or ''!s}",
                    f"removable_score={row.get('removable_score') or ''!s}",
                    f"branches={row.get('branch_count') or ''!s}",
                    f"nesting={row.get('nesting_depth') or ''!s}",
                    f"helper_calls={row.get('helper_call_count') or ''!s}",
                ],
                blocked_suffix,
            )
        )
        for marker_line in (
            _optional_joined_list_part(row, "indirection_markers"),
            _optional_joined_list_part(row, "stateful_markers"),
        ):
            if marker_line:
                lines.append(f"  {marker_line}")
    if len(lines) == 1:
        lines.append("- no overengineered candidates found")
    return "\n".join(lines)


def _format_removable_complexity_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        target_name = str(row.get("target_name") or "")
        if not target_name:
            continue
        marker_suffix = _marker_suffix(
            row,
            "deprecation_markers",
            "deprecation_markers",
        )
        lines.append(
            _target_row_line(
                row,
                [
                    f"removable_score={row.get('removable_score') or ''!s}",
                    f"removal_confidence={row.get('removal_confidence') or ''!s}",
                    *_anchor_count_parts(row),
                ],
                marker_suffix,
            )
        )
    if len(lines) == 1:
        lines.append("- no removable complexity candidates found")
    return "\n".join(lines)


def _format_simplification_blockers_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    lines = [f"{title}: `{name}`"]
    for row in rows:
        if not row.get("target_name"):
            continue
        lines.append(
            _target_row_line(
                row,
                [
                    f"classification={row.get('classification') or ''!s}",
                    *_anchor_count_parts(row),
                ],
            )
        )
        lines.extend(_sorted_prefixed_values(row.get("cycle_blockers"), "cycle_blocker"))
        lines.extend(_blocker_detail_lines(row.get("blockers")))
    if len(lines) == 1:
        lines.append("- no simplification blockers found")
    return "\n".join(lines)


def _format_owner_rows(title: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
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


ROW_FORMATTERS: dict[str, Callable[[str, str, list[dict[str, JsonValue]]], str]] = {
    "neighbors": _format_neighbors_rows,
    "docs_drift": _format_docs_drift_rows,
    "workflow_gates": _format_workflow_gates_rows,
    "workflow_artifacts": _format_workflow_artifacts_rows,
    "workflow_execution": _format_workflow_execution_rows,
    "storage_lineage": _format_storage_lineage_rows,
    "field_lineage": _format_field_lineage_rows,
    "schema_drift": _format_schema_drift_rows,
    "run_artifacts": _format_run_artifacts_rows,
    "runtime_state": _format_runtime_state_rows,
    "runtime_locks": _format_runtime_state_rows,
    "claim_trace": _format_claim_trace_rows,
    "cli_semantics": _format_cli_semantics_rows,
    "duplication_cluster": _format_duplication_cluster_rows,
    "normalization_pipeline": _format_normalization_pipeline_rows,
    "fallback_pipelines": _format_fallback_pipelines_rows,
    "promotion_candidates": _format_promotion_candidates_rows,
    "dead_code_candidates": _format_dead_code_candidates_rows,
    "current_cycle_code": _format_current_cycle_code_rows,
    "overengineered_candidates": _format_overengineered_candidates_rows,
    "removable_complexity": _format_removable_complexity_rows,
    "simplification_blockers": _format_simplification_blockers_rows,
    "owner": _format_owner_rows,
}


def _format_rows(profile: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    profile_config = QUERY_PROFILES[profile]
    mode = str(profile_config["mode"])
    title = profile_config["title"]
    if not rows:
        return _empty_result(title, mode, name)
    formatter = ROW_FORMATTERS.get(mode, _format_owner_rows)
    return formatter(title, name, rows)


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
