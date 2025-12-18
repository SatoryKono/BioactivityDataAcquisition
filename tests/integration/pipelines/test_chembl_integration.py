"""Integration tests for ChEMBL Activity Pipeline using VCR.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uuid import uuid4
from bioetl.domain.types import RunType
from bioetl.composition.bootstrap import bootstrap_pipeline
from bioetl.infrastructure.factories.storage_factory import StorageContext
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter


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
    def checkpoints_path(self, tmp_path) -> Path:
        """Temporary path for checkpoints."""
        p = tmp_path / "checkpoints"
        p.mkdir()
        return p

    @pytest.fixture
    def pipeline(
        self,
        monkeypatch,
        bronze_path,
        silver_path,
        gold_path,
        checkpoints_path,
    ):
        """Bootstrap the pipeline with temporary storage paths."""
        # Enable test mode to skip endpoint validation
        monkeypatch.setenv("BIOETL_TEST_MODE", "true")
        monkeypatch.setenv("BIOETL_ENV", "dev")

        # Clear settings cache so new env vars take effect
        from bioetl.infrastructure.config import get_settings
        get_settings.cache_clear()

        # Create real storage writers pointing to tmp paths
        bronze_writer = BronzeWriter(
            bucket=str(bronze_path),
            endpoint_url=None,
            access_key=None,
            secret_key=None,
            save_json=True,
            json_path=str(bronze_path / "json"),
            logger=MagicMock(),
        )
        silver_writer = DeltaWriter(
            base_path=str(silver_path),
            storage_options=None,
        )
        gold_writer = GoldWriter(
            base_path=str(gold_path),
            storage_options=None,
        )

        storage_adapter = StorageAdapter(
            bronze_writer=bronze_writer,
            silver_writer=silver_writer,
            gold_writer=gold_writer,
        )

        storage_context = StorageContext(
            adapter=storage_adapter,
            bronze_path=str(bronze_path),
            silver_path=str(silver_path),
            gold_path=str(gold_path),
            checkpoints_path=str(checkpoints_path),
        )

        # Patch StorageFactory to return our test storage context
        with patch(
            "bioetl.composition.factories.base_services_factory.StorageFactory.create",
            return_value=storage_context,
        ):
            runner = bootstrap_pipeline(
                pipeline_name="chembl_activity",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=5,  # Small batch for VCR
            )
            yield runner

        # Cleanup: clear settings cache
        get_settings.cache_clear()

    async def test_chembl_extract_transform_load(self, pipeline, silver_path):
        """Test full ETL flow for ChEMBL activity."""
        # 1. Execute Pipeline
        await pipeline.run()

        # 2. Verify Silver Output
        # The table should be created at silver_path / chembl / activity
        # Check for Delta Lake files (parquet + _delta_log)
        files = list(silver_path.rglob("*.parquet"))
        assert len(files) > 0, "No parquet files produced in Silver layer"

        # Verify Delta log was created
        delta_logs = list(silver_path.rglob("_delta_log"))
        assert len(delta_logs) > 0, "No Delta log created in Silver layer"
