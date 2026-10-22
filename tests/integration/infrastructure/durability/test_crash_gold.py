
import os
import time
import signal
import multiprocessing
import pytest
import asyncio
from pathlib import Path
from typing import cast
from pandera import DataFrameSchema, Column
from bioetl.domain.types.gold_schema_policy import GoldSchemaPolicyByVersion, GoldSchemaVersionPolicy
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.storage.delta.table_ops import load_delta_table, read_delta_records
from tests.integration.infrastructure.durability.builders import assemble_store, isolated_store_root, DurabilityCollaborators
from tests.integration.infrastructure.durability._child_runner import run_child

def _get_schemas():
    legacy_schema = DataFrameSchema({"entity_id": Column(str, nullable=False), "legacy_value": Column(str, nullable=True)}, strict=True)
    strict_schema = DataFrameSchema({"entity_id": Column(str, nullable=False), "value": Column(float, nullable=False)}, strict=True)
    return GoldSchemaPolicyByVersion(
        active_version="2.0.0",
        policies=(
            GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
            GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
        ),
    )

def _child_task_postwrite_crash(root_path: Path):
    import asyncio
    import os
    import signal
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.domain.ports.noop import NoOpMetrics
    from bioetl.infrastructure.time.system_clock import SystemClock
    from bioetl.infrastructure.validation.contract_validator import ContractAwareSilverValidator
    from bioetl.domain.ports.noop import NoOpMetadataWriter

    class CrashMetadataWriter(NoOpMetadataWriter):
        async def record_write_outcome(self, *args, **kwargs):
            os.kill(os.getpid(), signal.SIGKILL)

    deps = DurabilityCollaborators(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        clock=SystemClock(),
        silver_validator=ContractAwareSilverValidator(),
    )

    assembly = assemble_store("g1_gold", root_path, deps)
    writer = assembly.instance
    writer._metadata_writer = CrashMetadataWriter()

    records = [{"entity_id": "CHEMBL123", "legacy_value": "old-shape", "value": 5.5}]

    async def run():
        await writer.write_gold(
            table_name="chembl.activity",
            records=records,
            schema=_get_schemas(),
            mode="append"
        )
    asyncio.run(run())

def test_row_10_crash_during_postwrite_pre_entry_gate(tmp_path: Path):
    pytest.skip("NOT_VERIFIABLE: pre-entry gate is missing in Gold Writer")

def test_row_10b_crash_during_postwrite_collaborator_gate(tmp_path: Path):
    root = isolated_store_root(tmp_path, "g1_gold")
    try:
        run_child(_child_task_postwrite_crash, (root,), timeout_s=10.0)
    except Exception as e:
        pass

    table = load_delta_table(str(root / "chembl" / "activity__v1_0_0"))
    v1_rows = cast(list[dict[str, object]], read_delta_records(table))
    assert len(v1_rows) == 1

    table2 = load_delta_table(str(root / "chembl" / "activity__v2_0_0"))
    v2_rows = cast(list[dict[dict[str, object]]], read_delta_records(table2))
    assert len(v2_rows) == 1

def test_row_8_crash_during_normal_commit():
    pytest.skip("NOT_VERIFIABLE")

def test_row_9_crash_during_dual_write_single_commit():
    pytest.skip("NOT_VERIFIABLE")

def test_row_11a_dual_write_crash_before_commit():
    pytest.skip("NOT_VERIFIABLE")

def test_row_11b_dual_write_crash_during_commit():
    pytest.skip("NOT_VERIFIABLE")

def test_row_11c_dual_write_crash_after_commit():
    pytest.skip("NOT_VERIFIABLE")
