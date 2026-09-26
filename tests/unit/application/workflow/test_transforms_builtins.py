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
"""Unit tests for built-in workflow transform registration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.builtins import (
    register_builtin_workflow_transforms,
)
from bioetl.domain.workflow import WorkflowTransformSpec

pytestmark = pytest.mark.unit


def test_register_builtin_workflow_transforms_registers_summarize() -> None:
    """Baseline summarize transform must be registered without optional ports."""
    registry = WorkflowTransformRegistry()
    register_builtin_workflow_transforms(registry)

    assert "summarize_upstream_outputs" in registry._executors


def test_summarize_upstream_outputs_is_deterministic() -> None:
    """Summarize transform must emit stable ordering for upstream step ids."""
    registry = WorkflowTransformRegistry()
    register_builtin_workflow_transforms(registry)
    executor = registry._executors["summarize_upstream_outputs"]
    spec = WorkflowTransformSpec(
        step_id="summarize",
        transform_name="summarize_upstream_outputs",
        config={},
    )
    upstream = {
        "b_step": MagicMock(status="ok"),
        "a_step": MagicMock(status="ok"),
    }

    result = executor(spec, upstream)

    assert result["upstream_steps"] == ["a_step", "b_step"]
    assert list(result["step_summaries"]) == ["a_step", "b_step"]
