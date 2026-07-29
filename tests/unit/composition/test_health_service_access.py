# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
