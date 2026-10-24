"""Crash/restart sweep for Lineage fragment and index store (Wave E)."""

from __future__ import annotations

import asyncio
import os
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.control_plane._file_lineage_index import append_jsonl_payload
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time.system_clock import SystemClock
from bioetl.infrastructure.validation import ContractAwareSilverValidator

from tests.integration.infrastructure.durability._child_runner import run_child
from tests.integration.infrastructure.durability.builders import (
    DurabilityCollaborators,
    assemble_store,
    isolated_store_root,
)

pytestmark = pytest.mark.integration

_CHILD_TIMEOUT_S = 10.0
_SIGKILL_ONLY = pytest.mark.skipif(
    not hasattr(signal, "SIGKILL"),
    reason="SIGKILL is unavailable on this platform",
)

def _collaborators() -> DurabilityCollaborators:
    return DurabilityCollaborators(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        clock=SystemClock(),
        silver_validator=ContractAwareSilverValidator(),
    )

def _assembled_store(root: Path) -> FileLineageStore:
    assembly = assemble_store("g3_lineage", root, _collaborators())
    return cast(FileLineageStore, assembly.instance)

def _dummy_fragment() -> LineageGraphFragment:
    return LineageGraphFragment(
        fragment_id="frag_1",
        run_id="run_1",
        manifest_id="manifest_1",
        created_at=datetime.now(UTC),
        stored_fragment_id=None,
    )

def _child_kill_after_fragment_write(root_path: Path) -> None:
    store = _assembled_store(root_path)
    fragment = _dummy_fragment()

    # Patch the _fragment_indexes method to exit before indexes are updated.
    def mock_fragment_indexes(
        self_store: FileLineageStore,
        frag: LineageGraphFragment,
        stored_fragment_id: str,
        index_rollbacks: list[tuple[Path, int]],
    ) -> None:
        os.kill(os.getpid(), signal.SIGKILL)

    with patch.object(FileLineageStore, "_fragment_indexes", new=mock_fragment_indexes):
        store.save(fragment)

@pytest.mark.integration
@_SIGKILL_ONLY
@pytest.mark.unit
def test_row_15a_lineage_crash_after_fragment_write(tmp_path: Path) -> None:
    """Row 15a: Crash after fragment write leaves fragment but no indexes (NOT_VERIFIABLE for recovery, need index sync).
    We test if a kill between atomic_write_text and _fragment_indexes leaves orphaned fragment.
    """
    root = isolated_store_root(tmp_path, "g3_lineage")
    exit_code = run_child(
        _child_kill_after_fragment_write,
        (root,),
        timeout_s=_CHILD_TIMEOUT_S,
    )
    assert exit_code == -signal.SIGKILL

    # Check physical state: fragment exists.
    store = _assembled_store(root)
    fragments_dir = root / "fragments"
    assert fragments_dir.exists()
    fragments = list(fragments_dir.glob("*.json"))
    assert len(fragments) == 1

    # Run ID index doesn't have the entry
    run_indexes = list((root / "indexes").glob("**/*.jsonl"))
    assert len(run_indexes) == 0

def _child_kill_mid_index_append(root_path: Path) -> None:
    store = _assembled_store(root_path)
    fragment = _dummy_fragment()

    # Patch append_jsonl_payload
    original_append = append_jsonl_payload
    def mock_append(*args: object, **kwargs: object) -> int:
        index_path = kwargs.get("path") or args[0]
        if "run_id" in str(index_path):
            # Kill during the run_id index append
            os.kill(os.getpid(), signal.SIGKILL)
        return original_append(*args, **kwargs)

    with patch("bioetl.infrastructure.control_plane.file_lineage_store.append_jsonl_payload", new=mock_append):
        store.save(fragment)

@pytest.mark.integration
@_SIGKILL_ONLY
@pytest.mark.unit
def test_row_15b_lineage_crash_mid_index_append(tmp_path: Path) -> None:
    """Row 15b: Crash in the middle of index appends leaves partial indexes (NOT_VERIFIABLE)."""
    root = isolated_store_root(tmp_path, "g3_lineage")
    exit_code = run_child(
        _child_kill_mid_index_append,
        (root,),
        timeout_s=_CHILD_TIMEOUT_S,
    )
    assert exit_code == -signal.SIGKILL

    fragments_dir = root / "fragments"
    fragments = list(fragments_dir.glob("*.json"))
    assert len(fragments) == 1
