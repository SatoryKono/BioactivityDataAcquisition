"""Focused unit tests for CLI run orchestration models."""

from __future__ import annotations

from pathlib import Path

import pytest

import bioetl.application.services.cli_run_orchestration_models as legacy_models
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

    def test_legacy_execution_context_alias_warns_and_resolves(self) -> None:
        with pytest.warns(
            DeprecationWarning,
            match="RunExecutionContext is deprecated; use RunExecutionRequest instead",
        ):
            legacy_alias = legacy_models.RunExecutionContext

        assert legacy_alias is RunExecutionRequest

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

    def test_first_party_src_does_not_import_deprecated_execution_context(self) -> None:
        root = Path(__file__).resolve().parents[4] / "src" / "bioetl"
        compatibility_facade = (
            root / "application" / "services" / "cli_run_orchestration_models.py"
        )
        offenders: list[str] = []
        for path in root.rglob("*.py"):
            if path == compatibility_facade:
                continue
            text = path.read_text(encoding="utf-8")
            if "RunExecutionContext" in text:
                offenders.append(str(path.relative_to(root.parent.parent)))

        assert offenders == []


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
