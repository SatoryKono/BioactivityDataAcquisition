"""Runtime E2E tests for contract rollout through the full pipeline bootstrap."""

from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4
from unittest.mock import patch

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake
from tests.helpers.vcr_config import build_cassette_dir

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_contract_policy import (
        PipelineContractPolicy,
    )

_PIPELINE_NAME = "chembl_activity"


@pytest.fixture(scope="module")
def vcr_cassette_dir() -> Path:
    return build_cassette_dir(
        fixtures_root=Path(__file__).resolve().parents[1] / "fixtures" / "vcr",
        provider_dir="chembl",
    )


@pytest.fixture
def vcr_cassette_name() -> str:
    return "test_chembl_activity_full_cycle"


def _make_contract_policy(*, affects_hash: bool) -> PipelineContractPolicy:
    from bioetl.infrastructure.schemas.pipeline_contract_policy import (
        PipelineContractPolicy,
    )

    return PipelineContractPolicy.model_validate(
        {
            "primary_key": ["activity_id"],
            "merge_keys": ["activity_id"],
            "hash_include": [],
            "hash_exclude": [],
            "rename_map": {
                "run_id": "_run_id",
                "run_type": "_run_type",
                "source_batch_id": "_source_batch_id",
                "ingestion_ts": "_ingestion_ts",
                "source": "_source",
            },
            "contract_ref": "chembl.activity",
            "active_version": "1.0.0",
            "rollout": {
                "mode": "dual_read_write",
                "read_order": ["1.0.0", "2.0.0"],
                "write_versions": ["1.0.0", "2.0.0"],
                "affects_hash": affects_hash,
            },
        }
    )


def _versioned_table_path(
    *,
    silver_base_path: Path,
    logical_table: str,
    contract_version: str,
) -> Path:
    from bioetl.infrastructure.storage.versioned_table_resolver import (
        resolve_versioned_table_name,
    )

    provider, _ = logical_table.split(".", 1)
    table_name = resolve_versioned_table_name(logical_table, contract_version)
    return silver_base_path / provider / table_name.split(".", 1)[1]


async def _run_runtime_pipeline(
    *,
    contract_policy: PipelineContractPolicy,
    limit: int,
) -> None:
    from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
    from bioetl.domain.context import InputFilterContext, PipelineRunContext
    from bioetl.domain.types import RunID, RunType

    context = PipelineRunContext(
        pipeline_name=_PIPELINE_NAME,
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=limit,
        input_filter=InputFilterContext.disabled(),
    )

    with ExitStack() as stack:
        for target in (
            "bioetl.composition.factories.storage._helpers.load_pipeline_contract_policy",
            "bioetl.composition.factories.pipeline._creation_wiring.load_pipeline_contract_policy",
            "bioetl.composition.factories.pipeline.contract_validator.load_pipeline_contract_policy",
        ):
            stack.enter_context(patch(target, return_value=contract_policy))
        runner = bootstrap_pipeline_runner(context)
        await runner.run()


def _append_shadow_only_row(table_path: Path) -> None:
    existing_table = DeltaTable(str(table_path)).to_pyarrow_table()
    rows = existing_table.to_pylist()
    if not rows:
        raise AssertionError("Expected shadow table to contain at least one row")
    extra_row = deepcopy(rows[0])
    if "activity_id" in extra_row:
        extra_row["activity_id"] = f"{extra_row['activity_id']}-shadow"
    if "entity_id" in extra_row:
        extra_row["entity_id"] = f"{extra_row['entity_id']}-shadow"
    rows.append(extra_row)
    write_deltalake(
        str(table_path),
        pa.Table.from_pylist(rows, schema=existing_table.schema),
        mode="overwrite",
    )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_runtime_rollout_dual_write_populates_versioned_silver_tables(
    e2e_data_dir: Path,
) -> None:
    from bioetl.infrastructure.config import get_settings

    await _run_runtime_pipeline(
        contract_policy=_make_contract_policy(affects_hash=False),
        limit=10,
    )

    settings = get_settings()
    silver_base_path = Path(settings.silver_path)
    v1_path = _versioned_table_path(
        silver_base_path=silver_base_path,
        logical_table="chembl.activity",
        contract_version="1.0.0",
    )
    v2_path = _versioned_table_path(
        silver_base_path=silver_base_path,
        logical_table="chembl.activity",
        contract_version="2.0.0",
    )

    v1_rows = DeltaTable(str(v1_path)).to_pyarrow_table().to_pylist()
    v2_rows = DeltaTable(str(v2_path)).to_pyarrow_table().to_pylist()

    assert v1_rows, "Legacy Silver version should be written by runtime rollout"
    assert v2_rows, "Shadow Silver version should be written by runtime rollout"
    assert len(v1_rows) == len(v2_rows)
    assert all("_run_id" not in row for row in v1_rows)
    assert all("_run_id" not in row for row in v2_rows)
    assert all("_run_type" not in row for row in v1_rows)
    assert all("_run_type" not in row for row in v2_rows)
    assert all("_ingestion_ts" not in row for row in v1_rows)
    assert all("_ingestion_ts" not in row for row in v2_rows)


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_runtime_rollout_affects_hash_flag_executes_full_runtime_path(
    e2e_data_dir: Path,
) -> None:
    from bioetl.infrastructure.config import get_settings

    await _run_runtime_pipeline(
        contract_policy=_make_contract_policy(affects_hash=True),
        limit=10,
    )

    settings = get_settings()
    silver_base_path = Path(settings.silver_path)
    v1_path = _versioned_table_path(
        silver_base_path=silver_base_path,
        logical_table="chembl.activity",
        contract_version="1.0.0",
    )
    v2_path = _versioned_table_path(
        silver_base_path=silver_base_path,
        logical_table="chembl.activity",
        contract_version="2.0.0",
    )

    v1_rows = DeltaTable(str(v1_path)).to_pyarrow_table().to_pylist()
    v2_rows = DeltaTable(str(v2_path)).to_pyarrow_table().to_pylist()

    assert v1_rows and v2_rows
    assert len(v1_rows) == len(v2_rows)
    assert all(
        isinstance(row.get("content_hash"), str) and row["content_hash"]
        for row in v1_rows
    )
    assert all(
        isinstance(row.get("content_hash"), str) and row["content_hash"]
        for row in v2_rows
    )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_runtime_rollout_cutover_and_rollback_change_export_reader_priority(
    e2e_data_dir: Path,
) -> None:
    from bioetl.composition.bootstrap.cli.storage import bootstrap_export_service
    from bioetl.infrastructure.config import get_pipeline_config, get_settings
    from bioetl.infrastructure.storage.delta_reader import DeltaReader

    await _run_runtime_pipeline(
        contract_policy=_make_contract_policy(affects_hash=False),
        limit=10,
    )

    settings = get_settings()
    silver_base_path = Path(settings.silver_path)
    v2_path = _versioned_table_path(
        silver_base_path=silver_base_path,
        logical_table="chembl.activity",
        contract_version="2.0.0",
    )
    _append_shadow_only_row(v2_path)

    get_pipeline_config.cache_clear()
    service = bootstrap_export_service()
    reader = service.reader
    assert isinstance(reader, DeltaReader)

    before_cutover = await reader.read_with_fallback(
        "chembl.activity",
        ["1.0.0", "2.0.0"],
    )
    after_cutover = await reader.read_with_fallback(
        "chembl.activity",
        ["2.0.0", "1.0.0"],
    )
    after_rollback = await reader.read_with_fallback(
        "chembl.activity",
        ["1.0.0", "2.0.0"],
    )

    assert len(after_cutover.to_pylist()) == len(before_cutover.to_pylist()) + 1
    assert after_rollback.to_pylist() == before_cutover.to_pylist()
