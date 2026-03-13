"""Targeted tests for export CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_export_service_delegates_to_composition_entrypoints() -> None:
    """Export command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.export as export_module

    service = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_export_service",
        return_value=service,
    ) as mock_get_export_service:
        result = export_module.get_export_service()

    assert result is service
    mock_get_export_service.assert_called_once_with()
