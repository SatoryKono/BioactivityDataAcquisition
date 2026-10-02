"""Replay input priority and corruption handling through the existing port."""

from unittest.mock import Mock, call
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.manifest.service import (
    resolve_input_snapshot_refs,
)
from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest, RunSourceRef
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID

pytestmark = pytest.mark.unit
RUN_ID = "00000000-0000-4000-8000-000000000048"
SNAPSHOT = RunInputSnapshotRef(snapshot_id="sha256:captured", content_hash="captured")


def _manifest() -> Mock:
    return Mock(
        spec=RunManifest,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="assay",
                pipeline_name="chembl_assay",
                input_snapshots=(SNAPSHOT,),
            ),
        ),
    )


@pytest.mark.parametrize("refs", [(), (SNAPSHOT,)])
def test_enabled_cached_bronze_is_authoritative_even_when_empty(refs):
    port = Mock(spec=RunManifestPort)
    assert (
        resolve_input_snapshot_refs(
            manifest_port=port,
            cached_bronze_enabled=True,
            cached_bronze_refs=refs,
            manifest_id="parent",
            run_id=RUN_ID,
        )
        == refs
    )
    assert port.mock_calls == []
    assert (
        resolve_input_snapshot_refs(
            manifest_port=None,
            cached_bronze_enabled=True,
            cached_bronze_refs=refs,
            manifest_id="parent",
            run_id=RUN_ID,
        )
        == refs
    )


def test_manifest_id_has_priority_over_run_id():
    port = Mock(spec=RunManifestPort)
    port.get.return_value = _manifest()
    assert resolve_input_snapshot_refs(
        manifest_port=port,
        manifest_id="parent",
        run_id=RUN_ID,
    ) == (SNAPSHOT,)
    port.get.assert_called_once_with("parent")
    port.get_by_run_id.assert_not_called()


def test_manifest_id_miss_falls_back_to_typed_run_id():
    port = Mock(spec=RunManifestPort)
    port.get.return_value = None
    port.get_by_run_id.return_value = _manifest()
    assert resolve_input_snapshot_refs(
        manifest_port=port,
        manifest_id="missing",
        run_id=RUN_ID,
    ) == (SNAPSHOT,)
    assert port.mock_calls == [
        call.get("missing"),
        call.get_by_run_id(RunID(UUID(RUN_ID))),
    ]


@pytest.mark.parametrize("run_id", [None, "not-a-uuid", RUN_ID])
def test_missing_manifest_and_invalid_run_id_have_no_evidence(run_id):
    port = Mock(spec=RunManifestPort)
    port.get.return_value = None
    port.get_by_run_id.return_value = None
    assert (
        resolve_input_snapshot_refs(
            manifest_port=port,
            manifest_id="missing",
            run_id=run_id,
        )
        == ()
    )
    if run_id != RUN_ID:
        port.get_by_run_id.assert_not_called()


@pytest.mark.parametrize("lookup", ["get", "get_by_run_id"])
@pytest.mark.parametrize(
    "error", [OSError("unreadable"), ValueError("corrupt manifest")]
)
def test_manifest_read_errors_are_never_treated_as_invalid_uuid(lookup, error):
    port = Mock(spec=RunManifestPort)
    port.get.return_value = None
    getattr(port, lookup).side_effect = error
    with pytest.raises(type(error), match=str(error)):
        resolve_input_snapshot_refs(
            manifest_port=port, manifest_id="parent", run_id=RUN_ID
        )


def test_replay_lookup_requires_an_explicit_port():
    with pytest.raises(RuntimeError, match="RunManifestPort"):
        resolve_input_snapshot_refs(manifest_port=None, run_id=RUN_ID)
