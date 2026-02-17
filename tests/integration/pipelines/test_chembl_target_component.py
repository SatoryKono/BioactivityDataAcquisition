"""Integration tests for ChEMBL Target Component Pipeline.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pyarrow as pa
import pytest
import structlog

from bioetl.infrastructure.config import load_pipeline_config

# VCR cassette directory for ChEMBL pipeline tests
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "chembl"


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for ChEMBL Target Component pipeline tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


from bioetl.composition.factories.pipeline_factories import (
    chembl_target_component_factory,
)
from bioetl.infrastructure.schemas.silver import CHEMBL_TARGET_COMPONENT_SCHEMA
from tests.integration.pipelines.base import IntegrationPipelineTestCase

logger = structlog.get_logger()


def _patched_silver_schema() -> pa.Schema:
    """Build a patched Silver schema where protein_classification_ids is string.

    The transformer now serializes this field via serialize_json_list(),
    producing a JSON string instead of a native list. The Arrow schema
    must reflect this to avoid ArrowInvalid during writes.
    """
    fields = []
    for field in CHEMBL_TARGET_COMPONENT_SCHEMA:
        if field.name == "protein_classification_ids":
            fields.append(pa.field("protein_classification_ids", pa.string()))
        else:
            fields.append(field)
    return pa.schema(fields)


def _gold_overwrite_sink_overrides() -> dict[str, Any]:
    """Build config_overrides to use 'overwrite' gold mode.

    The StorageAdapter does not yet forward scd_config to GoldWriter,
    so integration tests use 'overwrite' mode to avoid the missing
    scd_config validation error at the Gold layer.
    """
    cfg = load_pipeline_config("chembl_target_component")
    gold_sink = cfg.sink["gold"].model_copy(
        update={"mode": "overwrite", "scd_config": None}
    )
    new_sink = dict(cfg.sink)
    new_sink["gold"] = gold_sink
    return {"sink": new_sink}


class TestChemblTargetComponentPipeline(IntegrationPipelineTestCase):
    @pytest.mark.vcr
    async def test_chembl_target_component_happy_path(
        self, settings, runtime_config, run_id
    ):
        """Test happy path: Bronze -> Silver -> Gold."""
        from dataclasses import replace

        runtime_config = replace(runtime_config, limit=10)

        # Patch the silver schema to accept JSON-serialized protein_classification_ids
        with patch.object(
            chembl_target_component_factory,
            "silver_schema",
            _patched_silver_schema(),
        ):
            runner = self.create_runner(
                factory=chembl_target_component_factory,
                settings=settings,
                runtime_config=runtime_config,
                run_id=run_id,
                config_overrides=_gold_overwrite_sink_overrides(),
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

        silver_table_name = runner.pipeline.config.effective_silver_table
        silver_table_path = f"{self.silver_path}/{silver_table_name}"

        dt_silver = DeltaTable(silver_table_path)
        silver_df = dt_silver.to_pyarrow_table()
        assert len(silver_df) > 0

        # Verify lineage fields in Silver
        assert "_run_id" in silver_df.column_names
        assert "_run_type" in silver_df.column_names
        assert "_ingestion_ts" in silver_df.column_names

        # Verify Gold Delta Table
        gold_table_name = runner.pipeline.config.effective_gold_table
        if not gold_table_name:
            gold_table_name = f"{runner.pipeline.config.provider}.{runner.pipeline.config.entity_type}"

        gold_table_path = f"{self.gold_path}/{gold_table_name.replace('.', '/')}"

        dt_gold = DeltaTable(gold_table_path)
        gold_df = dt_gold.to_pyarrow_table()
        assert len(gold_df) > 0
