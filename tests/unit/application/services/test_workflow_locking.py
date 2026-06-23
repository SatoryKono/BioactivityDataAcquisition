"""Unit tests for workflow local-runtime locking semantics."""

from __future__ import annotations

from uuid import UUID

import pytest

from bioetl.infrastructure.locking import MemoryLock
from bioetl.domain.types import RunID


@pytest.mark.asyncio
async def test_memory_lock_prevents_duplicate_workflow_key_within_one_process() -> None:
    lock = MemoryLock()
    owner_a = RunID(UUID("00000000-0000-0000-0000-000000000111"))
    owner_b = RunID(UUID("00000000-0000-0000-0000-000000000222"))

    first = await lock.acquire("workflow:chembl_core", owner_a, exclusive=True)
    second = await lock.acquire("workflow:chembl_core", owner_b, exclusive=True)

    assert first is not None
    assert second is None
    assert await lock.release("workflow:chembl_core", owner_a, exclusive=True) is True
    third = await lock.acquire("workflow:chembl_core", owner_b, exclusive=True)
    assert third is not None
