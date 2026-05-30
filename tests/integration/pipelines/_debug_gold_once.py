"""One-off debug helper; delete after investigation."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path

import pytest
from deltalake import DeltaTable

CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "chembl"


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


from bioetl.composition.factories.pipeline.registry import chembl_compound_record_factory
from tests.integration.pipelines.base import IntegrationPipelineTestCase


class TestChemblCompoundRecordPipeline(IntegrationPipelineTestCase):
    @pytest.mark.vcr
    async def test_chembl_compound_record_happy_path(self, settings, runtime_config, run_id):
        runtime_config = replace(runtime_config, limit=10, optimize_storage=False)
        runner = self.create_runner(
            factory=chembl_compound_record_factory,
            settings=settings,
            runtime_config=runtime_config,
            run_id=run_id,
        )
        print("runtime skip_gold:", runner._runtime.skip_gold)
        print("pipeline runtime skip_gold:", runner._pipeline.runtime.skip_gold)
        await runner.run()
        print("execution_metrics:", runner.execution_metrics)
        import glob

        print("gold tree:", glob.glob(f"{self.gold_path}/**/*", recursive=True))
        silver_table = runner._pipeline.config.effective_silver_table
        silver_path = self.resolve_delta_table_path(self.silver_path, silver_table)
        silver_count = len(DeltaTable(silver_path).to_pyarrow_table())
        print("silver_count:", silver_count)
