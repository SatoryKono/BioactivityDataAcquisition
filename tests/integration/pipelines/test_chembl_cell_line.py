"""Integration tests for ChEMBL Cell Line Pipeline."""

from __future__ import annotations

import pytest
import structlog

from bioetl.composition.factories.pipeline_factories import (
    chembl_cell_line_factory,
)
from tests.integration.pipelines.base import IntegrationPipelineTestCase

logger = structlog.get_logger()


class TestChemblCellLinePipeline(IntegrationPipelineTestCase):
    @pytest.mark.vcr
    async def test_chembl_cell_line_happy_path(self, settings, runtime_config, run_id):
        """Test happy path: Bronze -> Silver -> Gold."""
        from dataclasses import replace

        runtime_config = replace(runtime_config, limit=10)

        runner = self.create_runner(
            factory=chembl_cell_line_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )

        await runner.run()

        # Verify Bronze files exist
        import glob

        bronze_files = glob.glob(f"{self.bronze_path}/**/*.jsonl.zst", recursive=True)
        if not bronze_files:
            bronze_files = glob.glob(
                f"{self.bronze_path}/**/*.jsonl.zstd", recursive=True
            )

        assert len(bronze_files) > 0, f"No bronze files found in {self.bronze_path}"

        # Verify Silver Delta Table
        from deltalake import DeltaTable

        silver_table_name = runner.pipeline.config.silver_table
        silver_table_path = f"{self.silver_path}/{silver_table_name}"

        dt_silver = DeltaTable(silver_table_path)
        silver_df = dt_silver.to_pyarrow_table()
        assert len(silver_df) > 0

        # Verify lineage fields in Silver
        assert "_run_id" in silver_df.column_names
        assert "_run_type" in silver_df.column_names
        assert "_ingestion_ts" in silver_df.column_names

        # Verify cell_line specific fields
        assert "cell_chembl_id" in silver_df.column_names
        assert "cell_name" in silver_df.column_names

        # Verify Gold Delta Table
        gold_table_name = runner.pipeline.config.gold_table
        if not gold_table_name:
            gold_table_name = f"{runner.pipeline.config.provider}.{runner.pipeline.config.entity_type}"

        gold_table_path = f"{self.gold_path}/{gold_table_name.replace('.', '/')}"

        dt_gold = DeltaTable(gold_table_path)
        gold_df = dt_gold.to_pyarrow_table()
        assert len(gold_df) > 0

    @pytest.mark.vcr
    async def test_chembl_cell_line_source_fields(
        self, settings, runtime_config, run_id
    ):
        """Test that source and metadata fields are correctly captured."""
        from dataclasses import replace

        runtime_config = replace(runtime_config, limit=50)

        runner = self.create_runner(
            factory=chembl_cell_line_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )

        await runner.run()

        # Verify Silver Delta Table has source columns
        from deltalake import DeltaTable

        silver_table_name = runner.pipeline.config.silver_table
        silver_table_path = f"{self.silver_path}/{silver_table_name}"

        dt_silver = DeltaTable(silver_table_path)
        silver_df = dt_silver.to_pyarrow_table()

        # Core source fields should be present
        assert "cell_source_tissue" in silver_df.column_names
        assert "cell_source_organism" in silver_df.column_names
        # External references
        assert "cellosaurus_id" in silver_df.column_names
        assert "cl_lincs_id" in silver_df.column_names
