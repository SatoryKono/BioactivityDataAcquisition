"""Targeted tests for debug CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_pipeline_runner_service_delegates_to_composition_entrypoints() -> None:
    """Debug command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.debug as debug_module

    service = MagicMock()
    registry = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_pipeline_runner_service",
        return_value=service,
    ) as mock_get_pipeline_runner_service:
        result = debug_module.get_pipeline_runner_service(registry=registry)

    assert result is service
    mock_get_pipeline_runner_service.assert_called_once_with(registry=registry)
