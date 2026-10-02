"""InChIKey chunks preserve ordering while requests share existing limits."""

import asyncio
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem._fetch_strategy_identifiers import (
    _PubChemIdentifierFetchMixin,
)


class ConcurrentHost(_PubChemIdentifierFetchMixin):
    FETCH_STRATEGY_ERRORS = (RuntimeError,)
    _provider_name = "pubchem"

    def __init__(self):
        self.started = []
        self.ready = asyncio.Event()
        self._logger = MagicMock()

    async def _fetch_single_inchikey(self, key):
        self.started.append(key)
        if len(self.started) == 3:
            self.ready.set()
        await asyncio.wait_for(self.ready.wait(), 1)
        if key == "known":
            raise RuntimeError("recoverable")
        if key == "unexpected":
            raise ValueError("unexpected")
        return [{"key": key}]


@pytest.mark.asyncio
async def test_chunk_requests_overlap_and_keep_input_order():
    host = ConcurrentHost()
    result = [
        r async for r in host._iter_inchikey_chunk_records(["one", "two", "three"])
    ]
    assert result == [{"key": key} for key in ("one", "two", "three")]
    assert host.started == ["one", "two", "three"]


@pytest.mark.asyncio
async def test_recoverable_failure_does_not_discard_other_results():
    host = ConcurrentHost()
    result = [
        r async for r in host._iter_inchikey_chunk_records(["one", "known", "three"])
    ]
    assert result == [{"key": "one"}, {"key": "three"}]
    host._logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_unexpected_failure_is_not_silenced():
    host = ConcurrentHost()
    with pytest.raises(ValueError, match="unexpected"):
        [
            r
            async for r in host._iter_inchikey_chunk_records(
                ["one", "unexpected", "three"]
            )
        ]
