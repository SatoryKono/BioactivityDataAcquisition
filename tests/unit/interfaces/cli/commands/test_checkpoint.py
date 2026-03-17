"""Targeted tests for checkpoint CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_checkpoint_manager_delegates_to_resources_api() -> None:
    """Checkpoint command module should lazily delegate manager resolution."""
    import bioetl.interfaces.cli.commands.checkpoint as checkpoint_module

    manager = MagicMock()

    with patch(
        "bioetl.composition.resources_api.get_checkpoint_manager",
        return_value=manager,
    ) as mock_get_checkpoint_manager:
        result = checkpoint_module.get_checkpoint_manager("chembl_activity")

    assert result is manager
    mock_get_checkpoint_manager.assert_called_once_with("chembl_activity")
