"""Incomplete local references and cross-run ledgers cannot certify saved evidence."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.application.observability.control_plane_evidence.models import (
    _processing_status,
)
from bioetl.application.observability.control_plane_integrity_metrics import (
    _owned_slice_matches,
)
from bioetl.application.services.control_plane.ledger.input_snapshot_recording import (
    _local_batch_file_verified,
    _optional_datetime,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionCorruptionError,
    _ledger_entries_for_manifest,
)
from bioetl.application.services.control_plane.workflow.inspection_service import (
    WorkflowInspectionService,
)
from bioetl.application.services.run_reports._report_diff_support import (
    _parse_repository_env_line,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("uri", ["", "file://", "s3://bucket/object"])
def test_unverified_reference_is_never_treated_as_a_local_batch(uri):
    assert _local_batch_file_verified(uri) is None


def test_file_uri_requires_an_existing_file(tmp_path):
    path = tmp_path / "batch.jsonl"
    assert _local_batch_file_verified("file://" + str(path)) is None
    path.write_text("{}", encoding="utf-8")
    assert _local_batch_file_verified("file://" + str(path)) is True


def test_blank_optional_clock_is_missing_evidence():
    assert _optional_datetime("  ") is None


def test_quoted_environment_value_retains_escaped_quote_before_comment():
    value = 'KEY="a\\" # quoted" # actual comment'
    assert _parse_repository_env_line(value, {"KEY"}) == ("KEY", 'a\\" # quoted')


def test_shutdown_saved_in_launch_context_is_not_reported_as_success():
    assert (
        _processing_status(
            SimpleNamespace(launch_context={"processing_status": "shutdown"}), ()
        )
        == "shutdown"
    )


def test_owned_ledger_slice_rejects_another_manifest():
    assert (
        _owned_slice_matches("owner", (SimpleNamespace(manifest_id="other"),), ())
        is False
    )


def test_manifest_history_cannot_cross_run_ownership():
    predecessor = SimpleNamespace(
        manifest_id="before", run_id="other-run", predecessor_manifest_id=None
    )
    current = SimpleNamespace(
        manifest_id="current", run_id="run", predecessor_manifest_id="before"
    )
    service = SimpleNamespace(
        ledger_port=Mock(),
        manifest_port=SimpleNamespace(get=lambda identity: predecessor),
    )
    with pytest.raises(
        RunManifestInspectionCorruptionError, match="crosses run_id ownership"
    ):
        _ledger_entries_for_manifest(service, current)
    service.ledger_port.list_entries.assert_not_called()


def test_invalid_workflow_run_id_never_queries_storage():
    state = Mock()
    service = WorkflowInspectionService(Mock(), Mock(), state)
    assert service.inspect_run_id("not-a-run-uuid") is None
    state.get_by_run_id.assert_not_called()
