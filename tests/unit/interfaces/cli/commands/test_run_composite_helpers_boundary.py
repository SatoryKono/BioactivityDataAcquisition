"""Targeted tests for run-composite helper module boundary behavior."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_push_metrics_to_gateway_delegates_to_execution_api() -> None:
    """Run-composite helpers should lazily delegate metrics pushing."""
    from bioetl.interfaces.cli.commands.domains.composite import support as helpers_module

    with patch(
        "bioetl.composition.execution_api.push_metrics_to_gateway",
        return_value=True,
    ) as mock_push_metrics_to_gateway:
        result = helpers_module.push_metrics_to_gateway(
            run_label="composite",
            pipeline_name="publication",
        )

    assert result is True
    mock_push_metrics_to_gateway.assert_called_once_with(
        run_label="composite",
        pipeline_name="publication",
    )
