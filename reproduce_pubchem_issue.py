
import asyncio
from unittest.mock import MagicMock, patch

from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter


async def run():
    mock_logger = MagicMock()
    adapter = PubChemAdapter(logger=mock_logger, rate=100)

    # Mock rate limiter acquire
    original_acquire = adapter.rate_limiter.acquire
    call_count = 0

    async def counting_acquire():
        nonlocal call_count
        call_count += 1
        print(f"Acquire called! Count: {call_count}")
        import traceback
        traceback.print_stack()
        return await original_acquire()

    adapter.rate_limiter.acquire = counting_acquire

    mock_compound = MagicMock()
    mock_compound.cid = 123

    with patch("pubchempy.get_compounds", return_value=[mock_compound]):
        print("Fetching...")
        async for record in adapter.fetch("compound", query="aspirin"):
            print(f"Got record: {record['cid']}")

    print(f"Total acquire calls: {call_count}")
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(run())
