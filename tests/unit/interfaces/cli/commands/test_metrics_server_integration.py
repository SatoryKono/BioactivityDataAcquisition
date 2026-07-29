# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for metrics server CLI integration helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    metrics_server_context,
)


@pytest.mark.unit
def test_metrics_server_context_yields_started_flag() -> None:
    with patch(
        "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration.ensure_metrics_server_started"
    ) as mock_start:
        mock_start.return_value = True

        with metrics_server_context() as started:
            assert started is True

    mock_start.assert_called_once_with()


@pytest.mark.unit
def test_metrics_server_context_propagates_disabled_state() -> None:
    with patch(
        "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration.ensure_metrics_server_started"
    ) as mock_start:
        mock_start.return_value = False

        with metrics_server_context() as started:
            assert started is False
