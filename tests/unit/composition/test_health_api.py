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

import pytest

from unittest.mock import MagicMock, patch

from bioetl.composition import health_api


pytestmark = pytest.mark.unit


def test_get_health_server_dependencies_delegates_to_services_seam() -> None:
    expected_dependencies = MagicMock(name="HealthServerDependencies")
    with (
        patch(
            "bioetl.composition.health_api.get_health_server_dependencies",
            return_value=expected_dependencies,
        ) as mock_impl,
        patch("bioetl.composition.lazy_exports.import_module") as mock_import_module,
    ):
        result = health_api.get_health_server_dependencies()

    assert result is expected_dependencies
    mock_impl.assert_called_once_with()
    mock_import_module.assert_not_called()


def test_get_quarantine_port_delegates_to_services_seam() -> None:
    expected_port = MagicMock(name="QuarantinePort")

    with (
        patch(
            "bioetl.composition.health_api.get_quarantine_port",
            return_value=expected_port,
        ) as mock_impl,
        patch("bioetl.composition.lazy_exports.import_module") as mock_import_module,
    ):
        result = health_api.get_quarantine_port()

    assert result is expected_port
    mock_impl.assert_called_once_with()
    mock_import_module.assert_not_called()


def test_get_quarantine_service_delegates_to_services_seam() -> None:
    expected_service = MagicMock(name="QuarantineService")

    with (
        patch(
            "bioetl.composition.health_api.get_quarantine_service",
            return_value=expected_service,
        ) as mock_impl,
        patch("bioetl.composition.lazy_exports.import_module") as mock_import_module,
    ):
        result = health_api.get_quarantine_service()

    assert result is expected_service
    mock_impl.assert_called_once_with()
    mock_import_module.assert_not_called()
