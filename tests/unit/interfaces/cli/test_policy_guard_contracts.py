"""CLI output and startup errors retain the configured policy boundary."""

import json
from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.commands import config_dq
from bioetl.interfaces.cli.commands.domains.health import (
    observability_backend_runtime as backend,
)

pytestmark = pytest.mark.unit


def test_effective_config_json_preserves_service_artifact_and_overrides(monkeypatch):
    service = Mock()
    service.get_effective_config_artifact.return_value = {
        "pipeline_name": "chembl_assay",
        "batch_size": 20,
    }
    monkeypatch.setattr(config_dq, "get_config_service", lambda: service)
    output = CliRunner().invoke(
        config_dq.show_effective_config_command,
        ["chembl_assay", "--format", "json", "--override", "batch_size=20"],
    )
    assert output.exit_code == 0, output.output
    assert json.loads(output.output)["batch_size"] == 20
    service.get_effective_config_artifact.assert_called_once_with(
        "chembl_assay", {"batch_size": "20"}
    )


def test_explicit_backend_start_rejects_an_unready_docker_engine(monkeypatch):
    start = Mock()
    monkeypatch.setattr(
        backend, "docker_engine_not_ready_message", lambda: "engine unavailable"
    )
    with pytest.raises(click.ClickException, match="engine unavailable"):
        backend.ensure_observability_backend_started(enabled=True, start_fn=start)
    start.assert_not_called()
