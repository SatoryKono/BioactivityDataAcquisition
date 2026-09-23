"""Explicit graph-sync re-export shard (AUD-002 barrel split)."""

from __future__ import annotations

# ruff: noqa: I001
# fmt: off
from memory.graph.sync_pkg._core_ast import (
    _CONTROL_FLOW_NODES as _CONTROL_FLOW_NODES,
    _base_name as _base_name,
    _callable_ast_node_count as _callable_ast_node_count,
    _callable_branch_count as _callable_branch_count,
    _callable_call_count as _callable_call_count,
    _callable_helper_call_count as _callable_helper_call_count,
    _callable_max_nesting_depth as _callable_max_nesting_depth,
    _dataframe_model_class_names as _dataframe_model_class_names,
    _imported_repo_modules as _imported_repo_modules,
    _imported_symbols as _imported_symbols,
    _looks_like_dataframe_model_class as _looks_like_dataframe_model_class,
    _matching_imported_module_names as _matching_imported_module_names,
    _normalized_callable_hash as _normalized_callable_hash,
    _parse_python_ast as _parse_python_ast,
    _protocol_class_names as _protocol_class_names,
    _signature_hash as _signature_hash,
)
from memory.graph.sync_pkg._core_cli import (
    _export_snapshot_if_requested as _export_snapshot_if_requested,
    _normalization_operation_count as _normalization_operation_count,
    _parser as _parser,
    _print_snapshot_stats as _print_snapshot_stats,
    _report_payload as _report_payload,
    _run_apply_normalization_evidence_only as _run_apply_normalization_evidence_only,
    _run_snapshot_cli as _run_snapshot_cli,
    _selection_from_args as _selection_from_args,
    _snapshot_operation_count as _snapshot_operation_count,
    _sync_snapshot_if_requested as _sync_snapshot_if_requested,
    _validate_cli_args as _validate_cli_args,
    _write_json as _write_json,
    _write_report_if_requested as _write_report_if_requested,
    main as main,
)
from memory.graph.sync_pkg._core_convert import (
    GITHUB_DIR as GITHUB_DIR,
    GITHUB_PATH_PREFIX as GITHUB_PATH_PREFIX,
    YAML_SUFFIX as YAML_SUFFIX,
    _DOCS_DRIFT_EXCLUDED_PREFIXES as _DOCS_DRIFT_EXCLUDED_PREFIXES,
    _as_iterable as _as_iterable,
    _as_mapping as _as_mapping,
    _as_string_list as _as_string_list,
    _coerce_float as _coerce_float,
    _coerce_int as _coerce_int,
    _git_cached_commit_ages as _git_cached_commit_ages,
    _is_claim_candidate as _is_claim_candidate,
    _is_dataframe_model_base as _is_dataframe_model_base,
    _is_doc_artifact_file as _is_doc_artifact_file,
    _is_excluded_docs_drift_prefix as _is_excluded_docs_drift_prefix,
    _is_ignored_repo_path as _is_ignored_repo_path,
    _is_protocol_base as _is_protocol_base,
    _module_dotted_name as _module_dotted_name,
    _normalize_cli_command_name as _normalize_cli_command_name,
    _normalize_docs_glob_candidate as _normalize_docs_glob_candidate,
    _normalize_env_value as _normalize_env_value,
    _normalize_repo_relative_path as _normalize_repo_relative_path,
    _normalize_workflow_matrix_axis_name as _normalize_workflow_matrix_axis_name,
    _normalized_alert_selector as _normalized_alert_selector,
    _normalized_text_list as _normalized_text_list,
    _optional_text as _optional_text,
    _read_text as _read_text,
    _rel_path as _rel_path,
    _resolve_git_executable as _resolve_git_executable,
    _resolve_repo_path as _resolve_repo_path,
)
from memory.graph.sync_pkg._core_models import (
    AlertDashboardConfig as AlertDashboardConfig,
    AlertRuleContext as AlertRuleContext,
    AlertRuleGroupContext as AlertRuleGroupContext,
    AlertRuleSettings as AlertRuleSettings,
    AlertRunbookContext as AlertRunbookContext,
    AlertTargetInputs as AlertTargetInputs,
    AnalysisLabelSets as AnalysisLabelSets,
    ClaimLineContext as ClaimLineContext,
    ComplexityAnalysisConfig as ComplexityAnalysisConfig,
    ComplexityMetrics as ComplexityMetrics,
    ComplexityScoreInputs as ComplexityScoreInputs,
    ContractMappingConfig as ContractMappingConfig,
    ControlPlaneArtifactSpec as ControlPlaneArtifactSpec,
    EntityScope as EntityScope,
    GroupedStatementFailureContext as GroupedStatementFailureContext,
    JsonScalar as JsonScalar,
    JsonValue as JsonValue,
    NodeKey as NodeKey,
    PortSurfaceDescriptor as PortSurfaceDescriptor,
    RetirementAnalysisConfig as RetirementAnalysisConfig,
    RetirementScoreInputs as RetirementScoreInputs,
    SchemaFieldSpec as SchemaFieldSpec,
    SnapshotSelection as SnapshotSelection,
    StorageSurfaceSpec as StorageSurfaceSpec,
    SyncApplyOptions as SyncApplyOptions,
    _ShapeNormalizer as _ShapeNormalizer,
)
from memory.graph.sync_pkg.add_adapter_impl_surface import (
    _add_adapter_impl_surface as _add_adapter_impl_surface,
    _add_adapter_module_surface as _add_adapter_module_surface,
    _link_adapter_ports as _link_adapter_ports,
)
from memory.graph.sync_pkg.add_adr_decision_node import (
    _add_adr_decision_node as _add_adr_decision_node,
    _add_doc_command_reference_edges as _add_doc_command_reference_edges,
    _add_doc_path_reference_edges as _add_doc_path_reference_edges,
)
from memory.graph.sync_pkg.add_alert_rule_group_surfaces import (
    _add_alert_rule_group_surfaces as _add_alert_rule_group_surfaces,
)
from memory.graph.sync_pkg.add_ci_workflow_graph import _add_ci_workflow_graph as _add_ci_workflow_graph
from memory.graph.sync_pkg.add_claim_target_relation import (
    _add_claim_fallback_target as _add_claim_fallback_target,
    _add_claim_target_relation as _add_claim_target_relation,
)
from memory.graph.sync_pkg.add_claim_token_targets import _add_claim_token_targets as _add_claim_token_targets
from memory.graph.sync_pkg.add_cli_command_surface import (
    _add_cli_command_surface as _add_cli_command_surface,
    _add_cli_option_surfaces as _add_cli_option_surfaces,
    _cli_command_source_path as _cli_command_source_path,
    _cli_execution_indexes as _cli_execution_indexes,
    _link_cli_command_execution as _link_cli_command_execution,
    _link_cli_command_side_effects as _link_cli_command_side_effects,
)
from memory.graph.sync_pkg.add_contract_doc_dependency import (
    _add_contract_doc_dependency as _add_contract_doc_dependency,
    _add_contract_entry_surface as _add_contract_entry_surface,
    _contract_dependency_doc_path as _contract_dependency_doc_path,
)
from memory.graph.sync_pkg.add_control_plane_run_instance_surfaces import (
    _add_control_plane_run_instance_surfaces as _add_control_plane_run_instance_surfaces,
)
from memory.graph.sync_pkg.add_control_plane_runtime_evidence import (
    _add_control_plane_runtime_evidence as _add_control_plane_runtime_evidence,
)
from memory.graph.sync_pkg.add_curated_cluster_readme import (
    _add_curated_cluster_entrypoint as _add_curated_cluster_entrypoint,
    _add_curated_cluster_execution as _add_curated_cluster_execution,
    _add_curated_cluster_readme as _add_curated_cluster_readme,
)
from memory.graph.sync_pkg.add_curated_doc_source import _add_curated_doc_source as _add_curated_doc_source
from memory.graph.sync_pkg.add_curated_docs import (
    _add_curated_docs as _add_curated_docs,
    _add_decisions_and_risks as _add_decisions_and_risks,
    _add_provider_and_config_graph as _add_provider_and_config_graph,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _add_curated_quality_gates as _add_curated_quality_gates,
    _add_dashboard_surface as _add_dashboard_surface,
    _add_execution_path_node as _add_execution_path_node,
    _developer_workflow_readme as _developer_workflow_readme,
    _link_execution_gate as _link_execution_gate,
)
from memory.graph.sync_pkg.add_doc_claim_edges import _add_doc_claim_edges as _add_doc_claim_edges
from memory.graph.sync_pkg.add_doc_describes_relation import _add_doc_describes_relation as _add_doc_describes_relation
from memory.graph.sync_pkg.add_docs_to_code_drift_edges import (
    _add_adr_constraint_edges as _add_adr_constraint_edges,
    _add_docs_to_code_drift_edges as _add_docs_to_code_drift_edges,
)
from memory.graph.sync_pkg.add_duplication_callable_surface import (
    _add_duplication_callable_surface as _add_duplication_callable_surface,
    _duplication_callable_descriptor as _duplication_callable_descriptor,
)
from memory.graph.sync_pkg.add_entity_pipeline_surfaces import (
    _add_composite_pipeline_surfaces as _add_composite_pipeline_surfaces,
    _add_entity_pipeline_surfaces as _add_entity_pipeline_surfaces,
)
from memory.graph.sync_pkg.add_entity_regular_field_node import (
    _add_entity_metadata_field_node as _add_entity_metadata_field_node,
    _add_entity_regular_field_node as _add_entity_regular_field_node,
)
from memory.graph.sync_pkg.add_entity_storage_data_surfaces import (
    _add_entity_storage_data_surfaces as _add_entity_storage_data_surfaces,
)
from memory.graph.sync_pkg.add_entity_storage_layer import _add_entity_storage_layer as _add_entity_storage_layer
from memory.graph.sync_pkg.add_entity_storage_layers import _add_entity_storage_layers as _add_entity_storage_layers
from memory.graph.sync_pkg.add_file_structure_surfaces import (
    _add_entity_layer_field_nodes as _add_entity_layer_field_nodes,
    _add_file_structure_surfaces as _add_file_structure_surfaces,
)
from memory.graph.sync_pkg.add_file_structure_zone import (
    _add_file_structure_zone as _add_file_structure_zone,
    _field_quality_index as _field_quality_index,
)
from memory.graph.sync_pkg.add_impact_analysis_surfaces import (
    _add_impact_analysis_surfaces as _add_impact_analysis_surfaces,
)
from memory.graph.sync_pkg.add_package_topology_decisions_and_risks import (
    _add_package_topology_decisions_and_risks as _add_package_topology_decisions_and_risks,
)
from memory.graph.sync_pkg.add_pipeline_doc_edges import _add_pipeline_doc_edges as _add_pipeline_doc_edges
from memory.graph.sync_pkg.add_pipeline_test_edges import _add_pipeline_test_edges as _add_pipeline_test_edges
from memory.graph.sync_pkg.add_policy_surface import (
    _add_policy_artifact as _add_policy_artifact,
    _add_policy_surface as _add_policy_surface,
)
from memory.graph.sync_pkg.add_port_facade_surface import (
    _add_port_facade_surface as _add_port_facade_surface,
    _add_protocol_port_surface as _add_protocol_port_surface,
)
from memory.graph.sync_pkg.add_port_surfaces import _add_port_surfaces as _add_port_surfaces
from memory.graph.sync_pkg.add_provider_surfaces import (
    _add_policy_surfaces as _add_policy_surfaces,
    _add_provider_surfaces as _add_provider_surfaces,
)
from memory.graph.sync_pkg.add_repo_zone_directory_file import (
    _add_repo_zone_directory_file as _add_repo_zone_directory_file,
)
from memory.graph.sync_pkg.add_repo_zone_directory_files import (
    _add_repo_zone_directory_files as _add_repo_zone_directory_files,
)
from memory.graph.sync_pkg.add_repo_zone_file_surface import (
    _add_repo_zone_doc_artifact as _add_repo_zone_doc_artifact,
    _add_repo_zone_file_surface as _add_repo_zone_file_surface,
)
from memory.graph.sync_pkg.add_run_instance_spec_surfaces import (
    _add_run_instance_spec_surfaces as _add_run_instance_spec_surfaces,
    _add_runtime_state_surfaces as _add_runtime_state_surfaces,
    _process_workflow_steps as _process_workflow_steps,
)
from memory.graph.sync_pkg.add_runtime_evidence_surface import (
    _add_runtime_evidence_surface as _add_runtime_evidence_surface,
    _link_run_instance_surface as _link_run_instance_surface,
)
from memory.graph.sync_pkg.add_runtime_state_spec_surfaces import (
    _add_runtime_state_spec_surfaces as _add_runtime_state_spec_surfaces,
    _workflow_script_targets as _workflow_script_targets,
)
from memory.graph.sync_pkg.add_secret_requirements import (
    _add_secret_requirements as _add_secret_requirements,
    _add_workflow_output_surface as _add_workflow_output_surface,
    _add_workflow_outputs as _add_workflow_outputs,
)
from memory.graph.sync_pkg.add_single_adr_constraint_edges import (
    _add_single_adr_constraint_edges as _add_single_adr_constraint_edges,
)
from memory.graph.sync_pkg.add_single_alert_surface import (
    _add_alert_surface_from_rule as _add_alert_surface_from_rule,
    _add_single_alert_surface as _add_single_alert_surface,
)
from memory.graph.sync_pkg.add_storage_data_surfaces import _add_storage_data_surfaces as _add_storage_data_surfaces
from memory.graph.sync_pkg.add_test_suite_surface import (
    _add_test_artifact_surface as _add_test_artifact_surface,
    _add_test_suite_surface as _add_test_suite_surface,
)
from memory.graph.sync_pkg.add_workflow_file_surface import _add_workflow_file_surface as _add_workflow_file_surface
from memory.graph.sync_pkg.add_workflow_jobs import _add_workflow_jobs as _add_workflow_jobs
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _adr_constraint_candidates as _adr_constraint_candidates,
    _docs_command_pattern as _docs_command_pattern,
    _docs_drift_sources as _docs_drift_sources,
    _docs_path_pattern as _docs_path_pattern,
    _normalize_docs_drift_source_path as _normalize_docs_drift_source_path,
    _read_docs_drift_text as _read_docs_drift_text,
)
from memory.graph.sync_pkg.adr_title import (
    _adr_title as _adr_title,
    _doc_reference_context as _doc_reference_context,
    _resolve_adr_constraint_target as _resolve_adr_constraint_target,
)
from memory.graph.sync_pkg.alert_annotations import (
    _alert_annotations as _alert_annotations,
    _alert_dimension_text as _alert_dimension_text,
    _alert_labels as _alert_labels,
    _link_selected_alert_targets as _link_selected_alert_targets,
)
from memory.graph.sync_pkg.alert_group_name import (
    _alert_group_name as _alert_group_name,
    _alert_group_rules as _alert_group_rules,
    _alert_rule_group_context as _alert_rule_group_context,
)
from memory.graph.sync_pkg.alert_rule_context import _alert_rule_context as _alert_rule_context
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _add_alert_rules_artifact as _add_alert_rules_artifact,
    _add_alert_surface_node as _add_alert_surface_node,
    _alert_rule_file_payload as _alert_rule_file_payload,
    _alert_rule_groups as _alert_rule_groups,
    _link_workflow_job_reusable_target as _link_workflow_job_reusable_target,
)
from memory.graph.sync_pkg.alert_rules_paths import (
    _alert_rules_paths as _alert_rules_paths,
    _alert_surface_context as _alert_surface_context,
)
from memory.graph.sync_pkg.alert_runbook_context import (
    _add_pipeline_operational_edges as _add_pipeline_operational_edges,
    _alert_runbook_context as _alert_runbook_context,
)
from memory.graph.sync_pkg.alert_runbook_path import (
    _add_alert_runbook_doc as _add_alert_runbook_doc,
    _add_governance_edges as _add_governance_edges,
    _alert_runbook_path as _alert_runbook_path,
)
from memory.graph.sync_pkg.alert_target_context import _alert_target_context as _alert_target_context
from memory.graph.sync_pkg.alert_target_inputs import _alert_target_inputs as _alert_target_inputs
from memory.graph.sync_pkg.alert_targets import (
    _RUNTIME_DIMENSIONS as _RUNTIME_DIMENSIONS,
    _alert_dashboard_config as _alert_dashboard_config,
    _alert_dashboard_fallback_groups as _alert_dashboard_fallback_groups,
    _alert_dashboard_fallbacks as _alert_dashboard_fallbacks,
    _alert_override_maps as _alert_override_maps,
    _alert_pipeline_kind_override as _alert_pipeline_kind_override,
    _alert_rule_overrides as _alert_rule_overrides,
    _alert_rule_settings as _alert_rule_settings,
    _alerts_config_section as _alerts_config_section,
    _all_contract_targets as _all_contract_targets,
    _all_pipeline_targets as _all_pipeline_targets,
    _configured_alert_rule as _configured_alert_rule,
    _configured_dashboard_targets as _configured_dashboard_targets,
    _contract_targets_for_alert as _contract_targets_for_alert,
    _dashboard_target_keys as _dashboard_target_keys,
    _entity_alert_signal_detected as _entity_alert_signal_detected,
    _mapped_contract_targets as _mapped_contract_targets,
    _merged_alert_dashboard_targets as _merged_alert_dashboard_targets,
    _metric_dashboard_targets as _metric_dashboard_targets,
    _pipeline_targets_for_alert as _pipeline_targets_for_alert,
    _pipeline_targets_for_alert_mode as _pipeline_targets_for_alert_mode,
    _pipeline_targets_matching_kind as _pipeline_targets_matching_kind,
    _provider_alert_signal_detected as _provider_alert_signal_detected,
    _provider_targets_for_alert as _provider_targets_for_alert,
    _provider_targets_requested as _provider_targets_requested,
    _raw_alert_targets as _raw_alert_targets,
    _runtime_dimensions as _runtime_dimensions,
    _select_alert_dashboards as _select_alert_dashboards,
    _select_alert_targets as _select_alert_targets,
    _sorted_alert_targets as _sorted_alert_targets,
    _sorted_node_keys as _sorted_node_keys,
    _sorted_unique_node_keys as _sorted_unique_node_keys,
)
from memory.graph.sync_pkg.alertrulefilecontext import (
    AlertRuleFileContext as AlertRuleFileContext,
    _alert_rule_file_context as _alert_rule_file_context,
)
from memory.graph.sync_pkg.alerttargetselection import (
    AlertTargetSelection as AlertTargetSelection,
    ComplexityCandidateContext as ComplexityCandidateContext,
)
from memory.graph.sync_pkg.analysis_source import (
    ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS as ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS,
    _analysis_read_source_text as _analysis_read_source_text,
    _build_surface_relation_indexes as _build_surface_relation_indexes,
    _read_analysis_source_text as _read_analysis_source_text,
)
from memory.graph.sync_pkg.apply_anchors import (
    _anchor_count_rows as _anchor_count_rows,
    _ensure_targeted_apply_prerequisites as _ensure_targeted_apply_prerequisites,
    _missing_anchor_keys_in_chunk as _missing_anchor_keys_in_chunk,
    _missing_anchor_keys_message as _missing_anchor_keys_message,
    _missing_anchor_labels as _missing_anchor_labels,
    _missing_anchor_labels_message as _missing_anchor_labels_message,
    _missing_managed_anchor_keys as _missing_managed_anchor_keys,
    _targeted_apply_external_anchor_keys as _targeted_apply_external_anchor_keys,
    _targeted_apply_required_anchor_labels as _targeted_apply_required_anchor_labels,
)
from memory.graph.sync_pkg.apply_groups import (
    ANALYSIS_NODE_LABELS as ANALYSIS_NODE_LABELS,
    ANALYSIS_RELATION_TYPES as ANALYSIS_RELATION_TYPES,
    DEFAULT_LEGACY_PRUNE_LABELS as DEFAULT_LEGACY_PRUNE_LABELS,
    _analysis_batch_size as _analysis_batch_size,
    _analysis_node_batch_size as _analysis_node_batch_size,
    _analysis_relation_batch_size as _analysis_relation_batch_size,
    _apply_snapshot_statement_groups as _apply_snapshot_statement_groups,
    _delete_managed_wave_batch_size as _delete_managed_wave_batch_size,
    _delete_managed_wave_if_requested as _delete_managed_wave_if_requested,
    _execute_prune_stale_statements as _execute_prune_stale_statements,
    _legacy_or_default_batch_size as _legacy_or_default_batch_size,
    _node_statement_groups as _node_statement_groups,
    _partition_groups as _partition_groups,
    _prune_managed_graph_if_requested as _prune_managed_graph_if_requested,
    _relation_statement_groups as _relation_statement_groups,
    _reset_managed_relations_if_requested as _reset_managed_relations_if_requested,
    _resolved_sync_apply_options as _resolved_sync_apply_options,
    _selection_from_legacy_kwargs as _selection_from_legacy_kwargs,
    _statement_groups as _statement_groups,
    _verification_sync_run as _verification_sync_run,
)
from memory.graph.sync_pkg.apply_runtime import (
    _batched as _batched,
    _execute_grouped_statements as _execute_grouped_statements,
    _execute_statement_batch as _execute_statement_batch,
    _raise_grouped_statement_failure as _raise_grouped_statement_failure,
    _statement_failure_context as _statement_failure_context,
)
# fmt: on

__all__ = [name for name in globals() if not name.startswith("__")]
