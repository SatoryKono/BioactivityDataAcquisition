"""Targeted tests for archive CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_lifecycle_service_delegates_to_resources_api() -> None:
    """Archive command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.archive as archive_module

    service = MagicMock()

    with patch(
        "bioetl.composition.resources_api.get_lifecycle_service",
        return_value=service,
    ) as mock_get_lifecycle_service:
        result = archive_module.get_lifecycle_service()

    assert result is service
    mock_get_lifecycle_service.assert_called_once_with()
