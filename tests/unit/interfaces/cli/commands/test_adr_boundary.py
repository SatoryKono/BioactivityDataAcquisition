"""Targeted tests for ADR CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_adr_service_delegates_to_services_api() -> None:
    """ADR command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.adr as adr_module

    service = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_adr_service",
        return_value=service,
    ) as mock_get_adr_service:
        result = adr_module.get_adr_service()

    assert result is service
    mock_get_adr_service.assert_called_once_with()
