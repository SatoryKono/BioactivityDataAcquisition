#!/usr/bin/env python3
"""Build and optionally sync the canonical deterministic BioETL graph into Neo4j."""

from __future__ import annotations

import os
import re
import shutil as shutil  # re-exported via __all__
import sys
from collections.abc import Callable, Iterable, Mapping, Set
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TypeVar, cast

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
    load_contract_registry_payload,
)
from memory.graph.sync_pkg._core_ast import (
    _CONTROL_FLOW_NODES as _CONTROL_FLOW_NODES,
)
from memory.graph.sync_pkg._core_ast import _base_name as _base_name
from memory.graph.sync_pkg._core_ast import (
    _callable_ast_node_count as _callable_ast_node_count,
)
from memory.graph.sync_pkg._core_ast import (
    _callable_branch_count as _callable_branch_count,
)
from memory.graph.sync_pkg._core_ast import (
    _callable_call_count as _callable_call_count,
)
from memory.graph.sync_pkg._core_ast import (
    _callable_helper_call_count as _callable_helper_call_count,
)
from memory.graph.sync_pkg._core_ast import (
    _callable_max_nesting_depth as _callable_max_nesting_depth,
)
from memory.graph.sync_pkg._core_ast import (
    _dataframe_model_class_names as _dataframe_model_class_names,
)
from memory.graph.sync_pkg._core_ast import (
    _imported_repo_modules as _imported_repo_modules,
)
from memory.graph.sync_pkg._core_ast import _imported_symbols as _imported_symbols
from memory.graph.sync_pkg._core_ast import (
    _looks_like_dataframe_model_class as _looks_like_dataframe_model_class,
)
from memory.graph.sync_pkg._core_ast import (
    _matching_imported_module_names as _matching_imported_module_names,
)
from memory.graph.sync_pkg._core_ast import (
    _normalized_callable_hash as _normalized_callable_hash,
)
from memory.graph.sync_pkg._core_ast import _parse_python_ast as _parse_python_ast
from memory.graph.sync_pkg._core_ast import (
    _protocol_class_names as _protocol_class_names,
)
from memory.graph.sync_pkg._core_ast import _signature_hash as _signature_hash

# AUD-001 slice 1: extracted kernels, re-exported to preserve the public surface.
from memory.graph.sync_pkg._core_cli import (
    _export_snapshot_if_requested as _export_snapshot_if_requested,
)
from memory.graph.sync_pkg._core_cli import (
    _normalization_operation_count as _normalization_operation_count,
)
from memory.graph.sync_pkg._core_cli import _parser as _parser
from memory.graph.sync_pkg._core_cli import (
    _print_snapshot_stats as _print_snapshot_stats,
)
from memory.graph.sync_pkg._core_cli import _report_payload as _report_payload
from memory.graph.sync_pkg._core_cli import (
    _run_apply_normalization_evidence_only as _run_apply_normalization_evidence_only,
)
from memory.graph.sync_pkg._core_cli import _run_snapshot_cli as _run_snapshot_cli
from memory.graph.sync_pkg._core_cli import (
    _selection_from_args as _selection_from_args,
)
from memory.graph.sync_pkg._core_cli import (
    _snapshot_operation_count as _snapshot_operation_count,
)
from memory.graph.sync_pkg._core_cli import (
    _sync_snapshot_if_requested as _sync_snapshot_if_requested,
)
from memory.graph.sync_pkg._core_cli import _validate_cli_args as _validate_cli_args
from memory.graph.sync_pkg._core_cli import _write_json as _write_json
from memory.graph.sync_pkg._core_cli import (
    _write_report_if_requested as _write_report_if_requested,
)
from memory.graph.sync_pkg._core_cli import main as main
from memory.graph.sync_pkg._core_convert import (
    _DOCS_DRIFT_EXCLUDED_PREFIXES as _DOCS_DRIFT_EXCLUDED_PREFIXES,
)
from memory.graph.sync_pkg._core_convert import GITHUB_DIR as GITHUB_DIR
from memory.graph.sync_pkg._core_convert import GITHUB_PATH_PREFIX as GITHUB_PATH_PREFIX
from memory.graph.sync_pkg._core_convert import YAML_SUFFIX as YAML_SUFFIX
from memory.graph.sync_pkg._core_convert import _as_iterable as _as_iterable
from memory.graph.sync_pkg._core_convert import _as_mapping as _as_mapping
from memory.graph.sync_pkg._core_convert import _as_string_list as _as_string_list
from memory.graph.sync_pkg._core_convert import _coerce_float as _coerce_float
from memory.graph.sync_pkg._core_convert import _coerce_int as _coerce_int
from memory.graph.sync_pkg._core_convert import (
    _git_cached_commit_ages as _git_cached_commit_ages,
)
from memory.graph.sync_pkg._core_convert import (
    _is_claim_candidate as _is_claim_candidate,
)
from memory.graph.sync_pkg._core_convert import (
    _is_dataframe_model_base as _is_dataframe_model_base,
)
from memory.graph.sync_pkg._core_convert import (
    _is_doc_artifact_file as _is_doc_artifact_file,
)
from memory.graph.sync_pkg._core_convert import (
    _is_excluded_docs_drift_prefix as _is_excluded_docs_drift_prefix,
)
from memory.graph.sync_pkg._core_convert import (
    _is_ignored_repo_path as _is_ignored_repo_path,
)
from memory.graph.sync_pkg._core_convert import _is_protocol_base as _is_protocol_base
from memory.graph.sync_pkg._core_convert import (
    _module_dotted_name as _module_dotted_name,
)
from memory.graph.sync_pkg._core_convert import (
    _normalize_cli_command_name as _normalize_cli_command_name,
)
from memory.graph.sync_pkg._core_convert import (
    _normalize_docs_glob_candidate as _normalize_docs_glob_candidate,
)
from memory.graph.sync_pkg._core_convert import (
    _normalize_env_value as _normalize_env_value,
)
from memory.graph.sync_pkg._core_convert import (
    _normalize_repo_relative_path as _normalize_repo_relative_path,
)
from memory.graph.sync_pkg._core_convert import (
    _normalize_workflow_matrix_axis_name as _normalize_workflow_matrix_axis_name,
)
from memory.graph.sync_pkg._core_convert import (
    _normalized_alert_selector as _normalized_alert_selector,
)
from memory.graph.sync_pkg._core_convert import (
    _normalized_text_list as _normalized_text_list,
)
from memory.graph.sync_pkg._core_convert import _optional_text as _optional_text
from memory.graph.sync_pkg._core_convert import _read_text as _read_text
from memory.graph.sync_pkg._core_convert import _rel_path as _rel_path
from memory.graph.sync_pkg._core_convert import (
    _resolve_git_executable as _resolve_git_executable,
)
from memory.graph.sync_pkg._core_convert import _resolve_repo_path as _resolve_repo_path
from memory.graph.sync_pkg._core_models import (
    AlertDashboardConfig as AlertDashboardConfig,
)
from memory.graph.sync_pkg._core_models import AlertRuleContext as AlertRuleContext
from memory.graph.sync_pkg._core_models import (
    AlertRuleGroupContext as AlertRuleGroupContext,
)
from memory.graph.sync_pkg._core_models import AlertRuleSettings as AlertRuleSettings
from memory.graph.sync_pkg._core_models import (
    AlertRunbookContext as AlertRunbookContext,
)
from memory.graph.sync_pkg._core_models import AlertTargetInputs as AlertTargetInputs
from memory.graph.sync_pkg._core_models import AnalysisLabelSets as AnalysisLabelSets
from memory.graph.sync_pkg._core_models import ClaimLineContext as ClaimLineContext
from memory.graph.sync_pkg._core_models import (
    ComplexityAnalysisConfig as ComplexityAnalysisConfig,
)
from memory.graph.sync_pkg._core_models import ComplexityMetrics as ComplexityMetrics
from memory.graph.sync_pkg._core_models import (
    ComplexityScoreInputs as ComplexityScoreInputs,
)
from memory.graph.sync_pkg._core_models import (
    ContractMappingConfig as ContractMappingConfig,
)
from memory.graph.sync_pkg._core_models import (
    ControlPlaneArtifactSpec as ControlPlaneArtifactSpec,
)
from memory.graph.sync_pkg._core_models import EntityScope as EntityScope
from memory.graph.sync_pkg._core_models import (
    GroupedStatementFailureContext as GroupedStatementFailureContext,
)
from memory.graph.sync_pkg._core_models import JsonScalar as JsonScalar
from memory.graph.sync_pkg._core_models import JsonValue as JsonValue
from memory.graph.sync_pkg._core_models import NodeKey as NodeKey
from memory.graph.sync_pkg._core_models import (
    PortSurfaceDescriptor as PortSurfaceDescriptor,
)
from memory.graph.sync_pkg._core_models import (
    RetirementAnalysisConfig as RetirementAnalysisConfig,
)
from memory.graph.sync_pkg._core_models import (
    RetirementScoreInputs as RetirementScoreInputs,
)
from memory.graph.sync_pkg._core_models import SchemaFieldSpec as SchemaFieldSpec
from memory.graph.sync_pkg._core_models import SnapshotSelection as SnapshotSelection
from memory.graph.sync_pkg._core_models import StorageSurfaceSpec as StorageSurfaceSpec
from memory.graph.sync_pkg._core_models import SyncApplyOptions as SyncApplyOptions
from memory.graph.sync_pkg._core_models import _ShapeNormalizer as _ShapeNormalizer
from memory.graph.sync_pkg.add_adapter_impl_surface import (
    _add_adapter_impl_surface as _add_adapter_impl_surface,
)
from memory.graph.sync_pkg.add_adapter_impl_surface import (
    _add_adapter_module_surface as _add_adapter_module_surface,
)
from memory.graph.sync_pkg.add_adapter_impl_surface import (
    _link_adapter_ports as _link_adapter_ports,
)
from memory.graph.sync_pkg.add_claim_target_relation import (
    _add_claim_fallback_target as _add_claim_fallback_target,
)
from memory.graph.sync_pkg.add_claim_target_relation import (
    _add_claim_target_relation as _add_claim_target_relation,
)
from memory.graph.sync_pkg.add_claim_token_targets import (
    _add_claim_token_targets as _add_claim_token_targets,
)
from memory.graph.sync_pkg.add_cli_command_surface import (
    _add_cli_command_surface as _add_cli_command_surface,
)
from memory.graph.sync_pkg.add_cli_command_surface import (
    _add_cli_option_surfaces as _add_cli_option_surfaces,
)
from memory.graph.sync_pkg.add_cli_command_surface import (
    _cli_command_source_path as _cli_command_source_path,
)
from memory.graph.sync_pkg.add_cli_command_surface import (
    _cli_execution_indexes as _cli_execution_indexes,
)
from memory.graph.sync_pkg.add_cli_command_surface import (
    _link_cli_command_execution as _link_cli_command_execution,
)
from memory.graph.sync_pkg.add_cli_command_surface import (
    _link_cli_command_side_effects as _link_cli_command_side_effects,
)
from memory.graph.sync_pkg.add_contract_doc_dependency import (
    _add_contract_doc_dependency as _add_contract_doc_dependency,
)
from memory.graph.sync_pkg.add_contract_doc_dependency import (
    _add_contract_entry_surface as _add_contract_entry_surface,
)
from memory.graph.sync_pkg.add_contract_doc_dependency import (
    _contract_dependency_doc_path as _contract_dependency_doc_path,
)
from memory.graph.sync_pkg.add_curated_cluster_readme import (
    _add_curated_cluster_entrypoint as _add_curated_cluster_entrypoint,
)
from memory.graph.sync_pkg.add_curated_cluster_readme import (
    _add_curated_cluster_execution as _add_curated_cluster_execution,
)
from memory.graph.sync_pkg.add_curated_cluster_readme import (
    _add_curated_cluster_readme as _add_curated_cluster_readme,
)
from memory.graph.sync_pkg.add_curated_doc_source import (
    _add_curated_doc_source as _add_curated_doc_source,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _add_curated_quality_gates as _add_curated_quality_gates,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _add_dashboard_surface as _add_dashboard_surface,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _add_execution_path_node as _add_execution_path_node,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _developer_workflow_readme as _developer_workflow_readme,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _link_execution_gate as _link_execution_gate,
)
from memory.graph.sync_pkg.add_duplication_callable_surface import (
    _add_duplication_callable_surface as _add_duplication_callable_surface,
)
from memory.graph.sync_pkg.add_duplication_callable_surface import (
    _duplication_callable_descriptor as _duplication_callable_descriptor,
)
from memory.graph.sync_pkg.add_entity_pipeline_surfaces import (
    _add_composite_pipeline_surfaces as _add_composite_pipeline_surfaces,
)
from memory.graph.sync_pkg.add_entity_pipeline_surfaces import (
    _add_entity_pipeline_surfaces as _add_entity_pipeline_surfaces,
)
from memory.graph.sync_pkg.add_package_topology_decisions_and_risks import (
    _add_package_topology_decisions_and_risks as _add_package_topology_decisions_and_risks,
)
from memory.graph.sync_pkg.add_pipeline_doc_edges import (
    _add_pipeline_doc_edges as _add_pipeline_doc_edges,
)
from memory.graph.sync_pkg.add_policy_surface import (
    _add_policy_artifact as _add_policy_artifact,
)
from memory.graph.sync_pkg.add_policy_surface import (
    _add_policy_surface as _add_policy_surface,
)
from memory.graph.sync_pkg.add_port_facade_surface import (
    _add_port_facade_surface as _add_port_facade_surface,
)
from memory.graph.sync_pkg.add_port_facade_surface import (
    _add_protocol_port_surface as _add_protocol_port_surface,
)
from memory.graph.sync_pkg.add_port_surfaces import (
    _add_port_surfaces as _add_port_surfaces,
)
from memory.graph.sync_pkg.add_repo_zone_directory_file import (
    _add_repo_zone_directory_file as _add_repo_zone_directory_file,
)
from memory.graph.sync_pkg.add_repo_zone_directory_files import (
    _add_repo_zone_directory_files as _add_repo_zone_directory_files,
)
from memory.graph.sync_pkg.add_repo_zone_file_surface import (
    _add_repo_zone_doc_artifact as _add_repo_zone_doc_artifact,
)
from memory.graph.sync_pkg.add_repo_zone_file_surface import (
    _add_repo_zone_file_surface as _add_repo_zone_file_surface,
)
from memory.graph.sync_pkg.add_runtime_evidence_surface import (
    _add_runtime_evidence_surface as _add_runtime_evidence_surface,
)
from memory.graph.sync_pkg.add_runtime_evidence_surface import (
    _link_run_instance_surface as _link_run_instance_surface,
)
from memory.graph.sync_pkg.add_secret_requirements import (
    _add_secret_requirements as _add_secret_requirements,
)
from memory.graph.sync_pkg.add_secret_requirements import (
    _add_workflow_output_surface as _add_workflow_output_surface,
)
from memory.graph.sync_pkg.add_secret_requirements import (
    _add_workflow_outputs as _add_workflow_outputs,
)
from memory.graph.sync_pkg.add_test_suite_surface import (
    _add_test_artifact_surface as _add_test_artifact_surface,
)
from memory.graph.sync_pkg.add_test_suite_surface import (
    _add_test_suite_surface as _add_test_suite_surface,
)
from memory.graph.sync_pkg.add_workflow_file_surface import (
    _add_workflow_file_surface as _add_workflow_file_surface,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _adr_constraint_candidates as _adr_constraint_candidates,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _docs_command_pattern as _docs_command_pattern,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _docs_drift_sources as _docs_drift_sources,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _docs_path_pattern as _docs_path_pattern,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _normalize_docs_drift_source_path as _normalize_docs_drift_source_path,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _read_docs_drift_text as _read_docs_drift_text,
)
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _add_alert_rules_artifact as _add_alert_rules_artifact,
)
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _add_alert_surface_node as _add_alert_surface_node,
)
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _alert_rule_file_payload as _alert_rule_file_payload,
)
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _alert_rule_groups as _alert_rule_groups,
)
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _link_workflow_job_reusable_target as _link_workflow_job_reusable_target,
)
from memory.graph.sync_pkg.alert_runbook_path import (
    _add_alert_runbook_doc as _add_alert_runbook_doc,
)
from memory.graph.sync_pkg.alert_runbook_path import (
    _add_governance_edges as _add_governance_edges,
)
from memory.graph.sync_pkg.alert_runbook_path import (
    _alert_runbook_path as _alert_runbook_path,
)
from memory.graph.sync_pkg.alert_targets import (
    _RUNTIME_DIMENSIONS as _RUNTIME_DIMENSIONS,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_dashboard_config as _alert_dashboard_config,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_dashboard_fallback_groups as _alert_dashboard_fallback_groups,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_dashboard_fallbacks as _alert_dashboard_fallbacks,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_override_maps as _alert_override_maps,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_pipeline_kind_override as _alert_pipeline_kind_override,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_rule_overrides as _alert_rule_overrides,
)
from memory.graph.sync_pkg.alert_targets import (
    _alert_rule_settings as _alert_rule_settings,
)
from memory.graph.sync_pkg.alert_targets import (
    _alerts_config_section as _alerts_config_section,
)
from memory.graph.sync_pkg.alert_targets import (
    _all_contract_targets as _all_contract_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _all_pipeline_targets as _all_pipeline_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _configured_alert_rule as _configured_alert_rule,
)
from memory.graph.sync_pkg.alert_targets import (
    _configured_dashboard_targets as _configured_dashboard_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _contract_targets_for_alert as _contract_targets_for_alert,
)
from memory.graph.sync_pkg.alert_targets import (
    _dashboard_target_keys as _dashboard_target_keys,
)
from memory.graph.sync_pkg.alert_targets import (
    _entity_alert_signal_detected as _entity_alert_signal_detected,
)
from memory.graph.sync_pkg.alert_targets import (
    _mapped_contract_targets as _mapped_contract_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _merged_alert_dashboard_targets as _merged_alert_dashboard_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _metric_dashboard_targets as _metric_dashboard_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _pipeline_targets_for_alert as _pipeline_targets_for_alert,
)
from memory.graph.sync_pkg.alert_targets import (
    _pipeline_targets_for_alert_mode as _pipeline_targets_for_alert_mode,
)
from memory.graph.sync_pkg.alert_targets import (
    _pipeline_targets_matching_kind as _pipeline_targets_matching_kind,
)
from memory.graph.sync_pkg.alert_targets import (
    _provider_alert_signal_detected as _provider_alert_signal_detected,
)
from memory.graph.sync_pkg.alert_targets import (
    _provider_targets_for_alert as _provider_targets_for_alert,
)
from memory.graph.sync_pkg.alert_targets import (
    _provider_targets_requested as _provider_targets_requested,
)
from memory.graph.sync_pkg.alert_targets import _raw_alert_targets as _raw_alert_targets
from memory.graph.sync_pkg.alert_targets import (
    _runtime_dimensions as _runtime_dimensions,
)
from memory.graph.sync_pkg.alert_targets import (
    _select_alert_dashboards as _select_alert_dashboards,
)
from memory.graph.sync_pkg.alert_targets import (
    _select_alert_targets as _select_alert_targets,
)
from memory.graph.sync_pkg.alert_targets import (
    _sorted_alert_targets as _sorted_alert_targets,
)
from memory.graph.sync_pkg.alert_targets import _sorted_node_keys as _sorted_node_keys
from memory.graph.sync_pkg.alert_targets import (
    _sorted_unique_node_keys as _sorted_unique_node_keys,
)
from memory.graph.sync_pkg.analysis_source import (
    ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS as ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS,
)
from memory.graph.sync_pkg.analysis_source import (
    _analysis_read_source_text as _analysis_read_source_text,
)
from memory.graph.sync_pkg.analysis_source import (
    _build_surface_relation_indexes as _build_surface_relation_indexes,
)
from memory.graph.sync_pkg.analysis_source import (
    _read_analysis_source_text as _read_analysis_source_text,
)
from memory.graph.sync_pkg.apply_anchors import _anchor_count_rows as _anchor_count_rows
from memory.graph.sync_pkg.apply_anchors import (
    _ensure_targeted_apply_prerequisites as _ensure_targeted_apply_prerequisites,
)
from memory.graph.sync_pkg.apply_anchors import (
    _missing_anchor_keys_in_chunk as _missing_anchor_keys_in_chunk,
)
from memory.graph.sync_pkg.apply_anchors import (
    _missing_anchor_keys_message as _missing_anchor_keys_message,
)
from memory.graph.sync_pkg.apply_anchors import (
    _missing_anchor_labels as _missing_anchor_labels,
)
from memory.graph.sync_pkg.apply_anchors import (
    _missing_anchor_labels_message as _missing_anchor_labels_message,
)
from memory.graph.sync_pkg.apply_anchors import (
    _missing_managed_anchor_keys as _missing_managed_anchor_keys,
)
from memory.graph.sync_pkg.apply_anchors import (
    _targeted_apply_external_anchor_keys as _targeted_apply_external_anchor_keys,
)
from memory.graph.sync_pkg.apply_anchors import (
    _targeted_apply_required_anchor_labels as _targeted_apply_required_anchor_labels,
)
from memory.graph.sync_pkg.apply_groups import (
    ANALYSIS_NODE_LABELS as ANALYSIS_NODE_LABELS,
)
from memory.graph.sync_pkg.apply_groups import (
    ANALYSIS_RELATION_TYPES as ANALYSIS_RELATION_TYPES,
)
from memory.graph.sync_pkg.apply_groups import (
    DEFAULT_LEGACY_PRUNE_LABELS as DEFAULT_LEGACY_PRUNE_LABELS,
)
from memory.graph.sync_pkg.apply_groups import (
    _analysis_batch_size as _analysis_batch_size,
)
from memory.graph.sync_pkg.apply_groups import (
    _analysis_node_batch_size as _analysis_node_batch_size,
)
from memory.graph.sync_pkg.apply_groups import (
    _analysis_relation_batch_size as _analysis_relation_batch_size,
)
from memory.graph.sync_pkg.apply_groups import (
    _apply_snapshot_statement_groups as _apply_snapshot_statement_groups,
)
from memory.graph.sync_pkg.apply_groups import (
    _delete_managed_wave_batch_size as _delete_managed_wave_batch_size,
)
from memory.graph.sync_pkg.apply_groups import (
    _delete_managed_wave_if_requested as _delete_managed_wave_if_requested,
)
from memory.graph.sync_pkg.apply_groups import (
    _execute_prune_stale_statements as _execute_prune_stale_statements,
)
from memory.graph.sync_pkg.apply_groups import (
    _legacy_or_default_batch_size as _legacy_or_default_batch_size,
)
from memory.graph.sync_pkg.apply_groups import (
    _node_statement_groups as _node_statement_groups,
)
from memory.graph.sync_pkg.apply_groups import _partition_groups as _partition_groups
from memory.graph.sync_pkg.apply_groups import (
    _prune_managed_graph_if_requested as _prune_managed_graph_if_requested,
)
from memory.graph.sync_pkg.apply_groups import (
    _relation_statement_groups as _relation_statement_groups,
)
from memory.graph.sync_pkg.apply_groups import (
    _reset_managed_relations_if_requested as _reset_managed_relations_if_requested,
)
from memory.graph.sync_pkg.apply_groups import (
    _resolved_sync_apply_options as _resolved_sync_apply_options,
)
from memory.graph.sync_pkg.apply_groups import (
    _selection_from_legacy_kwargs as _selection_from_legacy_kwargs,
)
from memory.graph.sync_pkg.apply_groups import _statement_groups as _statement_groups
from memory.graph.sync_pkg.apply_groups import (
    _verification_sync_run as _verification_sync_run,
)
from memory.graph.sync_pkg.apply_runtime import _batched as _batched
from memory.graph.sync_pkg.apply_runtime import (
    _execute_grouped_statements as _execute_grouped_statements,
)
from memory.graph.sync_pkg.apply_runtime import (
    _execute_statement_batch as _execute_statement_batch,
)
from memory.graph.sync_pkg.apply_runtime import (
    _raise_grouped_statement_failure as _raise_grouped_statement_failure,
)
from memory.graph.sync_pkg.apply_runtime import (
    _statement_failure_context as _statement_failure_context,
)
from memory.graph.sync_pkg.apply_verify import (
    CRITICAL_ANALYSIS_NODE_LABELS as CRITICAL_ANALYSIS_NODE_LABELS,
)
from memory.graph.sync_pkg.apply_verify import (
    CRITICAL_ANALYSIS_RELATION_TYPES as CRITICAL_ANALYSIS_RELATION_TYPES,
)
from memory.graph.sync_pkg.apply_verify import (
    _active_group_names as _active_group_names,
)
from memory.graph.sync_pkg.apply_verify import (
    _critical_analysis_group_counts as _critical_analysis_group_counts,
)
from memory.graph.sync_pkg.apply_verify import (
    _critical_analysis_mismatch_messages as _critical_analysis_mismatch_messages,
)
from memory.graph.sync_pkg.apply_verify import (
    _critical_analysis_retry_batch_size as _critical_analysis_retry_batch_size,
)
from memory.graph.sync_pkg.apply_verify import (
    _expected_group_counts as _expected_group_counts,
)
from memory.graph.sync_pkg.apply_verify import (
    _expected_group_mismatches as _expected_group_mismatches,
)
from memory.graph.sync_pkg.apply_verify import (
    _group_count_mismatches as _group_count_mismatches,
)
from memory.graph.sync_pkg.apply_verify import (
    _group_mismatch_messages as _group_mismatch_messages,
)
from memory.graph.sync_pkg.apply_verify import _group_names as _group_names
from memory.graph.sync_pkg.apply_verify import (
    _missing_group_names as _missing_group_names,
)
from memory.graph.sync_pkg.apply_verify import (
    _raise_analysis_group_mismatches as _raise_analysis_group_mismatches,
)
from memory.graph.sync_pkg.apply_verify import (
    _refresh_node_counts_if_retried as _refresh_node_counts_if_retried,
)
from memory.graph.sync_pkg.apply_verify import (
    _refresh_relation_counts_if_retried as _refresh_relation_counts_if_retried,
)
from memory.graph.sync_pkg.apply_verify import (
    _retry_critical_analysis_groups as _retry_critical_analysis_groups,
)
from memory.graph.sync_pkg.apply_verify import (
    _retry_critical_node_groups as _retry_critical_node_groups,
)
from memory.graph.sync_pkg.apply_verify import (
    _retry_critical_relation_groups as _retry_critical_relation_groups,
)
from memory.graph.sync_pkg.apply_verify import (
    _retry_missing_groups as _retry_missing_groups,
)
from memory.graph.sync_pkg.apply_verify import (
    _verify_expected_group_counts as _verify_expected_group_counts,
)
from memory.graph.sync_pkg.batch_pipeline_names import (
    _batch_pipeline_names as _batch_pipeline_names,
)
from memory.graph.sync_pkg.batch_pipeline_names import (
    _normalization_progress_payload as _normalization_progress_payload,
)
from memory.graph.sync_pkg.claim_target_tokens import (
    _claim_exact_candidates as _claim_exact_candidates,
)
from memory.graph.sync_pkg.claim_target_tokens import (
    _claim_target_tokens as _claim_target_tokens,
)
from memory.graph.sync_pkg.classify_silver_storage_fields import (
    _classify_gold_storage_fields as _classify_gold_storage_fields,
)
from memory.graph.sync_pkg.classify_silver_storage_fields import (
    _classify_silver_storage_fields as _classify_silver_storage_fields,
)
from memory.graph.sync_pkg.classify_silver_storage_fields import (
    _composite_group_fields as _composite_group_fields,
)
from memory.graph.sync_pkg.collect_duplication_class_descriptors import (
    _collect_duplication_class_descriptors as _collect_duplication_class_descriptors,
)
from memory.graph.sync_pkg.collect_duplication_class_descriptors import (
    _collect_duplication_function_descriptor as _collect_duplication_function_descriptor,
)
from memory.graph.sync_pkg.collect_duplication_class_descriptors import (
    _duplication_class_method_index as _duplication_class_method_index,
)
from memory.graph.sync_pkg.collect_duplication_descriptors_for_modu import (
    _collect_duplication_descriptors_for_module as _collect_duplication_descriptors_for_module,
)
from memory.graph.sync_pkg.complexity_analysis_label_sets import (
    _complexity_analysis_label_sets as _complexity_analysis_label_sets,
)
from memory.graph.sync_pkg.complexity_analysis_label_sets import (
    _complexity_surface_prerequisites as _complexity_surface_prerequisites,
)
from memory.graph.sync_pkg.complexity_blocker_context import (
    _add_pipeline_surfaces as _add_pipeline_surfaces,
)
from memory.graph.sync_pkg.complexity_blocker_context import (
    _complexity_blocker_context as _complexity_blocker_context,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _classify_complexity_candidate as _classify_complexity_candidate,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _complexity_marker_buckets as _complexity_marker_buckets,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _complexity_scores as _complexity_scores,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _configured_duplicate_families as _configured_duplicate_families,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _configured_node_keys as _configured_node_keys,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _link_existing_targets as _link_existing_targets,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _retirement_scores as _retirement_scores,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _add_cli_command_graph as _add_cli_command_graph,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _add_curated_execution_paths as _add_curated_execution_paths,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _add_quality_and_scripts as _add_quality_and_scripts,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _composite_config_dependency_entries as _composite_config_dependency_entries,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _link_composite_dependency as _link_composite_dependency,
)
from memory.graph.sync_pkg.composite_config_dependency_entries import (
    _link_composite_seed_dependency as _link_composite_seed_dependency,
)
from memory.graph.sync_pkg.composite_config_paths import (
    _add_composite_config_surface as _add_composite_config_surface,
)
from memory.graph.sync_pkg.composite_config_paths import (
    _composite_config_identity as _composite_config_identity,
)
from memory.graph.sync_pkg.composite_config_paths import (
    _composite_config_paths as _composite_config_paths,
)
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _add_composite_dependency_surface as _add_composite_dependency_surface,
)
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _add_composite_output_layers as _add_composite_output_layers,
)
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _composite_dependency_storage_ref as _composite_dependency_storage_ref,
)
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _link_composite_dependency_surface as _link_composite_dependency_surface,
)
from memory.graph.sync_pkg.composite_dependency_target import (
    _add_dashboard_graph as _add_dashboard_graph,
)
from memory.graph.sync_pkg.composite_dependency_target import (
    _composite_dependency_target as _composite_dependency_target,
)
from memory.graph.sync_pkg.composite_dependency_target import (
    _link_config_artifact as _link_config_artifact,
)
from memory.graph.sync_pkg.composite_group_field_entries import (
    _add_composite_seed_surface as _add_composite_seed_surface,
)
from memory.graph.sync_pkg.composite_group_field_entries import (
    _composite_group_field_entries as _composite_group_field_entries,
)
from memory.graph.sync_pkg.composite_output_storage_ref import (
    _add_composite_output_field_nodes as _add_composite_output_field_nodes,
)
from memory.graph.sync_pkg.composite_output_storage_ref import (
    _add_composite_output_surface as _add_composite_output_surface,
)
from memory.graph.sync_pkg.composite_output_storage_ref import (
    _base_pipeline_storage_config as _base_pipeline_storage_config,
)
from memory.graph.sync_pkg.composite_output_storage_ref import (
    _composite_output_storage_ref as _composite_output_storage_ref,
)
from memory.graph.sync_pkg.composite_pipeline_dependency_keys import (
    _build_normalization_pipeline_evidence as _build_normalization_pipeline_evidence,
)
from memory.graph.sync_pkg.composite_pipeline_dependency_keys import (
    _composite_pipeline_dependency_keys as _composite_pipeline_dependency_keys,
)
from memory.graph.sync_pkg.composite_pipeline_name import (
    _add_composite_pipeline_surface as _add_composite_pipeline_surface,
)
from memory.graph.sync_pkg.composite_pipeline_name import (
    _composite_pipeline_name as _composite_pipeline_name,
)
from memory.graph.sync_pkg.composite_seed_pipeline_name import (
    _add_pipeline_normalization_edges as _add_pipeline_normalization_edges,
)
from memory.graph.sync_pkg.composite_seed_pipeline_name import (
    _composite_dependency_pipeline_keys as _composite_dependency_pipeline_keys,
)
from memory.graph.sync_pkg.composite_seed_pipeline_name import (
    _composite_seed_pipeline_name as _composite_seed_pipeline_name,
)
from memory.graph.sync_pkg.composite_seed_storage_ref import (
    _add_composite_dependency_surfaces as _add_composite_dependency_surfaces,
)
from memory.graph.sync_pkg.composite_seed_storage_ref import (
    _composite_seed_storage_ref as _composite_seed_storage_ref,
)
from memory.graph.sync_pkg.composite_seed_storage_ref import (
    _link_composite_seed_surface as _link_composite_seed_surface,
)
from memory.graph.sync_pkg.contains_any import (
    _WORKFLOW_GATE_RULES as _WORKFLOW_GATE_RULES,
)
from memory.graph.sync_pkg.contains_any import (
    _add_workflow_call_entrypoint as _add_workflow_call_entrypoint,
)
from memory.graph.sync_pkg.contains_any import _contains_any as _contains_any
from memory.graph.sync_pkg.contains_any import (
    _enrich_workflow_surface as _enrich_workflow_surface,
)
from memory.graph.sync_pkg.contains_any import _workflow_family as _workflow_family
from memory.graph.sync_pkg.contains_any import (
    _workflow_job_surface_metadata as _workflow_job_surface_metadata,
)
from memory.graph.sync_pkg.contract_dependency_module_key import (
    _contract_dependency_module_key as _contract_dependency_module_key,
)
from memory.graph.sync_pkg.contract_dependency_module_key import (
    _link_contract_dependency_module as _link_contract_dependency_module,
)
from memory.graph.sync_pkg.contract_dependency_module_key import (
    _link_contract_doc_dependencies as _link_contract_doc_dependencies,
)
from memory.graph.sync_pkg.contract_dependency_module_specs import (
    _contract_dependency_doc_specs as _contract_dependency_doc_specs,
)
from memory.graph.sync_pkg.contract_dependency_module_specs import (
    _contract_dependency_module_specs as _contract_dependency_module_specs,
)
from memory.graph.sync_pkg.contract_mapping_values import (
    _add_contract_policy_config as _add_contract_policy_config,
)
from memory.graph.sync_pkg.contract_mapping_values import (
    _contract_mapping_values as _contract_mapping_values,
)
from memory.graph.sync_pkg.contract_mapping_values import (
    _link_contract_source_dependencies as _link_contract_source_dependencies,
)
from memory.graph.sync_pkg.contract_policy_config_path import (
    _add_contract_policy_artifact as _add_contract_policy_artifact,
)
from memory.graph.sync_pkg.contract_policy_config_path import (
    _contract_policy_config_path as _contract_policy_config_path,
)
from memory.graph.sync_pkg.contract_policy_config_path import (
    _contract_policy_fields as _contract_policy_fields,
)
from memory.graph.sync_pkg.contract_source_resolved_path import (
    _contract_source_resolved_path as _contract_source_resolved_path,
)
from memory.graph.sync_pkg.contract_source_resolved_path import (
    _link_contract_imported_modules as _link_contract_imported_modules,
)
from memory.graph.sync_pkg.contract_source_resolved_path import (
    _link_contract_source_module as _link_contract_source_module,
)
from memory.graph.sync_pkg.contract_source_resolved_path import (
    _update_contract_schema_classes as _update_contract_schema_classes,
)
from memory.graph.sync_pkg.create_workflow_job_surface import (
    _add_workflow_action_surface as _add_workflow_action_surface,
)
from memory.graph.sync_pkg.create_workflow_job_surface import (
    _create_workflow_job_surface as _create_workflow_job_surface,
)
from memory.graph.sync_pkg.create_workflow_job_surface import (
    _link_reusable_job_workflow as _link_reusable_job_workflow,
)
from memory.graph.sync_pkg.curated_policy_surfaces import (
    CURATED_POLICY_SURFACES as CURATED_POLICY_SURFACES,
)
from memory.graph.sync_pkg.curated_quality_gates import (
    CURATED_EXECUTION_PATHS as CURATED_EXECUTION_PATHS,
)
from memory.graph.sync_pkg.curated_quality_gates import (
    CURATED_QUALITY_GATES as CURATED_QUALITY_GATES,
)
from memory.graph.sync_pkg.curated_quality_gates import (
    _anchor_bucket_for_label as _anchor_bucket_for_label,
)
from memory.graph.sync_pkg.curated_quality_gates import (
    _collect_analysis_anchor_nodes as _collect_analysis_anchor_nodes,
)
from memory.graph.sync_pkg.curated_script_clusters import (
    CURATED_SCRIPT_CLUSTERS as CURATED_SCRIPT_CLUSTERS,
)
from memory.graph.sync_pkg.curated_script_clusters import (
    _analysis_family_for_source_path as _analysis_family_for_source_path,
)
from memory.graph.sync_pkg.curated_script_clusters import (
    _analysis_keys_to_scan as _analysis_keys_to_scan,
)
from memory.graph.sync_pkg.curated_script_clusters import (
    _analysis_package_name as _analysis_package_name,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    BIOETL_METRIC_PATTERN as BIOETL_METRIC_PATTERN,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _dashboard_metric_index as _dashboard_metric_index,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _dashboard_metrics_from_payload as _dashboard_metrics_from_payload,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _dashboard_panel_stack as _dashboard_panel_stack,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _dashboard_panel_target_metrics as _dashboard_panel_target_metrics,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _extract_bioetl_metrics as _extract_bioetl_metrics,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _nested_dashboard_panels as _nested_dashboard_panels,
)
from memory.graph.sync_pkg.dashboard_metrics import (
    _path_contains_any_token as _path_contains_any_token,
)
from memory.graph.sync_pkg.default_batch_size import (
    ADR_DECISIONS_DIR as ADR_DECISIONS_DIR,
)
from memory.graph.sync_pkg.default_batch_size import (
    CHEMBL_ACTIVITY_CONTRACT_REF as CHEMBL_ACTIVITY_CONTRACT_REF,
)
from memory.graph.sync_pkg.default_batch_size import (
    CONTRACT_REGISTRY_RELATIVE_PATH as CONTRACT_REGISTRY_RELATIVE_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    CURATED_DOC_SOURCES as CURATED_DOC_SOURCES,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_BATCH_SIZE as DEFAULT_BATCH_SIZE,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_COMMON_PIPELINE_DASHBOARDS as DEFAULT_COMMON_PIPELINE_DASHBOARDS,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS as DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_ENTITY_PIPELINE_DASHBOARDS as DEFAULT_ENTITY_PIPELINE_DASHBOARDS,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_LEGACY_REPORT_PATH as DEFAULT_LEGACY_REPORT_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_PIPELINE_RUNTIME_PATHS as DEFAULT_PIPELINE_RUNTIME_PATHS,
)
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_PIPELINE_VALIDATION_GATES as DEFAULT_PIPELINE_VALIDATION_GATES,
)
from memory.graph.sync_pkg.default_batch_size import (
    DOC_ARCHITECTURE_DIAGRAMS_HUB as DOC_ARCHITECTURE_DIAGRAMS_HUB,
)
from memory.graph.sync_pkg.default_batch_size import (
    DOC_DIAGRAM_TOOLING_README as DOC_DIAGRAM_TOOLING_README,
)
from memory.graph.sync_pkg.default_batch_size import (
    DOC_GRAFANA_DASHBOARDS_JSON as DOC_GRAFANA_DASHBOARDS_JSON,
)
from memory.graph.sync_pkg.default_batch_size import (
    DOCS_VERIFICATION_GUIDE_PATH as DOCS_VERIFICATION_GUIDE_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    EFFECTIVE_CONFIG_ARTIFACT_REF as EFFECTIVE_CONFIG_ARTIFACT_REF,
)
from memory.graph.sync_pkg.default_batch_size import (
    GATE_CONFIG_VALIDATION as GATE_CONFIG_VALIDATION,
)
from memory.graph.sync_pkg.default_batch_size import (
    GATE_DIAGRAM_QUALITY as GATE_DIAGRAM_QUALITY,
)
from memory.graph.sync_pkg.default_batch_size import (
    GATE_DOCS_VERIFICATION as GATE_DOCS_VERIFICATION,
)
from memory.graph.sync_pkg.default_batch_size import (
    GATE_MYPY_STRICT as GATE_MYPY_STRICT,
)
from memory.graph.sync_pkg.default_batch_size import (
    GATE_NEO4J_ONTOLOGY_INVARIANTS as GATE_NEO4J_ONTOLOGY_INVARIANTS,
)
from memory.graph.sync_pkg.default_batch_size import (
    GATE_PRETEST_GUARDRAILS as GATE_PRETEST_GUARDRAILS,
)
from memory.graph.sync_pkg.default_batch_size import (
    GITHUB_WORKFLOWS_PREFIX as GITHUB_WORKFLOWS_PREFIX,
)
from memory.graph.sync_pkg.default_batch_size import (
    GOVERNANCE_DECISIONS_SUMMARY_PATH as GOVERNANCE_DECISIONS_SUMMARY_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    INTEGRATION_VCR_POLICY_PATH as INTEGRATION_VCR_POLICY_PATH,
)
from memory.graph.sync_pkg.default_batch_size import KNOWN_LAYERS as KNOWN_LAYERS
from memory.graph.sync_pkg.default_batch_size import (
    MANIFEST_ID_TEMPLATE as MANIFEST_ID_TEMPLATE,
)
from memory.graph.sync_pkg.default_batch_size import (
    PORTS_FACADE_SOURCE_PATH as PORTS_FACADE_SOURCE_PATH,
)
from memory.graph.sync_pkg.default_batch_size import RULES_DOC_PATH as RULES_DOC_PATH
from memory.graph.sync_pkg.default_batch_size import RUN_ID_TEMPLATE as RUN_ID_TEMPLATE
from memory.graph.sync_pkg.default_batch_size import (
    RUN_LEDGER_ARTIFACT_REF as RUN_LEDGER_ARTIFACT_REF,
)
from memory.graph.sync_pkg.default_batch_size import (
    RUN_MANIFEST_ARTIFACT_REF as RUN_MANIFEST_ARTIFACT_REF,
)
from memory.graph.sync_pkg.default_batch_size import (
    RUN_MANIFEST_INSPECTION_DOC_PATH as RUN_MANIFEST_INSPECTION_DOC_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    RUN_MANIFEST_LEDGER_DOC_PATH as RUN_MANIFEST_LEDGER_DOC_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    TEST_MATRIX_CONFIG_PATH as TEST_MATRIX_CONFIG_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    TEST_SURFACE_ARCHITECTURE as TEST_SURFACE_ARCHITECTURE,
)
from memory.graph.sync_pkg.default_batch_size import (
    TEST_SURFACE_E2E as TEST_SURFACE_E2E,
)
from memory.graph.sync_pkg.default_batch_size import (
    TEST_SURFACE_INTEGRATION as TEST_SURFACE_INTEGRATION,
)
from memory.graph.sync_pkg.default_batch_size import TEST_SURFACES as TEST_SURFACES
from memory.graph.sync_pkg.default_batch_size import (
    TESTING_GUIDE_PATH as TESTING_GUIDE_PATH,
)
from memory.graph.sync_pkg.default_batch_size import (
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH as TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
)
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB as YAML_FILE_GLOB
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _DOC_LIKE_LABELS as _DOC_LIKE_LABELS,
)
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _DOCS_DRIFT_TEXT_EXTENSIONS as _DOCS_DRIFT_TEXT_EXTENSIONS,
)
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _DOCS_REFERENCE_ALLOWED_PREFIXES as _DOCS_REFERENCE_ALLOWED_PREFIXES,
)
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _heading_anchor_slug as _heading_anchor_slug,
)
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _is_docs_drift_source_candidate as _is_docs_drift_source_candidate,
)
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _trim_docs_reference_candidate as _trim_docs_reference_candidate,
)
from memory.graph.sync_pkg.docs_reference_exact_candidates import (
    _docs_reference_exact_candidates as _docs_reference_exact_candidates,
)
from memory.graph.sync_pkg.docs_reference_exact_candidates import (
    _resolve_claim_targets as _resolve_claim_targets,
)
from memory.graph.sync_pkg.duplication_cluster_groups import (
    _add_duplication_cluster_node as _add_duplication_cluster_node,
)
from memory.graph.sync_pkg.duplication_cluster_groups import (
    _duplication_cluster_groups as _duplication_cluster_groups,
)
from memory.graph.sync_pkg.duplication_cluster_groups import (
    _link_duplication_cluster_members as _link_duplication_cluster_members,
)
from memory.graph.sync_pkg.duplication_cluster_groups import (
    _link_same_shape_members as _link_same_shape_members,
)
from memory.graph.sync_pkg.emit_normalization_batch_progress import (
    _emit_normalization_batch_progress as _emit_normalization_batch_progress,
)
from memory.graph.sync_pkg.emit_normalization_batch_progress import (
    _normalization_batch_summary as _normalization_batch_summary,
)
from memory.graph.sync_pkg.empty_normalization_evidence_payload import (
    _accumulate_field_matrix_evidence as _accumulate_field_matrix_evidence,
)
from memory.graph.sync_pkg.empty_normalization_evidence_payload import (
    _empty_normalization_evidence_payload as _empty_normalization_evidence_payload,
)
from memory.graph.sync_pkg.empty_normalization_evidence_payload import (
    _enrich_registry_normalization_evidence as _enrich_registry_normalization_evidence,
)
from memory.graph.sync_pkg.empty_normalization_evidence_payload import (
    _finalize_normalization_evidence_defaults as _finalize_normalization_evidence_defaults,
)
from memory.graph.sync_pkg.entity_config_identity import (
    _add_composite_config_surfaces as _add_composite_config_surfaces,
)
from memory.graph.sync_pkg.entity_config_identity import (
    _entity_config_identity as _entity_config_identity,
)
from memory.graph.sync_pkg.entity_config_paths import (
    _add_entity_config_surface as _add_entity_config_surface,
)
from memory.graph.sync_pkg.entity_config_paths import (
    _entity_config_paths as _entity_config_paths,
)
from memory.graph.sync_pkg.entity_pipeline_identity import (
    _add_entity_pipeline_surface as _add_entity_pipeline_surface,
)
from memory.graph.sync_pkg.entity_pipeline_identity import (
    _entity_pipeline_identity as _entity_pipeline_identity,
)
from memory.graph.sync_pkg.entity_pipeline_identity import (
    _link_entity_pipeline_dependencies as _link_entity_pipeline_dependencies,
)
from memory.graph.sync_pkg.entity_storage_promotion_pairs import (
    _classify_projected_storage_fields as _classify_projected_storage_fields,
)
from memory.graph.sync_pkg.entity_storage_promotion_pairs import (
    _entity_storage_promotion_pairs as _entity_storage_promotion_pairs,
)
from memory.graph.sync_pkg.entity_storage_promotion_pairs import (
    _link_storage_layer_promotion as _link_storage_layer_promotion,
)
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _active_critical_names as _active_critical_names,
)
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _fast_analysis_live_counts as _fast_analysis_live_counts,
)
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _fast_analysis_live_summary as _fast_analysis_live_summary,
)
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _fast_analysis_snapshot_counts as _fast_analysis_snapshot_counts,
)
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _fast_audit_snapshot_payload as _fast_audit_snapshot_payload,
)
from memory.graph.sync_pkg.file_structure import (
    DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES as DEFAULT_FILE_STRUCTURE_EXCLUDED_DIR_NAMES,
)
from memory.graph.sync_pkg.file_structure import (
    DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES as DEFAULT_FILE_STRUCTURE_EXCLUDED_PREFIXES,
)
from memory.graph.sync_pkg.file_structure import (
    DEFAULT_FILE_STRUCTURE_REPO_ZONES as DEFAULT_FILE_STRUCTURE_REPO_ZONES,
)
from memory.graph.sync_pkg.file_structure import (
    _file_structure_config as _file_structure_config,
)
from memory.graph.sync_pkg.git_history import (
    _git_chunk_commit_ages as _git_chunk_commit_ages,
)
from memory.graph.sync_pkg.git_history import (
    _git_chunk_tracked_paths as _git_chunk_tracked_paths,
)
from memory.graph.sync_pkg.git_history import (
    _git_last_commit_age_days as _git_last_commit_age_days,
)
from memory.graph.sync_pkg.git_history import (
    _git_last_commit_age_days_bulk as _git_last_commit_age_days_bulk,
)
from memory.graph.sync_pkg.git_history import (
    _parse_git_chunk_age_output as _parse_git_chunk_age_output,
)
from memory.graph.sync_pkg.git_history import (
    _run_git_history_subprocess as _run_git_history_subprocess,
)
from memory.graph.sync_pkg.governance_policy_definitions import (
    _governance_policy_definitions as _governance_policy_definitions,
)
from memory.graph.sync_pkg.governance_policy_definitions import (
    _governance_policy_spec as _governance_policy_spec,
)
from memory.graph.sync_pkg.governance_policy_targets import (
    _governance_policy_targets as _governance_policy_targets,
)
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _add_layer_topology as _add_layer_topology,
)
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _add_runtime_layer_families as _add_runtime_layer_families,
)
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _add_runtime_layer_modules as _add_runtime_layer_modules,
)
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _add_runtime_layer_surface as _add_runtime_layer_surface,
)
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _governance_summary_table_specs as _governance_summary_table_specs,
)
from memory.graph.sync_pkg.governance_summary_table_specs import (
    _runtime_module_family_key as _runtime_module_family_key,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _alert_surface_nodes as _alert_surface_nodes,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _governance_target_groups as _governance_target_groups,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _link_policy_governance_group as _link_policy_governance_group,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _pipeline_dashboard_targets as _pipeline_dashboard_targets,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _pipeline_operational_section as _pipeline_operational_section,
)
from memory.graph.sync_pkg.graph_contexts import (
    AlertTargetContext as AlertTargetContext,
)
from memory.graph.sync_pkg.graph_contexts import AnalysisAnchors as AnalysisAnchors
from memory.graph.sync_pkg.graph_contexts import (
    CallableDescriptor as CallableDescriptor,
)
from memory.graph.sync_pkg.graph_contexts import ClassDescriptor as ClassDescriptor
from memory.graph.sync_pkg.graph_contexts import (
    ComplexityAnalysisContext as ComplexityAnalysisContext,
)
from memory.graph.sync_pkg.graph_contexts import (
    CompositeOutputConfig as CompositeOutputConfig,
)
from memory.graph.sync_pkg.graph_contexts import (
    CompositePipelineContext as CompositePipelineContext,
)
from memory.graph.sync_pkg.graph_contexts import (
    ContractEntryContext as ContractEntryContext,
)
from memory.graph.sync_pkg.graph_contexts import (
    DuplicateFamilyConfig as DuplicateFamilyConfig,
)
from memory.graph.sync_pkg.graph_contexts import (
    DuplicationExtractionContext as DuplicationExtractionContext,
)
from memory.graph.sync_pkg.graph_contexts import (
    EntityLayerFieldContext as EntityLayerFieldContext,
)
from memory.graph.sync_pkg.graph_contexts import (
    EntityPipelineContext as EntityPipelineContext,
)
from memory.graph.sync_pkg.graph_contexts import (
    RetirementAnalysisContext as RetirementAnalysisContext,
)
from memory.graph.sync_pkg.graph_contexts import SurfaceAnchorSets as SurfaceAnchorSets
from memory.graph.sync_pkg.graph_contexts import (
    SurfaceComplexityMetrics as SurfaceComplexityMetrics,
)
from memory.graph.sync_pkg.graph_contexts import (
    SurfaceRelationIndexes as SurfaceRelationIndexes,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowContext as WorkflowContext
from memory.graph.sync_pkg.graph_contexts import (
    WorkflowJobContext as WorkflowJobContext,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode as GraphNode
from memory.graph.sync_pkg.graph_snapshot import GraphRelation as GraphRelation
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot as GraphSnapshot
from memory.graph.sync_pkg.graph_snapshot import _write_export as _write_export
from memory.graph.sync_pkg.graph_snapshot import snapshot_orphans as snapshot_orphans
from memory.graph.sync_pkg.included_file_structure_dirs import (
    _add_repo_zone_directory_surface as _add_repo_zone_directory_surface,
)
from memory.graph.sync_pkg.included_file_structure_dirs import (
    _included_file_structure_dirs as _included_file_structure_dirs,
)
from memory.graph.sync_pkg.index_storage_layer_fields import (
    _add_composite_storage_data_surfaces as _add_composite_storage_data_surfaces,
)
from memory.graph.sync_pkg.index_storage_layer_fields import (
    _index_storage_layer_fields as _index_storage_layer_fields,
)
from memory.graph.sync_pkg.int_node_property import (
    _aggregate_callable_metrics as _aggregate_callable_metrics,
)
from memory.graph.sync_pkg.int_node_property import (
    _aggregate_surface_complexity_metrics as _aggregate_surface_complexity_metrics,
)
from memory.graph.sync_pkg.int_node_property import (
    _callable_surface_complexity_metrics as _callable_surface_complexity_metrics,
)
from memory.graph.sync_pkg.int_node_property import (
    _casefolded_markers as _casefolded_markers,
)
from memory.graph.sync_pkg.int_node_property import (
    _class_surface_complexity_metrics as _class_surface_complexity_metrics,
)
from memory.graph.sync_pkg.int_node_property import (
    _int_node_property as _int_node_property,
)
from memory.graph.sync_pkg.int_node_property import (
    _module_surface_complexity_metrics as _module_surface_complexity_metrics,
)
from memory.graph.sync_pkg.is_describes_doc_to_module import (
    _add_reverse_module_doc_edges as _add_reverse_module_doc_edges,
)
from memory.graph.sync_pkg.is_describes_doc_to_module import (
    _collect_artifact_source_surfaces as _collect_artifact_source_surfaces,
)
from memory.graph.sync_pkg.is_describes_doc_to_module import (
    _is_describes_doc_to_module as _is_describes_doc_to_module,
)
from memory.graph.sync_pkg.iter_normalization_evidence_updates import (
    _iter_normalization_evidence_updates as _iter_normalization_evidence_updates,
)
from memory.graph.sync_pkg.iter_normalization_evidence_updates import (
    _normalization_evidence_statements as _normalization_evidence_statements,
)
from memory.graph.sync_pkg.iter_normalization_evidence_updates import (
    apply_normalization_evidence_only as apply_normalization_evidence_only,
)
from memory.graph.sync_pkg.link_composite_config_dependencies import (
    _add_test_graph as _add_test_graph,
)
from memory.graph.sync_pkg.link_composite_config_dependencies import (
    _link_composite_config_dependencies as _link_composite_config_dependencies,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    CONTROL_PLANE_LEDGER_DOCS as CONTROL_PLANE_LEDGER_DOCS,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    EFFECTIVE_CONFIG_RUNTIME_MODULES as EFFECTIVE_CONFIG_RUNTIME_MODULES,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    LINEAGE_RUNTIME_MODULES as LINEAGE_RUNTIME_MODULES,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    RUN_LEDGER_RUNTIME_MODULES as RUN_LEDGER_RUNTIME_MODULES,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    RUN_MANIFEST_RUNTIME_MODULES as RUN_MANIFEST_RUNTIME_MODULES,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    _composite_storage_context as _composite_storage_context,
)
from memory.graph.sync_pkg.link_composite_layer_promotions import (
    _link_composite_layer_promotions as _link_composite_layer_promotions,
)
from memory.graph.sync_pkg.link_composite_pipeline_dependencies import (
    _add_pipeline_normalization_evidence as _add_pipeline_normalization_evidence,
)
from memory.graph.sync_pkg.link_composite_pipeline_dependencies import (
    _link_composite_pipeline_dependencies as _link_composite_pipeline_dependencies,
)
from memory.graph.sync_pkg.link_contract_dependency_modules import (
    _link_contract_dependency_docs as _link_contract_dependency_docs,
)
from memory.graph.sync_pkg.link_contract_dependency_modules import (
    _link_contract_dependency_modules as _link_contract_dependency_modules,
)
from memory.graph.sync_pkg.link_contract_provider import (
    _add_contract_registry_artifact as _add_contract_registry_artifact,
)
from memory.graph.sync_pkg.link_contract_provider import (
    _link_contract_provider as _link_contract_provider,
)
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _add_summary_identifiers as _add_summary_identifiers,
)
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _add_summary_table_identifiers as _add_summary_table_identifiers,
)
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _evidence_summary_doc as _evidence_summary_doc,
)
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _link_curated_doc_artifact as _link_curated_doc_artifact,
)
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _summary_identifier_matches as _summary_identifier_matches,
)
from memory.graph.sync_pkg.link_curated_doc_artifact import (
    _summary_table_rows as _summary_table_rows,
)
from memory.graph.sync_pkg.link_curated_execution_script import (
    _add_curated_script_clusters as _add_curated_script_clusters,
)
from memory.graph.sync_pkg.link_curated_execution_script import (
    _link_curated_execution_script as _link_curated_execution_script,
)
from memory.graph.sync_pkg.link_entity_storage_promotions import (
    _link_entity_storage_promotions as _link_entity_storage_promotions,
)
from memory.graph.sync_pkg.link_relation_backed_structure_for_relat import (
    _link_relation_backed_structure_for_relation as _link_relation_backed_structure_for_relation,
)
from memory.graph.sync_pkg.link_run_instance_dependencies import (
    _add_runtime_state_surface as _add_runtime_state_surface,
)
from memory.graph.sync_pkg.link_run_instance_dependencies import (
    _link_run_instance_artifacts as _link_run_instance_artifacts,
)
from memory.graph.sync_pkg.link_run_instance_dependencies import (
    _link_run_instance_dependencies as _link_run_instance_dependencies,
)
from memory.graph.sync_pkg.link_run_instance_dependencies import (
    _link_run_instance_documents as _link_run_instance_documents,
)
from memory.graph.sync_pkg.link_runtime_evidence_support import (
    _add_run_instance_surface as _add_run_instance_surface,
)
from memory.graph.sync_pkg.link_runtime_evidence_support import (
    _add_runtime_evidence_storage_refs as _add_runtime_evidence_storage_refs,
)
from memory.graph.sync_pkg.link_runtime_evidence_support import (
    _link_runtime_evidence_support as _link_runtime_evidence_support,
)
from memory.graph.sync_pkg.link_runtime_state_run_and_pipeline import (
    _link_runtime_state_dependencies as _link_runtime_state_dependencies,
)
from memory.graph.sync_pkg.link_runtime_state_run_and_pipeline import (
    _link_runtime_state_run_and_pipeline as _link_runtime_state_run_and_pipeline,
)
from memory.graph.sync_pkg.live_queries import (
    _audit_live_summary as _audit_live_summary,
)
from memory.graph.sync_pkg.live_queries import (
    _build_diff_entries as _build_diff_entries,
)
from memory.graph.sync_pkg.live_queries import _count_rows_by_key as _count_rows_by_key
from memory.graph.sync_pkg.live_queries import (
    _live_managed_node_count as _live_managed_node_count,
)
from memory.graph.sync_pkg.live_queries import (
    _live_managed_node_counts as _live_managed_node_counts,
)
from memory.graph.sync_pkg.live_queries import (
    _live_managed_relation_count as _live_managed_relation_count,
)
from memory.graph.sync_pkg.live_queries import (
    _live_managed_relation_counts as _live_managed_relation_counts,
)
from memory.graph.sync_pkg.live_queries import (
    _live_managed_relation_rows as _live_managed_relation_rows,
)
from memory.graph.sync_pkg.live_queries import _live_orphan_rows as _live_orphan_rows
from memory.graph.sync_pkg.live_queries import (
    _live_repo_label_rows as _live_repo_label_rows,
)
from memory.graph.sync_pkg.live_queries import _live_scalar as _live_scalar
from memory.graph.sync_pkg.live_queries import (
    _live_unmanaged_repo_rows as _live_unmanaged_repo_rows,
)
from memory.graph.sync_pkg.live_queries import (
    _managed_label_counts_from_rows as _managed_label_counts_from_rows,
)
from memory.graph.sync_pkg.live_queries import (
    _managed_label_summary_from_counts as _managed_label_summary_from_counts,
)
from memory.graph.sync_pkg.live_queries import (
    _managed_relation_counts_from_rows as _managed_relation_counts_from_rows,
)
from memory.graph.sync_pkg.live_queries import (
    _managed_relation_summary_from_counts as _managed_relation_summary_from_counts,
)
from memory.graph.sync_pkg.live_queries import (
    _managed_sync_run_clause as _managed_sync_run_clause,
)
from memory.graph.sync_pkg.live_queries import _row_int_total as _row_int_total
from memory.graph.sync_pkg.live_queries import (
    _snapshot_count_map as _snapshot_count_map,
)
from memory.graph.sync_pkg.live_queries import (
    _snapshot_subset_count_map as _snapshot_subset_count_map,
)
from memory.graph.sync_pkg.mapping_io import (
    DEFAULT_MEMORY_MAPPING_PATH as DEFAULT_MEMORY_MAPPING_PATH,
)
from memory.graph.sync_pkg.mapping_io import (
    LEGACY_MEMORY_MAPPING_PATH as LEGACY_MEMORY_MAPPING_PATH,
)
from memory.graph.sync_pkg.mapping_io import (
    _load_memory_mapping as _load_memory_mapping,
)
from memory.graph.sync_pkg.mapping_io import (
    _mapping_dict_or_empty as _mapping_dict_or_empty,
)
from memory.graph.sync_pkg.mapping_io import _mapping_section as _mapping_section
from memory.graph.sync_pkg.mapping_io import (
    _memory_mapping_path as _memory_mapping_path,
)
from memory.graph.sync_pkg.mapping_io import _read_json as _read_json
from memory.graph.sync_pkg.mapping_io import _read_yaml as _read_yaml
from memory.graph.sync_pkg.markdown_headings import (
    _markdown_headings as _markdown_headings,
)
from memory.graph.sync_pkg.markdown_headings import (
    _resolve_docs_reference_target as _resolve_docs_reference_target,
)
from memory.graph.sync_pkg.merge_field_validation_item import (
    _add_schema_field_surface as _add_schema_field_surface,
)
from memory.graph.sync_pkg.merge_field_validation_item import (
    _add_storage_surface as _add_storage_surface,
)
from memory.graph.sync_pkg.merge_field_validation_item import (
    _merge_field_validation_item as _merge_field_validation_item,
)
from memory.graph.sync_pkg.merge_field_validation_item import (
    _merge_key_nullability_item as _merge_key_nullability_item,
)
from memory.graph.sync_pkg.merge_field_validation_item import (
    _merged_maintenance_config as _merged_maintenance_config,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _entity_pipeline_sink_config as _entity_pipeline_sink_config,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _filtered_group_fields as _filtered_group_fields,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _infer_storage_format as _infer_storage_format,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _merge_sink_config as _merge_sink_config,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _merge_storage_layer_config as _merge_storage_layer_config,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _schema_group_field_map as _schema_group_field_map,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _storage_ref_from_output_path as _storage_ref_from_output_path,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _storage_ref_identity as _storage_ref_identity,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _storage_schema_properties as _storage_schema_properties,
)
from memory.graph.sync_pkg.neo4j_statements import (
    DEFAULT_INGEST_WAVE as DEFAULT_INGEST_WAVE,
)
from memory.graph.sync_pkg.neo4j_statements import (
    DEFAULT_MANAGED_BY as DEFAULT_MANAGED_BY,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _delete_managed_wave_nodes_statement as _delete_managed_wave_nodes_statement,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _managed_properties as _managed_properties,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _neo4j_property_value as _neo4j_property_value,
)
from memory.graph.sync_pkg.neo4j_statements import _node_statement as _node_statement
from memory.graph.sync_pkg.neo4j_statements import (
    _prune_legacy_unmanaged_nodes_statement as _prune_legacy_unmanaged_nodes_statement,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _prune_stale_nodes_statement as _prune_stale_nodes_statement,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _prune_stale_relations_statement as _prune_stale_relations_statement,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _relation_statement as _relation_statement,
)
from memory.graph.sync_pkg.neo4j_statements import (
    _reset_managed_relations_statement as _reset_managed_relations_statement,
)
from memory.graph.sync_pkg.normalization_evidence_batches import (
    _execute_normalization_evidence_batch as _execute_normalization_evidence_batch,
)
from memory.graph.sync_pkg.normalization_evidence_batches import (
    _normalization_evidence_batches as _normalization_evidence_batches,
)
from memory.graph.sync_pkg.normalization_evidence_statement import (
    _NORMALIZATION_EVIDENCE_STATEMENT as _NORMALIZATION_EVIDENCE_STATEMENT,
)
from memory.graph.sync_pkg.normalization_evidence_statement import (
    _normalization_statement_params as _normalization_statement_params,
)
from memory.graph.sync_pkg.normalization_evidence_update_payload import (
    _link_normalization_registry_module as _link_normalization_registry_module,
)
from memory.graph.sync_pkg.normalization_evidence_update_payload import (
    _normalization_evidence_update_payload as _normalization_evidence_update_payload,
)
from memory.graph.sync_pkg.normalization_statement import (
    _emit_normalization_apply_progress as _emit_normalization_apply_progress,
)
from memory.graph.sync_pkg.normalization_statement import (
    _normalization_batch_pipeline_span as _normalization_batch_pipeline_span,
)
from memory.graph.sync_pkg.normalization_statement import (
    _normalization_statement as _normalization_statement,
)
from memory.graph.sync_pkg.override_target_classes import (
    _duplication_family_by_name as _duplication_family_by_name,
)
from memory.graph.sync_pkg.override_target_classes import (
    _override_target_classes as _override_target_classes,
)
from memory.graph.sync_pkg.package_topology_summary_specs import (
    _add_governance_decisions_and_risks as _add_governance_decisions_and_risks,
)
from memory.graph.sync_pkg.package_topology_summary_specs import (
    _package_topology_summary_specs as _package_topology_summary_specs,
)
from memory.graph.sync_pkg.pipeline_dashboard_config import (
    PipelineOperationalContext as PipelineOperationalContext,
)
from memory.graph.sync_pkg.pipeline_dashboard_config import (
    _link_pipeline_operational_targets as _link_pipeline_operational_targets,
)
from memory.graph.sync_pkg.pipeline_dashboard_config import (
    _pipeline_dashboard_config as _pipeline_dashboard_config,
)
from memory.graph.sync_pkg.pipeline_dashboard_config import (
    _pipeline_kind_dashboards as _pipeline_kind_dashboards,
)
from memory.graph.sync_pkg.pipeline_normalization_targets import (
    _link_pipeline_normalization_modules as _link_pipeline_normalization_modules,
)
from memory.graph.sync_pkg.pipeline_normalization_targets import (
    _normalization_edge_config as _normalization_edge_config,
)
from memory.graph.sync_pkg.pipeline_normalization_targets import (
    _pipeline_normalization_modules as _pipeline_normalization_modules,
)
from memory.graph.sync_pkg.pipeline_normalization_targets import (
    _pipeline_normalization_targets as _pipeline_normalization_targets,
)
from memory.graph.sync_pkg.pipeline_operational_targets_config import (
    _link_pipeline_operational_for_pipeline as _link_pipeline_operational_for_pipeline,
)
from memory.graph.sync_pkg.pipeline_operational_targets_config import (
    _pipeline_operational_targets_config as _pipeline_operational_targets_config,
)
from memory.graph.sync_pkg.pipeline_operational_targets_config import (
    _sorted_pipeline_nodes as _sorted_pipeline_nodes,
)
from memory.graph.sync_pkg.pipeline_operational_targets_config import (
    build_audit_report as build_audit_report,
)
from memory.graph.sync_pkg.pipeline_source_config_artifact import (
    _link_pipeline_doc_artifacts as _link_pipeline_doc_artifacts,
)
from memory.graph.sync_pkg.pipeline_source_config_artifact import (
    _pipeline_doc_artifact_targets as _pipeline_doc_artifact_targets,
)
from memory.graph.sync_pkg.pipeline_source_config_artifact import (
    _pipeline_source_config_artifact as _pipeline_source_config_artifact,
)
from memory.graph.sync_pkg.port_surfaces import (
    PORTS_MODULE_PREFIX as PORTS_MODULE_PREFIX,
)
from memory.graph.sync_pkg.port_surfaces import (
    _build_port_surface_catalog as _build_port_surface_catalog,
)
from memory.graph.sync_pkg.port_surfaces import (
    _imported_port_surfaces as _imported_port_surfaces,
)
from memory.graph.sync_pkg.port_surfaces import (
    _imported_port_surfaces_for_node as _imported_port_surfaces_for_node,
)
from memory.graph.sync_pkg.port_surfaces import (
    _imported_port_surfaces_from_import as _imported_port_surfaces_from_import,
)
from memory.graph.sync_pkg.port_surfaces import (
    _imported_port_surfaces_from_import_from as _imported_port_surfaces_from_import_from,
)
from memory.graph.sync_pkg.port_surfaces import (
    _merge_port_init_exports as _merge_port_init_exports,
)
from memory.graph.sync_pkg.port_surfaces import (
    _propagate_port_init_exports as _propagate_port_init_exports,
)
from memory.graph.sync_pkg.port_surfaces import (
    _register_port_protocol_descriptors as _register_port_protocol_descriptors,
)
from memory.graph.sync_pkg.port_surfaces import (
    _resolve_python_module_surface as _resolve_python_module_surface,
)
from memory.graph.sync_pkg.port_surfaces import (
    _seed_port_surface_catalog as _seed_port_surface_catalog,
)
from memory.graph.sync_pkg.process_adapter_module import (
    _add_adapter_package_impls as _add_adapter_package_impls,
)
from memory.graph.sync_pkg.process_adapter_module import (
    _add_adapter_package_surface as _add_adapter_package_surface,
)
from memory.graph.sync_pkg.process_adapter_module import (
    _process_adapter_module as _process_adapter_module,
)
from memory.graph.sync_pkg.process_adapter_package import (
    _process_adapter_package as _process_adapter_package,
)
from memory.graph.sync_pkg.process_adapter_root_child import (
    _process_adapter_root_child as _process_adapter_root_child,
)
from memory.graph.sync_pkg.process_workflow_uses_step import (
    _process_workflow_uses_step as _process_workflow_uses_step,
)
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _complexity_analysis_config as _complexity_analysis_config,
)
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _configured_duplication_families as _configured_duplication_families,
)
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _duplicate_family_config as _duplicate_family_config,
)
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _promotion_targets_from_payload as _promotion_targets_from_payload,
)
from memory.graph.sync_pkg.promotion_targets_from_payload import (
    _retirement_analysis_config as _retirement_analysis_config,
)
from memory.graph.sync_pkg.provider_config_paths import (
    _add_provider_surface as _add_provider_surface,
)
from memory.graph.sync_pkg.provider_config_paths import (
    _provider_config_paths as _provider_config_paths,
)
from memory.graph.sync_pkg.provider_config_properties import (
    _add_entity_config_surfaces as _add_entity_config_surfaces,
)
from memory.graph.sync_pkg.provider_config_properties import (
    _provider_config_properties as _provider_config_properties,
)
from memory.graph.sync_pkg.published_contract_artifact_paths import (
    _link_contract_module_dependencies as _link_contract_module_dependencies,
)
from memory.graph.sync_pkg.published_contract_artifact_paths import (
    _published_contract_artifact_key as _published_contract_artifact_key,
)
from memory.graph.sync_pkg.published_contract_artifact_paths import (
    _published_contract_artifact_paths as _published_contract_artifact_paths,
)
from memory.graph.sync_pkg.python_paths import INIT_PY as INIT_PY
from memory.graph.sync_pkg.python_paths import MAIN_PY as MAIN_PY
from memory.graph.sync_pkg.python_paths import (
    OPS_SCRIPT_HUB_PREFIXES as OPS_SCRIPT_HUB_PREFIXES,
)
from memory.graph.sync_pkg.python_paths import (
    _coerce_repo_relative_path as _coerce_repo_relative_path,
)
from memory.graph.sync_pkg.python_paths import (
    _is_excluded_file_structure_path as _is_excluded_file_structure_path,
)
from memory.graph.sync_pkg.python_paths import (
    _promoted_directory_hubs as _promoted_directory_hubs,
)
from memory.graph.sync_pkg.python_paths import (
    _python_surface_name as _python_surface_name,
)
from memory.graph.sync_pkg.python_paths import (
    _supplemental_directory_hubs_for_node as _supplemental_directory_hubs_for_node,
)
from memory.graph.sync_pkg.register_duplication_class_surface import (
    _register_duplication_class_surface as _register_duplication_class_surface,
)
from memory.graph.sync_pkg.register_duplication_class_surface import (
    _register_duplication_function_surface as _register_duplication_function_surface,
)
from memory.graph.sync_pkg.register_duplication_class_surface import (
    _register_duplication_method_surfaces as _register_duplication_method_surfaces,
)
from memory.graph.sync_pkg.register_protocol_port_surface import (
    _add_adapter_surfaces as _add_adapter_surfaces,
)
from memory.graph.sync_pkg.register_protocol_port_surface import (
    _register_protocol_port_surface as _register_protocol_port_surface,
)
from memory.graph.sync_pkg.relation_backed_file_structure_types import (
    _link_relation_backed_directory_housing as _link_relation_backed_directory_housing,
)
from memory.graph.sync_pkg.relation_backed_file_structure_types import (
    _relation_backed_file_structure_labels as _relation_backed_file_structure_labels,
)
from memory.graph.sync_pkg.relation_backed_file_structure_types import (
    _relation_backed_file_structure_types as _relation_backed_file_structure_types,
)
from memory.graph.sync_pkg.relation_backed_file_structure_types import (
    _relation_backed_parent_relative as _relation_backed_parent_relative,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _append_path_issue as _append_path_issue,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _append_snapshot_support_issues as _append_snapshot_support_issues,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _audit_report_payload as _audit_report_payload,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _bind_support_predicate as _bind_support_predicate,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _excluded_file_structure_paths as _excluded_file_structure_paths,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _format_orphan_nodes as _format_orphan_nodes,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _ignored_runtime_paths as _ignored_runtime_paths,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _orphan_node_issues as _orphan_node_issues,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _path_leak_issues as _path_leak_issues,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _relation_requirement_keys as _relation_requirement_keys,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _sampled_sorted_unique as _sampled_sorted_unique,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    _support_and_relation_issues as _support_and_relation_issues,
)
from memory.graph.sync_pkg.relation_requirement_keys import (
    snapshot_invariant_issues as snapshot_invariant_issues,
)
from memory.graph.sync_pkg.resolved_base_classes import (
    _link_duplication_override_methods as _link_duplication_override_methods,
)
from memory.graph.sync_pkg.resolved_base_classes import (
    _resolved_base_classes as _resolved_base_classes,
)
from memory.graph.sync_pkg.retirement_analysis_context import (
    _prime_retirement_age_cache as _prime_retirement_age_cache,
)
from memory.graph.sync_pkg.retirement_analysis_context import (
    _retirement_analysis_context as _retirement_analysis_context,
)
from memory.graph.sync_pkg.retirement_analysis_context import (
    _retirement_candidate_payload as _retirement_candidate_payload,
)
from memory.graph.sync_pkg.retirement_analysis_label_sets import (
    _evaluate_retirement_surface as _evaluate_retirement_surface,
)
from memory.graph.sync_pkg.retirement_analysis_label_sets import (
    _retirement_analysis_label_sets as _retirement_analysis_label_sets,
)
from memory.graph.sync_pkg.retirement_analysis_label_sets import (
    _retirement_candidate_nodes as _retirement_candidate_nodes,
)
from memory.graph.sync_pkg.retirement_candidate_metrics import (
    _add_retirement_candidate_node as _add_retirement_candidate_node,
)
from memory.graph.sync_pkg.retirement_candidate_metrics import (
    _annotate_current_cycle_surface as _annotate_current_cycle_surface,
)
from memory.graph.sync_pkg.retirement_candidate_metrics import (
    _link_retirement_candidate as _link_retirement_candidate,
)
from memory.graph.sync_pkg.retirement_candidate_metrics import (
    _retirement_candidate_confidence as _retirement_candidate_confidence,
)
from memory.graph.sync_pkg.retirement_candidate_metrics import (
    _retirement_candidate_metrics as _retirement_candidate_metrics,
)
from memory.graph.sync_pkg.retirement_marker_sets import (
    _analysis_anchor_counts as _analysis_anchor_counts,
)
from memory.graph.sync_pkg.retirement_marker_sets import (
    _emit_retirement_candidate as _emit_retirement_candidate,
)
from memory.graph.sync_pkg.retirement_marker_sets import (
    _retirement_marker_sets as _retirement_marker_sets,
)
from memory.graph.sync_pkg.retirement_marker_sets import (
    _retirement_score_inputs as _retirement_score_inputs,
)
from memory.graph.sync_pkg.retirement_marker_sets import (
    _retirement_surface_payload as _retirement_surface_payload,
)
from memory.graph.sync_pkg.reusable_target_workflow_key import (
    _add_job_matrix_variants as _add_job_matrix_variants,
)
from memory.graph.sync_pkg.reusable_target_workflow_key import (
    _add_job_outputs as _add_job_outputs,
)
from memory.graph.sync_pkg.reusable_target_workflow_key import (
    _reusable_target_workflow_key as _reusable_target_workflow_key,
)
from memory.graph.sync_pkg.run_instance_doc_targets import (
    _run_instance_artifact_targets as _run_instance_artifact_targets,
)
from memory.graph.sync_pkg.run_instance_doc_targets import (
    _run_instance_doc_targets as _run_instance_doc_targets,
)
from memory.graph.sync_pkg.run_instance_doc_targets import (
    _runtime_state_specs as _runtime_state_specs,
)
from memory.graph.sync_pkg.run_instance_properties import (
    _link_run_instance_contract_dependency as _link_run_instance_contract_dependency,
)
from memory.graph.sync_pkg.run_instance_properties import (
    _link_run_instance_pipeline_dependency as _link_run_instance_pipeline_dependency,
)
from memory.graph.sync_pkg.run_instance_properties import (
    _run_instance_properties as _run_instance_properties,
)
from memory.graph.sync_pkg.runtime_evidence_definitions import (
    RUNTIME_EVIDENCE_DEFINITIONS as RUNTIME_EVIDENCE_DEFINITIONS,
)
from memory.graph.sync_pkg.runtime_evidence_definitions import (
    _control_plane_runtime_evidence_specs as _control_plane_runtime_evidence_specs,
)
from memory.graph.sync_pkg.runtime_evidence_definitions import (
    _runtime_evidence_definition_spec as _runtime_evidence_definition_spec,
)
from memory.graph.sync_pkg.runtime_evidence_definitions import (
    _runtime_evidence_spec as _runtime_evidence_spec,
)
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _add_runtime_evidence_storage_artifact as _add_runtime_evidence_storage_artifact,
)
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _control_plane_run_instance_specs as _control_plane_run_instance_specs,
)
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _iter_object_values as _iter_object_values,
)
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _link_runtime_evidence_docs as _link_runtime_evidence_docs,
)
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _link_runtime_evidence_modules as _link_runtime_evidence_modules,
)
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _runtime_evidence_storage_refs as _runtime_evidence_storage_refs,
)
from memory.graph.sync_pkg.runtime_state_properties import (
    _link_runtime_state_evidence_dependencies as _link_runtime_state_evidence_dependencies,
)
from memory.graph.sync_pkg.runtime_state_properties import (
    _link_runtime_state_workflow_dependency as _link_runtime_state_workflow_dependency,
)
from memory.graph.sync_pkg.runtime_state_properties import (
    _runtime_state_properties as _runtime_state_properties,
)
from memory.graph.sync_pkg.score_family import _family_for_path as _family_for_path
from memory.graph.sync_pkg.score_family import (
    _family_matches_relative_path as _family_matches_relative_path,
)
from memory.graph.sync_pkg.score_family import (
    _family_root_priority as _family_root_priority,
)
from memory.graph.sync_pkg.score_family import _presence_score as _presence_score
from memory.graph.sync_pkg.score_family import _semantic_tags as _semantic_tags
from memory.graph.sync_pkg.score_family import _threshold_score as _threshold_score
from memory.graph.sync_pkg.shard_filters import DOCS_DRIFT_FILTER as DOCS_DRIFT_FILTER
from memory.graph.sync_pkg.shard_filters import (
    RUNTIME_EVIDENCE_LAYER_FILTER as RUNTIME_EVIDENCE_LAYER_FILTER,
)
from memory.graph.sync_pkg.shard_filters import (
    STORAGE_LAYER_FILTER as STORAGE_LAYER_FILTER,
)
from memory.graph.sync_pkg.shard_filters import (
    WORKFLOW_GRAPH_FILTER as WORKFLOW_GRAPH_FILTER,
)
from memory.graph.sync_pkg.shard_filters import RelationSpec as RelationSpec
from memory.graph.sync_pkg.shard_filters import ShardFilter as ShardFilter
from memory.graph.sync_pkg.shard_filters import ShardFilterSpec as ShardFilterSpec
from memory.graph.sync_pkg.should_emit_complexity_candidate import (
    _complexity_candidate_classification as _complexity_candidate_classification,
)
from memory.graph.sync_pkg.should_emit_complexity_candidate import (
    _complexity_surface_payload as _complexity_surface_payload,
)
from memory.graph.sync_pkg.should_emit_complexity_candidate import (
    _should_emit_complexity_candidate as _should_emit_complexity_candidate,
)
from memory.graph.sync_pkg.skip_entity_storage_layer import (
    _create_entity_storage_layer_surface as _create_entity_storage_layer_surface,
)
from memory.graph.sync_pkg.skip_entity_storage_layer import (
    _link_entity_storage_layer_backing as _link_entity_storage_layer_backing,
)
from memory.graph.sync_pkg.skip_entity_storage_layer import (
    _skip_entity_storage_layer as _skip_entity_storage_layer,
)
from memory.graph.sync_pkg.snapshot_filters import (
    COMPLEXITY_NODE_LABELS as COMPLEXITY_NODE_LABELS,
)
from memory.graph.sync_pkg.snapshot_filters import (
    COMPLEXITY_RELATION_TYPES as COMPLEXITY_RELATION_TYPES,
)
from memory.graph.sync_pkg.snapshot_filters import (
    RETIREMENT_NODE_LABELS as RETIREMENT_NODE_LABELS,
)
from memory.graph.sync_pkg.snapshot_filters import (
    RETIREMENT_RELATION_TYPES as RETIREMENT_RELATION_TYPES,
)
from memory.graph.sync_pkg.snapshot_filters import RelationKey as RelationKey
from memory.graph.sync_pkg.snapshot_filters import (
    _allowed_analysis_relation_types as _allowed_analysis_relation_types,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _build_allowed_labels as _build_allowed_labels,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _filtered_snapshot as _filtered_snapshot,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _include_analysis_relation as _include_analysis_relation,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _include_filtered_relation as _include_filtered_relation,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _include_shard_filtered_relation as _include_shard_filtered_relation,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _include_shard_relation_nodes as _include_shard_relation_nodes,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _relation_matches_shard_filters as _relation_matches_shard_filters,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _resolved_snapshot_selection as _resolved_snapshot_selection,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _seed_filtered_nodes as _seed_filtered_nodes,
)
from memory.graph.sync_pkg.snapshot_filters import (
    _selected_shard_filters as _selected_shard_filters,
)
from memory.graph.sync_pkg.snapshot_relation_requirements import (
    SNAPSHOT_RELATION_REQUIREMENTS as SNAPSHOT_RELATION_REQUIREMENTS,
)
from memory.graph.sync_pkg.snapshot_required_labels import (
    SNAPSHOT_REQUIRED_LABELS as SNAPSHOT_REQUIRED_LABELS,
)
from memory.graph.sync_pkg.snapshot_required_labels import (
    SNAPSHOT_REQUIRED_RELATION_TYPES as SNAPSHOT_REQUIRED_RELATION_TYPES,
)
from memory.graph.sync_pkg.snapshot_required_labels import (
    _support_control_plane_artifact_surface as _support_control_plane_artifact_surface,
)
from memory.graph.sync_pkg.snapshot_required_labels import (
    _support_run_instance_surface as _support_run_instance_surface,
)
from memory.graph.sync_pkg.snapshot_required_labels import (
    _support_runtime_evidence_surface as _support_runtime_evidence_surface,
)
from memory.graph.sync_pkg.snapshot_required_labels import (
    _support_runtime_state_surface as _support_runtime_state_surface,
)
from memory.graph.sync_pkg.snapshot_support_specs import (
    _required_population_issues as _required_population_issues,
)
from memory.graph.sync_pkg.snapshot_support_specs import (
    _snapshot_support_specs as _snapshot_support_specs,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _build_snapshot_relation_index as _build_snapshot_relation_index,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _has_inbound_relation as _has_inbound_relation,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _has_outbound_relation as _has_outbound_relation,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _missing_required_population as _missing_required_population,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _nodes_with_label as _nodes_with_label,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _port_and_contract_metadata_issues as _port_and_contract_metadata_issues,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _protocol_class_ports as _protocol_class_ports,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _rich_contract_surfaces as _rich_contract_surfaces,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _SnapshotRelationIndex as _SnapshotRelationIndex,
)
from memory.graph.sync_pkg.sorted_governance_targets import (
    _governance_policy_specs as _governance_policy_specs,
)
from memory.graph.sync_pkg.sorted_governance_targets import (
    _sorted_governance_targets as _sorted_governance_targets,
)
from memory.graph.sync_pkg.source_backed_path_kind import (
    _link_source_backed_directory_structure as _link_source_backed_directory_structure,
)
from memory.graph.sync_pkg.source_backed_path_kind import (
    _source_backed_file_structure_labels as _source_backed_file_structure_labels,
)
from memory.graph.sync_pkg.source_backed_path_kind import (
    _source_backed_path_kind as _source_backed_path_kind,
)
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_CHAIN_ARTIFACT_REFS as RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
)
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_CHAIN_DOCS as RUN_INSTANCE_CHAIN_DOCS,
)
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_PRIMARY_ARTIFACT_REFS as RUN_INSTANCE_PRIMARY_ARTIFACT_REFS,
)
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_PRIMARY_DOCS as RUN_INSTANCE_PRIMARY_DOCS,
)
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_SPECS as RUN_INSTANCE_SPECS,
)
from memory.graph.sync_pkg.storage_surface_format import (
    RUN_INSTANCE_TRACEABILITY_DOCS as RUN_INSTANCE_TRACEABILITY_DOCS,
)
from memory.graph.sync_pkg.storage_surface_format import (
    _chembl_activity_run_instance_fixture as _chembl_activity_run_instance_fixture,
)
from memory.graph.sync_pkg.storage_surface_format import (
    _run_instance_definition_spec as _run_instance_definition_spec,
)
from memory.graph.sync_pkg.storage_surface_format import (
    _run_instance_fixture_spec as _run_instance_fixture_spec,
)
from memory.graph.sync_pkg.storage_surface_format import (
    _storage_surface_format as _storage_surface_format,
)
from memory.graph.sync_pkg.storage_surface_state import (
    _add_control_plane_artifact_surface as _add_control_plane_artifact_surface,
)
from memory.graph.sync_pkg.storage_surface_state import (
    _entity_pipeline_scope as _entity_pipeline_scope,
)
from memory.graph.sync_pkg.storage_surface_state import (
    _scd_config_columns as _scd_config_columns,
)
from memory.graph.sync_pkg.storage_surface_state import (
    _storage_surface_semantic_properties as _storage_surface_semantic_properties,
)
from memory.graph.sync_pkg.storage_surface_state import (
    _storage_surface_state as _storage_surface_state,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_cli_command_surface as _support_cli_command_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_cli_option_surface as _support_cli_option_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_doc_claim_surface as _support_doc_claim_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_schema_field_surface as _support_schema_field_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_storage_surface as _support_storage_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_workflow_artifact_surface as _support_workflow_artifact_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_workflow_call_surface as _support_workflow_call_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_workflow_job_surface as _support_workflow_job_surface,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_workflow_output_surface as _support_workflow_output_surface,
)
from memory.graph.sync_pkg.sync_run_id import (
    _append_missing_relation_issues as _append_missing_relation_issues,
)
from memory.graph.sync_pkg.sync_run_id import (
    _append_support_issue as _append_support_issue,
)
from memory.graph.sync_pkg.sync_run_id import (
    _has_required_relation as _has_required_relation,
)
from memory.graph.sync_pkg.sync_run_id import (
    _missing_node_support_names as _missing_node_support_names,
)
from memory.graph.sync_pkg.sync_run_id import _sync_run_id as _sync_run_id
from memory.graph.sync_pkg.sync_run_id import (
    _verify_sync_snapshot as _verify_sync_snapshot,
)
from memory.graph.sync_pkg.sync_run_id import sync_snapshot as sync_snapshot
from memory.graph.sync_pkg.test_suite_name import (
    _link_test_artifact_scope as _link_test_artifact_scope,
)
from memory.graph.sync_pkg.test_suite_name import _test_suite_name as _test_suite_name
from memory.graph.sync_pkg.transport import (
    _DEFAULT_NEO4J_AUDIT_DATABASE as _DEFAULT_NEO4J_AUDIT_DATABASE,
)
from memory.graph.sync_pkg.transport import (
    _DEFAULT_NEO4J_AUDIT_USERNAME as _DEFAULT_NEO4J_AUDIT_USERNAME,
)
from memory.graph.sync_pkg.transport import (
    Neo4jHttpClient as Neo4jHttpClient,
)
from memory.graph.sync_pkg.transport import (
    _default_neo4j_host as _default_neo4j_host,
)
from memory.graph.sync_pkg.transport import (
    _env_flag_is_enabled as _env_flag_is_enabled,
)
from memory.graph.sync_pkg.transport import _parse_auth_pair as _parse_auth_pair
from memory.graph.sync_pkg.transport import _read_env_file as _read_env_file
from memory.graph.sync_pkg.transport import derive_http_uri as derive_http_uri
from memory.graph.sync_pkg.transport import load_repo_env as load_repo_env
from memory.graph.sync_pkg.transport import (
    resolve_neo4j_connection as resolve_neo4j_connection,
)
from memory.graph.sync_pkg.workflow_environment_mapping_name import (
    _sorted_string_items as _sorted_string_items,
)
from memory.graph.sync_pkg.workflow_environment_mapping_name import (
    _workflow_environment_mapping_name as _workflow_environment_mapping_name,
)
from memory.graph.sync_pkg.workflow_environment_mapping_name import (
    _workflow_matrix_axes as _workflow_matrix_axes,
)
from memory.graph.sync_pkg.workflow_environment_mapping_name import (
    _workflow_matrix_variants as _workflow_matrix_variants,
)
from memory.graph.sync_pkg.workflow_family_rules import (
    _WORKFLOW_FAMILY_RULES as _WORKFLOW_FAMILY_RULES,
)
from memory.graph.sync_pkg.workflow_family_rules import (
    _workflow_environment_name as _workflow_environment_name,
)
from memory.graph.sync_pkg.workflow_family_rules import (
    _workflow_on_payload as _workflow_on_payload,
)
from memory.graph.sync_pkg.workflow_family_rules import (
    _workflow_trigger_names as _workflow_trigger_names,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _append_workflow_matrix_include_variants as _append_workflow_matrix_include_variants,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _attach_workflow_file_backing as _attach_workflow_file_backing,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_action_key as _workflow_action_key,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_matrix_axis_values as _workflow_matrix_axis_values,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_matrix_base_variants as _workflow_matrix_base_variants,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_output_specs as _workflow_output_specs,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_reusable_target as _workflow_reusable_target,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_secret_refs as _workflow_secret_refs,
)
from memory.graph.sync_pkg.workflow_matrix_payload import (
    _workflow_matrix_base_axes as _workflow_matrix_base_axes,
)
from memory.graph.sync_pkg.workflow_matrix_payload import (
    _workflow_matrix_payload as _workflow_matrix_payload,
)
from memory.graph.sync_pkg.workflow_matrix_payload import (
    _workflow_matrix_variants_with_includes as _workflow_matrix_variants_with_includes,
)
from memory.graph.sync_pkg.workflow_module_script_targets import (
    _add_workflow_job_surface as _add_workflow_job_surface,
)
from memory.graph.sync_pkg.workflow_module_script_targets import (
    _workflow_module_script_targets as _workflow_module_script_targets,
)
from memory.graph.sync_pkg.workflow_module_script_targets import (
    _workflow_quality_gates as _workflow_quality_gates,
)
from memory.graph.sync_pkg.workflow_module_script_targets import (
    _workflow_repo_path_targets as _workflow_repo_path_targets,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _add_workflow_surface as _add_workflow_surface,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _claim_modality as _claim_modality,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _cli_side_effect_class as _cli_side_effect_class,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _extract_cli_options as _extract_cli_options,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _job_step_counts as _job_step_counts,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _workflow_artifact_specs as _workflow_artifact_specs,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _workflow_concurrency_group as _workflow_concurrency_group,
)
from memory.graph.sync_pkg.workflow_output_expression import (
    _workflow_output_expression as _workflow_output_expression,
)

# Graph assembly ingests heterogeneous YAML/JSON and AST-derived values. Keep
# that pre-serialization boundary explicit; serializers below narrow values to
# the scalar/list shapes accepted by Neo4j and JSON.
T = TypeVar("T")

SRC_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = Path(__file__).resolve().parents[4]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))


def _duplication_analysis_config(
    memory_mapping: dict[str, object],
) -> dict[str, object]:
    payload = _mapping_section(memory_mapping, "duplication_analysis")
    families = _configured_duplication_families(payload.get("families", {}))
    return {
        "enabled": bool(payload.get("enabled", True)),
        "min_cluster_size": _coerce_int(payload.get("min_cluster_size", 2), 2),
        "min_ast_nodes": _coerce_int(payload.get("min_ast_nodes", 12), 12),
        "families": tuple(families),
    }


def build_snapshot(root: Path, verified_at: str | None = None) -> GraphSnapshot:
    snapshot = GraphSnapshot()
    today = verified_at or date.today().isoformat()
    memory_mapping = _load_memory_mapping(root)
    project = snapshot.add_node(
        "project",
        "BioETL",
        summary="Python ETL framework for bioactivity data acquisition.",
        source_path="docs/00-project/ai/memory/agent-memory.md",
        source_kind="memory_entrypoint",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    _add_curated_docs(snapshot, root, project, today)
    _add_decisions_and_risks(snapshot, root, project, today)
    _add_layer_topology(snapshot, root, project, today)
    _add_provider_and_config_graph(snapshot, root, project, today)
    _add_dashboard_graph(snapshot, root, project, today)
    _add_quality_and_scripts(snapshot, root, project, today)
    _add_test_graph(snapshot, root, project, today)
    _add_policy_surfaces(snapshot, root, project, today)
    _add_impact_analysis_surfaces(snapshot, root, project, today)
    _add_file_structure_surfaces(snapshot, root, project, today)
    _add_storage_data_surfaces(snapshot, root, project, today)
    _add_control_plane_runtime_evidence(snapshot, root, project, today)
    _add_ci_workflow_graph(snapshot, root, project, today)
    _add_cli_command_graph(snapshot, root, project, today)
    _add_docs_to_code_drift_edges(snapshot, root)
    _add_pipeline_doc_edges(snapshot)
    _add_reverse_module_doc_edges(snapshot)
    _add_adr_constraint_edges(snapshot, root, project, today)
    _add_retirement_analysis_surfaces(snapshot, root, project, today, memory_mapping)
    _add_complexity_analysis_surfaces(snapshot, root, project, today, memory_mapping)
    return snapshot


def _add_curated_docs(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    for entry in CURATED_DOC_SOURCES:
        _add_curated_doc_source(snapshot, root, project, today, entry)


def _add_decisions_and_risks(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    _add_package_topology_decisions_and_risks(snapshot, root, project, today)
    _add_governance_decisions_and_risks(snapshot, root, project, today)


def _add_provider_and_config_graph(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    provider_nodes = _add_provider_surfaces(snapshot, root, project, today)
    entity_nodes = _add_entity_config_surfaces(snapshot, root, today, provider_nodes)
    _add_composite_config_surfaces(snapshot, root, project, today, entity_nodes)


def _add_provider_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> dict[str, NodeKey]:
    providers_root = root / "configs" / "providers"
    provider_nodes: dict[str, NodeKey] = {}
    for provider_path in _provider_config_paths(providers_root):
        _add_provider_surface(
            snapshot,
            root,
            project,
            today,
            provider_path,
            provider_nodes=provider_nodes,
        )
    return provider_nodes


def _add_policy_surfaces(
    snapshot: GraphSnapshot, _root: Path, project: NodeKey, today: str
) -> None:
    for policy_payload in _curated_policy_surfaces():
        _add_policy_surface_entry(snapshot, project, today, policy_payload)


def _curated_policy_surfaces() -> tuple[dict[str, object], ...]:
    return tuple(CURATED_POLICY_SURFACES)


def _add_policy_surface_entry(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    policy_payload: dict[str, object],
) -> None:
    policy_context = _policy_surface_context(snapshot, policy_payload, today)
    policy = policy_context.policy
    snapshot.add_relation(
        project, "HAS_POLICY_SURFACE", policy, provenance="curated_policy"
    )
    snapshot.add_relation(
        policy, "BACKED_BY", policy_context.artifact, provenance="curated_policy"
    )
    _link_policy_governance_targets(snapshot, policy, policy_payload)


@dataclass(frozen=True)
class PolicySurfaceContext:
    policy: NodeKey
    artifact: NodeKey


def _policy_surface_context(
    snapshot: GraphSnapshot,
    policy_payload: dict[str, object],
    today: str,
) -> PolicySurfaceContext:
    return PolicySurfaceContext(
        policy=_add_policy_surface(snapshot, policy_payload, today),
        artifact=_add_policy_artifact(snapshot, policy_payload, today),
    )


def _link_policy_governance_targets(
    snapshot: GraphSnapshot,
    policy: NodeKey,
    policy_payload: dict[str, object],
) -> None:
    for target in _policy_governance_targets(policy_payload):
        snapshot.add_relation(policy, "GOVERNS", target, provenance="curated_policy")


def _policy_governance_targets(
    policy_payload: dict[str, object],
) -> tuple[NodeKey, ...]:
    targets: list[NodeKey] = []
    targets.extend(
        NodeKey("layer_family", str(name))
        for name in _as_iterable(policy_payload.get("governs_layers"))
    )
    targets.extend(
        NodeKey("quality_gate", str(name))
        for name in _as_iterable(policy_payload.get("governs_quality_gates"))
    )
    targets.extend(
        NodeKey("test_surface", str(name))
        for name in _as_iterable(policy_payload.get("governs_test_surfaces"))
    )
    targets.extend(
        NodeKey("doc_source_surface", str(name))
        for name in _as_iterable(policy_payload.get("governs_docs"))
    )
    return tuple(targets)


def _add_impact_analysis_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    memory_mapping = _load_memory_mapping(root)
    port_nodes, adapter_nodes, contract_nodes, pipeline_nodes = (
        _impact_analysis_context(
            snapshot,
            root,
            project,
            today,
            memory_mapping,
        )
    )
    _run_impact_analysis_passes(
        snapshot,
        root,
        project,
        today,
        memory_mapping=memory_mapping,
        port_nodes=port_nodes,
        adapter_nodes=adapter_nodes,
        contract_nodes=contract_nodes,
        pipeline_nodes=pipeline_nodes,
    )


def _run_impact_analysis_passes(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    memory_mapping: dict[str, object],
    port_nodes: set[NodeKey],
    adapter_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    _add_pipeline_normalization_edges(snapshot, pipeline_nodes, memory_mapping)
    _add_pipeline_normalization_evidence(snapshot, pipeline_nodes)
    _add_pipeline_test_edges(snapshot, root, pipeline_nodes, memory_mapping)
    _add_alert_surfaces(
        snapshot, root, project, today, pipeline_nodes, contract_nodes, memory_mapping
    )
    _add_governance_edges(
        snapshot, port_nodes, adapter_nodes, pipeline_nodes, contract_nodes
    )
    _add_pipeline_operational_edges(snapshot, pipeline_nodes, memory_mapping)
    _extract_code_duplication_surfaces(snapshot, root, project, today, memory_mapping)


def _impact_analysis_context(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> tuple[set[NodeKey], dict[str, NodeKey], dict[str, NodeKey], dict[str, NodeKey]]:
    port_nodes = _add_port_surfaces(snapshot, root, project, today)
    adapter_nodes = _add_adapter_surfaces(
        snapshot, root, project, today, port_nodes, memory_mapping
    )
    contract_nodes = _add_contract_surfaces(
        snapshot, root, project, today, memory_mapping
    )
    pipeline_nodes = _add_pipeline_surfaces(
        snapshot, root, project, today, contract_nodes, adapter_nodes
    )
    return port_nodes, adapter_nodes, contract_nodes, pipeline_nodes


def _repo_zone_for_path(
    source_path_value: str, zone_roots: dict[str, tuple[str, ...]]
) -> str | None:
    return next(
        (
            zone_name
            for zone_name, relative_roots in zone_roots.items()
            if any(
                source_path_value == zone_root
                or source_path_value.startswith(f"{zone_root}/")
                for zone_root in relative_roots
            )
        ),
        None,
    )


def _add_repo_zone_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_name: str,
    relative_roots: tuple[str, ...],
    config: dict[str, object],
) -> None:
    zone = snapshot.add_node(
        "repo_zone",
        zone_name,
        summary=f"Primary repository zone `{zone_name}`.",
        source_kind="file_structure_zone",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_REPO_ZONE", zone, provenance="file_structure")

    for relative_root in relative_roots:
        _walk_repo_zone_root(
            snapshot,
            root,
            project,
            zone,
            today,
            zone_name=zone_name,
            relative_root=relative_root,
            config=config,
        )


def _walk_repo_zone_root(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    config: dict[str, object],
) -> None:
    zone_root = root / relative_root
    if not zone_root.is_dir():
        return
    _walk_repo_zone_file_structure(
        snapshot,
        root,
        project,
        zone,
        today,
        zone_name=zone_name,
        relative_root=relative_root,
        zone_root=zone_root,
        config=config,
    )


def _walk_repo_zone_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    zone_root: Path,
    config: dict[str, object],
) -> None:
    for current_dir, dirnames, filenames in os.walk(zone_root):
        current_path = Path(current_dir)
        relative_dir = _rel_path(root, current_path)
        if _is_excluded_file_structure_path(relative_dir, config):
            dirnames[:] = []
            filenames[:] = []
            continue
        dirnames[:] = _included_file_structure_dirs(
            root, current_path, dirnames, config
        )
        directory = _add_repo_zone_directory_surface(
            snapshot,
            root,
            zone,
            today,
            zone_name=zone_name,
            relative_root=relative_root,
            current_path=current_path,
            relative_dir=relative_dir,
        )
        _add_repo_zone_directory_files(
            snapshot,
            root,
            project,
            directory,
            current_path,
            filenames,
            today,
            zone_name=zone_name,
            config=config,
        )


def _link_source_backed_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    source_backed_labels = _source_backed_file_structure_labels()
    path_kind_cache: dict[str, str | None] = {}
    for node in tuple(snapshot.nodes.values()):
        _link_source_backed_node_structure(
            snapshot,
            root,
            node,
            source_backed_labels=source_backed_labels,
            path_kind_cache=path_kind_cache,
            today=today,
            zone_roots=zone_roots,
            config=config,
        )


def _link_source_backed_node_structure(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    source_backed_labels: set[str],
    path_kind_cache: dict[str, str | None],
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    if node.key.label not in source_backed_labels:
        return
    source_path_value = node.properties.get("source_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        return
    if _is_excluded_file_structure_path(source_path_value, config):
        return

    path_kind = _source_backed_path_kind(snapshot, source_path_value, path_kind_cache)
    if path_kind == "directory":
        _link_source_backed_directory_structure(
            snapshot,
            node.key,
            source_path_value=source_path_value,
            config=config,
        )
        return
    if path_kind != "file":
        return
    _link_source_backed_file_node(
        snapshot,
        root,
        node.key,
        root / source_path_value,
        source_path_value=source_path_value,
        today=today,
        zone_roots=zone_roots,
        config=config,
    )


def _link_source_backed_file_node(
    snapshot: GraphSnapshot,
    root: Path,
    node_key: NodeKey,
    source_path: Path,
    *,
    source_path_value: str,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    parent_relative = _rel_path(root, source_path.parent)
    file_surface = snapshot.add_node(
        "file_surface",
        source_path_value,
        summary=f"Primary repository file `{source_path_value}`.",
        source_path=source_path_value,
        source_kind="file_structure_file",
        repo_zone=_repo_zone_for_path(source_path_value, zone_roots),
        suffix=source_path.suffix,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    directory_key = NodeKey("directory_surface", parent_relative)
    if directory_key in snapshot.nodes:
        snapshot.add_relation(
            directory_key, "CONTAINS", file_surface, provenance="file_structure"
        )
        snapshot.add_relation(
            directory_key, "HOUSES", node_key, provenance="file_structure"
        )
    for promoted_hub in _promoted_directory_hubs(parent_relative, config):
        hub_key = NodeKey("directory_surface", promoted_hub)
        if hub_key in snapshot.nodes:
            snapshot.add_relation(
                hub_key, "HOUSES", node_key, provenance="file_structure"
            )
    for supplemental_hub in _supplemental_directory_hubs_for_node(
        node_key, source_path_value
    ):
        hub_key = NodeKey("directory_surface", supplemental_hub)
        snapshot.add_relation(
            hub_key, "CONTAINS", file_surface, provenance="file_structure_promoted"
        )
        snapshot.add_relation(
            hub_key, "HOUSES", node_key, provenance="file_structure_promoted"
        )
    snapshot.add_relation(file_surface, "BACKS", node_key, provenance="file_structure")


def _link_relation_backed_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    config: dict[str, object],
) -> None:
    relation_backed_types = _relation_backed_file_structure_types()
    file_backed_labels = _relation_backed_file_structure_labels()
    for relation in tuple(snapshot.relations.values()):
        _link_relation_backed_structure_for_relation(
            snapshot,
            root,
            relation,
            relation_backed_types=relation_backed_types,
            file_backed_labels=file_backed_labels,
            config=config,
        )


def _add_file_structure_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    memory_mapping = _load_memory_mapping(root)
    config = _file_structure_config(memory_mapping)
    zone_roots = _file_structure_zone_roots(config)
    _materialize_file_structure(snapshot, root, project, today, zone_roots, config)


def _materialize_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    _add_file_structure_zones(snapshot, root, project, today, zone_roots, config)
    _link_source_backed_file_structure(snapshot, root, today, zone_roots, config)
    _link_relation_backed_file_structure(snapshot, root, config)


def _file_structure_zone_roots(config: dict[str, object]) -> dict[str, tuple[str, ...]]:
    raw_zones = config.get("repo_zones")
    if not isinstance(raw_zones, dict):
        return {}
    return {
        str(name): tuple(_as_string_list(paths)) for name, paths in raw_zones.items()
    }


def _add_file_structure_zones(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    for zone_name, relative_roots in zone_roots.items():
        _add_file_structure_zone(
            snapshot,
            root,
            project,
            today,
            zone_name,
            relative_roots,
            config,
        )


def _add_file_structure_zone(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_name: str,
    relative_roots: tuple[str, ...],
    config: dict[str, object],
) -> None:
    _add_repo_zone_file_structure(
        snapshot,
        root,
        project,
        today,
        zone_name,
        relative_roots,
        config,
    )


def _field_quality_index(payload: dict[str, object]) -> dict[str, dict[str, JsonValue]]:
    quality_payload = _as_mapping(payload.get("quality"))
    index: dict[str, dict[str, JsonValue]] = {}
    field_validations = quality_payload.get("entity_field_validations")
    if isinstance(field_validations, list):
        for item in field_validations:
            _merge_field_validation_item(index, item)
    key_nullability = quality_payload.get("key_nullability")
    if isinstance(key_nullability, list):
        for item in key_nullability:
            _merge_key_nullability_item(index, item)
    return index


def _add_entity_layer_field_nodes(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
) -> dict[str, NodeKey]:
    layer_field_nodes: dict[str, NodeKey] = {}
    scope = _entity_pipeline_scope(
        context.provider_name, context.entity_name, context.pipeline_name
    )
    drift_classification = (
        "staging_projection" if layer_context.layer_name == "bronze" else None
    )
    for field_group, field_name in _filtered_group_fields(
        layer_context.payload, layer_name=layer_context.layer_name
    ):
        _add_entity_regular_field_node(
            snapshot,
            project,
            context,
            layer_context,
            scope=scope,
            field_group=field_group,
            field_name=field_name,
            drift_classification=drift_classification,
            layer_field_nodes=layer_field_nodes,
        )
    for metadata_field in _scd_config_columns(layer_context.layer_config).values():
        _add_entity_metadata_field_node(
            snapshot,
            project,
            context,
            layer_context,
            scope=scope,
            metadata_field=metadata_field,
            layer_field_nodes=layer_field_nodes,
        )
    return layer_field_nodes


def _add_entity_regular_field_node(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
    *,
    scope: EntityScope,
    field_group: str,
    field_name: str,
    drift_classification: str | None,
    layer_field_nodes: dict[str, NodeKey],
) -> None:
    field_quality = layer_context.quality_index.get(field_name, {})
    field_node = _add_schema_field_surface(
        snapshot,
        project,
        layer_context.surface,
        field_name=field_name,
        field_group=field_group,
        today=context.today,
        spec=SchemaFieldSpec(
            contract_ref=context.contract_ref,
            scope=scope,
            required_in_quality=(
                bool(field_quality.get("required_in_quality"))
                if field_quality.get("required_in_quality") is not None
                else None
            ),
            validation_types=_normalized_text_list(
                field_quality.get("validation_types")
            ),
            drift_classification=drift_classification,
        ),
    )
    layer_field_nodes[field_name] = field_node
    _link_schema_field_definition(snapshot, field_node, context.config_artifact)


def _add_entity_metadata_field_node(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
    *,
    scope: EntityScope,
    metadata_field: str | None,
    layer_field_nodes: dict[str, NodeKey],
) -> None:
    if metadata_field is None or metadata_field in layer_field_nodes:
        return
    field_node = _add_schema_field_surface(
        snapshot,
        project,
        layer_context.surface,
        field_name=metadata_field,
        field_group="system",
        today=context.today,
        spec=SchemaFieldSpec(
            contract_ref=context.contract_ref,
            scope=scope,
            drift_classification="runtime_metadata",
        ),
    )
    layer_field_nodes[metadata_field] = field_node
    _link_schema_field_definition(snapshot, field_node, context.config_artifact)


def _link_schema_field_definition(
    snapshot: GraphSnapshot,
    field_node: NodeKey,
    config_artifact: NodeKey,
) -> None:
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            field_node, "DEFINED_BY", config_artifact, provenance="schema_fields"
        )


def _add_entity_storage_layers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    quality_index: dict[str, dict[str, JsonValue]],
) -> tuple[dict[str, NodeKey], dict[str, dict[str, NodeKey]]]:
    layer_nodes: dict[str, NodeKey] = {}
    field_nodes_by_layer: dict[str, dict[str, NodeKey]] = {}
    scope = _entity_pipeline_scope(
        context.provider_name, context.entity_name, context.pipeline_name
    )
    for layer_name in ("bronze", "silver", "gold"):
        _add_entity_storage_layer(
            snapshot,
            project,
            context,
            payload,
            base_sink,
            pipeline_sink,
            quality_index,
            scope=scope,
            layer_name=layer_name,
            layer_nodes=layer_nodes,
            field_nodes_by_layer=field_nodes_by_layer,
        )
    return layer_nodes, field_nodes_by_layer


def _add_entity_storage_layer(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    quality_index: dict[str, dict[str, JsonValue]],
    *,
    scope: EntityScope,
    layer_name: str,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    layer_config = _merge_storage_layer_config(base_sink, pipeline_sink, layer_name)
    if _skip_entity_storage_layer(layer_name, layer_config):
        return
    surface = _create_entity_storage_layer_surface(
        snapshot,
        project,
        context,
        payload,
        scope=scope,
        layer_name=layer_name,
        layer_config=layer_config,
    )
    layer_nodes[layer_name] = surface
    _link_entity_storage_layer_backing(snapshot, context, surface)
    field_nodes_by_layer[layer_name] = _add_entity_layer_field_nodes(
        snapshot,
        project,
        context,
        EntityLayerFieldContext(
            payload=payload,
            surface=surface,
            layer_name=layer_name,
            quality_index=quality_index,
            layer_config=layer_config,
        ),
    )


def _add_storage_data_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    base_payload, base_sink = _base_pipeline_storage_config(root)
    schema_fields_by_storage: dict[str, dict[str, NodeKey]] = {}
    _add_entity_storage_data_surfaces(
        snapshot,
        root,
        project,
        today,
        base_payload=base_payload,
        base_sink=base_sink,
        schema_fields_by_storage=schema_fields_by_storage,
    )
    _add_composite_storage_data_surfaces(
        snapshot,
        root,
        project,
        today,
        schema_fields_by_storage=schema_fields_by_storage,
    )


def _add_entity_storage_data_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    *,
    base_payload: dict[str, object],
    base_sink: dict[str, object],
    schema_fields_by_storage: dict[str, dict[str, NodeKey]],
) -> None:
    entities_root = root / "configs" / "entities"
    for entity_path in sorted(entities_root.rglob(YAML_FILE_GLOB)):
        payload = _read_yaml(entity_path)
        context, pipeline_sink, quality_index = _entity_storage_context(
            root,
            entity_path,
            payload,
            today=today,
            base_payload=base_payload,
        )
        layer_nodes, field_nodes_by_layer = _add_entity_storage_layers(
            snapshot,
            project,
            context,
            payload=payload,
            base_sink=base_sink,
            pipeline_sink=pipeline_sink,
            quality_index=quality_index,
        )
        _index_storage_layer_fields(
            schema_fields_by_storage, layer_nodes, field_nodes_by_layer
        )
        _link_entity_storage_promotions(snapshot, layer_nodes, field_nodes_by_layer)


def _entity_storage_context(
    root: Path,
    entity_path: Path,
    payload: dict[str, object],
    *,
    today: str,
    base_payload: dict[str, object],
) -> tuple[
    EntityPipelineContext,
    dict[str, object],
    dict[str, dict[str, JsonValue]],
]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline_payload = _as_mapping(payload.get("pipeline"))
    pipeline_name = str(
        pipeline_payload.get("pipeline_name", f"{provider_name}_{entity_name}")
    )
    maintenance_config = _merged_maintenance_config(base_payload, payload)
    retention_days = maintenance_config.get("vacuum_retention_days")
    quality_payload = _as_mapping(payload.get("quality"))
    context = EntityPipelineContext(
        provider_name=provider_name,
        entity_name=entity_name,
        pipeline_name=pipeline_name,
        pipeline_key=NodeKey("pipeline_surface", pipeline_name),
        entity_key=NodeKey("entity_config", pipeline_name),
        config_artifact=NodeKey("config_artifact", _rel_path(root, entity_path)),
        today=today,
        contract_ref=f"{provider_name}.{entity_name}",
        retention_days=_coerce_int(retention_days)
        if isinstance(retention_days, int | float)
        else None,
        config_version=_optional_text(payload.get("version")),
        quality_version=_optional_text(quality_payload.get("version")),
    )
    pipeline_sink = _entity_pipeline_sink_config(payload)
    return context, pipeline_sink, _field_quality_index(payload)


def _add_control_plane_runtime_evidence(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _control_plane_runtime_evidence_specs():
        _add_runtime_evidence_surface(snapshot, project, today, spec)

    _add_control_plane_run_instance_surfaces(snapshot, root, project, today)


def _link_runtime_state_surface(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    _link_runtime_state_run_and_pipeline(snapshot, state, spec)
    _link_runtime_state_dependencies(snapshot, state, spec)
    _link_runtime_state_evidence_materials(snapshot, state, spec)


def _link_runtime_state_evidence_materials(
    snapshot: GraphSnapshot,
    state: NodeKey,
    spec: dict[str, object],
) -> None:
    for artifact_key in _runtime_state_artifact_targets(spec):
        if artifact_key in snapshot.nodes:
            snapshot.add_relation(
                state, "REFERENCES_ARTIFACT", artifact_key, provenance="runtime_state"
            )
    for doc_key in _runtime_state_doc_targets(spec):
        if doc_key in snapshot.nodes:
            snapshot.add_relation(
                state, "DESCRIBED_IN", doc_key, provenance="runtime_state"
            )


def _runtime_state_artifact_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    return tuple(
        NodeKey("control_plane_artifact_surface", str(artifact_name))
        for artifact_name in _as_iterable(spec.get("artifact_refs"))
    )


def _runtime_state_doc_targets(spec: dict[str, object]) -> tuple[NodeKey, ...]:
    return tuple(
        NodeKey("doc_artifact", str(doc_path))
        for doc_path in _as_iterable(spec.get("doc_paths"))
    )


def _add_control_plane_run_instance_surfaces(
    snapshot: GraphSnapshot,
    _root: Path,
    project: NodeKey,
    today: str,
) -> None:
    _add_run_instance_spec_surfaces(snapshot, project, today)
    _add_runtime_state_surfaces(snapshot, project, today)


def _add_run_instance_spec_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _control_plane_run_instance_specs():
        surface = _add_run_instance_surface(snapshot, project, today, spec)
        _link_run_instance_surface(snapshot, surface, spec)


def _add_runtime_state_surfaces(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
    _add_runtime_state_spec_surfaces(snapshot, project, today)


def _add_runtime_state_spec_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _runtime_state_specs():
        state = _add_runtime_state_surface(snapshot, project, today, spec)
        _link_runtime_state_surface(snapshot, state, spec)


def _workflow_script_targets(run_text: str) -> set[NodeKey]:
    targets: set[NodeKey] = set()
    targets.update(_workflow_module_script_targets(run_text))
    targets.update(_workflow_repo_path_targets(run_text))
    return targets


def _process_workflow_steps(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    steps: object,
) -> None:
    if not isinstance(steps, list):
        return
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses_ref = step.get("uses")
        if isinstance(uses_ref, str):
            _process_workflow_uses_step(snapshot, context, uses_ref, step)
        run_text = step.get("run")
        if not isinstance(run_text, str):
            continue
        _link_workflow_run_targets(snapshot, context, run_text)
        _add_secret_requirements(
            snapshot,
            context.job,
            _workflow_secret_refs(step),
            relative_path=context.relative_path,
            today=context.today,
        )


def _link_workflow_run_targets(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    run_text: str,
) -> None:
    for target in sorted(
        _workflow_script_targets(run_text), key=lambda item: (item.label, item.name)
    ):
        if target in snapshot.nodes:
            snapshot.add_relation(
                context.job, "RUNS_VIA", target, provenance="workflow_graph"
            )
    for gate_name in _workflow_quality_gates(run_text):
        gate_key = NodeKey("quality_gate", gate_name)
        if gate_key in snapshot.nodes:
            snapshot.add_relation(
                context.job, "EXECUTES_GATE", gate_key, provenance="workflow_graph"
            )


def _link_workflow_job_dependencies(
    snapshot: GraphSnapshot,
    workflow_name: str,
    jobs: dict[str, object],
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    for job_id, job_payload in jobs.items():
        if not isinstance(job_payload, dict):
            continue
        job = job_nodes.get((workflow_name, str(job_id)))
        if job is None:
            continue
        for dependency_id in _workflow_job_dependency_ids(job_payload):
            dependency_key = job_nodes.get((workflow_name, dependency_id))
            if dependency_key is not None:
                snapshot.add_relation(
                    job, "DEPENDS_ON", dependency_key, provenance="workflow_graph"
                )


def _workflow_job_dependency_ids(job_payload: dict[str, object]) -> tuple[str, ...]:
    needs_payload = job_payload.get("needs")
    if isinstance(needs_payload, str):
        return (needs_payload,)
    if isinstance(needs_payload, list):
        return tuple(str(item) for item in needs_payload if isinstance(item, str))
    return ()


def _add_ci_workflow_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    workflows_root = root / GITHUB_DIR / "workflows"
    if not workflows_root.is_dir():
        return

    workflow_files = _workflow_graph_files(workflows_root)
    workflow_name_by_relative_path = {
        _rel_path(root, workflow_path): workflow_path.stem
        for workflow_path in workflow_files
    }
    workflow_nodes: dict[str, NodeKey] = {}
    job_nodes: dict[tuple[str, str], NodeKey] = {}
    for workflow_path in workflow_files:
        _process_workflow_file(
            snapshot,
            root,
            project,
            today,
            workflow_path,
            workflow_nodes=workflow_nodes,
            workflow_name_by_relative_path=workflow_name_by_relative_path,
            job_nodes=job_nodes,
        )


def _workflow_graph_files(workflows_root: Path) -> list[Path]:
    return sorted(workflows_root.glob("*.y*ml"))


def _process_workflow_file(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    workflow_path: Path,
    *,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    workflow_name, payload, context, workflow_call_entrypoint = (
        _add_workflow_file_surface(
            snapshot,
            root,
            project,
            today,
            workflow_path,
        )
    )
    workflow_nodes[workflow_name] = context.workflow
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return
    _add_workflow_jobs(
        snapshot,
        context=context,
        jobs=jobs,
        workflow_nodes=workflow_nodes,
        workflow_name_by_relative_path=workflow_name_by_relative_path,
        workflow_call_entrypoint=workflow_call_entrypoint,
        job_nodes=job_nodes,
    )


def _add_workflow_jobs(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    jobs: dict[object, object],
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    for job_id, job_payload in jobs.items():
        if not isinstance(job_payload, dict):
            continue
        _process_workflow_job(
            snapshot,
            context=context,
            job_id=str(job_id),
            job_payload=job_payload,
            workflow_nodes=workflow_nodes,
            workflow_name_by_relative_path=workflow_name_by_relative_path,
            workflow_call_entrypoint=workflow_call_entrypoint,
            job_nodes=job_nodes,
        )
    _link_workflow_job_dependencies(
        snapshot,
        context.workflow_name,
        {str(key): value for key, value in jobs.items()},
        job_nodes,
    )


def _process_workflow_job(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    job_id: str,
    job_payload: dict[str, object],
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    job_context, matrix_variants, secret_usage_hints = _add_workflow_job_surface(
        snapshot,
        context,
        job_id=job_id,
        job_payload=job_payload,
    )
    _register_workflow_job(
        snapshot,
        context=context,
        job_id=job_id,
        job_context=job_context,
        workflow_call_entrypoint=workflow_call_entrypoint,
        job_nodes=job_nodes,
    )
    _populate_workflow_job_surface(
        snapshot,
        workflow_nodes=workflow_nodes,
        workflow_name_by_relative_path=workflow_name_by_relative_path,
        job_context=job_context,
        job_payload=job_payload,
        matrix_variants=matrix_variants,
        secret_usage_hints=secret_usage_hints,
    )


def _register_workflow_job(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    job_id: str,
    job_context: WorkflowJobContext,
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    job_nodes[(context.workflow_name, job_id)] = job_context.job
    if workflow_call_entrypoint is not None:
        snapshot.add_relation(
            job_context.job,
            "CALLS_WORKFLOW",
            workflow_call_entrypoint,
            provenance="workflow_graph",
        )


def _populate_workflow_job_surface(
    snapshot: GraphSnapshot,
    *,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_context: WorkflowJobContext,
    job_payload: dict[str, object],
    matrix_variants: tuple[dict[str, str], ...],
    secret_usage_hints: tuple[str, ...],
) -> None:
    _link_workflow_job_reusable_target(
        snapshot,
        workflow_nodes,
        workflow_name_by_relative_path,
        job_context,
        job_payload.get("uses"),
    )
    _add_secret_requirements(
        snapshot,
        job_context.job,
        secret_usage_hints,
        relative_path=job_context.relative_path,
        today=job_context.today,
    )
    _add_job_matrix_variants(snapshot, job_context, matrix_variants)
    _add_job_outputs(snapshot, job_context, job_payload.get("outputs"))
    _process_workflow_steps(snapshot, job_context, job_payload.get("steps"))


def _normalize_docs_repo_reference(raw_ref: str) -> str | None:
    candidate = _trim_docs_reference_candidate(raw_ref)
    if not candidate:
        return None
    candidate = _normalize_docs_glob_candidate(candidate)
    candidate = candidate.rstrip("/")
    if candidate in {"README.md", "mkdocs.yml"}:
        return candidate
    if any(candidate.startswith(prefix) for prefix in _DOCS_REFERENCE_ALLOWED_PREFIXES):
        return candidate
    return None


def _markdown_heading_context(text: str, offset: int) -> tuple[str | None, str | None]:
    current_title: str | None = None
    current_anchor: str | None = None
    for line_start, title in _markdown_headings(text):
        if line_start > offset:
            break
        current_title = title
        current_anchor = _heading_anchor_slug(current_title)
    return current_title, current_anchor


def _add_docs_to_code_drift_edges(snapshot: GraphSnapshot, root: Path) -> None:
    path_pattern = _docs_path_pattern()
    command_pattern = _docs_command_pattern()
    config = _file_structure_config(_load_memory_mapping(root))
    for source_node, source_path, text in _docs_drift_sources(snapshot, root, config):
        _add_doc_path_reference_edges(snapshot, source_node, text, path_pattern)
        _add_doc_command_reference_edges(snapshot, source_node, text, command_pattern)
        _add_doc_claim_edges(snapshot, source_node, source_path, text, path_pattern)


def _add_adr_constraint_edges(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    decisions_dir = root / ADR_DECISIONS_DIR
    if not decisions_dir.is_dir():
        return
    path_pattern = _docs_path_pattern()
    for adr_path in sorted(decisions_dir.glob("ADR-*.md")):
        _add_single_adr_constraint_edges(
            snapshot,
            root,
            project,
            today,
            adr_path,
            path_pattern,
        )


def _add_single_adr_constraint_edges(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    adr_path: Path,
    path_pattern: re.Pattern[str],
) -> None:
    relative_adr_path = _rel_path(root, adr_path)
    adr_node = _add_adr_decision_node(snapshot, root, project, today, adr_path)
    adr_doc = NodeKey("doc_artifact", relative_adr_path)
    if adr_doc in snapshot.nodes:
        snapshot.add_relation(
            adr_node, "DESCRIBED_IN", adr_doc, provenance="adr_constraints"
        )
    text = _read_text(adr_path)
    seen_targets: set[NodeKey] = set()
    for path_match in path_pattern.finditer(text):
        normalized = _normalize_docs_repo_reference(path_match.group(1))
        if normalized is None or normalized == relative_adr_path:
            continue
        target = _resolve_adr_constraint_target(snapshot, normalized)
        if target is None or target in seen_targets:
            continue
        seen_targets.add(target)
        section_title, section_anchor, line_number = _doc_reference_context(
            text, path_match.start()
        )
        snapshot.add_relation(
            adr_node,
            "CONSTRAINS",
            target,
            provenance="adr_path_reference",
            doc_reference=normalized,
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            confidence="medium",
        )


def _add_adr_decision_node(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    adr_path: Path,
) -> NodeKey:
    relative_adr_path = _rel_path(root, adr_path)
    title = _adr_title(adr_path)
    adr_node = snapshot.add_node(
        "decision",
        adr_path.stem,
        summary=title,
        source_path=relative_adr_path,
        source_kind="adr",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_DECISION", adr_node, provenance="adr")
    return adr_node


def _adr_title(adr_path: Path) -> str:
    text = _read_text(adr_path)
    for _offset, title in _markdown_headings(text):
        return title
    return adr_path.stem


def _resolve_adr_constraint_target(
    snapshot: GraphSnapshot, normalized_ref: str
) -> NodeKey | None:
    for candidate in _adr_constraint_candidates(normalized_ref):
        if candidate in snapshot.nodes:
            return candidate
    return None


def _doc_reference_context(
    text: str, offset: int
) -> tuple[str | None, str | None, int]:
    section_title, section_anchor = _markdown_heading_context(text, offset)
    line_number = text.count("\n", 0, offset) + 1
    return section_title, section_anchor, line_number


def _add_doc_path_reference_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    text: str,
    path_pattern: re.Pattern[str],
) -> None:
    seen_matches: set[tuple[str, str]] = set()
    for path_match in path_pattern.finditer(text):
        match = path_match.group(1)
        normalized = _normalize_docs_repo_reference(match)
        if normalized is None:
            continue
        target, evidence_kind, confidence = _resolve_docs_reference_target(
            snapshot, normalized
        )
        if target is None or target == source_node:
            continue
        dedupe_key = (normalized, target.name)
        if dedupe_key in seen_matches:
            continue
        seen_matches.add(dedupe_key)
        _add_doc_describes_relation(
            snapshot,
            source_node,
            target,
            text,
            path_match.start(),
            doc_reference=normalized,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )


def _add_doc_command_reference_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    text: str,
    command_pattern: re.Pattern[str],
) -> None:
    seen_commands: set[str] = set()
    for command_match in command_pattern.finditer(text):
        raw_command = command_match.group(0).strip()
        command_name = _normalize_cli_command_name(raw_command)
        if command_name is None or command_name in seen_commands:
            continue
        command_key = NodeKey("cli_command_surface", command_name)
        if command_key not in snapshot.nodes:
            continue
        seen_commands.add(command_name)
        _add_doc_describes_relation(
            snapshot,
            source_node,
            command_key,
            text,
            command_match.start(),
            doc_reference=raw_command,
            evidence_kind="command_reference",
            confidence="medium",
        )


def _add_doc_describes_relation(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    target: NodeKey,
    text: str,
    offset: int,
    *,
    doc_reference: str,
    evidence_kind: str,
    confidence: str,
) -> None:
    section_title, section_anchor, line_number = _doc_reference_context(text, offset)
    snapshot.add_relation(
        source_node,
        "DESCRIBES",
        target,
        provenance="docs_code_drift",
        doc_reference=doc_reference,
        evidence_kind=evidence_kind,
        confidence=confidence,
        section_title=section_title,
        section_anchor=section_anchor,
        line_number=line_number,
    )


def _add_doc_claim_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    source_path: str,
    text: str,
    path_pattern: re.Pattern[str],
) -> None:
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        claim_line = _claim_line_context(raw_line)
        if claim_line is None:
            continue
        section_title, section_anchor = _claim_section_context(text, raw_line)
        claim = snapshot.add_node(
            "doc_claim_surface",
            f"{source_path}#L{line_number}",
            summary=f"Claim extracted from `{source_path}`.",
            source_path=source_path,
            source_kind="doc_claim_surface",
            claim_text=claim_line.clean_text,
            modality=_claim_modality(claim_line.clean_text),
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            last_verified=str(date.today()),
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(source_node, "ASSERTS", claim, provenance="docs_claims")
        claim_has_target = _add_claim_path_targets(
            snapshot,
            claim,
            source_node,
            claim_line.stripped,
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            path_pattern=path_pattern,
        )
        claim_has_target = (
            _add_claim_token_targets(
                snapshot,
                claim,
                claim_line.clean_text,
                section_title=section_title,
                section_anchor=section_anchor,
                line_number=line_number,
            )
            or claim_has_target
        )
        if not claim_has_target:
            _add_claim_fallback_target(
                snapshot,
                claim,
                source_path,
                section_title=section_title,
                section_anchor=section_anchor,
                line_number=line_number,
            )


def _claim_line_context(raw_line: str) -> ClaimLineContext | None:
    stripped = raw_line.strip()
    if not _is_claim_candidate(stripped):
        return None
    return ClaimLineContext(
        stripped=stripped,
        clean_text=stripped.lstrip("-*0123456789. ").strip(),
    )


def _claim_section_context(text: str, raw_line: str) -> tuple[str | None, str | None]:
    line_offset = text.find(raw_line)
    return _markdown_heading_context(text, line_offset)


def _add_claim_path_targets(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    source_node: NodeKey,
    stripped: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
    path_pattern: re.Pattern[str],
) -> bool:
    claim_has_target = False
    for claim_match in path_pattern.finditer(stripped):
        normalized = _normalize_docs_repo_reference(claim_match.group(1))
        if normalized is None:
            continue
        target, evidence_kind, confidence = _resolve_docs_reference_target(
            snapshot, normalized
        )
        if target is None or target == source_node:
            continue
        _add_claim_target_relation(
            snapshot,
            claim,
            target,
            provenance="docs_claims",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            doc_reference=normalized,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )
        claim_has_target = True
    return claim_has_target


def _contract_mapping_config(
    memory_mapping: dict[str, object],
) -> ContractMappingConfig:
    contracts_mapping = _mapping_dict_or_empty(memory_mapping.get("contracts"))
    return ContractMappingConfig(
        source_prefixes=_contract_source_prefixes(contracts_mapping),
        control_plane_modules=_contract_mapping_values(
            contracts_mapping, "control_plane_modules"
        ),
        control_plane_runtime_modules=_contract_mapping_values(
            contracts_mapping, "control_plane_runtime_modules"
        ),
        lineage_modules=_contract_mapping_values(contracts_mapping, "lineage_modules"),
        lineage_runtime_modules=_contract_mapping_values(
            contracts_mapping, "lineage_runtime_modules"
        ),
        control_plane_docs=_contract_mapping_values(
            contracts_mapping, "control_plane_docs"
        ),
        lineage_docs=_contract_mapping_values(contracts_mapping, "lineage_docs"),
        control_plane_anchor_fields=_contract_mapping_values(
            contracts_mapping, "control_plane_anchor_fields"
        ),
        lineage_anchor_fields=_contract_mapping_values(
            contracts_mapping, "lineage_anchor_fields"
        ),
    )


def _contract_source_prefixes(contracts_mapping: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        _contract_mapping_values(contracts_mapping, "registry_source_prefixes")
        or [
            "bioetl.domain.contracts.gold",
            "bioetl.domain.schemas",
        ]
    )


def _add_published_contract_artifacts(
    snapshot: GraphSnapshot, context: ContractEntryContext
) -> None:
    for published_path in _published_contract_artifact_paths(context):
        artifact = _published_contract_artifact_key(snapshot, context, published_path)
        if artifact is None:
            continue
        snapshot.add_relation(
            context.contract, "BACKED_BY", artifact, provenance="impact_contracts"
        )


def _contract_registry_entries(root: Path) -> dict[str, dict[str, object]]:
    return {
        contract_ref: raw_entry
        for contract_ref, raw_entry in sorted(_contract_registry_payload(root).items())
        if isinstance(contract_ref, str) and isinstance(raw_entry, dict)
    }


def _contract_registry_payload(root: Path) -> dict[object, object]:
    payload = load_contract_registry_payload(root / DEFAULT_CONTRACT_REGISTRY_PATH)
    entries = payload.get("entries")
    return entries if isinstance(entries, dict) else {}


def _link_contract_dependencies(
    snapshot: GraphSnapshot,
    entry_context: ContractEntryContext,
    mapping_config: ContractMappingConfig,
) -> None:
    _link_contract_source_dependencies(
        snapshot, entry_context, mapping_config.source_prefixes
    )
    _add_contract_policy_config(snapshot, entry_context)
    _add_published_contract_artifacts(snapshot, entry_context)
    _link_contract_dependency_modules(snapshot, entry_context, mapping_config)
    _link_contract_dependency_docs(snapshot, entry_context, mapping_config)


def _add_contract_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> dict[str, NodeKey]:
    registry_artifact = _add_contract_registry_artifact(snapshot, root, today)
    if registry_artifact is None:
        return {}
    entries = _contract_registry_entries(root)
    if not entries:
        return {}
    mapping_config = _contract_mapping_config(memory_mapping)

    contract_nodes: dict[str, NodeKey] = {}
    for contract_ref, raw_entry in entries.items():
        _register_contract_entry(
            snapshot,
            root,
            project,
            registry_artifact,
            contract_ref=contract_ref,
            raw_entry=raw_entry,
            today=today,
            mapping_config=mapping_config,
            contract_nodes=contract_nodes,
        )

    return contract_nodes


def _register_contract_entry(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    registry_artifact: NodeKey,
    *,
    contract_ref: str,
    raw_entry: dict[str, object],
    today: str,
    mapping_config: ContractMappingConfig,
    contract_nodes: dict[str, NodeKey],
) -> None:
    entry_context = _add_contract_entry_surface(
        snapshot,
        root,
        project,
        registry_artifact,
        contract_ref=contract_ref,
        raw_entry=raw_entry,
        today=today,
    )
    contract_nodes[contract_ref] = entry_context.contract
    _link_contract_dependencies(snapshot, entry_context, mapping_config)


def _link_duplication_override_relations(
    snapshot: GraphSnapshot,
    class_descriptors: dict[NodeKey, ClassDescriptor],
    class_name_index: dict[str, list[NodeKey]],
    class_method_index: dict[tuple[NodeKey, str], NodeKey],
) -> None:
    for class_descriptor in class_descriptors.values():
        for base_class in _resolved_base_classes(
            snapshot, class_descriptor, class_name_index
        ):
            snapshot.add_relation(
                class_descriptor.node_key,
                "DEPENDS_ON",
                base_class,
                provenance="code_duplication",
            )
            _link_duplication_override_methods(
                snapshot,
                class_descriptor=class_descriptor,
                base_class=base_class,
                class_method_index=class_method_index,
            )


def _duplication_promotion_target(
    snapshot: GraphSnapshot,
    config: dict[str, object],
    family_name: str,
    surface_kind: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey | None:
    promotion_target = _method_surface_promotion_target(
        snapshot, surface_kind, unique_members
    )
    if promotion_target is not None:
        return promotion_target
    family = _duplication_family_by_name(config, family_name)
    if not isinstance(family, DuplicateFamilyConfig):
        return None
    for candidate in family.promotion_targets:
        if candidate in snapshot.nodes:
            return candidate
    return None


def _method_surface_promotion_target(
    snapshot: GraphSnapshot,
    surface_kind: str,
    unique_members: list[CallableDescriptor],
) -> NodeKey | None:
    if surface_kind != "method_surface" or not unique_members:
        return None
    method_name = unique_members[0].callable_name
    if not all(
        member.callable_name == method_name and member.parent_class
        for member in unique_members
    ):
        return None
    common_base_candidates: set[NodeKey] | None = None
    for member in unique_members:
        class_targets = _override_target_classes(snapshot, member)
        common_base_candidates = (
            class_targets
            if common_base_candidates is None
            else common_base_candidates & class_targets
        )
    if not common_base_candidates:
        return None
    return sorted(common_base_candidates, key=lambda item: item.name)[0]


def _emit_duplication_clusters(
    snapshot: GraphSnapshot,
    project: NodeKey,
    *,
    today: str,
    config: dict[str, object],
    callable_descriptors: dict[NodeKey, CallableDescriptor],
    min_cluster_size: int,
    min_ast_nodes: int,
) -> None:
    for (family_name, surface_kind, shape_hash), members in _duplication_cluster_groups(
        callable_descriptors,
        min_ast_nodes=min_ast_nodes,
    ):
        if len(members) < min_cluster_size:
            continue
        unique_members = sorted(members, key=lambda item: item.node_key.name)
        cluster = _add_duplication_cluster_node(
            snapshot,
            today=today,
            family_name=family_name,
            surface_kind=surface_kind,
            shape_hash=shape_hash,
            unique_members=unique_members,
        )
        snapshot.add_relation(
            project, "CONTAINS", cluster, provenance="code_duplication"
        )
        _link_duplication_cluster_members(snapshot, cluster, unique_members)
        _link_same_shape_members(snapshot, unique_members)
        promotion_target = _duplication_promotion_target(
            snapshot, config, family_name, surface_kind, unique_members
        )
        if promotion_target is not None:
            snapshot.add_relation(
                cluster,
                "CAN_PROMOTE_TO",
                promotion_target,
                provenance="code_duplication",
            )
        package_family = NodeKey("package_family", unique_members[0].package_family)
        for relation in tuple(snapshot.relations.values()):
            if (
                relation.relation_type == "TESTS_PACKAGE_FAMILY"
                and relation.target == package_family
            ):
                snapshot.add_relation(
                    cluster,
                    "COVERED_BY_TEST",
                    relation.source,
                    provenance="code_duplication",
                )


def _extract_code_duplication_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    config = _duplication_analysis_config(memory_mapping)
    if not bool(config.get("enabled", True)):
        return

    min_cluster_size, min_ast_nodes = _duplication_cluster_thresholds(config)
    extraction = DuplicationExtractionContext(
        snapshot=snapshot,
        root=root,
        today=today,
        config=config,
    )
    for module in tuple(snapshot.nodes.values()):
        if module.key.label != "module_surface":
            continue
        _collect_duplication_descriptors_for_module(extraction, module)

    class_method_index = _duplication_class_method_index(
        extraction.callable_descriptors
    )
    _link_duplication_override_relations(
        snapshot,
        extraction.class_descriptors,
        extraction.class_name_index,
        class_method_index,
    )
    _emit_duplication_clusters(
        snapshot,
        project,
        today=today,
        config=config,
        callable_descriptors=extraction.callable_descriptors,
        min_cluster_size=min_cluster_size,
        min_ast_nodes=min_ast_nodes,
    )


def _duplication_cluster_thresholds(config: dict[str, object]) -> tuple[int, int]:
    return _coerce_int(config.get("min_cluster_size", 2), 2), _coerce_int(
        config.get("min_ast_nodes", 12), 12
    )


def _add_retirement_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    config = _retirement_analysis_config(memory_mapping, duplication_config)
    if not config.enabled or not config.family_names:
        return
    context = _retirement_analysis_context(snapshot, config, today)

    candidate_nodes = _retirement_candidate_nodes(
        snapshot,
        duplication_config=duplication_config,
        family_names=context.family_names,
        family_cache=context.family_cache,
    )
    _prime_retirement_age_cache(
        root, context.today_date, context.age_cache, candidate_nodes
    )

    for node, source_path, family, module_key in candidate_nodes:
        candidate_payload = _retirement_candidate_payload(
            snapshot,
            root,
            node,
            source_path,
            module_key,
            indexes=context.indexes,
            label_sets=context.label_sets,
            text_cache=context.text_cache,
            age_cache=context.age_cache,
            family_name=family.name,
            config=config,
        )
        if candidate_payload is None:
            continue
        _emit_retirement_candidate(
            snapshot, project, today, config, node, candidate_payload
        )


def _add_complexity_analysis_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> None:
    duplication_config = _duplication_analysis_config(memory_mapping)
    retirement_config = _retirement_analysis_config(memory_mapping, duplication_config)
    config = _complexity_analysis_config(
        memory_mapping, duplication_config, retirement_config
    )
    if not config.enabled or not config.family_names:
        return
    analysis_context = _complexity_analysis_context(snapshot, config)
    for node in sorted(
        snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)
    ):
        candidate_payload = _evaluate_complexity_surface(
            snapshot,
            root,
            node,
            duplication_config=duplication_config,
            family_names=analysis_context.family_names,
            family_cache=analysis_context.family_cache,
            label_sets=analysis_context.label_sets,
            indexes=analysis_context.indexes,
            text_cache=analysis_context.text_cache,
            config=config,
        )
        if candidate_payload is None:
            continue
        _emit_complexity_candidate(
            snapshot, project, today, config, node, candidate_payload
        )


def _complexity_analysis_context(
    snapshot: GraphSnapshot,
    config: ComplexityAnalysisConfig,
) -> ComplexityAnalysisContext:
    return ComplexityAnalysisContext(
        family_names=set(config.family_names),
        label_sets=_complexity_analysis_label_sets(),
        indexes=_build_surface_relation_indexes(snapshot),
    )


def _complexity_surface_measurements(
    snapshot: GraphSnapshot,
    node: GraphNode,
    *,
    source_path: str,
    module_key: NodeKey,
    source_text: str,
    label_sets: AnalysisLabelSets,
    indexes: SurfaceRelationIndexes,
    config: ComplexityAnalysisConfig,
) -> tuple[
    SurfaceAnchorSets,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    SurfaceComplexityMetrics,
    bool,
    float,
    float,
    float,
]:
    anchors = _collect_analysis_anchor_nodes(
        snapshot, indexes, node.key, module_key, label_sets
    )
    symbol_name = node.key.name.removeprefix(f"{_module_dotted_name(source_path)}.")
    indirection_markers, stateful_markers, deprecation_markers = (
        _complexity_marker_buckets(
            config,
            source_path,
            symbol_name,
            source_text,
        )
    )
    metrics = _aggregate_surface_complexity_metrics(snapshot, indexes, node.key)
    blocked_by_current_cycle = bool(node.properties.get("current_cycle_status"))
    complexity_score, simplification_score, removable_score = (
        _complexity_surface_scores(
            metrics,
            anchors,
            blocked_by_current_cycle=blocked_by_current_cycle,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
        )
    )
    return (
        anchors,
        indirection_markers,
        stateful_markers,
        deprecation_markers,
        metrics,
        blocked_by_current_cycle,
        complexity_score,
        simplification_score,
        removable_score,
    )


def _complexity_surface_scores(
    metrics: SurfaceComplexityMetrics,
    anchors: SurfaceAnchorSets,
    *,
    blocked_by_current_cycle: bool,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
) -> tuple[float, float, float]:
    return _complexity_scores(
        metrics,
        _complexity_score_inputs(
            anchors,
            blocked_by_current_cycle=blocked_by_current_cycle,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
        ),
    )


def _complexity_score_inputs(
    anchors: SurfaceAnchorSets,
    *,
    blocked_by_current_cycle: bool,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
) -> ComplexityScoreInputs:
    return ComplexityScoreInputs(
        indirection_markers=indirection_markers,
        stateful_markers=stateful_markers,
        deprecation_markers=deprecation_markers,
        runtime_count=len(anchors.runtime),
        config_count=len(anchors.config),
        doc_count=len(anchors.docs),
        test_count=len(anchors.tests),
        blocked_by_current_cycle=blocked_by_current_cycle,
    )


def _complexity_candidate_context(
    payload: dict[str, object],
    *,
    config: ComplexityAnalysisConfig,
) -> ComplexityCandidateContext:
    anchors = cast("SurfaceAnchorSets", payload["anchors"])
    runtime_anchors, config_anchors, doc_anchors, test_anchors = (
        _complexity_candidate_anchor_slices(
            anchors,
            blocker_anchor_limit=config.blocker_anchor_limit,
        )
    )
    return ComplexityCandidateContext(
        anchors=anchors,
        metrics=cast("SurfaceComplexityMetrics", payload["metrics"]),
        runtime_anchors=runtime_anchors,
        config_anchors=config_anchors,
        doc_anchors=doc_anchors,
        test_anchors=test_anchors,
        blocked_by_current_cycle=bool(payload["blocked_by_current_cycle"]),
        simplification_score=_coerce_float(payload["simplification_score"]),
        classification=str(payload["classification"]),
    )


def _evaluate_complexity_surface(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
    label_sets: AnalysisLabelSets,
    indexes: SurfaceRelationIndexes,
    text_cache: dict[str, str],
    config: ComplexityAnalysisConfig,
) -> dict[str, object] | None:
    prerequisites = _complexity_surface_prerequisites(
        snapshot,
        root,
        node,
        duplication_config=duplication_config,
        family_names=family_names,
        family_cache=family_cache,
        text_cache=text_cache,
    )
    if prerequisites is None:
        return None
    source_path, family, module_key, source_text = prerequisites
    (
        anchors,
        indirection_markers,
        stateful_markers,
        deprecation_markers,
        metrics,
        blocked_by_current_cycle,
        complexity_score,
        simplification_score,
        removable_score,
    ) = _complexity_surface_measurements(
        snapshot,
        node,
        source_path=source_path,
        module_key=module_key,
        source_text=source_text,
        label_sets=label_sets,
        indexes=indexes,
        config=config,
    )
    anchor_counts = _analysis_anchor_counts(anchors)
    if not _should_emit_complexity_candidate(
        config,
        complexity_score=complexity_score,
        removable_score=removable_score,
    ):
        return None
    classification, removal_confidence = _complexity_candidate_classification(
        config,
        removable_score=removable_score,
        anchor_counts=anchor_counts,
        blocked_by_current_cycle=blocked_by_current_cycle,
    )
    return _complexity_surface_payload(
        source_path=source_path,
        family_name=family.name,
        anchors=anchors,
        metrics=metrics,
        indirection_markers=indirection_markers,
        stateful_markers=stateful_markers,
        deprecation_markers=deprecation_markers,
        blocked_by_current_cycle=blocked_by_current_cycle,
        classification=classification,
        complexity_score=complexity_score,
        simplification_score=simplification_score,
        removable_score=removable_score,
        removal_confidence=removal_confidence,
    )


def _emit_complexity_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    config: ComplexityAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
) -> None:
    context = _complexity_candidate_context(payload, config=config)
    candidate = _add_complexity_candidate_node(
        snapshot,
        today,
        config,
        node,
        payload,
        context=context,
    )
    _link_complexity_candidate(
        snapshot,
        project,
        candidate,
        node.key,
        context=context,
    )


def _complexity_candidate_anchor_slices(
    anchors: SurfaceAnchorSets,
    *,
    blocker_anchor_limit: int,
) -> tuple[
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
]:
    return (
        anchors.runtime[:blocker_anchor_limit],
        anchors.config[:blocker_anchor_limit],
        anchors.docs[:blocker_anchor_limit],
        anchors.tests[:blocker_anchor_limit],
    )


def _link_complexity_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    candidate: NodeKey,
    target: NodeKey,
    *,
    context: ComplexityCandidateContext,
) -> None:
    snapshot.add_relation(
        project, "CONTAINS", candidate, provenance="complexity_analysis"
    )
    snapshot.add_relation(
        target, "HAS_COMPLEXITY_SIGNAL", candidate, provenance="complexity_analysis"
    )
    snapshot.add_relation(
        candidate,
        "CANDIDATE_FOR_SIMPLIFICATION",
        target,
        provenance="complexity_analysis",
    )
    if context.classification == "removable_complexity":
        snapshot.add_relation(
            candidate, "CANDIDATE_FOR_REMOVAL", target, provenance="complexity_analysis"
        )
    for anchor in context.runtime_anchors:
        snapshot.add_relation(
            candidate, "JUSTIFIED_BY_RUNTIME", anchor, provenance="complexity_analysis"
        )
    for anchor in [*context.config_anchors, *context.doc_anchors]:
        snapshot.add_relation(
            candidate, "BLOCKED_BY_VARIANCE", anchor, provenance="complexity_analysis"
        )


def _add_complexity_candidate_node(
    snapshot: GraphSnapshot,
    today: str,
    config: ComplexityAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
    *,
    context: ComplexityCandidateContext,
) -> NodeKey:
    blocker_context = _complexity_blocker_context(
        node,
        blocked_by_current_cycle=context.blocked_by_current_cycle,
    )
    return snapshot.add_node(
        "complexity_candidate",
        f"{node.key.label}:{node.key.name}",
        summary=f"Complexity analysis candidate for `{node.key.name}` in `{payload['family_name']}`.",
        source_path=str(payload["source_path"]),
        source_kind="complexity_candidate",
        family_name=str(payload["family_name"]),
        target_label=node.key.label,
        target_name=node.key.name,
        classification=context.classification,
        complexity_score=payload["complexity_score"],
        simplification_score=payload["simplification_score"],
        removable_score=payload["removable_score"],
        simplification_confidence="high"
        if context.simplification_score >= config.complexity_score_threshold + 2
        else "medium",
        removal_confidence=payload["removal_confidence"],
        branch_count=context.metrics.branch_count,
        nesting_depth=context.metrics.nesting_depth,
        call_count=context.metrics.call_count,
        helper_call_count=context.metrics.helper_call_count,
        abstraction_fanout=context.metrics.abstraction_fanout,
        api_surface_to_logic_ratio=context.metrics.api_surface_to_logic_ratio,
        runtime_anchor_count=len(context.anchors.runtime),
        config_anchor_count=len(context.anchors.config),
        doc_anchor_count=len(context.anchors.docs),
        test_anchor_count=len(context.anchors.tests),
        indirection_markers=payload["indirection_markers"],
        stateful_markers=payload["stateful_markers"],
        deprecation_markers=payload["deprecation_markers"],
        blocked_by_current_cycle=context.blocked_by_current_cycle,
        blocked_by_current_cycle_target_name=blocker_context["target_name"],
        blocked_by_current_cycle_score=blocker_context["score"],
        blocked_by_current_cycle_wip_markers=blocker_context["wip_markers"],
        runtime_anchors=[anchor.name for anchor in context.runtime_anchors],
        config_anchors=[anchor.name for anchor in context.config_anchors],
        doc_anchors=[anchor.name for anchor in context.doc_anchors],
        test_anchors=[anchor.name for anchor in context.test_anchors],
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )


def _add_pipeline_test_edges(
    snapshot: GraphSnapshot,
    root: Path,
    _pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    test_context = _pipeline_test_context(
        snapshot, root, memory_mapping.get("pipeline_tests")
    )
    if test_context is None:
        return
    test_linker = _pipeline_test_linker(snapshot, test_context.relation_type)
    _link_entity_pipeline_tests(
        test_linker,
        test_context.entity_pipeline_index,
        test_context.ownership,
    )
    _link_provider_regression_suite_tests(
        test_linker,
        test_context.provider_pipeline_index,
        suites=test_context.provider_regression_suites,
        enabled=test_context.include_provider_regression_suites,
    )


@dataclass(frozen=True)
class PipelineTestContext:
    relation_type: str
    ownership: dict[object, object]
    provider_regression_suites: object
    include_provider_regression_suites: bool
    entity_pipeline_index: dict[tuple[str, str], NodeKey]
    provider_pipeline_index: dict[str, list[NodeKey]]


def _pipeline_test_context(
    snapshot: GraphSnapshot,
    root: Path,
    tests_mapping: object,
) -> PipelineTestContext | None:
    relation_type, ownership_config, include_provider_regression_suites = (
        _pipeline_test_mapping_config(tests_mapping)
    )
    payload, ownership = _pipeline_test_payload(root, ownership_config)
    if payload is None or ownership is None:
        return None
    entity_pipeline_index, provider_pipeline_index = _pipeline_test_indexes(snapshot)
    return PipelineTestContext(
        relation_type=relation_type,
        ownership=ownership,
        provider_regression_suites=payload.get("provider_regression_suites"),
        include_provider_regression_suites=include_provider_regression_suites,
        entity_pipeline_index=entity_pipeline_index,
        provider_pipeline_index=provider_pipeline_index,
    )


def _pipeline_test_payload(
    root: Path,
    ownership_config: str,
) -> tuple[dict[str, object] | None, dict[object, object] | None]:
    ownership_path = _pipeline_test_ownership_path(root, ownership_config)
    if not ownership_path.is_file():
        return None, None
    payload = _read_yaml(ownership_path)
    return payload, _pipeline_test_ownership(payload)


def _pipeline_test_ownership_path(root: Path, ownership_config: str) -> Path:
    return root / ownership_config


def _pipeline_test_ownership(payload: dict[str, object]) -> dict[object, object] | None:
    ownership = payload.get("entity_test_ownership")
    return ownership if isinstance(ownership, dict) else None


def _pipeline_test_mapping_config(
    tests_mapping: object,
) -> tuple[str, str, bool]:
    if not isinstance(tests_mapping, dict):
        return "TESTED_BY", TEST_MATRIX_CONFIG_PATH, True
    return (
        str(tests_mapping.get("relation_type", "TESTED_BY")),
        str(tests_mapping.get("ownership_config", TEST_MATRIX_CONFIG_PATH)),
        bool(tests_mapping.get("provider_regression_suites", True)),
    )


def _pipeline_test_indexes(
    snapshot: GraphSnapshot,
) -> tuple[dict[tuple[str, str], NodeKey], dict[str, list[NodeKey]]]:
    return _entity_pipeline_test_index(snapshot), _provider_pipeline_test_index(
        snapshot
    )


def _entity_pipeline_test_index(
    snapshot: GraphSnapshot,
) -> dict[tuple[str, str], NodeKey]:
    return {
        identity: node.key
        for node in snapshot.nodes.values()
        for identity in [_entity_pipeline_node_identity(node)]
        if identity is not None
    }


def _entity_pipeline_node_identity(node: GraphNode) -> tuple[str, str] | None:
    if (
        node.key.label != "pipeline_surface"
        or node.properties.get("pipeline_kind") != "entity"
    ):
        return None
    return str(node.properties.get("provider")), str(node.properties.get("entity"))


def _provider_pipeline_test_index(snapshot: GraphSnapshot) -> dict[str, list[NodeKey]]:
    provider_pipeline_index: dict[str, list[NodeKey]] = {}
    for provider, node_key in _provider_pipeline_index_entries(snapshot):
        provider_pipeline_index.setdefault(provider, []).append(node_key)
    return provider_pipeline_index


def _provider_pipeline_index_entries(
    snapshot: GraphSnapshot,
) -> tuple[tuple[str, NodeKey], ...]:
    return tuple(
        (provider, node.key)
        for node in snapshot.nodes.values()
        for provider in [_provider_pipeline_index_key(node)]
        if provider is not None
    )


def _provider_pipeline_index_key(node: GraphNode) -> str | None:
    if node.key.label != "pipeline_surface":
        return None
    provider = node.properties.get("provider")
    return provider if isinstance(provider, str) else None


def _pipeline_test_linker(
    snapshot: GraphSnapshot,
    relation_type: str,
) -> Callable[[NodeKey, str, str], None]:
    def link_test_target(
        pipeline_key: NodeKey, test_path: str, provenance: str
    ) -> None:
        artifact_key = _test_artifact_key(test_path)
        if artifact_key not in snapshot.nodes:
            return
        _link_pipeline_test_artifact(
            snapshot, pipeline_key, relation_type, artifact_key, provenance
        )
        _link_pipeline_test_suite(
            snapshot, pipeline_key, relation_type, artifact_key, provenance
        )

    return link_test_target


def _test_artifact_key(test_path: str) -> NodeKey:
    return NodeKey("test_artifact", test_path)


def _link_pipeline_test_artifact(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    relation_type: str,
    artifact_key: NodeKey,
    provenance: str,
) -> None:
    snapshot.add_relation(
        pipeline_key, relation_type, artifact_key, provenance=provenance
    )


def _link_pipeline_test_suite(
    snapshot: GraphSnapshot,
    pipeline_key: NodeKey,
    relation_type: str,
    artifact_key: NodeKey,
    provenance: str,
) -> None:
    suite_name = _pipeline_test_suite_name(snapshot, artifact_key)
    if suite_name is None:
        return
    snapshot.add_relation(
        pipeline_key,
        relation_type,
        NodeKey("test_surface", suite_name),
        provenance=provenance,
    )


def _pipeline_test_suite_name(
    snapshot: GraphSnapshot,
    artifact_key: NodeKey,
) -> str | None:
    return TEST_SURFACES.get(
        str(snapshot.nodes[artifact_key].properties.get("suite", ""))
    )


def _link_entity_pipeline_tests(
    link_test_target: Callable[[NodeKey, str, str], None],
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    ownership: dict[object, object],
) -> None:
    _link_pipeline_test_targets(
        link_test_target,
        _entity_pipeline_contract_tests(entity_pipeline_index, ownership),
        provenance="impact_pipeline_tests",
    )


def _entity_pipeline_contract_tests(
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    ownership: dict[object, object],
) -> tuple[tuple[NodeKey, tuple[str, ...]], ...]:
    return tuple(
        target
        for contract_ref, raw_tests in ownership.items()
        for target in [
            _entity_pipeline_contract_target(
                entity_pipeline_index, contract_ref, raw_tests
            )
        ]
        if target is not None
    )


def _entity_pipeline_contract_target(
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    contract_ref: object,
    raw_tests: object,
) -> tuple[NodeKey, tuple[str, ...]] | None:
    contract_identity = _contract_ref_identity(contract_ref)
    if contract_identity is None:
        return None
    pipeline_key = entity_pipeline_index.get(contract_identity)
    if pipeline_key is None:
        return None
    test_paths = tuple(_as_string_list(raw_tests))
    if not test_paths:
        return None
    return pipeline_key, test_paths


def _contract_ref_identity(contract_ref: object) -> tuple[str, str] | None:
    if not isinstance(contract_ref, str) or "." not in contract_ref:
        return None
    provider_name, entity_name = contract_ref.split(".", 1)
    return provider_name, entity_name


def _link_provider_regression_suite_tests(
    link_test_target: Callable[[NodeKey, str, str], None],
    provider_pipeline_index: dict[str, list[NodeKey]],
    *,
    suites: object,
    enabled: bool,
) -> None:
    if not enabled or not isinstance(suites, dict):
        return
    for suite_name, provider_targets in _provider_regression_suite_targets(suites):
        _link_provider_suite_targets(
            link_test_target,
            provider_pipeline_index,
            suite_name=suite_name,
            provider_targets=provider_targets,
        )


def _link_pipeline_test_targets(
    link_test_target: Callable[[NodeKey, str, str], None],
    targets: tuple[tuple[NodeKey, tuple[str, ...]], ...],
    *,
    provenance: str,
) -> None:
    for pipeline_key, test_paths in targets:
        _link_pipeline_test_paths(
            link_test_target,
            pipeline_key,
            test_paths,
            provenance=provenance,
        )


def _link_pipeline_test_paths(
    link_test_target: Callable[[NodeKey, str, str], None],
    pipeline_key: NodeKey,
    test_paths: tuple[str, ...],
    *,
    provenance: str,
) -> None:
    for test_path in test_paths:
        link_test_target(pipeline_key, test_path, provenance)


def _link_provider_suite_targets(
    link_test_target: Callable[[NodeKey, str, str], None],
    provider_pipeline_index: dict[str, list[NodeKey]],
    *,
    suite_name: str,
    provider_targets: tuple[tuple[str, str], ...],
) -> None:
    provenance = _provider_suite_provenance(suite_name)
    for provider_name, raw_test_path in provider_targets:
        for pipeline_key in provider_pipeline_index.get(provider_name, []):
            link_test_target(pipeline_key, raw_test_path, provenance)


def _provider_suite_provenance(suite_name: str) -> str:
    return f"impact_pipeline_regression_suite:{suite_name}"


def _provider_regression_suite_targets(
    suites: dict[object, object],
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return tuple(
        suite_target
        for suite_name, suite_payload in suites.items()
        for suite_target in [
            _provider_regression_suite_target(suite_name, suite_payload)
        ]
        if suite_target is not None
    )


def _provider_regression_suite_target(
    suite_name: object,
    suite_payload: object,
) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    if not isinstance(suite_name, str) or not isinstance(suite_payload, dict):
        return None
    provider_targets = _provider_regression_provider_targets(suite_payload)
    if not provider_targets:
        return None
    return suite_name, provider_targets


def _provider_regression_provider_targets(
    suite_payload: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    providers = suite_payload.get("providers")
    if not isinstance(providers, dict):
        return ()
    return tuple(
        target
        for provider_name, raw_test_path in providers.items()
        for target in [
            _provider_regression_provider_target(provider_name, raw_test_path)
        ]
        if target is not None
    )


def _provider_regression_provider_target(
    provider_name: object,
    raw_test_path: object,
) -> tuple[str, str] | None:
    if isinstance(provider_name, str) and isinstance(raw_test_path, str):
        return provider_name, raw_test_path
    return None


def _add_alert_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    rules_root = root / "grafana" / "prometheus-rules"
    if not rules_root.is_dir():
        return

    dashboard_metrics, target_context = _alert_surface_context(
        snapshot,
        root,
        pipeline_nodes=pipeline_nodes,
        contract_nodes=contract_nodes,
        memory_mapping=memory_mapping,
    )
    for rules_path in _alert_rules_paths(rules_root):
        _add_alert_rule_file_surfaces(
            snapshot,
            root,
            project,
            today,
            rules_path,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )


def _alert_rules_paths(rules_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(rules_root.glob("*.y*ml")))


def _alert_surface_context(
    snapshot: GraphSnapshot,
    root: Path,
    *,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> tuple[dict[NodeKey, set[str]], AlertTargetContext]:
    return (
        _dashboard_metric_index(root),
        _alert_target_context(
            snapshot,
            pipeline_nodes=pipeline_nodes,
            contract_nodes=contract_nodes,
            memory_mapping=memory_mapping,
        ),
    )


def _alert_target_context(
    snapshot: GraphSnapshot,
    *,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> AlertTargetContext:
    return AlertTargetContext(
        snapshot=snapshot,
        pipeline_nodes=pipeline_nodes,
        provider_nodes=_sorted_provider_surface_nodes(snapshot),
        contract_nodes=contract_nodes,
        memory_mapping=memory_mapping,
    )


def _sorted_provider_surface_nodes(snapshot: GraphSnapshot) -> list[NodeKey]:
    return sorted(
        (key for key in snapshot.nodes if key.label == "provider_surface"),
        key=lambda node: node.name,
    )


def _add_alert_rule_file_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    *,
    dashboard_metrics: dict[NodeKey, set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    file_context = _alert_rule_file_context(snapshot, root, today, rules_path)
    for group in _alert_rule_groups(file_context.payload):
        _add_alert_rule_group_surfaces(
            snapshot,
            root,
            project,
            today,
            rules_path,
            file_context.artifact,
            group,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )


@dataclass(frozen=True)
class AlertRuleFileContext:
    payload: dict[str, object]
    artifact: NodeKey


def _alert_rule_file_context(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    rules_path: Path,
) -> AlertRuleFileContext:
    return AlertRuleFileContext(
        payload=_alert_rule_file_payload(rules_path),
        artifact=_add_alert_rules_artifact(snapshot, root, rules_path, today),
    )


def _add_alert_rule_group_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group: dict[str, object],
    *,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    group_context = _alert_rule_group_context(group, rules_path)
    for rule in group_context.rules:
        _add_alert_surface_from_rule(
            snapshot,
            root,
            project,
            today,
            rules_path,
            artifact,
            group_name=group_context.group_name,
            rule=rule,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )


def _alert_group_name(group: dict[str, object], rules_path: Path) -> str:
    return str(group.get("name", rules_path.stem))


def _alert_group_rules(group: dict[str, object]) -> tuple[dict[str, object], ...]:
    rules = group.get("rules")
    if not isinstance(rules, list):
        return ()
    return tuple(rule for rule in rules if isinstance(rule, dict))


def _alert_rule_group_context(
    group: dict[str, object],
    rules_path: Path,
) -> AlertRuleGroupContext:
    return AlertRuleGroupContext(
        group_name=_alert_group_name(group, rules_path),
        rules=_alert_group_rules(group),
    )


def _add_single_alert_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group_name: str,
    rule: dict[str, object],
    *,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    alert_context = _alert_rule_context(rule)
    if alert_context is None:
        return
    alert = _add_alert_surface_node(
        snapshot,
        root,
        project,
        today,
        rules_path,
        artifact,
        group_name,
        alert_context.alert_name,
        alert_context.annotations,
        alert_context.labels,
    )
    _link_alert_targets(
        snapshot,
        alert,
        alert_context.alert_name,
        group_name,
        rule,
        dashboard_metrics=dashboard_metrics,
        target_context=target_context,
        memory_mapping=memory_mapping,
    )
    _link_alert_runbook(
        snapshot,
        root,
        alert,
        alert_context.alert_name,
        alert_context.annotations,
        today,
    )


def _add_alert_surface_from_rule(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    *,
    group_name: str,
    rule: dict[str, object],
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    _add_single_alert_surface(
        snapshot,
        root,
        project,
        today,
        rules_path,
        artifact,
        group_name,
        rule,
        dashboard_metrics=dashboard_metrics,
        target_context=target_context,
        memory_mapping=memory_mapping,
    )


def _alert_rule_context(rule: dict[str, object]) -> AlertRuleContext | None:
    alert_name = rule.get("alert")
    if not isinstance(alert_name, str):
        return None
    return AlertRuleContext(
        alert_name=alert_name,
        annotations=_alert_annotations(rule),
        labels=_alert_labels(rule),
    )


def _link_alert_targets(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    alert_name: str,
    group_name: str,
    rule: dict[str, object],
    *,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    expr, dimensions = _alert_target_inputs(rule)
    selection = _select_alert_targets(
        target_context,
        alert_name,
        group_name,
        expr,
        dimensions,
    )
    _link_selected_alert_targets(snapshot, alert, selection)
    _link_alert_observer_dashboards(
        snapshot,
        alert,
        alert_name,
        group_name,
        expr,
        dashboard_metrics,
        memory_mapping,
    )


@dataclass(frozen=True)
class AlertTargetSelection:
    selected_pipelines: tuple[NodeKey, ...]
    selected_providers: tuple[NodeKey, ...]
    selected_contracts: tuple[NodeKey, ...]


@dataclass(frozen=True)
class ComplexityCandidateContext:
    anchors: SurfaceAnchorSets
    metrics: SurfaceComplexityMetrics
    runtime_anchors: tuple[NodeKey, ...]
    config_anchors: tuple[NodeKey, ...]
    doc_anchors: tuple[NodeKey, ...]
    test_anchors: tuple[NodeKey, ...]
    blocked_by_current_cycle: bool
    simplification_score: float
    classification: str


def _alert_target_inputs(rule: dict[str, object]) -> tuple[str, set[str]]:
    annotations = _alert_annotations(rule)
    expr = str(rule.get("expr", ""))
    context = AlertTargetInputs(
        expr=expr,
        dimensions=_runtime_dimensions(expr, _alert_dimension_text(annotations)),
    )
    return context.expr, context.dimensions


def _alert_annotations(rule: dict[str, object]) -> dict[str, object]:
    annotations = rule.get("annotations")
    return annotations if isinstance(annotations, dict) else {}


def _alert_labels(rule: dict[str, object]) -> dict[str, object]:
    labels = rule.get("labels")
    return labels if isinstance(labels, dict) else {}


def _alert_dimension_text(annotations: dict[str, object]) -> str:
    return " ".join(str(value) for value in annotations.values())


def _link_selected_alert_targets(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    selection: AlertTargetSelection,
) -> None:
    for target_group in _selected_alert_target_groups(selection):
        _link_alert_target_group(snapshot, alert, target_group)


def _selected_alert_target_groups(
    selection: AlertTargetSelection,
) -> tuple[tuple[NodeKey, ...], ...]:
    return tuple(
        targets
        for targets in (
            selection.selected_pipelines,
            selection.selected_providers,
            selection.selected_contracts,
        )
        if targets
    )


def _link_alert_target_group(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    targets: tuple[NodeKey, ...],
) -> None:
    for target in targets:
        snapshot.add_relation(alert, "DEPENDS_ON", target, provenance="impact_alerts")


def _link_alert_observer_dashboards(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    memory_mapping: dict[str, object],
) -> None:
    for dashboard in _existing_snapshot_nodes(
        snapshot,
        _selected_alert_dashboards(
            alert_name,
            group_name,
            expr,
            dashboard_metrics,
            memory_mapping,
        ),
    ):
        snapshot.add_relation(
            alert, "OBSERVED_BY", dashboard, provenance="impact_alerts"
        )


def _existing_snapshot_nodes(
    snapshot: GraphSnapshot,
    nodes: Iterable[NodeKey],
) -> tuple[NodeKey, ...]:
    return tuple(node for node in nodes if node in snapshot.nodes)


def _selected_alert_dashboards(
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    memory_mapping: dict[str, object],
) -> tuple[NodeKey, ...]:
    return tuple(
        _select_alert_dashboards(
            alert_name,
            group_name,
            expr,
            dashboard_metrics,
            memory_mapping,
        )
    )


def _link_alert_runbook(
    snapshot: GraphSnapshot,
    root: Path,
    alert: NodeKey,
    alert_name: str,
    annotations: dict[str, object],
    today: str,
) -> None:
    runbook_context = _alert_runbook_context(root, annotations)
    if runbook_context is None:
        return
    doc = _add_alert_runbook_doc(snapshot, alert_name, runbook_context.runbook, today)
    snapshot.add_relation(alert, "DESCRIBED_IN", doc, provenance="impact_alerts")


def _alert_runbook_context(
    root: Path,
    annotations: dict[str, object],
) -> AlertRunbookContext | None:
    runbook = _alert_runbook_path(root, annotations)
    if runbook is None:
        return None
    return AlertRunbookContext(runbook=runbook)


def _add_pipeline_operational_edges(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    operational_context = _pipeline_operational_context(memory_mapping)
    for pipeline in _sorted_pipeline_nodes(pipeline_nodes):
        _link_pipeline_operational_for_pipeline(
            snapshot,
            pipeline,
            operational_context=operational_context,
        )


def _pipeline_operational_context(
    memory_mapping: dict[str, object],
) -> PipelineOperationalContext:
    pipeline_ops = _pipeline_operational_section(memory_mapping)
    runtime_paths, validation_gates = _pipeline_operational_targets_config(pipeline_ops)
    common_dashboards, entity_dashboards, composite_dashboards = (
        _pipeline_dashboard_targets(pipeline_ops)
    )
    return PipelineOperationalContext(
        runtime_paths=runtime_paths,
        validation_gates=validation_gates,
        common_dashboards=common_dashboards,
        entity_dashboards=entity_dashboards,
        composite_dashboards=composite_dashboards,
    )


def build_fast_analysis_audit_report(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
) -> dict[str, JsonValue]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    snapshot_stats = snapshot.stats()
    active_labels, active_relation_types = _fast_analysis_scope(snapshot_stats)
    snapshot_label_counts, snapshot_relation_counts = _fast_analysis_snapshot_counts(
        snapshot_stats,
        active_labels,
        active_relation_types,
    )
    live_managed_label_counts, live_managed_relation_counts = (
        _fast_analysis_live_counts(
            client,
            active_labels,
            active_relation_types,
        )
    )
    live_summary = _fast_analysis_live_summary(
        live_managed_label_counts,
        live_managed_relation_counts,
    )
    return _audit_report_payload(
        snapshot_payload=_fast_audit_snapshot_payload(
            snapshot_label_counts, snapshot_relation_counts
        ),
        managed_labels=list(active_labels),
        live_summary=live_summary,
        snapshot_label_counts=snapshot_label_counts,
        live_managed_label_counts=live_managed_label_counts,
        snapshot_relation_counts=snapshot_relation_counts,
        live_managed_relation_counts=live_managed_relation_counts,
    )


def _fast_analysis_scope(
    snapshot_stats: dict[str, JsonValue],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        _active_critical_names(snapshot_stats, "labels", CRITICAL_ANALYSIS_NODE_LABELS),
        _active_critical_names(
            snapshot_stats, "relation_types", CRITICAL_ANALYSIS_RELATION_TYPES
        ),
    )


def _critical_analysis_audit_issues(report: dict[str, JsonValue]) -> list[str]:
    issues: list[str] = []
    diff = report.get("diff", {})
    label_rows = diff.get("labels", []) if isinstance(diff, dict) else []
    relation_rows = diff.get("relation_types", []) if isinstance(diff, dict) else []

    issues.extend(
        _critical_diff_issues(label_rows, CRITICAL_ANALYSIS_NODE_LABELS, kind="label")
    )
    issues.extend(
        _critical_diff_issues(
            relation_rows, CRITICAL_ANALYSIS_RELATION_TYPES, kind="relation"
        )
    )
    return issues


def _critical_diff_issues(
    rows: object,
    critical_names: Iterable[str],
    *,
    kind: str,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list):
        return issues
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        delta = row.get("delta")
        if isinstance(name, str) and name in critical_names and delta:
            issues.append(
                f"{kind} `{name}` expected {row.get('snapshot')}, live managed {row.get('live_managed')}"
            )
    return issues


__all__ = [name for name in globals() if not name.startswith("__")]

if __name__ == "__main__":
    raise SystemExit(main())
