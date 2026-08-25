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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Focused tests for maintenance CLI composition accessors."""

from __future__ import annotations

from types import ModuleType

import pytest

import bioetl.interfaces.cli.commands.domains.maintenance.service_access as subject


pytestmark = pytest.mark.unit


def test_service_access_delegates_sync_accessors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    entrypoints = ModuleType("bioetl.composition.entrypoints")
    entrypoints.get_lifecycle_service = (
        lambda: calls.append("lifecycle") or "lifecycle"
    )
    entrypoints.get_vacuum_service = lambda: calls.append("vacuum") or "vacuum"
    entrypoints.get_contract_migration_service = lambda: (
        calls.append("contract") or "contract"
    )
    services = ModuleType("bioetl.composition._services")
    services.get_bronze_cleanup_service = (
        lambda: calls.append("bronze") or "bronze"
    )
    monkeypatch.setitem(__import__("sys").modules, entrypoints.__name__, entrypoints)
    monkeypatch.setitem(__import__("sys").modules, services.__name__, services)

    assert subject.get_lifecycle_service() == "lifecycle"
    assert subject.get_vacuum_service() == "vacuum"
    assert subject.get_bronze_cleanup_service() == "bronze"
    assert subject.get_contract_migration_service() == "contract"
    assert calls == ["lifecycle", "vacuum", "bronze", "contract"]


@pytest.mark.asyncio
async def test_service_access_preview_cleanup_delegates_async(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _preview_cleanup(pipeline: str) -> str:
        return f"preview:{pipeline}"

    fake_access = ModuleType("bioetl.composition.entrypoints")
    fake_access.preview_cleanup = _preview_cleanup
    monkeypatch.setitem(__import__("sys").modules, fake_access.__name__, fake_access)

    assert await subject.preview_cleanup("chembl_activity") == "preview:chembl_activity"
