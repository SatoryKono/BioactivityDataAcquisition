"""Issue #12475 physical/logical schema checks on local storage backends."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
import yaml
from deltalake import DeltaTable
from bioetl.domain.exceptions import SchemaEvolutionError
from bioetl.domain.constants import NONDETERMINISTIC_PERSISTED_FIELDS
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types.enums import RunType
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.helpers.clock import fixed_test_clock
from bioetl.domain.types import ScdConfig
from pandera.pandas import Column, DataFrameSchema
from tests.helpers.deterministic_ids import (
    deterministic_batch_id,
    deterministic_run_id,
    deterministic_run_uuid_from_callsite,
)


@pytest.mark.integration
def test_resolved_production_sink_matrix_for_issue_12475() -> None:
    """Enumerate every configured pipeline after the canonical default merge."""
    configs_root = Path("configs")
    resolved: list[tuple[str, str | None, str | None, str | None, str, str | None]] = []
    for entity_path in sorted((configs_root / "entities").rglob("*.yaml")):
        payload = yaml.safe_load(entity_path.read_text(encoding="utf-8")) or {}
        pipeline_name = (payload.get("pipeline") or {}).get("pipeline_name")
        if not pipeline_name:
            continue
        config = load_pipeline_config_from_root(
            pipeline_name,
            configs_root=configs_root,
        )
        sink = config.sink
        resolved.append(
            (
                sink["bronze"].format,
                sink["silver"].format,
                sink["silver"].mode,
                sink["silver"].on_schema_mismatch,
                sink["gold"].format,
                sink["gold"].mode,
            )
        )

    assert len(resolved) == 27
    assert Counter(resolved) == Counter(
        {
            ("jsonl", "delta", "merge", "evolve", "delta", "scd2"): 25,
            ("jsonl", "delta", "merge", "evolve", "delta", "overwrite"): 2,
        }
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_every_resolved_pipeline_config_writes_and_reads_all_layers(
    tmp_path: Path,
) -> None:
    """Exercise Bronze, Silver and configured Gold mode for all 27 pipelines."""
    configs_root = Path("configs")
    bronze_writer = BronzeWriter(
        base_path=tmp_path / "bronze",
        logger=NoOpLogger(),
        metrics=NoOpMetrics(warn_on_use=False),
    )
    silver_writer = _silver_writer(tmp_path / "silver")
    gold_writer = GoldWriter(base_path=tmp_path / "gold", logger=NoOpLogger())
    gold_schema = DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "value": Column(float, nullable=False),
        },
        strict=True,
    )
    observed = 0

    for entity_path in sorted((configs_root / "entities").rglob("*.yaml")):
        payload = yaml.safe_load(entity_path.read_text(encoding="utf-8")) or {}
        pipeline_name = (payload.get("pipeline") or {}).get("pipeline_name")
        if not pipeline_name:
            continue

        config = load_pipeline_config_from_root(
            pipeline_name,
            configs_root=configs_root,
        )
        table_name = f"issue12475_matrix.pipeline_{observed:02d}"
        record_id = f"matrix-{observed:02d}"
        bronze_payload = {"entity_id": record_id, "value": 1.5, "optional": None}
        bronze_result = await bronze_writer.write_bronze(
            records=[json.dumps(bronze_payload).encode("utf-8")],
            provider="issue12475_matrix",
            entity=f"pipeline_{observed:02d}",
            date=datetime(2026, 10, 28, tzinfo=UTC),
            batch_id=deterministic_batch_id(f"issue12475.matrix.{observed}.batch"),
            run_id=deterministic_run_id(f"issue12475.matrix.{observed}.run"),
            run_type=RunType.INCREMENTAL,
            ingestion_ts=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
        )
        assert [
            row async for row in bronze_writer.read_bronze(bronze_result.relative_path)
        ] == [bronze_payload]

        await silver_writer.write_silver(
            table_name=table_name,
            records=[_silver_record(record_id, 1)],
            primary_keys=["entity_id"],
            schema=_silver_schema(value_type=pa.int64()),
            mode=config.sink["silver"].mode,
            on_schema_mismatch=config.sink["silver"].on_schema_mismatch,
        )
        silver_table_path = (
            tmp_path / "silver" / "issue12475_matrix" / f"pipeline_{observed:02d}"
        )
        silver_rows = DeltaTable(str(silver_table_path)).to_pyarrow_table().to_pylist()
        assert len(silver_rows) == 1
        assert silver_rows[0]["entity_id"] == record_id
        assert silver_rows[0]["value"] == 1

        configured_gold_mode = config.sink["gold"].mode
        gold_mode = getattr(configured_gold_mode, "value", configured_gold_mode)
        gold_write_options: dict[str, Any] = {}
        if gold_mode == "scd2":
            gold_write_options["scd_config"] = ScdConfig(
                business_key="entity_id",
                valid_from_col="_valid_from",
                valid_to_col="_valid_to",
                current_flag_col="_is_current",
                version_col="_version",
            )
        await gold_writer.write_gold(
            table_name=table_name,
            records=[{"entity_id": record_id, "value": 1.5}],
            schema=gold_schema,
            primary_keys=["entity_id"],
            mode=gold_mode,
            ingestion_ts=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
            run_id=deterministic_run_uuid_from_callsite(
                f"issue12475_matrix_{observed}"
            ),
            **gold_write_options,
        )
        gold_table_path = (
            tmp_path / "gold" / "issue12475_matrix" / f"pipeline_{observed:02d}"
        )
        gold_rows = DeltaTable(str(gold_table_path)).to_pyarrow_table().to_pylist()
        assert len(gold_rows) == 1
        assert gold_rows[0]["entity_id"] == record_id
        assert gold_rows[0]["value"] == 1.5
        observed += 1

    assert observed == 27


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bronze_jsonl_zstd_write_read_preserves_json_values(
    tmp_path: Path,
) -> None:
    """The configured Bronze backend is compressed JSONL, with no stored schema."""
    writer = BronzeWriter(
        base_path=tmp_path / "bronze",
        logger=NoOpLogger(),
        metrics=NoOpMetrics(warn_on_use=False),
    )
    payload = {
        "entity_id": "CHEMBL123",
        "score": 8.5,
        "count": 3,
        "active": True,
        "optional_text": None,
    }
    result = await writer.write_bronze(
        records=iter([json.dumps(payload, separators=(",", ":")).encode("utf-8")]),
        provider="chembl",
        entity="activity",
        date=datetime(2026, 10, 28, tzinfo=UTC),
        batch_id=deterministic_batch_id("issue12475.bronze.batch"),
        run_id=deterministic_run_id("issue12475.bronze.run"),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
    )

    observed = [row async for row in writer.read_bronze(result.relative_path)]
    assert observed == [payload]
    assert (tmp_path / "bronze" / result.relative_path).suffix == ".zst"
    assert type(observed[0]["score"]) is float
    assert type(observed[0]["count"]) is int
    assert type(observed[0]["active"]) is bool
    assert observed[0]["optional_text"] is None


def _silver_schema(*, added_field: bool = False, value_type: pa.DataType) -> pa.Schema:
    fields = [
        pa.field("entity_id", pa.string(), nullable=False),
        pa.field("value", value_type, nullable=False),
        pa.field("_run_id", pa.string(), nullable=False),
        pa.field("_run_type", pa.string(), nullable=False),
        pa.field("_source_batch_id", pa.string(), nullable=False),
        pa.field("_ingestion_ts", pa.string(), nullable=False),
    ]
    if added_field:
        fields.insert(2, pa.field("new_field", pa.string(), nullable=True))
    return pa.schema(fields)


def _silver_record(
    entity_id: str,
    value: str | int,
    *,
    new_field: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "entity_id": entity_id,
        "value": value,
        "_run_id": deterministic_run_id(f"issue12475.silver.{entity_id}"),
        "_run_type": "incremental",
        "_source_batch_id": deterministic_batch_id(f"issue12475.silver.{entity_id}"),
        "_ingestion_ts": "2026-10-28T12:00:00+00:00",
    }
    if new_field is not None:
        record["new_field"] = new_field
    return record


def _silver_writer(base_path: Path) -> SilverWriter:
    return SilverWriter(
        runtime_request=SilverWriterRuntimeServicesRequest(clock=fixed_test_clock()),
        base_path=str(base_path),
        logger=NoOpLogger(),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_silver_delta_evolve_readback_matches_types_and_nullability(
    tmp_path: Path,
) -> None:
    """A new field evolves independently and the Delta readback preserves schema."""
    writer = _silver_writer(tmp_path / "silver")
    table_path = tmp_path / "silver" / "issue12475_evolve"
    base_schema = _silver_schema(value_type=pa.int64())
    evolved_schema = _silver_schema(added_field=True, value_type=pa.int64())

    await writer.write_silver(
        table_name="issue12475_evolve",
        records=[_silver_record("e1", 1)],
        primary_keys=["entity_id"],
        schema=base_schema,
        mode="merge",
        on_schema_mismatch="evolve",
    )
    await writer.write_silver(
        table_name="issue12475_evolve",
        records=[_silver_record("e2", 2, new_field="added")],
        primary_keys=["entity_id"],
        schema=evolved_schema,
        mode="merge",
        on_schema_mismatch="evolve",
    )

    table = DeltaTable(str(table_path))
    actual = table.schema().to_pyarrow()
    expected = pa.schema(
        [
            field
            for field in evolved_schema
            if field.name not in NONDETERMINISTIC_PERSISTED_FIELDS
        ]
    )
    assert actual.names == expected.names
    assert [field.type for field in actual] == [field.type for field in expected]
    assert [field.nullable for field in actual] == [
        field.nullable for field in expected
    ]
    assert table.to_pyarrow_table().num_rows == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_silver_delta_type_change_negative_control_is_schema_mismatch(
    tmp_path: Path,
) -> None:
    """An incompatible field type is rejected by Delta schema validation itself."""
    writer = _silver_writer(tmp_path / "silver")
    table_path = tmp_path / "silver" / "issue12475_type_change"
    await writer.write_silver(
        table_name="issue12475_type_change",
        records=[_silver_record("e1", "1")],
        primary_keys=["entity_id"],
        schema=_silver_schema(value_type=pa.string()),
        mode="merge",
        on_schema_mismatch="evolve",
    )

    with pytest.raises(SchemaEvolutionError) as outcome:
        await writer.write_silver(
            table_name="issue12475_type_change",
            records=[_silver_record("e2", 2)],
            primary_keys=["entity_id"],
            schema=_silver_schema(value_type=pa.int64()),
            mode="merge",
            on_schema_mismatch="evolve",
        )

    assert outcome.value.changed_fields == {"value": ("string", "int64")}
    assert "changed field types" in str(outcome.value)
    actual = DeltaTable(str(table_path)).schema().to_pyarrow()
    assert actual.field("value").type == pa.string()
    assert table_path.exists()
