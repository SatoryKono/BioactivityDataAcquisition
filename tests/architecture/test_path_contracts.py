"""Architecture test: path contract stability for Medallion layers.

Ensures Bronze file layout and Silver/Gold Delta table paths remain stable
and documented in ADR-025.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from bioetl.application.core.preflight_service import _MedallionConfigValidator
from bioetl.domain.ports import NoOpMetrics
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

ADR_PATH = Path("docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md")

BRONZE_CONTRACT = (
    "data/output/bronze/v1/{provider}/{entity}/{YYYY-MM-DD}/{filename}.jsonl.zst"
)
SILVER_CONTRACT = "data/output/silver/{provider}/{entity}/"
GOLD_CONTRACT = "data/output/gold/{provider}/{entity}/"


def _read_adr() -> str:
    if ADR_PATH.exists():
        path = ADR_PATH
    else:
        path = Path(__file__).parent.parent.parent / ADR_PATH
    return path.read_text(encoding="utf-8")


def test_adr_documents_path_contracts() -> None:
    """ADR-025 MUST document Bronze/Silver/Gold path contracts."""
    adr_text = _read_adr()
    assert BRONZE_CONTRACT in adr_text
    assert SILVER_CONTRACT in adr_text
    assert GOLD_CONTRACT in adr_text


def test_bronze_path_contract() -> None:
    """Bronze file layout MUST follow provider/entity/date/filename.jsonl.zst."""
    writer = BronzeWriter(
        base_path="data/output/bronze",
        logger=Mock(),
        metrics=NoOpMetrics(),
    )
    path = writer._resolve_bronze_path(
        provider="chembl",
        entity="activity",
        date_str="2026-01-21",
        filename="batch_2026-01-21_123.jsonl.zst",
    )
    normalized = path.replace("\\", "/")
    assert normalized == "v1/chembl/activity/2026-01-21/batch_2026-01-21_123.jsonl.zst"
    assert normalized.endswith(BronzeWriter.BRONZE_FILE_SUFFIX)
    assert re.match(
        r"^v1/chembl/activity/\d{4}-\d{2}-\d{2}/.+\.jsonl\.zst$",
        normalized,
    )


def test_silver_path_contract() -> None:
    """Silver Delta tables MUST resolve to provider/entity directories."""
    writer = SilverWriter(base_path="data/output/silver", logger=Mock())
    path = writer._resolve_table_path("chembl.activity")
    normalized = path.replace("\\", "/")
    assert normalized == "data/output/silver/chembl/activity"


def test_gold_path_contract() -> None:
    """Gold Delta tables MUST resolve to provider/entity directories."""
    writer = GoldWriter(base_path="data/output/gold", logger=Mock())
    path = writer._resolve_table_path("chembl.activity")
    normalized = path.replace("\\", "/")
    assert normalized == "data/output/gold/chembl/activity"


def test_bronze_legacy_layout_compatibility() -> None:
    """Bronze legacy layout MAY be written in compatibility mode."""
    writer = BronzeWriter(
        base_path="data/output/bronze",
        logger=Mock(),
        metrics=NoOpMetrics(),
        legacy_layout=True,
    )
    path = writer._resolve_bronze_path(
        provider="chembl",
        entity="activity",
        date_str="2026-01-21",
        filename="batch_2026-01-21_123.jsonl.zst",
    )
    assert (
        path.replace("\\", "/")
        == "chembl/activity/2026-01-21/batch_2026-01-21_123.jsonl.zst"
    )


def test_silver_partition_contract_year_month() -> None:
    """Silver partition contract MUST use year/month partition columns."""
    cfg = SimpleNamespace(
        table=SimpleNamespace(partition_cols=("year", "month"), primary_keys=()),
        dq=SimpleNamespace(key_nullability_rules=()),
    )
    validator = _MedallionConfigValidator(config=cfg, logger=Mock())

    errors = validator._validate_silver_partition_contract()
    assert errors == []


def test_silver_partition_contract_rejects_legacy_partitioning() -> None:
    """Legacy partitioning MUST be rejected by preflight contract validation."""
    cfg = SimpleNamespace(
        table=SimpleNamespace(partition_cols=("source_date",), primary_keys=()),
        dq=SimpleNamespace(key_nullability_rules=()),
    )
    validator = _MedallionConfigValidator(config=cfg, logger=Mock())

    errors = validator._validate_silver_partition_contract()
    assert len(errors) == 1
    assert errors[0].field == "table.partition_cols"
    assert "year=YYYY/month=MM" in errors[0].rule


def test_bronze_compat_reader_finds_legacy_batches(tmp_path: Path) -> None:
    """Compat-read mode MUST detect legacy Bronze batches."""
    legacy_batch = (
        tmp_path
        / "chembl"
        / "activity"
        / "2026-01-21"
        / "batch_2026-01-21_123.jsonl.zst"
    )
    legacy_batch.parent.mkdir(parents=True, exist_ok=True)
    legacy_batch.write_bytes(b"stub")

    writer = BronzeWriter(
        base_path=tmp_path,
        logger=Mock(),
        metrics=NoOpMetrics(),
        compat_read_legacy_layout=True,
    )

    batches = asyncio.run(writer.list_batches("chembl", "activity"))
    assert batches == ["chembl/activity/2026-01-21/batch_2026-01-21_123.jsonl.zst"]
