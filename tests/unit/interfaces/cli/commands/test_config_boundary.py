"""Targeted tests for config CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_config_service_delegates_to_composition_entrypoints() -> None:
    """Config command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.config as config_module

    service = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_config_service",
        return_value=service,
    ) as mock_get_config_service:
        result = config_module.get_config_service()

    assert result is service
    mock_get_config_service.assert_called_once_with()
