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
"""Architecture test: Medallion clear policy contract."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.application.services.medallion.medallion_lifecycle import (
    MedallionLifecycleService,
)
from bioetl.domain.medallion import MedallionPolicy
from bioetl.domain.types import RunType


@pytest.mark.parametrize(
    ("run_type", "should_clear"),
    [
        (RunType.REBUILD, True),
        (RunType.BACKFILL, True),
        (RunType.INCREMENTAL, False),
    ],
)
@pytest.mark.asyncio
async def test_medallion_clear_policy(run_type: RunType, should_clear: bool) -> None:
    """REBUILD/BACKFILL MUST clear Silver+Gold; INCREMENTAL MUST NOT."""
    storage = Mock()
    storage.clear_silver = AsyncMock(return_value=1)
    storage.clear_gold = AsyncMock(return_value=1)
    service = MedallionLifecycleService(storage=storage, logger=Mock())

    await service.clear(
        policy=MedallionPolicy.for_run_type(run_type),
        silver_table="chembl.activity",
        gold_table="chembl.activity",
    )

    if should_clear:
        storage.clear_silver.assert_awaited_once()
        storage.clear_gold.assert_awaited_once()
    else:
        storage.clear_silver.assert_not_awaited()
        storage.clear_gold.assert_not_awaited()
