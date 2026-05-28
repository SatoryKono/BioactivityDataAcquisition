"""Snapshot invariant support tests for Neo4j memory sync."""

from __future__ import annotations

from .common import *  # noqa: F403


def test_snapshot_invariants_are_clean() -> None:
    _, snapshot = _snapshot()

    assert snapshot_invariant_issues(snapshot) == []


def test_snapshot_invariants_require_docs_to_code_drift_edges() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.relation_type == "DESCRIBES"
        and relation.source.label
        in {"doc_source_surface", "doc_artifact", "policy_surface"}
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert "missing docs-to-code drift edges" in issues


def test_snapshot_invariants_require_workflow_job_parent_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.relation_type == "CONTAINS"
        and relation.source.label == "workflow_surface"
        and relation.target.label == "workflow_job_surface"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing workflow_surface -> CONTAINS -> workflow_job_surface links" in issues
    )
    assert any(
        issue.startswith("workflow jobs without workflow parent links:")
        for issue in issues
    )


def test_snapshot_invariants_require_runtime_evidence_support_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.source.label == "runtime_evidence_surface"
        and relation.relation_type in {"BACKED_BY", "DESCRIBED_IN", "WRITES_TO"}
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing runtime_evidence_surface -> WRITES_TO -> storage_surface links"
        in issues
    )
    assert any(
        issue.startswith("runtime evidence surfaces without support links:")
        for issue in issues
    )


def test_snapshot_invariants_require_control_plane_artifact_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.source.label == "runtime_evidence_surface"
        and relation.relation_type == "EMITS_ARTIFACT"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing runtime_evidence_surface -> EMITS_ARTIFACT -> control_plane_artifact_surface links"
        in issues
    )
    assert any(
        issue.startswith("control-plane artifacts without runtime/storage links:")
        for issue in issues
    )


def test_snapshot_invariants_require_run_instance_artifact_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.source.label == "run_instance_surface"
        and relation.relation_type == "REFERENCES_ARTIFACT"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing run_instance_surface -> REFERENCES_ARTIFACT -> control_plane_artifact_surface links"
        in issues
    )
    assert any(
        issue.startswith("run instance surfaces without support links:")
        for issue in issues
    )


def test_snapshot_invariants_require_runtime_state_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.target.label == "runtime_state_surface"
        and relation.relation_type == "HAS_RUNTIME_STATE"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing project -> HAS_RUNTIME_STATE -> runtime_state_surface links" in issues
    )
    assert any(
        issue.startswith("runtime state surfaces without support links:")
        for issue in issues
    )


def test_snapshot_invariants_require_schema_field_links() -> None:
    _, snapshot = _snapshot()
    keys_to_delete = [
        key
        for key, relation in snapshot.relations.items()
        if relation.target.label == "schema_field_surface"
        and relation.relation_type == "HAS_SCHEMA_FIELD"
    ]
    for key in keys_to_delete:
        snapshot.relations.pop(key)

    issues = snapshot_invariant_issues(snapshot)

    assert (
        "missing storage_surface -> HAS_SCHEMA_FIELD -> schema_field_surface links"
        in issues
    )
    assert any(
        issue.startswith("schema fields without storage/contract/lineage links:")
        for issue in issues
    )
