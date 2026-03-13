"""Tests for CLI package-level convenience exports."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_create_pipeline_runner_delegates_to_composition_entrypoints() -> None:
    """CLI package export should remain a thin wrapper around entrypoints."""
    import bioetl.interfaces.cli as cli_package

    options = MagicMock()
    runner = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.create_pipeline_runner",
        return_value=runner,
    ) as mock_create_runner:
        result = cli_package.create_pipeline_runner("chembl_activity", options)

    assert result is runner
    mock_create_runner.assert_called_once_with("chembl_activity", options)
