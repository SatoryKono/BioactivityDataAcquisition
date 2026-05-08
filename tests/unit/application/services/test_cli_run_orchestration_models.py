"""Focused unit tests for CLI run orchestration models."""

from __future__ import annotations

import pytest

import bioetl.application.services.cli_run_orchestration_models as legacy_models
import bioetl.application.services.execution.cli_run_orchestration_models as canonical_models
from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)
from bioetl.application.services.pipeline_runner_models import RunOptions


@pytest.mark.unit
class TestStartOffsetValidationResult:
    """Direct tests for validation result model behavior."""

    def test_valid_result_defaults_error_message_to_none(self) -> None:
        result = StartOffsetValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.error_message is None


@pytest.mark.unit
class TestRunExecutionRequest:
    """Direct tests for prepared execution request semantics."""

    def test_canonical_module_exports_only_run_execution_request(self) -> None:
        assert "RunExecutionRequest" in canonical_models.__all__
        assert "RunExecutionSpec" not in canonical_models.__all__
        assert not hasattr(canonical_models, "RunExecutionSpec")

    def test_legacy_module_no_longer_exports_execution_context_alias(self) -> None:
        removed_name = "RunExecution" + "Context"
        assert removed_name not in legacy_models.__all__
        assert not hasattr(legacy_models, removed_name)
        assert removed_name not in dir(legacy_models)

    def test_execution_request_preserves_options_and_health_config(self) -> None:
        options = RunOptions(run_type="backfill", dry_run=True)
        request = RunExecutionRequest(
            pipeline="chembl_activity",
            options=options,
            health_server=False,
            health_port=9090,
        )

        assert request.pipeline == "chembl_activity"
        assert request.options is options
        assert request.health_server is False
        assert request.health_port == 9090


@pytest.mark.unit
class TestRunPreparationResult:
    """Direct tests for preparation result validity contract."""

    def test_is_valid_true_when_request_exists(self) -> None:
        request = RunExecutionRequest(
            pipeline="chembl_activity",
            options=RunOptions(),
            health_server=True,
            health_port=8080,
        )
        result = RunPreparationResult(request=request)

        assert result.is_valid is True
        assert result.error_message is None

    def test_is_valid_false_when_request_missing(self) -> None:
        result = RunPreparationResult(error_message="invalid arguments")

        assert result.is_valid is False
        assert result.request is None
        assert result.error_message == "invalid arguments"

    def test_is_valid_depends_only_on_request_presence(self) -> None:
        request = RunExecutionRequest(
            pipeline="chembl_activity",
            options=RunOptions(),
            health_server=True,
            health_port=8080,
        )
        result = RunPreparationResult(
            request=request,
            error_message="stale warning",
        )

        assert result.is_valid is True
