"""Integration tests for ChEMBL Activity Pipeline using VCR.py."""

import json
from typing import AsyncGenerator
import pytest
from pathlib import Path

from uuid import uuid4
from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.domain.types import RunType
from bioetl.composition.bootstrap import bootstrap_pipeline
from bioetl.infrastructure.storage.delta_writer import DeltaWriter

# Integration tests need real infrastructure or highly realistic mocks (VCR)
@pytest.mark.integration
@pytest.mark.vcr
class TestChEMBLIntegration:
    """Integration tests for ChEMBL pipeline flow."""

    @pytest.fixture
    def bronze_path(self, tmp_path) -> Path:
        """Temporary path for bronze data."""
        p = tmp_path / "bronze"
        p.mkdir()
        return p

    @pytest.fixture
    def silver_path(self, tmp_path) -> Path:
        """Temporary path for silver data."""
        p = tmp_path / "silver"
        p.mkdir()
        return p

    @pytest.fixture
    def gold_path(self, tmp_path) -> Path:
        """Temporary path for gold data."""
        p = tmp_path / "gold"
        p.mkdir()
        return p

    @pytest.fixture
    async def pipeline(
        self,
        monkeypatch,
        bronze_path,
        silver_path,
        gold_path,
    ) -> AsyncGenerator[ChEMBLActivityPipeline, None]:
        """Bootstrap the pipeline with temporary storage paths."""

        # Override storage paths in configuration using environment vars
        # This assumes ProviderSettings/PipelineConfig pick these up or we mock the factory
        monkeypatch.setenv("STORAGE_BRONZE_BUCKET", str(bronze_path))
        monkeypatch.setenv("STORAGE_SILVER_PATH", str(silver_path))
        monkeypatch.setenv("STORAGE_GOLD_PATH", str(gold_path))

        # Disable metrics server for tests
        monkeypatch.setenv("METRICS_ENABLED", "false")

        # Use fake redis if not provided by docker (but docker-compose usually provides it)
        # For this test, we assume the environment is set up (make test-integration)

        runner = bootstrap_pipeline(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=5  # Small batch for VCR
        )

        # The runner has the pipeline services. We can extract the pipeline or run the runner.
        # But runner.run() is complex. Let's just run the runner to test the full flow.
        return runner

    async def test_chembl_extract_transform_load(self, pipeline, silver_path):
        """Test full ETL flow for ChEMBL activity."""
        # 1. Execute Pipeline
        await pipeline.run()

        # 2. Verify Silver Output
        # The table should be created at silver_path / chembl / activity
        # Note: DeltaTable path depends on how the config resolves it.
        # Assuming defaults: silver/chembl/activity

        # We need to find where it actually wrote.
        # Based on pipeline logic, it writes to silver_table defined in yaml.

        # Since we can't easily query DeltaTable without knowing exact path,
        # let's list files in the silver directory.
        files = list(silver_path.rglob("*.parquet"))
        assert len(files) > 0, "No parquet files produced in Silver layer"

        # We can also check that checkpoints were created
        # (Assuming checkpoint storage was also redirected to tmp or mocked)
