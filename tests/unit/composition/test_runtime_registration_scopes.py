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
"""Unit tests for composition runtime registration scopes."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

import pytest

from bioetl.composition import _registration
from bioetl.composition._registration import RuntimeRegistrationScope

pytestmark = pytest.mark.unit


class _PopulatedRegistry:
    def list_pipelines(self) -> list[str]:
        return ["chembl_activity"]


class _EmptyRegistry:
    def list_pipelines(self) -> list[str]:
        return []


def test_provider_scope_loads_providers_without_registering_pipelines() -> None:
    with (
        patch.object(_registration, "ensure_providers_loaded") as ensure_providers,
        patch.object(_registration, "register_all_pipelines") as register_pipelines,
    ):
        _registration.ensure_runtime_registrations(
            scope=RuntimeRegistrationScope.PROVIDERS
        )

    ensure_providers.assert_called_once_with()
    register_pipelines.assert_not_called()


def test_pipeline_scope_loads_providers_and_registers_missing_pipelines() -> None:
    registry = cast(Any, _EmptyRegistry())

    with (
        patch.object(_registration, "ensure_providers_loaded") as ensure_providers,
        patch.object(_registration, "register_all_pipelines") as register_pipelines,
    ):
        _registration.ensure_runtime_registrations(
            registry=registry,
            scope=RuntimeRegistrationScope.PIPELINES,
        )

    ensure_providers.assert_called_once_with()
    register_pipelines.assert_called_once_with(registry=registry)


def test_pipeline_scope_rejects_missing_explicit_registry() -> None:
    with (
        patch.object(_registration, "ensure_providers_loaded") as ensure_providers,
        patch.object(_registration, "register_all_pipelines") as register_pipelines,
        pytest.raises(ValueError, match="explicit registry"),
    ):
        _registration.ensure_runtime_registrations(
            scope=RuntimeRegistrationScope.PIPELINES
        )

    ensure_providers.assert_called_once_with()
    register_pipelines.assert_not_called()


def test_pipeline_scope_skips_registration_when_registry_is_populated() -> None:
    registry = cast(Any, _PopulatedRegistry())

    with (
        patch.object(_registration, "ensure_providers_loaded") as ensure_providers,
        patch.object(_registration, "register_all_pipelines") as register_pipelines,
    ):
        _registration.ensure_runtime_registrations(
            registry=registry,
            scope="pipelines",
        )

    ensure_providers.assert_called_once_with()
    register_pipelines.assert_not_called()


def test_unknown_registration_scope_is_rejected_before_side_effects() -> None:
    with (
        patch.object(_registration, "ensure_providers_loaded") as ensure_providers,
        patch.object(_registration, "register_all_pipelines") as register_pipelines,
        pytest.raises(ValueError),
    ):
        _registration.ensure_runtime_registrations(scope="everything")

    ensure_providers.assert_not_called()
    register_pipelines.assert_not_called()
