"""Targeted tests for lock CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_lock_service_delegates_to_control_plane_api() -> None:
    """Lock command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.lock as lock_module

    service = MagicMock()

    with patch(
        "bioetl.composition.control_plane_api.get_lock_service",
        return_value=service,
    ) as mock_get_lock_service:
        result = lock_module.get_lock_service()

    assert result is service
    mock_get_lock_service.assert_called_once_with()
