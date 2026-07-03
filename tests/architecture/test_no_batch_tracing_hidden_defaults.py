"""Architecture guardrail for explicit batch tracing DI."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

BATCH_TRACING_PATH = Path("src/bioetl/application/core/batch_tracing.py")
RUNNER_PATH = Path("src/bioetl/application/core/runner.py")


def test_batch_tracing_manager_does_not_construct_noop_tracer() -> None:
    """Application batch tracing service must consume explicit tracer injection."""
    content = BATCH_TRACING_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
            continue
        calls = {
            inner.func.id
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
        }
        assert "NoOpTracing" not in calls, (
            "BatchTracingManagerService.__init__ must not construct NoOpTracing; "
            "build tracing defaults in composition or tests."
        )
        return

    raise AssertionError("BatchTracingManagerService.__init__ not found")


def test_pipeline_runner_does_not_construct_noop_tracer() -> None:
    """PipelineRunner must consume explicit tracer injection."""
    content = RUNNER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
            continue
        calls = {
            inner.func.id
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
        }
        assert "NoOpTracing" not in calls, (
            "PipelineRunner.__init__ must not construct NoOpTracing; "
            "build tracing defaults in composition or tests."
        )
        return

    raise AssertionError("PipelineRunner.__init__ not found")
