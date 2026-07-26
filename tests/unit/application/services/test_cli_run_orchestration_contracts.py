"""Focused unit tests for CLI run orchestration protocol contracts."""

from __future__ import annotations

from inspect import signature

import pytest

from bioetl.application.services.execution.cli_run_orchestration_contracts import (
    MetricsFlushCallable,
    RunCoroutineCallable,
    RunPreparedPipelineCallable,
)


@pytest.mark.unit
class TestCliRunOrchestrationProtocols:
    """Keep protocol surfaces stable for CLI orchestration wiring."""

    def test_protocol_markers_are_present(self) -> None:
        assert RunPreparedPipelineCallable._is_protocol is True
        assert RunCoroutineCallable._is_protocol is True
        assert MetricsFlushCallable._is_protocol is True

    def test_run_prepared_pipeline_callable_signature_is_stable(self) -> None:
        params = signature(RunPreparedPipelineCallable.__call__).parameters

        assert list(params) == ["self", "request"]

    def test_run_coroutine_callable_signature_keeps_keyword_only_debug(self) -> None:
        params = signature(RunCoroutineCallable.__call__).parameters

        assert list(params) == ["self", "main", "debug"]
        assert params["debug"].kind.name == "KEYWORD_ONLY"
        assert params["debug"].default is None

    def test_metrics_flush_callable_signature_keeps_default_arguments(self) -> None:
        params = signature(MetricsFlushCallable.__call__).parameters

        assert list(params) == ["self", "run_label", "pipeline_name", "run_type"]
        assert params["run_label"].default == "bioetl"
        assert params["pipeline_name"].kind.name == "KEYWORD_ONLY"
        assert params["pipeline_name"].default is None
        assert params["run_type"].kind.name == "KEYWORD_ONLY"
        assert params["run_type"].default is None
