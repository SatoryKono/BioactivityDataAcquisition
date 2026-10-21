"""A pointer introduced during a successor read cannot create a silent cycle."""

import pytest

from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import (
    RunLedgerCorruptionError,
)

pytestmark = pytest.mark.unit


def test_successor_pointer_cycle_created_during_read_is_rejected(tmp_path, monkeypatch):
    pointer = tmp_path / "_predecessors" / "first.txt"
    pointer.parent.mkdir()
    pointer.write_text("old", encoding="utf-8")
    store = FileRunLedgerStore(tmp_path)
    original = store._direct_successor_id

    def changed_during_read(manifest_id):
        if manifest_id == "first":
            (pointer.parent / "old.txt").write_text("first", encoding="utf-8")
        return original(manifest_id)

    monkeypatch.setattr(
        type(store),
        "_direct_successor_id",
        lambda self, identity: changed_during_read(identity),
    )
    with pytest.raises(RunLedgerCorruptionError, match="successor pointer cycle"):
        store._ledger_chain_entries("old")
