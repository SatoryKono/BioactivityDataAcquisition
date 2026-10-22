"""Construction smoke for the S1 durability-sweep denominator.

These tests prove each concrete store can be assembled under an isolated
root and that the child-process harness reports exit codes. The Gold case
also reads back one dual-write. They do not interrupt a write or record a
crash verdict.
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import cast

import pytest
from pandera.pandas import Column, DataFrameSchema

from bioetl.domain.types.gold_schema_policy import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    load_delta_table,
    read_delta_records,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter

from tests.integration.infrastructure.durability._child_runner import (
    child_exit_failure,
    child_exit_success,
)
from tests.integration.infrastructure.durability.builders import (
    DurabilityCollaborators,
    StoreAssembly,
    assemble_store,
    builder_names,
    isolated_store_root,
)
from tests.integration.infrastructure.durability.data_factories import (
    CHILD_FAILURE_CODE,
    RUN_REPORT_MARKER,
    STORE_NAMES,
)
from tests.integration.infrastructure.durability.harness import DurabilityHarness

pytestmark = pytest.mark.integration


def _assert_anchored(root: Path, assembly: StoreAssembly) -> None:
    assert assembly.anchored_paths
    resolved_root = root.resolve()
    for anchored in assembly.anchored_paths:
        assert anchored.resolve().is_relative_to(resolved_root)


def _assert_wiring(
    store_name: str,
    assembly: StoreAssembly,
    deps: DurabilityCollaborators,
) -> None:
    if store_name == "g1_bronze":
        assert assembly.bound_metrics is deps.metrics
        return
    if store_name == "g1_silver":
        assert assembly.bound_validator is deps.silver_validator
        assert assembly.bound_clock is deps.clock
        return
    if store_name == "g4_workflow_transform_artifact":
        assert assembly.bound_clock is deps.clock
        return
    if store_name == "g5_run_report":
        marker = assembly.anchored_paths[0]
        assert marker.read_text(encoding="utf-8") == RUN_REPORT_MARKER


def _store_cases() -> list[object]:
    cases: list[object] = []
    for store_name in STORE_NAMES:
        if store_name == "g1_silver":
            cases.append(
                pytest.param(
                    store_name,
                    marks=pytest.mark.require_silver_validator,
                )
            )
        else:
            cases.append(store_name)
    return cases


@pytest.mark.parametrize("store_name", _store_cases())
def test_store_assembles_under_isolated_root(
    tmp_path: Path,
    durability_collaborators: DurabilityCollaborators,
    store_name: str,
) -> None:
    root = isolated_store_root(tmp_path, store_name)
    assembly = assemble_store(store_name, root, durability_collaborators)
    assert type(assembly.instance) is assembly.expected_type
    assert assembly.name == store_name
    _assert_anchored(root, assembly)
    _assert_wiring(store_name, assembly, durability_collaborators)


def test_store_catalog_matches_builders() -> None:
    assert builder_names() == STORE_NAMES


def test_runtime_fixtures_expose_utc_clock_and_contract_validator(
    durability_collaborators: DurabilityCollaborators,
) -> None:
    moment = durability_collaborators.clock.now()
    durability_collaborators.logger.info("durability-construction-smoke")
    assert moment.tzinfo is UTC
    assert durability_collaborators.silver_validator.policy_ref is None


def test_harness_reports_child_exit_codes() -> None:
    harness = DurabilityHarness()
    assert harness.run_isolated(child_exit_success, ()) == 0
    assert harness.run_isolated(child_exit_failure, ()) == CHILD_FAILURE_CODE


async def test_gold_dual_write_smoke(
    tmp_path: Path,
    durability_collaborators: DurabilityCollaborators,
) -> None:
    """Gold builder dual-write projects each contract version on readback."""
    root = isolated_store_root(tmp_path, "g1_gold")
    assembly = assemble_store("g1_gold", root, durability_collaborators)
    writer = cast(GoldWriter, assembly.instance)
    legacy_schema = DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "legacy_value": Column(str, nullable=False),
        },
        strict=True,
    )
    strict_schema = DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "value": Column(float, nullable=False),
        },
        strict=True,
    )
    schema_policy = GoldSchemaPolicyByVersion(
        active_version="2.0.0",
        policies=(
            GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
            GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
        ),
    )

    await writer.write_gold(
        table_name="chembl.activity",
        records=[
            {
                "entity_id": "CHEMBL123",
                "legacy_value": "old-shape",
                "value": 5.5,
            }
        ],
        schema=schema_policy,
        mode="append",
    )

    def _load_delta_rows(table_path: Path) -> list[dict[str, object]]:
        table = load_delta_table(str(table_path))
        return cast(list[dict[str, object]], read_delta_records(table))

    v1_rows = _load_delta_rows(root / "chembl" / "activity__v1_0_0")
    v2_rows = _load_delta_rows(root / "chembl" / "activity__v2_0_0")
    assert v1_rows == [{"entity_id": "CHEMBL123", "legacy_value": "old-shape"}]
    assert v2_rows == [{"entity_id": "CHEMBL123", "value": 5.5}]
