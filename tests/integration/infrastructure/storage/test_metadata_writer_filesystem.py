"""Integration tests for MetadataWriter filesystem behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from tests.helpers.metadata_fixtures import build_bronze_metadata

from bioetl.domain.models.metadata import (
    BronzeMetadata,
    GoldMetadata,
    SilverMetadata,
)
from bioetl.infrastructure.storage.metadata_writer import (
    METADATA_FILENAME,
    MetadataWriter,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_write_bronze_metadata_creates_file(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Bronze metadata writes should create one persisted sidecar."""
    base_path = tmp_path / "bronze" / "v1" / "chembl" / "activity" / "2025-01-15"
    base_path.mkdir(parents=True)

    result = await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    metadata_path = base_path / METADATA_FILENAME
    assert metadata_path.exists()
    assert result == str(metadata_path.resolve())


@pytest.mark.asyncio
async def test_write_bronze_metadata_valid_yaml(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Bronze metadata sidecars should serialize to canonical YAML."""
    base_path = tmp_path / "bronze"
    base_path.mkdir(parents=True)

    await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert content["version"] == "1.1"
    assert content["layer"] == "bronze"
    assert content["pipeline"]["name"] == "chembl_activity"
    assert content["pipeline"]["provider"] == "chembl"
    assert content["source"]["type"] == "api"
    assert content["output"]["record_count"] == 10000


@pytest.mark.asyncio
async def test_write_silver_metadata_creates_file(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver metadata writes should create one persisted sidecar."""
    base_path = tmp_path / "silver" / "chembl" / "activity"
    base_path.mkdir(parents=True)

    result = await metadata_writer.write_silver_metadata(base_path, silver_metadata)

    metadata_path = base_path / METADATA_FILENAME
    assert metadata_path.exists()
    assert result == str(metadata_path.resolve())


@pytest.mark.asyncio
async def test_write_silver_metadata_includes_lineage(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver metadata sidecars should persist lineage fields."""
    base_path = tmp_path / "silver"
    base_path.mkdir(parents=True)

    await metadata_writer.write_silver_metadata(base_path, silver_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert "lineage" in content
    assert "source_batch_ids" in content["lineage"]
    assert "bronze_paths" in content["lineage"]
    assert "transform_steps" in content["lineage"]


@pytest.mark.asyncio
async def test_write_silver_metadata_includes_dq_summary(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver metadata sidecars should persist DQ summary fields."""
    base_path = tmp_path / "silver"
    base_path.mkdir(parents=True)

    await metadata_writer.write_silver_metadata(base_path, silver_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert "dq_summary" in content
    assert content["dq_summary"]["total_records"] == 15000
    assert content["dq_summary"]["error_rate"] == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_write_gold_metadata_creates_file(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    gold_metadata: GoldMetadata,
) -> None:
    """Gold metadata writes should create one persisted sidecar."""
    base_path = tmp_path / "gold" / "chembl" / "activity_aggregated"
    base_path.mkdir(parents=True)

    result = await metadata_writer.write_gold_metadata(base_path, gold_metadata)

    metadata_path = base_path / METADATA_FILENAME
    assert metadata_path.exists()
    assert result == str(metadata_path.resolve())


@pytest.mark.asyncio
async def test_write_gold_metadata_includes_schema_contract(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    gold_metadata: GoldMetadata,
) -> None:
    """Gold metadata sidecars should persist schema contract fields."""
    base_path = tmp_path / "gold"
    base_path.mkdir(parents=True)

    await metadata_writer.write_gold_metadata(base_path, gold_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert "schema" in content
    assert (
        content["schema"]["contract_path"] == "docs/contracts/gold/activity_v1.0.json"
    )
    assert content["schema"]["validation"] == "strict"


@pytest.mark.asyncio
async def test_finalize_silver_metadata_updates_existing_sidecar(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver finalization should patch the persisted sidecar in place."""
    base_path = tmp_path / "silver"
    base_path.mkdir(parents=True)
    await metadata_writer.write_silver_metadata(base_path, silver_metadata)
    dq_report_path = str(tmp_path / "dq" / "silver-report.json")

    completed_at = datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC)
    result = await metadata_writer.finalize_silver_metadata(
        base_path,
        dq_report_path=dq_report_path,
        completed_at=completed_at,
        delta_version_after=99,
    )

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    expected_completed_at = completed_at.isoformat().replace("+00:00", "Z")
    assert result == str((base_path / METADATA_FILENAME).resolve())
    assert content["dq_report_path"] == dq_report_path
    assert content["runtime"]["completed_at_utc"] == expected_completed_at
    assert content["output"]["write_completed_at"] == expected_completed_at
    assert content["delta"]["version_after"] == 99
    assert content["output_ext"]["delta_version_after"] == 99


@pytest.mark.asyncio
async def test_finalize_gold_metadata_updates_existing_sidecar(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    gold_metadata: GoldMetadata,
) -> None:
    """Gold finalization should patch the persisted sidecar in place."""
    base_path = tmp_path / "gold"
    base_path.mkdir(parents=True)
    await metadata_writer.write_gold_metadata(base_path, gold_metadata)
    dq_report_path = str(tmp_path / "dq" / "gold-report.json")

    completed_at = datetime(2025, 1, 16, 12, 5, 0, tzinfo=UTC)
    result = await metadata_writer.finalize_gold_metadata(
        base_path,
        dq_report_path=dq_report_path,
        completed_at=completed_at,
    )

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    expected_completed_at = completed_at.isoformat().replace("+00:00", "Z")
    assert result == str((base_path / METADATA_FILENAME).resolve())
    assert content["dq_report_path"] == dq_report_path
    assert content["runtime"]["completed_at_utc"] == expected_completed_at
    assert content["output"]["write_completed_at"] == expected_completed_at


@pytest.mark.asyncio
async def test_atomic_write_creates_no_temp_files(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Atomic metadata writes should not leak temporary files."""
    base_path = tmp_path / "bronze"
    base_path.mkdir(parents=True)

    await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    assert list(base_path.glob("*.tmp")) == []


@pytest.mark.asyncio
async def test_write_metadata_overwrites_existing(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Repeated metadata writes should replace prior file contents."""
    base_path = tmp_path / "bronze"
    base_path.mkdir(parents=True)
    await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    updated_metadata = build_bronze_metadata(
        version="1.0",
        runtime=bronze_metadata.runtime.model_copy(update={"run_type": "rebuild"}),
        pipeline=bronze_metadata.pipeline,
        environment=bronze_metadata.environment,
    )
    await metadata_writer.write_bronze_metadata(base_path, updated_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert content["runtime"]["run_type"] == "rebuild"
