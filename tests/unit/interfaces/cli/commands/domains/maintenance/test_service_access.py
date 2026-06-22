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

    fake_access = ModuleType("bioetl.composition.maintenance_service_access")
    fake_access.get_lifecycle_service = (
        lambda: calls.append("lifecycle") or "lifecycle"
    )
    fake_access.get_vacuum_service = lambda: calls.append("vacuum") or "vacuum"
    fake_access.get_bronze_cleanup_service = (
        lambda: calls.append("bronze") or "bronze"
    )
    fake_access.get_contract_migration_service = (
        lambda: calls.append("contract") or "contract"
    )
    monkeypatch.setitem(__import__("sys").modules, fake_access.__name__, fake_access)

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

    fake_access = ModuleType("bioetl.composition.maintenance_service_access")
    fake_access.preview_cleanup = _preview_cleanup
    monkeypatch.setitem(__import__("sys").modules, fake_access.__name__, fake_access)

    assert await subject.preview_cleanup("chembl_activity") == "preview:chembl_activity"
