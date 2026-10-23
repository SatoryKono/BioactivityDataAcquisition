"""Crash/restart sweep for Gold Delta writer (Wave D)."""

from __future__ import annotations

import ast
import asyncio
import inspect
import os
import signal
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from pandera.pandas import Column, DataFrameSchema

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types.gold_schema_policy import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta.table_ops import (
    load_delta_table,
    read_delta_records,
)
from bioetl.infrastructure.storage.gold.io_delta_runtime import (
    _write_prepared_simple_delta,
)
from bioetl.infrastructure.storage.gold.writer_implementation import (
    _write_dual_target,
    _write_single_target_impl,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.time.system_clock import SystemClock
from bioetl.infrastructure.validation import ContractAwareSilverValidator

from tests.integration.infrastructure.durability._child_runner import run_child
from tests.integration.infrastructure.durability.builders import (
    DurabilityCollaborators,
    assemble_store,
    isolated_store_root,
)

pytestmark = pytest.mark.integration

_CHILD_TIMEOUT_S = 120.0
_SIGKILL_ONLY = pytest.mark.skipif(
    not hasattr(signal, "SIGKILL"),
    reason="SIGKILL is unavailable on this platform",
)


def _schema_policy() -> GoldSchemaPolicyByVersion:
    """Versioned activity schemas used by the dual-write crash probes."""
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
    return GoldSchemaPolicyByVersion(
        active_version="2.0.0",
        policies=(
            GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
            GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
        ),
    )


def _activity_rows() -> list[dict[str, object]]:
    return [
        {
            "entity_id": "CHEMBL123",
            "legacy_value": "old-shape",
            "value": 5.5,
        }
    ]


def _table_path(root: Path, version_suffix: str) -> Path:
    return root / "chembl" / f"activity__{version_suffix}"


def _load_rows(table_path: Path) -> list[dict[str, object]]:
    table = load_delta_table(str(table_path))
    return cast(list[dict[str, object]], read_delta_records(table))


def _collaborators() -> DurabilityCollaborators:
    return DurabilityCollaborators(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        clock=SystemClock(),
        silver_validator=ContractAwareSilverValidator(),
    )


def _assembled_writer(root: Path) -> GoldWriter:
    assembly = assemble_store("g1_gold", root, _collaborators())
    return cast(GoldWriter, assembly.instance)


class _PostwriteMetadataWriter:
    """Non-noop writer so Gold postwrite reaches the metadata coordinator."""

    async def write_gold_metadata(
        self,
        base_path: str,
        metadata: object,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Accept the sidecar payload and leave the Delta table untouched."""
        del base_path, metadata, table_name, flat_structure, provider, entity
        return ""


class _KillOnSecondMetadataBundle:
    """Kill during the second target's postwrite collaborator call."""

    def __init__(self) -> None:
        self.calls = 0

    def create_gold_metadata_bundle(self, input_data: object) -> SimpleNamespace:
        """Return a bundle for v1 and SIGKILL once v2 has already committed."""
        del input_data
        self.calls += 1
        if self.calls >= 2:
            os.kill(os.getpid(), signal.SIGKILL)
        return SimpleNamespace(metadata=object(), lineage_fragment=None)


def _child_kill_on_second_metadata_bundle(root_path: Path) -> None:
    """Commit both Gold versions, then die inside the second postwrite."""
    writer = _assembled_writer(root_path)
    writer._metadata_writer = _PostwriteMetadataWriter()
    writer._metadata_coordinator = _KillOnSecondMetadataBundle()
    asyncio.run(
        writer.write_gold(
            table_name="chembl.activity",
            records=_activity_rows(),
            schema=_schema_policy(),
            mode="append",
        )
    )


def _child_kill_before_dispatch(root_path: Path) -> None:
    """Die at dispatch entry, before ``write_deltalake`` runs."""
    writer = _assembled_writer(root_path)

    async def _kill_before_commit(_context: object) -> None:
        os.kill(os.getpid(), signal.SIGKILL)

    writer._dispatch_write = _kill_before_commit  # type: ignore[method-assign]
    asyncio.run(
        writer.write_gold(
            table_name="chembl.activity",
            records=_activity_rows(),
            schema=_schema_policy(),
            mode="append",
        )
    )


def _assert_killed(exit_code: int) -> None:
    assert exit_code == -signal.SIGKILL


def _assert_no_python_phase_boundary(target: object) -> None:
    """Fail when a native Delta helper exposes a yield or await boundary."""
    assert not inspect.isgeneratorfunction(target)
    assert not inspect.isasyncgenfunction(target)
    assert not inspect.iscoroutinefunction(target)
    source = textwrap.dedent(inspect.getsource(target))
    tree = ast.parse(source)
    assert not any(
        isinstance(node, (ast.Await, ast.Yield, ast.YieldFrom))
        for node in ast.walk(tree)
    )


@_SIGKILL_ONLY
def test_row_10b_crash_during_postwrite_collaborator_gate(tmp_path: Path) -> None:
    """Row 10b: SIGKILL in the second postwrite leaves both Delta tables."""
    root = isolated_store_root(tmp_path, "g1_gold")
    exit_code = run_child(
        _child_kill_on_second_metadata_bundle,
        (root,),
        timeout_s=_CHILD_TIMEOUT_S,
    )
    _assert_killed(exit_code)

    v1_rows = _load_rows(_table_path(root, "v1_0_0"))
    v2_rows = _load_rows(_table_path(root, "v2_0_0"))
    assert v1_rows == [{"entity_id": "CHEMBL123", "legacy_value": "old-shape"}]
    assert v2_rows == [{"entity_id": "CHEMBL123", "value": 5.5}]


@_SIGKILL_ONLY
def test_row_11a_dual_write_crash_before_commit(tmp_path: Path) -> None:
    """Row 11a: a kill at dispatch entry publishes no Gold Delta table."""
    root = isolated_store_root(tmp_path, "g1_gold")
    exit_code = run_child(
        _child_kill_before_dispatch,
        (root,),
        timeout_s=_CHILD_TIMEOUT_S,
    )
    _assert_killed(exit_code)
    assert not _table_path(root, "v1_0_0").exists()
    assert not _table_path(root, "v2_0_0").exists()


def test_row_8_crash_during_normal_commit() -> None:
    """Row 8: the simple-commit helper has no Python yield or await boundary.

    The check does not interrupt ``write_deltalake``. A crash inside that
    native call stays ``NOT_VERIFIABLE``.
    """
    _assert_no_python_phase_boundary(_write_prepared_simple_delta)
    source = inspect.getsource(_write_prepared_simple_delta)
    assert "module.write_deltalake(" in source


def test_row_9_crash_during_dual_write_single_commit() -> None:
    """Row 9: each dual-write target commits through the same native helper."""
    _assert_no_python_phase_boundary(_write_prepared_simple_delta)
    source = inspect.getsource(_write_dual_target)
    assert "await writer._write_single_target" in source


def test_row_10_crash_during_postwrite_pre_entry_gate() -> None:
    """Row 10: postwrite has no separate pre-entry gate before the call."""
    source = inspect.getsource(_write_single_target_impl)
    assert "_post_write_gold" in source
    assert "pre_entry" not in source
    assert "before_postwrite" not in source


def test_row_11b_dual_write_crash_during_commit() -> None:
    """Row 11b: the dual-write commit helper has no Python phase boundary.

    Absence of ``await`` or ``yield`` does not show that ``SIGKILL`` cannot
    land inside ``write_deltalake``. That native-commit crash stays
    ``NOT_VERIFIABLE``.
    """
    _assert_no_python_phase_boundary(_write_prepared_simple_delta)
    source = inspect.getsource(_write_prepared_simple_delta)
    assert source.strip().endswith(")")


def test_row_11c_dual_write_crash_after_commit() -> None:
    """Row 11c: the native helper returns only after ``write_deltalake``."""
    _assert_no_python_phase_boundary(_write_prepared_simple_delta)
    source = textwrap.dedent(inspect.getsource(_write_prepared_simple_delta))
    write_at = source.index("module.write_deltalake(")
    assert "await" not in source[write_at:]
    assert "yield" not in source[write_at:]
