"""Integration tests for ChEMBL Activity Pipeline.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import pytest
import structlog

# VCR cassette directory for ChEMBL pipeline tests
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "chembl"
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for ChEMBL pipeline tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


from bioetl.composition.factories.pipeline.registry import chembl_activity_factory
from tests.integration.pipelines.base import IntegrationPipelineTestCase

logger = structlog.get_logger()


class TestChemblActivityPipeline(IntegrationPipelineTestCase):
    @pytest.mark.vcr
    async def test_chembl_activity_happy_path(self, settings, runtime_config, run_id):
        """Test happy path: Bronze -> Silver -> Gold."""

        # Override limit via config override since RuntimeConfig is frozen

        # We need to create a new RuntimeConfig with limit=10
        from dataclasses import replace

        runtime_config = replace(runtime_config, limit=10)

        runner = self.create_runner(
            factory=chembl_activity_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )

        # Run the pipeline
        await runner.run()

        # We can't easily check report from runner.run() because it returns None in the version I read.
        # But we can check side effects (files created).

        # Verify Bronze files exist
        import glob

        # Look for both compressed and uncompressed just in case, though BronzeWriter uses zstd
        # Also check the path structure
        # BronzeWriter writes to: {base_path}/v1/{provider}/{entity}/{date}/...
        # Bronze writer appends 'bronze' prefix again if path doesn't have it?
        # Output says: File found: .../storage/bronze/bronze/v1/...
        # This is because self.bronze_path is .../storage/bronze
        # And BronzeWriter appends `bucket=bronze_path`.
        # If BronzeWriter treats `bucket` as root, it writes to `bucket/v1/...`.
        # However, the debug output shows double `bronze`: `.../storage/bronze/bronze/v1/...`
        # This implies BronzeWriter logic adds 'bronze' to the path, or `bucket` was set to `.../storage/bronze`.
        # If BronzeWriter takes `bucket` argument and creates `S3Path` or writes to `{bucket}/v1`, that's fine.
        # But if it thinks `bucket` is a bucket name, and we pass a full path, it might be weird.
        # But for local file test, it seems to just append.

        # assert len(bronze_files) > 0, f"No bronze files found in {self.bronze_path}"
        # The glob might be failing because of double bronze.
        # self.bronze_path is /tmp/.../storage/bronze
        # File is /tmp/.../storage/bronze/bronze/v1/...
        # glob should find it with recursive=True.

        # Wait, zst vs zstd.
        # Output says: ...jsonl.zst
        # Test code says: ...jsonl.zstd

        bronze_files = glob.glob(f"{self.bronze_path}/**/*.jsonl.zst", recursive=True)
        if not bronze_files:
            bronze_files = glob.glob(
                f"{self.bronze_path}/**/*.jsonl.zstd", recursive=True
            )

        assert len(bronze_files) > 0, f"No bronze files found in {self.bronze_path}"

        # Verify Silver Delta Table
        from deltalake import DeltaTable

        # Config says silver_table is 'chembl_activity' (underscore) not slash
        silver_table_name = (
            runner._pipeline.config.effective_silver_table
        )  # e.g., chembl_activity
        silver_table_path = self.resolve_delta_table_path(
            self.silver_path,
            silver_table_name,
        )

        dt_silver = DeltaTable(silver_table_path)
        silver_df = dt_silver.to_pyarrow_table()
        assert len(silver_df) > 0

        # Persisted Silver rows should exclude occurrence-scoped runtime metadata.
        assert "_run_id" not in silver_df.column_names
        assert "_run_type" not in silver_df.column_names
        assert "_ingestion_ts" not in silver_df.column_names

        # Verify Gold Delta Table
        # Check what the factory uses if gold_table is None
        # runner._pipeline.config.effective_gold_table might be None if config doesn't set it.
        # But GoldWriter usually gets a default or config must exist.
        gold_table_name = runner._pipeline.config.effective_gold_table

        # If config returns None, it means the pipeline default is used or config is incomplete for tests.
        # ChEMBL Activity usually has `gold_table: chembl.activity` or `chembl_activity`.
        # If None, let's look at the filesystem debug output to find it.
        # Output shows: .../storage/gold/chembl/activity/_delta_log...
        # So it seems it wrote to `chembl/activity`.

        if not gold_table_name:
            # Default fallback logic from PipelineRunner._clear_exports:
            # gold_table = f"{self._config.provider}.{self._config.entity_type}"
            # which is chembl.activity.
            # BUT filesystem shows chembl/activity.
            # SilverWriter replaces . with /.
            gold_table_name = f"{runner._pipeline.config.provider}.{runner._pipeline.config.entity_type}"

        gold_table_path = self.resolve_delta_table_path(
            self.gold_path,
            gold_table_name,
        )

        dt_gold = DeltaTable(gold_table_path)
        gold_df = dt_gold.to_pyarrow_table()
        assert len(gold_df) > 0

    @pytest.mark.vcr
    async def test_chembl_activity_error_handling(
        self, settings, runtime_config, run_id
    ):
        """Test error handling when API fails or data is bad."""

        runner = self.create_runner(
            factory=chembl_activity_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )

        # Use a general exception since DataSourceError is not in exceptions.py
        # Or check if there is a generic API error or create a mock exception
        from bioetl.domain.exceptions import ApiError

        async def mock_async_gen(*args, **kwargs):
            await asyncio.sleep(0)
            if args or kwargs:
                pass
            raise ApiError("Simulated API Failure")

        # Patch the instance method on the adapter object
        runner.services.data_source.fetch = mock_async_gen

        # runner.run() does NOT return report, it returns None.
        # But it logs errors.
        # It catches exceptions?
        # I need to check `PipelineRunner.run`.
        # It calls `self._executor.execute`.

        # If `execute` fails, `run` might propagate the exception or handle it.
        # If it propagates, we should use pytest.raises.

        # Looking at `runner.py`:
        # async with self._services, self._lock_manager:
        #    ...
        #    await self._executor.execute(...)

        # If `execute` raises, it bubble up.

        with pytest.raises(ApiError, match="Simulated API Failure"):
            await runner.run()
