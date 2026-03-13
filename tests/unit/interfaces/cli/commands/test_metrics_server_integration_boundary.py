"""Targeted tests for metrics server integration CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_ensure_metrics_server_started_delegates_to_composition_entrypoints() -> None:
    """Metrics helper module should lazily delegate server startup."""
    import bioetl.interfaces.cli.commands.metrics_server_integration as metrics_module

    with patch(
        "bioetl.composition.entrypoints.ensure_metrics_server_started",
        return_value=True,
    ) as mock_ensure_metrics_server_started:
        result = metrics_module.ensure_metrics_server_started()

    assert result is True
    mock_ensure_metrics_server_started.assert_called_once_with()
