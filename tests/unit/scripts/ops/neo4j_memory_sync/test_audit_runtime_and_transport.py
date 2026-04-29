"""Audit, runtime, and HTTP transport invariants for Neo4j memory sync."""

from __future__ import annotations

import pytest

from tests.testing_support.neo4j_memory_sync import (  # noqa: F401
    test_build_audit_report_uses_bulk_summary_queries,
    test_build_diff_entries_tracks_missing_and_extra_keys,
    test_build_fast_analysis_audit_report_uses_bulk_count_queries,
    test_complexity_analysis_reuses_declared_surface_metrics_without_ast_parsing,
    test_default_legacy_prune_labels_cover_repo_managed_surfaces,
    test_git_last_commit_age_days_bulk_batches_history_lookup,
    test_live_managed_count_helpers_batch_labels_and_relations,
    test_main_skips_global_post_apply_fast_audit_for_targeted_sync,
    test_neo4j_http_client_distinguishes_query_runtime_http_errors,
    test_neo4j_http_client_reports_all_transport_attempts,
    test_prune_statements_target_repo_sync_subgraph,
    test_sync_snapshot_uses_current_sync_run_for_prune_stale_verification,
    test_sync_statements_include_management_metadata,
    test_verify_expected_group_counts_uses_sync_run_for_targeted_relation_checks,
)

pytestmark = pytest.mark.memory
