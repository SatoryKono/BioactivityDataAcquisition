"""Targeted tests for vacuum CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_lifecycle_service_delegates_to_composition_entrypoints() -> None:
    """Vacuum command module should lazily delegate lifecycle resolution."""
    import bioetl.interfaces.cli.commands.vacuum as vacuum_module

    service = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_lifecycle_service",
        return_value=service,
    ) as mock_get_lifecycle_service:
        result = vacuum_module.get_lifecycle_service()

    assert result is service
    mock_get_lifecycle_service.assert_called_once_with()


@pytest.mark.unit
def test_get_vacuum_service_delegates_to_composition_entrypoints() -> None:
    """Vacuum command module should lazily delegate vacuum service resolution."""
    import bioetl.interfaces.cli.commands.vacuum as vacuum_module

    service = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_vacuum_service",
        return_value=service,
    ) as mock_get_vacuum_service:
        result = vacuum_module.get_vacuum_service()

    assert result is service
    mock_get_vacuum_service.assert_called_once_with()
