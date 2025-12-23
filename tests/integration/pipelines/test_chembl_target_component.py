"""Integration tests for ChEMBL Target Component Pipeline."""

import pytest
import structlog

from bioetl.composition.factories.pipeline_factories import chembl_target_component_factory
from tests.integration.pipelines.base import IntegrationPipelineTestCase

logger = structlog.get_logger()


class TestChemblTargetComponentPipeline(IntegrationPipelineTestCase):

    @pytest.mark.vcr
    async def test_chembl_target_component_happy_path(
        self, settings, runtime_config, run_id
    ):
        """Test happy path: Bronze -> Silver -> Gold."""
        from dataclasses import replace

        runtime_config = replace(runtime_config, limit=10)

        runner = self.create_runner(
            factory=chembl_target_component_factory,
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

        # Verify Gold Delta Table
        gold_table_name = runner.pipeline.config.gold_table
        if not gold_table_name:
            gold_table_name = (
                f"{runner.pipeline.config.provider}.{runner.pipeline.config.entity_type}"
            )

        gold_table_path = f"{self.gold_path}/{gold_table_name.replace('.', '/')}"

        dt_gold = DeltaTable(gold_table_path)
        gold_df = dt_gold.to_pyarrow_table()
        assert len(gold_df) > 0
