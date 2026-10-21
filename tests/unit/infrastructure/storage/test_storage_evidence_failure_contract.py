"""Unreadable paths and invalid sidecars never become trusted storage evidence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.infrastructure.quarantine.filtered_reads import _delta_partition_columns
from bioetl.infrastructure.storage.bronze import cleanup_support
from bioetl.infrastructure.storage.bronze.write_execution import (
    _same_existing_association,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader

pytestmark = pytest.mark.unit


def test_unreadable_root_components_refuse_cleanup(monkeypatch, tmp_path):
    def denied(path):
        raise PermissionError("root metadata unavailable")

    monkeypatch.setattr(Path, "lstat", denied)
    assert cleanup_support.root_components_safe(tmp_path) is False


def test_unresolvable_path_never_passes_containment(monkeypatch, tmp_path):
    def invalid(*args):
        raise ValueError("invalid path")

    monkeypatch.setattr(cleanup_support.os.path, "realpath", invalid)
    assert cleanup_support.is_within_root(tmp_path / "candidate", tmp_path) is False


def test_outside_path_is_not_fully_resolved_under_root(tmp_path):
    assert (
        cleanup_support.is_fully_resolved(
            tmp_path.parent / "outside", tmp_path, tmp_path
        )
        is False
    )


@pytest.mark.parametrize(
    "raw", [b"not json", b"[]", b"{}", b'{"cleanup_association":{"copy_sha256":42}}']
)
def test_invalid_association_cannot_match_an_existing_bronze_batch(raw):
    assert (
        _same_existing_association(raw, SimpleNamespace(metadata={}), "payload", None)
        is False
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("version, identity", [(1, None), (None, "table")])
async def test_pinned_delta_read_requires_both_version_and_table_identity(
    tmp_path, version, identity
):
    reader = DeltaReader(tmp_path, Mock())
    with pytest.raises(ValueError, match="version and table identity"):
        await reader.read_table(
            "provider/entity", snapshot_version=version, snapshot_table_id=identity
        )


def test_unavailable_historical_partition_metadata_stays_unknown():
    table = SimpleNamespace(
        metadata=Mock(side_effect=RuntimeError("metadata unavailable"))
    )
    assert _delta_partition_columns(table) == frozenset()
