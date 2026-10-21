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


def test_manifest_inspection_rejects_a_cyclic_predecessor_chain():
    current = SimpleNamespace(
        manifest_id="current", run_id="run", predecessor_manifest_id="current"
    )
    service = SimpleNamespace(
        ledger_port=Mock(), manifest_port=SimpleNamespace(get=lambda identity: current)
    )
    with pytest.raises(RunManifestInspectionCorruptionError, match="cycle"):
        _ledger_entries_for_manifest(service, current)
    service.ledger_port.list_entries.assert_not_called()


def test_published_snapshot_with_malformed_details_cannot_claim_identity():
    from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_ledger import (
        _published_details,
    )
    from bioetl.domain.control_plane.run_ledger import INPUT_SNAPSHOT_PUBLISHED_EVENT

    assert (
        _published_details(
            SimpleNamespace(event_type=INPUT_SNAPSHOT_PUBLISHED_EVENT, details=[])
        )
        == {}
    )


def test_directory_named_like_cached_bronze_batch_is_not_an_artifact(tmp_path):
    from bioetl.application.services.run_reports.enrichment import (
        build_artifacts_from_result,
    )

    (tmp_path / "batch_fake.jsonl.zst").mkdir()
    result = SimpleNamespace(debug_export_uri=None)
    options = SimpleNamespace(
        use_cached_bronze=True,
        cached_bronze_path=str(tmp_path),
        cached_bronze_date=None,
    )
    assert build_artifacts_from_result(result, options=options) == ()


def test_historical_core_identity_serializes_without_inventing_certification():
    from bioetl.application.services.control_plane.replay.historical_identity_models import (
        HistoricalReplayRunIdentity,
        build_historical_identity_core_payload,
    )

    identity = HistoricalReplayRunIdentity(
        "manifest", "run", "chembl_assay", "chembl", "assay", "historical"
    )
    assert build_historical_identity_core_payload(identity) == {
        "manifest_id": "manifest",
        "run_id": "run",
        "pipeline_name": "chembl_assay",
        "provider": "chembl",
        "entity": "assay",
        "execution_context": "historical",
    }
