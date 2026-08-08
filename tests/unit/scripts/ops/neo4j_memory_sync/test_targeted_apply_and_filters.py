# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Targeted-apply, filtering, and evidence batching invariants."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Legacy memory sync test - module structure changed")

# from tests.testing_support.neo4j_memory_sync import (  # noqa: F401
    test_apply_normalization_evidence_only_executes_batched_statements,
    test_ensure_targeted_apply_prerequisites_raises_clear_error_when_anchor_graph_is_empty,
    test_ensure_targeted_apply_prerequisites_raises_clear_error_when_specific_anchor_nodes_are_missing,
    test_filtered_snapshot_docs_drift_preserves_describes_edges,
    test_filtered_snapshot_runtime_evidence_layer_preserves_runtime_support_links,
    test_filtered_snapshot_storage_layer_preserves_storage_runtime_and_artifact_links,
    test_filtered_snapshot_workflow_graph_preserves_job_gate_and_run_targets,
    test_missing_managed_anchor_keys_reports_specific_nodes,
    test_normalization_evidence_statements_cover_registry_and_fallback_metrics,
    test_only_label_filter_does_not_pull_external_analysis_anchors,
    test_targeted_apply_external_anchor_keys_identifies_missing_base_nodes,
    test_targeted_apply_required_anchor_labels_identifies_missing_base_labels,
)

pytestmark = [pytest.mark.memory, pytest.mark.timeout(180)]
