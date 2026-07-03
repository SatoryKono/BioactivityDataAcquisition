from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.cli.commands.domains.quarantine import runtime_access
from bioetl.interfaces.cli.commands.domains.quarantine.server_backend import (
    run_long_lived_quarantine_backend_command,
)

pytestmark = pytest.mark.unit


def test_get_quarantine_runtime_service_delegates_to_health_service_access() -> None:
    expected_service = MagicMock(name="QuarantineRuntimeService")

    with patch(
        "bioetl.composition.health_service_access.get_quarantine_runtime_service",
        return_value=expected_service,
    ) as mock_impl:
        result = runtime_access.get_quarantine_runtime_service("chembl_activity")

    assert result is expected_service
    mock_impl.assert_called_once_with("chembl_activity")


def test_get_quarantine_service_delegates_to_health_service_access() -> None:
    expected_service = MagicMock(name="QuarantineService")

    with patch(
        "bioetl.composition.health_service_access.get_quarantine_service",
        return_value=expected_service,
    ) as mock_impl:
        result = runtime_access.get_quarantine_service()

    assert result is expected_service
    mock_impl.assert_called_once_with()


def test_run_long_lived_quarantine_backend_command_delegates_to_shared_backend() -> (
    None
):
    with patch(
        "bioetl.interfaces.cli.commands.domains.health.server_integration.run_long_lived_health_server_command"
    ) as mock_impl:
        run_long_lived_quarantine_backend_command(host="127.0.0.1", port=18081)

    mock_impl.assert_called_once_with(
        host="127.0.0.1",
        port=18081,
        start_metrics=False,
    )
