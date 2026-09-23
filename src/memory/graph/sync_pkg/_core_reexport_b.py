"""Explicit graph-sync re-export shard (AUD-002 barrel split)."""

from __future__ import annotations

# ruff: noqa: I001
# fmt: off
from memory.graph.sync_pkg.apply_verify import (
    CRITICAL_ANALYSIS_NODE_LABELS as CRITICAL_ANALYSIS_NODE_LABELS,
    CRITICAL_ANALYSIS_RELATION_TYPES as CRITICAL_ANALYSIS_RELATION_TYPES,
    _active_group_names as _active_group_names,
    _critical_analysis_group_counts as _critical_analysis_group_counts,
    _critical_analysis_mismatch_messages as _critical_analysis_mismatch_messages,
    _critical_analysis_retry_batch_size as _critical_analysis_retry_batch_size,
    _expected_group_counts as _expected_group_counts,
    _expected_group_mismatches as _expected_group_mismatches,
    _group_count_mismatches as _group_count_mismatches,
    _group_mismatch_messages as _group_mismatch_messages,
    _group_names as _group_names,
    _missing_group_names as _missing_group_names,
    _raise_analysis_group_mismatches as _raise_analysis_group_mismatches,
    _refresh_node_counts_if_retried as _refresh_node_counts_if_retried,
    _refresh_relation_counts_if_retried as _refresh_relation_counts_if_retried,
    _retry_critical_analysis_groups as _retry_critical_analysis_groups,
    _retry_critical_node_groups as _retry_critical_node_groups,
    _retry_critical_relation_groups as _retry_critical_relation_groups,
    _retry_missing_groups as _retry_missing_groups,
    _verify_expected_group_counts as _verify_expected_group_counts,
)
from memory.graph.sync_pkg.batch_pipeline_names import (
    _batch_pipeline_names as _batch_pipeline_names,
    _normalization_progress_payload as _normalization_progress_payload,
)
from memory.graph.sync_pkg.build_snapshot import build_snapshot as build_snapshot
from memory.graph.sync_pkg.claim_line_context import (
    _add_claim_path_targets as _add_claim_path_targets,
    _claim_line_context as _claim_line_context,
    _claim_section_context as _claim_section_context,
)
from memory.graph.sync_pkg.claim_target_tokens import (
    _claim_exact_candidates as _claim_exact_candidates,
    _claim_target_tokens as _claim_target_tokens,
)
from memory.graph.sync_pkg.classify_silver_storage_fields import (
    _classify_gold_storage_fields as _classify_gold_storage_fields,
    _classify_silver_storage_fields as _classify_silver_storage_fields,
    _composite_group_fields as _composite_group_fields,
)
from memory.graph.sync_pkg.collect_duplication_class_descriptors import (
    _collect_duplication_class_descriptors as _collect_duplication_class_descriptors,
    _collect_duplication_function_descriptor as _collect_duplication_function_descriptor,
    _duplication_class_method_index as _duplication_class_method_index,
)
from memory.graph.sync_pkg.collect_duplication_descriptors_for_modu import (
    _collect_duplication_descriptors_for_module as _collect_duplication_descriptors_for_module,
)
from memory.graph.sync_pkg.complexity_analysis_context import (
    _complexity_analysis_context as _complexity_analysis_context,
    _complexity_surface_measurements as _complexity_surface_measurements,
)
from memory.graph.sync_pkg.complexity_analysis_label_sets import (
    _complexity_analysis_label_sets as _complexity_analysis_label_sets,
    _complexity_surface_prerequisites as _complexity_surface_prerequisites,
)
from memory.graph.sync_pkg.complexity_blocker_context import (
    _add_pipeline_surfaces as _add_pipeline_surfaces,
    _complexity_blocker_context as _complexity_blocker_context,
)
from memory.graph.sync_pkg.complexity_candidate_anchor_slices import (
    _add_complexity_candidate_node as _add_complexity_candidate_node,
    _complexity_candidate_anchor_slices as _complexity_candidate_anchor_slices,
    _link_complexity_candidate as _link_complexity_candidate,
)
from memory.graph.sync_pkg.complexity_candidate_context import (
    _complexity_candidate_context as _complexity_candidate_context,
    _emit_complexity_candidate as _emit_complexity_candidate,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _classify_complexity_candidate as _classify_complexity_candidate,
    _complexity_marker_buckets as _complexity_marker_buckets,
    _complexity_scores as _complexity_scores,
    _configured_duplicate_families as _configured_duplicate_families,
    _configured_node_keys as _configured_node_keys,
    _link_existing_targets as _link_existing_targets,
    _retirement_scores as _retirement_scores,
)
from memory.graph.sync_pkg.complexity_score_inputs import _complexity_score_inputs as _complexity_score_inputs
from memory.graph.sync_pkg.complexity_surface_scores import _complexity_surface_scores as _complexity_surface_scores
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _add_cli_command_graph as _add_cli_command_graph,
    _add_curated_execution_paths as _add_curated_execution_paths,
    _add_quality_and_scripts as _add_quality_and_scripts,
    _composite_config_dependency_entries as _composite_config_dependency_entries,
    _link_composite_dependency as _link_composite_dependency,
    _link_composite_seed_dependency as _link_composite_seed_dependency,
)
from memory.graph.sync_pkg.composite_config_paths import (
    _add_composite_config_surface as _add_composite_config_surface,
    _composite_config_identity as _composite_config_identity,
    _composite_config_paths as _composite_config_paths,
)
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _add_composite_dependency_surface as _add_composite_dependency_surface,
    _add_composite_output_layers as _add_composite_output_layers,
    _composite_dependency_storage_ref as _composite_dependency_storage_ref,
    _link_composite_dependency_surface as _link_composite_dependency_surface,
)
from memory.graph.sync_pkg.composite_dependency_target import (
    _add_dashboard_graph as _add_dashboard_graph,
    _composite_dependency_target as _composite_dependency_target,
    _link_config_artifact as _link_config_artifact,
)
from memory.graph.sync_pkg.composite_group_field_entries import (
    _add_composite_seed_surface as _add_composite_seed_surface,
    _composite_group_field_entries as _composite_group_field_entries,
)
from memory.graph.sync_pkg.composite_output_storage_ref import (
    _add_composite_output_field_nodes as _add_composite_output_field_nodes,
    _add_composite_output_surface as _add_composite_output_surface,
    _base_pipeline_storage_config as _base_pipeline_storage_config,
    _composite_output_storage_ref as _composite_output_storage_ref,
)
from memory.graph.sync_pkg.composite_pipeline_dependency_keys import (
    _build_normalization_pipeline_evidence as _build_normalization_pipeline_evidence,
    _composite_pipeline_dependency_keys as _composite_pipeline_dependency_keys,
)
from memory.graph.sync_pkg.composite_pipeline_name import (
    _add_composite_pipeline_surface as _add_composite_pipeline_surface,
    _composite_pipeline_name as _composite_pipeline_name,
)
from memory.graph.sync_pkg.composite_seed_pipeline_name import (
    _add_pipeline_normalization_edges as _add_pipeline_normalization_edges,
    _composite_dependency_pipeline_keys as _composite_dependency_pipeline_keys,
    _composite_seed_pipeline_name as _composite_seed_pipeline_name,
)
from memory.graph.sync_pkg.composite_seed_storage_ref import (
    _add_composite_dependency_surfaces as _add_composite_dependency_surfaces,
    _composite_seed_storage_ref as _composite_seed_storage_ref,
    _link_composite_seed_surface as _link_composite_seed_surface,
)
from memory.graph.sync_pkg.contains_any import (
    _WORKFLOW_GATE_RULES as _WORKFLOW_GATE_RULES,
    _add_workflow_call_entrypoint as _add_workflow_call_entrypoint,
    _contains_any as _contains_any,
    _enrich_workflow_surface as _enrich_workflow_surface,
    _workflow_family as _workflow_family,
    _workflow_job_surface_metadata as _workflow_job_surface_metadata,
)
from memory.graph.sync_pkg.contract_dependency_module_key import (
    _contract_dependency_module_key as _contract_dependency_module_key,
    _link_contract_dependency_module as _link_contract_dependency_module,
    _link_contract_doc_dependencies as _link_contract_doc_dependencies,
)
from memory.graph.sync_pkg.contract_dependency_module_specs import (
    _contract_dependency_doc_specs as _contract_dependency_doc_specs,
    _contract_dependency_module_specs as _contract_dependency_module_specs,
)
from memory.graph.sync_pkg.contract_mapping_config import _contract_mapping_config as _contract_mapping_config
from memory.graph.sync_pkg.contract_mapping_values import (
    _add_contract_policy_config as _add_contract_policy_config,
    _contract_mapping_values as _contract_mapping_values,
    _link_contract_source_dependencies as _link_contract_source_dependencies,
)
from memory.graph.sync_pkg.contract_policy_config_path import (
    _add_contract_policy_artifact as _add_contract_policy_artifact,
    _contract_policy_config_path as _contract_policy_config_path,
    _contract_policy_fields as _contract_policy_fields,
)
from memory.graph.sync_pkg.contract_ref_identity import (
    _contract_ref_identity as _contract_ref_identity,
    _link_provider_regression_suite_tests as _link_provider_regression_suite_tests,
)
from memory.graph.sync_pkg.contract_registry_entries import (
    _add_contract_surfaces as _add_contract_surfaces,
    _contract_registry_entries as _contract_registry_entries,
)
from memory.graph.sync_pkg.contract_registry_payload import (
    _contract_registry_payload as _contract_registry_payload,
    _link_contract_dependencies as _link_contract_dependencies,
)
from memory.graph.sync_pkg.contract_source_prefixes import (
    _add_published_contract_artifacts as _add_published_contract_artifacts,
    _contract_source_prefixes as _contract_source_prefixes,
)
from memory.graph.sync_pkg.contract_source_resolved_path import (
    _contract_source_resolved_path as _contract_source_resolved_path,
    _link_contract_imported_modules as _link_contract_imported_modules,
    _link_contract_source_module as _link_contract_source_module,
    _update_contract_schema_classes as _update_contract_schema_classes,
)
from memory.graph.sync_pkg.create_workflow_job_surface import (
    _add_workflow_action_surface as _add_workflow_action_surface,
    _create_workflow_job_surface as _create_workflow_job_surface,
    _link_reusable_job_workflow as _link_reusable_job_workflow,
)
from memory.graph.sync_pkg.critical_diff_issues import _critical_diff_issues as _critical_diff_issues
from memory.graph.sync_pkg.curated_policy_surfaces import CURATED_POLICY_SURFACES as CURATED_POLICY_SURFACES
from memory.graph.sync_pkg.curated_policy_surfaces_2 import (
    _add_policy_surface_entry as _add_policy_surface_entry,
    _curated_policy_surfaces as _curated_policy_surfaces,
)
from memory.graph.sync_pkg.curated_quality_gates import (
    CURATED_EXECUTION_PATHS as CURATED_EXECUTION_PATHS,
    CURATED_QUALITY_GATES as CURATED_QUALITY_GATES,
    _anchor_bucket_for_label as _anchor_bucket_for_label,
    _collect_analysis_anchor_nodes as _collect_analysis_anchor_nodes,
)
from memory.graph.sync_pkg.curated_script_clusters import (
    CURATED_SCRIPT_CLUSTERS as CURATED_SCRIPT_CLUSTERS,
    _analysis_family_for_source_path as _analysis_family_for_source_path,
    _analysis_keys_to_scan as _analysis_keys_to_scan,
    _analysis_package_name as _analysis_package_name,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    BIOETL_METRIC_PATTERN as BIOETL_METRIC_PATTERN,
    _dashboard_metric_index as _dashboard_metric_index,
    _dashboard_metrics_from_payload as _dashboard_metrics_from_payload,
    _dashboard_panel_stack as _dashboard_panel_stack,
    _dashboard_panel_target_metrics as _dashboard_panel_target_metrics,
    _extract_bioetl_metrics as _extract_bioetl_metrics,
    _nested_dashboard_panels as _nested_dashboard_panels,
    _path_contains_any_token as _path_contains_any_token,
)
from memory.graph.sync_pkg.default_batch_size import (
    ADR_DECISIONS_DIR as ADR_DECISIONS_DIR,
    CHEMBL_ACTIVITY_CONTRACT_REF as CHEMBL_ACTIVITY_CONTRACT_REF,
    CONTRACT_REGISTRY_RELATIVE_PATH as CONTRACT_REGISTRY_RELATIVE_PATH,
    CURATED_DOC_SOURCES as CURATED_DOC_SOURCES,
    DEFAULT_BATCH_SIZE as DEFAULT_BATCH_SIZE,
    DEFAULT_COMMON_PIPELINE_DASHBOARDS as DEFAULT_COMMON_PIPELINE_DASHBOARDS,
    DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS as DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS,
    DEFAULT_ENTITY_PIPELINE_DASHBOARDS as DEFAULT_ENTITY_PIPELINE_DASHBOARDS,
    DEFAULT_LEGACY_REPORT_PATH as DEFAULT_LEGACY_REPORT_PATH,
    DEFAULT_PIPELINE_RUNTIME_PATHS as DEFAULT_PIPELINE_RUNTIME_PATHS,
    DEFAULT_PIPELINE_VALIDATION_GATES as DEFAULT_PIPELINE_VALIDATION_GATES,
    DOCS_VERIFICATION_GUIDE_PATH as DOCS_VERIFICATION_GUIDE_PATH,
    DOC_ARCHITECTURE_DIAGRAMS_HUB as DOC_ARCHITECTURE_DIAGRAMS_HUB,
    DOC_DIAGRAM_TOOLING_README as DOC_DIAGRAM_TOOLING_README,
    DOC_GRAFANA_DASHBOARDS_JSON as DOC_GRAFANA_DASHBOARDS_JSON,
    EFFECTIVE_CONFIG_ARTIFACT_REF as EFFECTIVE_CONFIG_ARTIFACT_REF,
    GATE_CONFIG_VALIDATION as GATE_CONFIG_VALIDATION,
    GATE_DIAGRAM_QUALITY as GATE_DIAGRAM_QUALITY,
    GATE_DOCS_VERIFICATION as GATE_DOCS_VERIFICATION,
    GATE_MYPY_STRICT as GATE_MYPY_STRICT,
    GATE_NEO4J_ONTOLOGY_INVARIANTS as GATE_NEO4J_ONTOLOGY_INVARIANTS,
    GATE_PRETEST_GUARDRAILS as GATE_PRETEST_GUARDRAILS,
    GITHUB_WORKFLOWS_PREFIX as GITHUB_WORKFLOWS_PREFIX,
    GOVERNANCE_DECISIONS_SUMMARY_PATH as GOVERNANCE_DECISIONS_SUMMARY_PATH,
    INTEGRATION_VCR_POLICY_PATH as INTEGRATION_VCR_POLICY_PATH,
    KNOWN_LAYERS as KNOWN_LAYERS,
    MANIFEST_ID_TEMPLATE as MANIFEST_ID_TEMPLATE,
    PORTS_FACADE_SOURCE_PATH as PORTS_FACADE_SOURCE_PATH,
    RULES_DOC_PATH as RULES_DOC_PATH,
    RUN_ID_TEMPLATE as RUN_ID_TEMPLATE,
    RUN_LEDGER_ARTIFACT_REF as RUN_LEDGER_ARTIFACT_REF,
    RUN_MANIFEST_ARTIFACT_REF as RUN_MANIFEST_ARTIFACT_REF,
    RUN_MANIFEST_INSPECTION_DOC_PATH as RUN_MANIFEST_INSPECTION_DOC_PATH,
    RUN_MANIFEST_LEDGER_DOC_PATH as RUN_MANIFEST_LEDGER_DOC_PATH,
    TESTING_GUIDE_PATH as TESTING_GUIDE_PATH,
    TEST_MATRIX_CONFIG_PATH as TEST_MATRIX_CONFIG_PATH,
    TEST_SURFACES as TEST_SURFACES,
    TEST_SURFACE_ARCHITECTURE as TEST_SURFACE_ARCHITECTURE,
    TEST_SURFACE_E2E as TEST_SURFACE_E2E,
    TEST_SURFACE_INTEGRATION as TEST_SURFACE_INTEGRATION,
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH as TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
    YAML_FILE_GLOB as YAML_FILE_GLOB,
)
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _DOCS_DRIFT_TEXT_EXTENSIONS as _DOCS_DRIFT_TEXT_EXTENSIONS,
    _DOCS_REFERENCE_ALLOWED_PREFIXES as _DOCS_REFERENCE_ALLOWED_PREFIXES,
    _DOC_LIKE_LABELS as _DOC_LIKE_LABELS,
    _heading_anchor_slug as _heading_anchor_slug,
    _is_docs_drift_source_candidate as _is_docs_drift_source_candidate,
    _trim_docs_reference_candidate as _trim_docs_reference_candidate,
)
from memory.graph.sync_pkg.docs_reference_exact_candidates import (
    _docs_reference_exact_candidates as _docs_reference_exact_candidates,
    _resolve_claim_targets as _resolve_claim_targets,
)
from memory.graph.sync_pkg.duplication_analysis_config import (
    _duplication_analysis_config as _duplication_analysis_config,
)
from memory.graph.sync_pkg.duplication_cluster_groups import (
    _add_duplication_cluster_node as _add_duplication_cluster_node,
    _duplication_cluster_groups as _duplication_cluster_groups,
    _link_duplication_cluster_members as _link_duplication_cluster_members,
    _link_same_shape_members as _link_same_shape_members,
)
from memory.graph.sync_pkg.duplication_cluster_thresholds import (
    _add_complexity_analysis_surfaces as _add_complexity_analysis_surfaces,
    _add_retirement_analysis_surfaces as _add_retirement_analysis_surfaces,
    _duplication_cluster_thresholds as _duplication_cluster_thresholds,
)
from memory.graph.sync_pkg.emit_normalization_batch_progress import (
    _emit_normalization_batch_progress as _emit_normalization_batch_progress,
    _normalization_batch_summary as _normalization_batch_summary,
)
from memory.graph.sync_pkg.empty_normalization_evidence_payload import (
    _accumulate_field_matrix_evidence as _accumulate_field_matrix_evidence,
    _empty_normalization_evidence_payload as _empty_normalization_evidence_payload,
    _enrich_registry_normalization_evidence as _enrich_registry_normalization_evidence,
    _finalize_normalization_evidence_defaults as _finalize_normalization_evidence_defaults,
)
from memory.graph.sync_pkg.entity_config_identity import (
    _add_composite_config_surfaces as _add_composite_config_surfaces,
    _entity_config_identity as _entity_config_identity,
)
from memory.graph.sync_pkg.entity_config_paths import (
    _add_entity_config_surface as _add_entity_config_surface,
    _entity_config_paths as _entity_config_paths,
)
from memory.graph.sync_pkg.entity_pipeline_contract_target import (
    _entity_pipeline_contract_target as _entity_pipeline_contract_target,
)
from memory.graph.sync_pkg.entity_pipeline_contract_tests import (
    _entity_pipeline_contract_tests as _entity_pipeline_contract_tests,
)
from memory.graph.sync_pkg.entity_pipeline_identity import (
    _add_entity_pipeline_surface as _add_entity_pipeline_surface,
    _entity_pipeline_identity as _entity_pipeline_identity,
    _link_entity_pipeline_dependencies as _link_entity_pipeline_dependencies,
)
from memory.graph.sync_pkg.entity_pipeline_node_identity import (
    _entity_pipeline_node_identity as _entity_pipeline_node_identity,
    _provider_pipeline_test_index as _provider_pipeline_test_index,
)
from memory.graph.sync_pkg.entity_pipeline_test_index import _entity_pipeline_test_index as _entity_pipeline_test_index
from memory.graph.sync_pkg.entity_storage_context import _entity_storage_context as _entity_storage_context
from memory.graph.sync_pkg.entity_storage_promotion_pairs import (
    _classify_projected_storage_fields as _classify_projected_storage_fields,
    _entity_storage_promotion_pairs as _entity_storage_promotion_pairs,
    _link_storage_layer_promotion as _link_storage_layer_promotion,
)
from memory.graph.sync_pkg.evaluate_complexity_surface import (
    _evaluate_complexity_surface as _evaluate_complexity_surface,
)
from memory.graph.sync_pkg.existing_snapshot_nodes import (
    _existing_snapshot_nodes as _existing_snapshot_nodes,
    _selected_alert_dashboards as _selected_alert_dashboards,
)
from memory.graph.sync_pkg.extract_code_duplication_surfaces import (
    _extract_code_duplication_surfaces as _extract_code_duplication_surfaces,
)
from memory.graph.sync_pkg.fast_analysis_scope import (
    _critical_analysis_audit_issues as _critical_analysis_audit_issues,
    _fast_analysis_scope as _fast_analysis_scope,
)
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _active_critical_names as _active_critical_names,
    _fast_analysis_live_counts as _fast_analysis_live_counts,
    _fast_analysis_live_summary as _fast_analysis_live_summary,
    _fast_analysis_snapshot_counts as _fast_analysis_snapshot_counts,
    _fast_audit_snapshot_payload as _fast_audit_snapshot_payload,
)
from memory.graph.sync_pkg.file_structure import (
    DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES as DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES,
    DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES as DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES,
    DEFAULT_FILE_STRUCTURE_REPO_ZONES as DEFAULT_FILE_STRUCTURE_REPO_ZONES,
    _file_structure_config as _file_structure_config,
)
from memory.graph.sync_pkg.file_structure_zone_roots import (
    _add_file_structure_zones as _add_file_structure_zones,
    _file_structure_zone_roots as _file_structure_zone_roots,
)
from memory.graph.sync_pkg.git_history import (
    _git_chunk_commit_ages as _git_chunk_commit_ages,
    _git_chunk_tracked_paths as _git_chunk_tracked_paths,
    _git_last_commit_age_days as _git_last_commit_age_days,
    _git_last_commit_age_days_bulk as _git_last_commit_age_days_bulk,
    _parse_git_chunk_age_output as _parse_git_chunk_age_output,
    _run_git_history_subprocess as _run_git_history_subprocess,
)
from memory.graph.sync_pkg.governance_policy_definitions import (
    _governance_policy_definitions as _governance_policy_definitions,
    _governance_policy_spec as _governance_policy_spec,
)
from memory.graph.sync_pkg.governance_policy_targets import _governance_policy_targets as _governance_policy_targets
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _add_layer_topology as _add_layer_topology,
    _add_runtime_layer_families as _add_runtime_layer_families,
    _add_runtime_layer_modules as _add_runtime_layer_modules,
    _add_runtime_layer_surface as _add_runtime_layer_surface,
    _governance_summary_table_specs as _governance_summary_table_specs,
    _runtime_module_family_key as _runtime_module_family_key,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _alert_surface_nodes as _alert_surface_nodes,
    _governance_target_groups as _governance_target_groups,
    _link_policy_governance_group as _link_policy_governance_group,
    _pipeline_dashboard_targets as _pipeline_dashboard_targets,
    _pipeline_operational_section as _pipeline_operational_section,
)
# fmt: on

__all__ = [name for name in globals() if not name.startswith("__")]
