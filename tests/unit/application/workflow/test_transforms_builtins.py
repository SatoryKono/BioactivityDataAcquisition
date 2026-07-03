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
