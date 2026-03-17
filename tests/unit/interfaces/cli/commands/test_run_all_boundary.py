"""Targeted tests for run-all CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_pipeline_runner_service_delegates_to_services_api() -> None:
    """Run-all module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.run_all as run_all_module

    service = MagicMock()
    registry = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_pipeline_runner_service",
        return_value=service,
    ) as mock_get_pipeline_runner_service:
        result = run_all_module.get_pipeline_runner_service(registry=registry)

    assert result is service
    mock_get_pipeline_runner_service.assert_called_once_with(registry=registry)
