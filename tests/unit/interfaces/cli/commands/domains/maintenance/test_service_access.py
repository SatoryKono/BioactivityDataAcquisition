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

    fake_api = ModuleType("bioetl.composition.maintenance_api")
    fake_api.get_lifecycle_service = lambda: calls.append("lifecycle") or "lifecycle"
    fake_api.get_vacuum_service = lambda: calls.append("vacuum") or "vacuum"
    fake_api.get_bronze_cleanup_service = lambda: calls.append("bronze") or "bronze"
    fake_api.get_contract_migration_service = (
        lambda: calls.append("contract") or "contract"
    )
    monkeypatch.setitem(__import__("sys").modules, fake_api.__name__, fake_api)

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

    fake_api = ModuleType("bioetl.composition.maintenance_api")
    fake_api.preview_cleanup = _preview_cleanup
    monkeypatch.setitem(__import__("sys").modules, fake_api.__name__, fake_api)

    assert await subject.preview_cleanup("chembl_activity") == "preview:chembl_activity"

