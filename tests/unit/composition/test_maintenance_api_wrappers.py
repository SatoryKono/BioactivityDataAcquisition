"""Delegation contracts for retained maintenance API wrappers."""

from types import SimpleNamespace

import pytest

from bioetl.composition import maintenance_api
from bioetl.composition import resources_api

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_async_maintenance_wrappers_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_options = SimpleNamespace()
    vacuum_options = SimpleNamespace()

    async def archive(table: str, options: object) -> int:
        assert (table, options) == ("table", archive_options)
        return 2

    async def preview(pipeline: str) -> str:
        assert pipeline == "pipeline"
        return "preview"

    async def vacuum(table: str, options: object) -> int:
        assert (table, options) == ("table", vacuum_options)
        return 3

    monkeypatch.setattr(resources_api, "archive_table", archive)
    monkeypatch.setattr(resources_api, "preview_cleanup", preview)
    monkeypatch.setattr(resources_api, "vacuum_table", vacuum)

    assert await maintenance_api.archive_table("table", archive_options) == 2
    assert await maintenance_api.preview_cleanup("pipeline") == "preview"
    assert await maintenance_api.vacuum_table("table", vacuum_options) == 3


def test_get_lifecycle_service_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(resources_api, "get_lifecycle_service", lambda: sentinel)

    assert maintenance_api.get_lifecycle_service() is sentinel
