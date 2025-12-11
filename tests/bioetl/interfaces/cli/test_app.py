"""CLI command tests for run and validation workflows."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from typer.testing import CliRunner

from bioetl.application.use_cases import InterfaceDisabledError, RunPipelineResponse

cli_app = import_module("bioetl.interfaces.cli.app")

runner = CliRunner()


class StubPathResolver:
    """Stub for config path resolver."""

    def __init__(self, configs_root: Path) -> None:
        self.configs_root = configs_root


class StubCompositionRoot:
    """Stub composition root for CLI tests."""

    def __init__(self, configs_root: Path) -> None:
        self._resolver = StubPathResolver(configs_root)

    def create_config_path_resolver(self) -> StubPathResolver:
        return self._resolver


class StubUseCaseFactory:
    """Factory returning predefined use case stub."""

    def __init__(self, use_case: Any) -> None:
        self._use_case = use_case

    def create_run_pipeline_use_case(self) -> Any:
        return self._use_case


class StubContext:
    """Application context stub used by CLI handlers."""

    def __init__(self, use_case: Any, composition_root: StubCompositionRoot) -> None:
        self.use_case_factory = StubUseCaseFactory(use_case)
        self.composition_root = composition_root
        self.config_loader = Mock()


class StubRunPipelineUseCase:
    """Stub use case for controlling run results."""

    def __init__(self, response: RunPipelineResponse | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.requests: list[Any] = []

    def execute(self, request: Any) -> RunPipelineResponse:
        self.requests.append(request)
        if self._error:
            raise self._error
        if self._response is None:
            raise RuntimeError("Response not configured")
        return self._response


def test_run_success(monkeypatch: Any, tmp_path: Path) -> None:
    """CLI returns zero exit code when pipeline succeeds."""
    response = RunPipelineResponse(
        run_id="run-123",
        success=True,
        row_count=10,
        duration_sec=0.1,
        output_path=None,
    )
    composition_root = StubCompositionRoot(tmp_path)
    context = StubContext(StubRunPipelineUseCase(response=response), composition_root)

    monkeypatch.setattr(cli_app, "get_application_context", lambda: context)
    monkeypatch.setattr(cli_app, "get_composition_root", lambda: composition_root)

    result = runner.invoke(cli_app.app, ["run", "activity_chembl"])

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout


def test_run_interface_disabled(monkeypatch: Any, tmp_path: Path) -> None:
    """CLI exits with code 1 when interface disabled error is raised."""
    composition_root = StubCompositionRoot(tmp_path)
    context = StubContext(
        StubRunPipelineUseCase(error=InterfaceDisabledError("REST")), composition_root
    )

    monkeypatch.setattr(cli_app, "get_application_context", lambda: context)
    monkeypatch.setattr(cli_app, "get_composition_root", lambda: composition_root)

    result = runner.invoke(cli_app.app, ["run", "activity_chembl"])

    assert result.exit_code == 1
    assert "interface is disabled" in result.stdout


def test_run_missing_config(monkeypatch: Any, tmp_path: Path) -> None:
    """CLI shows file error and exits with code 1 when config missing."""
    composition_root = StubCompositionRoot(tmp_path)
    context = StubContext(StubRunPipelineUseCase(response=None), composition_root)

    monkeypatch.setattr(cli_app, "get_application_context", lambda: context)
    monkeypatch.setattr(cli_app, "get_composition_root", lambda: composition_root)

    result = runner.invoke(
        cli_app.app, ["run", "activity_chembl", "--config", "missing.yaml"]
    )

    assert result.exit_code == 1
    assert "Config file not found" in result.stdout


def test_run_invalid_limit(monkeypatch: Any, tmp_path: Path) -> None:
    """CLI validates limit and exits with code 1 when limit is invalid."""
    composition_root = StubCompositionRoot(tmp_path)
    context = StubContext(StubRunPipelineUseCase(response=None), composition_root)

    monkeypatch.setattr(cli_app, "get_application_context", lambda: context)
    monkeypatch.setattr(cli_app, "get_composition_root", lambda: composition_root)

    result = runner.invoke(cli_app.app, ["run", "activity_chembl", "--limit", "-5"])

    assert result.exit_code == 1
    assert "Limit must be a positive integer" in result.stdout


def test_validate_config_success(monkeypatch: Any, tmp_path: Path) -> None:
    """Config validation succeeds and returns exit code 0."""
    config_file = tmp_path / "pipeline.yml"
    config_file.write_text("content", encoding="utf-8")
    composition_root = StubCompositionRoot(tmp_path)
    context = StubContext(StubRunPipelineUseCase(response=None), composition_root)

    monkeypatch.setattr(cli_app, "get_application_context", lambda: context)
    monkeypatch.setattr(cli_app, "get_composition_root", lambda: composition_root)
    monkeypatch.setattr(cli_app, "build_runtime_config", lambda **_: None)

    result = runner.invoke(cli_app.app, ["validate-config", str(config_file)])

    assert result.exit_code == 0
    assert "Config is valid" in result.stdout


def test_validate_config_missing(monkeypatch: Any, tmp_path: Path) -> None:
    """Config validation returns exit code 1 when file not found."""
    composition_root = StubCompositionRoot(tmp_path)
    context = StubContext(StubRunPipelineUseCase(response=None), composition_root)

    monkeypatch.setattr(cli_app, "get_application_context", lambda: context)
    monkeypatch.setattr(cli_app, "get_composition_root", lambda: composition_root)

    result = runner.invoke(cli_app.app, ["validate-config", "missing.yml"])

    assert result.exit_code == 1
    assert "Config file not found" in result.stdout
