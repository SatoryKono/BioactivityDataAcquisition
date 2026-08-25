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
"""Delegation contracts for retained maintenance API wrappers."""

from types import SimpleNamespace

import pytest

from bioetl.composition import maintenance_api
from bioetl.composition import resources_runtime

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

    monkeypatch.setattr(resources_runtime, "archive_table", archive)
    monkeypatch.setattr(resources_runtime, "preview_cleanup", preview)
    monkeypatch.setattr(resources_runtime, "vacuum_table", vacuum)

    assert await maintenance_api.archive_table("table", archive_options) == 2
    assert await maintenance_api.preview_cleanup("pipeline") == "preview"
    assert await maintenance_api.vacuum_table("table", vacuum_options) == 3


def test_get_lifecycle_service_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(
        resources_runtime,
        "get_lifecycle_service",
        lambda: sentinel,
    )

    assert maintenance_api.get_lifecycle_service() is sentinel
