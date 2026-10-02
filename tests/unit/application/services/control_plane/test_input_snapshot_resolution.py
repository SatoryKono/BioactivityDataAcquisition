"""Replay selection preserves priority and propagates storage corruption."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.manifest.input_snapshot_resolution import (
    resolve_manifest_input_snapshot_refs,
    resolve_pipeline_input_snapshot_refs,
)

pytestmark = pytest.mark.unit
RUN_ID = "12345678-1234-5678-1234-567812345678"


@pytest.mark.parametrize("cached_refs", [(), (Mock(),)])
def test_enabled_cache_never_falls_back(cached_refs: tuple) -> None:
    load_parent = Mock(side_effect=AssertionError("parent must not be read"))
    assert (
        resolve_pipeline_input_snapshot_refs(
            cached_bronze_enabled=True,
            cached_bronze_refs=cached_refs,
            load_parent_refs=load_parent,
        )
        == cached_refs
    )
    load_parent.assert_not_called()


def test_disabled_empty_cache_uses_parent() -> None:
    refs = (Mock(),)
    load_parent = Mock(return_value=refs)
    assert (
        resolve_pipeline_input_snapshot_refs(
            cached_bronze_enabled=False,
            cached_bronze_refs=(),
            load_parent_refs=load_parent,
        )
        == refs
    )
    load_parent.assert_called_once_with()


def test_manifest_miss_falls_back_to_run_id() -> None:
    first, second = Mock(), Mock()
    store = Mock()
    store.get.return_value = None
    store.get_by_run_id.return_value = SimpleNamespace(
        source_refs=[SimpleNamespace(input_snapshots=(first, second))]
    )
    assert resolve_manifest_input_snapshot_refs(
        store=store, manifest_id="missing", run_id=RUN_ID
    ) == (first, second)
    store.get.assert_called_once_with("missing")
    store.get_by_run_id.assert_called_once_with(UUID(RUN_ID))


def test_found_empty_manifest_does_not_fall_back() -> None:
    store = Mock()
    store.get.return_value = SimpleNamespace(source_refs=[])
    assert (
        resolve_manifest_input_snapshot_refs(
            store=store, manifest_id="found", run_id=RUN_ID
        )
        == ()
    )
    store.get_by_run_id.assert_not_called()


@pytest.mark.parametrize("run_id", [None, "", "invalid"])
def test_invalid_or_absent_run_id_is_an_empty_selection(run_id: str | None) -> None:
    store = Mock()
    assert resolve_manifest_input_snapshot_refs(store=store, run_id=run_id) == ()
    store.get_by_run_id.assert_not_called()


@pytest.mark.parametrize(
    "error", [ValueError("corrupt manifest"), OSError("read failed")]
)
@pytest.mark.parametrize("lookup", ["get", "get_by_run_id"])
def test_storage_errors_propagate(error: Exception, lookup: str) -> None:
    store = Mock()
    store.get.return_value = None
    getattr(store, lookup).side_effect = error
    with pytest.raises(type(error), match=str(error)):
        resolve_manifest_input_snapshot_refs(
            store=store, manifest_id="parent", run_id=RUN_ID
        )


def test_missing_run_manifest_is_empty() -> None:
    store = Mock()
    store.get_by_run_id.return_value = None
    assert resolve_manifest_input_snapshot_refs(store=store, run_id=RUN_ID) == ()
