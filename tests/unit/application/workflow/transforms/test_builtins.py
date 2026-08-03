# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for built-in workflow transforms."""

from __future__ import annotations

import pytest

from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.builtins import (
    _summarize_upstream_outputs,
    register_builtin_workflow_transforms,
)
from bioetl.domain.workflow import WorkflowTransformSpec

pytestmark = pytest.mark.unit


def test_register_builtin_workflow_transforms_without_fk_port() -> None:
    """Test registering built-in transforms without foreign key reconciliation."""
    registry = WorkflowTransformRegistry()
    result = register_builtin_workflow_transforms(registry)

    assert result is registry
    assert "summarize_upstream_outputs" in registry._executors


def test_register_builtin_workflow_transforms_with_fk_port() -> None:
    """Test registering built-in transforms with foreign key reconciliation."""
    from bioetl.domain.ports import ForeignKeyReconciliationPort

    class MockFKPort(ForeignKeyReconciliationPort):
        def reconcile(self, foreign_keys: set[str]) -> dict[str, str]:
            return {fk: fk for fk in foreign_keys}

    registry = WorkflowTransformRegistry()
    result = register_builtin_workflow_transforms(
        registry,
        foreign_key_reconciliation_port=MockFKPort(),
    )

    assert result is registry
    assert "summarize_upstream_outputs" in registry._executors
    assert "reconcile_foreign_keys" in registry._executors


def test_register_builtin_workflow_transforms_with_row_reconciliation_port() -> None:
    """Test registering built-ins with row reconciliation."""
    from bioetl.domain.ports import RowReconciliationPort

    class MockRowPort(RowReconciliationPort):
        pass

    registry = WorkflowTransformRegistry()
    result = register_builtin_workflow_transforms(
        registry,
        row_reconciliation_port=MockRowPort(),
    )

    assert result is registry
    assert "summarize_upstream_outputs" in registry._executors
    assert "reconcile_rows" in registry._executors


def test_summarize_upstream_outputs() -> None:
    """Test the summarize_upstream_outputs transform."""
    spec = WorkflowTransformSpec(
        step_id="test_step",
        transform_name="test_transform",
    )

    class MockPayload:
        status = "completed"

    class MockPayload2:
        status = "pending"

    upstream_outputs = {
        "step1": MockPayload(),
        "step2": MockPayload2(),
    }

    result = _summarize_upstream_outputs(spec, upstream_outputs)

    assert result["transform_name"] == "test_transform"
    assert result["fingerprint"] is not None
    assert result["upstream_steps"] == ["step1", "step2"]
    assert "step_summaries" in result
    assert result["step_summaries"]["step1"]["payload_type"] == "MockPayload"
    assert result["step_summaries"]["step1"]["status"] == "completed"
    assert result["step_summaries"]["step2"]["payload_type"] == "MockPayload2"
    assert result["step_summaries"]["step2"]["status"] == "pending"


def test_summarize_upstream_outputs_deterministic_ordering() -> None:
    """Test that summarize_upstream_outputs produces deterministic output."""
    spec = WorkflowTransformSpec(
        step_id="test_step",
        transform_name="test_transform",
    )

    class MockPayload:
        status = "completed"

    upstream_outputs = {
        "step2": MockPayload(),
        "step1": MockPayload(),
        "step3": MockPayload(),
    }

    result1 = _summarize_upstream_outputs(spec, upstream_outputs)
    result2 = _summarize_upstream_outputs(spec, upstream_outputs)

    assert result1 == result2
    assert result1["upstream_steps"] == ["step1", "step2", "step3"]
