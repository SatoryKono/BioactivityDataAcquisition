from __future__ import annotations

from importlib import import_module
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition import health_service_access


pytestmark = pytest.mark.unit


def _owner_module(module_suffix: str) -> object:
    return import_module("bioetl.composition" + module_suffix)


def test_get_health_server_dependencies_delegates_to_services_owner() -> None:
    expected = MagicMock(name="HealthServerDependencies")
    owner_module = _owner_module("._services")

    with patch.object(
        owner_module,
        "get_health_server_dependencies",
        return_value=expected,
    ) as mock_impl:
        result = health_service_access.get_health_server_dependencies()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_health_service_delegates_to_services_owner() -> None:
    expected = MagicMock(name="HealthService")
    owner_module = _owner_module("._services")

    with patch.object(
        owner_module,
        "get_health_service",
        return_value=expected,
    ) as mock_impl:
        result = health_service_access.get_health_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_quarantine_runtime_service_delegates_to_resource_management_owner() -> (
    None
):
    expected = MagicMock(name="QuarantineRuntimeService")
    owner_module = _owner_module("._resource_management")

    with patch.object(
        owner_module,
        "get_quarantine_runtime_service",
        return_value=expected,
    ) as mock_impl:
        result = health_service_access.get_quarantine_runtime_service("chembl_activity")

    assert result is expected
    mock_impl.assert_called_once_with("chembl_activity")


def test_get_quarantine_service_delegates_to_services_owner() -> None:
    expected = MagicMock(name="QuarantineService")
    owner_module = _owner_module("._services")

    with patch.object(
        owner_module,
        "get_quarantine_service",
        return_value=expected,
    ) as mock_impl:
        result = health_service_access.get_quarantine_service()

    assert result is expected
    mock_impl.assert_called_once_with()
