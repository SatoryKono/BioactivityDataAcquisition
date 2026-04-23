"""Snapshot topology and graph-shape invariants for Neo4j memory sync."""

from __future__ import annotations

import pytest

from testing_support.neo4j_memory_sync import (  # noqa: F401
    test_development_cycle_surface_filter_is_now_a_clean_noop,
    test_duplication_analysis_config_excludes_normalization_registry_path,
    test_normalize_docs_repo_reference_strips_globs_and_keeps_repo_paths,
    test_snapshot_contains_complexity_candidates_with_simplification_links,
    test_snapshot_contains_core_repo_surfaces,
    test_snapshot_contains_duplication_clusters_with_promotion_targets,
    test_snapshot_contains_expected_relations,
    test_snapshot_contains_workflow_execution_cli_and_claim_extensions,
    test_snapshot_enriches_current_normalization_topology,
    test_snapshot_excludes_normalization_registry_duplication_noise,
    test_storage_ref_from_output_path_normalizes_data_output_prefix,
    test_storage_surface_helpers_merge_base_and_pipeline_overrides,
    test_workflow_quality_gates_detect_repo_gate_signals,
)

pytestmark = pytest.mark.memory
