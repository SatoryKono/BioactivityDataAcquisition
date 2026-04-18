"""Integration tests for ChEMBL Compound Record Pipeline.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

import asyncio
import glob
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import structlog
from deltalake import DeltaTable

# VCR cassette directory for ChEMBL pipeline tests
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "chembl"
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for ChEMBL Compound Record pipeline tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


from bioetl.composition.factories.pipeline.registry import (
    chembl_compound_record_factory,
)
from bioetl.domain.exceptions import ApiError
from tests.integration.pipelines.base import IntegrationPipelineTestCase

logger = structlog.get_logger()


class TestChemblCompoundRecordPipeline(IntegrationPipelineTestCase):
    """Integration tests for chembl_compound_record pipeline."""

    @pytest.mark.vcr
    async def test_chembl_compound_record_happy_path(
        self, settings, runtime_config, run_id
    ):
        """Test happy path: Bronze -> Silver -> Gold."""
        # Override limit via config override since RuntimeConfig is frozen
        runtime_config = replace(runtime_config, limit=10)

        runner = self.create_runner(
            factory=chembl_compound_record_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )

        # Run the pipeline
        await runner.run()

        # Debug: list all files in storage root
        for root, _dirs, files in os.walk(self.storage_root):
            for file in files:
                logger.debug("file_found", path=os.path.join(root, file))

        # Verify Bronze files exist
        bronze_files = glob.glob(f"{self.bronze_path}/**/*.jsonl.zst", recursive=True)
        if not bronze_files:
            bronze_files = glob.glob(
                f"{self.bronze_path}/**/*.jsonl.zstd", recursive=True
            )

        assert len(bronze_files) > 0, f"No bronze files found in {self.bronze_path}"

        # Verify Silver Delta Table
        silver_table_name = runner._pipeline.config.effective_silver_table
        silver_table_path = self.resolve_delta_table_path(
            self.silver_path,
            silver_table_name,
        )

        dt_silver = DeltaTable(silver_table_path)
        silver_df = dt_silver.to_pyarrow_table()
        assert len(silver_df) > 0, "Silver table is empty"

        # Persisted Silver rows should exclude occurrence-scoped runtime metadata.
        assert "_run_id" not in silver_df.column_names
        assert "_run_type" not in silver_df.column_names
        assert "_ingestion_ts" not in silver_df.column_names

        # Verify business fields in Silver
        assert "record_id" in silver_df.column_names
        assert "molecule_id" in silver_df.column_names
        assert "publication_id" in silver_df.column_names
        assert "src_id" in silver_df.column_names

        # Verify Gold Delta Table
        gold_table_name = runner._pipeline.config.effective_gold_table
        if not gold_table_name:
            gold_table_name = (
                f"{runner._pipeline.config.provider}."
                f"{runner._pipeline.config.entity_type}"
            )

        gold_table_path = self.resolve_delta_table_path(
            self.gold_path,
            gold_table_name,
        )

        dt_gold = DeltaTable(gold_table_path)
        gold_df = dt_gold.to_pyarrow_table()
        assert len(gold_df) > 0, "Gold table is empty"

    @pytest.mark.vcr
    async def test_chembl_compound_record_error_handling(
        self, settings, runtime_config, run_id
    ):
        """Test error handling when API fails."""
        runner = self.create_runner(
            factory=chembl_compound_record_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )

        class _FailingAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                await asyncio.sleep(0)
                raise ApiError("Simulated API Failure")

        def mock_async_gen(*args, **kwargs):
            if args or kwargs:
                pass
            return _FailingAsyncIterator()

        # Patch the instance method on the adapter object
        runner.services.data_source.fetch = mock_async_gen

        with pytest.raises(ApiError, match="Simulated API Failure"):
            await runner.run()
