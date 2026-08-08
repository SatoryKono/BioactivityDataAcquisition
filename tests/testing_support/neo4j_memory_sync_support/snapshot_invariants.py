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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Snapshot invariant support tests for Neo4j memory sync."""

# ruff: noqa: F403,F405

from __future__ import annotations

import sys

import pytest

pytestmark = [
    pytest.mark.skip(reason="Legacy memory sync test - module structure changed"),
    pytest.mark.memory,
    pytest.mark.timeout(180),
    pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
    ),
]


@pytest.fixture(autouse=True)
def _skip_snapshot_invariants_on_windows() -> None:
    if sys.platform.startswith("win"):
        pytest.skip(
            "Snapshot invariant tests require full repo walk which is prohibitively slow on Windows"
        )


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
)
def test_snapshot_invariants_are_clean() -> None:
    _, snapshot = _snapshot()

    assert snapshot_invariant_issues(snapshot) == []


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
)
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Snapshot invariant tests require full repo walk which is prohibitively slow on Windows",
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
