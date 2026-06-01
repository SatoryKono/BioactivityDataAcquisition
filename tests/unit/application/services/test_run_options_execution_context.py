"""Tests for RunOptions execution_context handling."""

from __future__ import annotations

import pytest

from bioetl.application.services.execution.pipeline_runner_models import RunOptions


pytestmark = pytest.mark.unit

class TestRunOptionsSeverityContext:
    """Tests for RunOptions execution_context field."""

    def test_default_execution_context(self) -> None:
        opts = RunOptions()
        assert opts.execution_context == "isolated"

    def test_enricher_execution_context(self) -> None:
        opts = RunOptions(execution_context="enricher")
        assert opts.execution_context == "enricher"

    def test_dependency_execution_context(self) -> None:
        opts = RunOptions(execution_context="dependency")
        assert opts.execution_context == "dependency"
