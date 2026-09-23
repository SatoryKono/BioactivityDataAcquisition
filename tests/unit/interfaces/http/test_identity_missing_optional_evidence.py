"""Absent optional forensic facts must not render as observed healthy facts."""

from datetime import UTC, datetime

import pytest

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.types import RunType
from bioetl.interfaces.http.control_plane_identity.payload import build_anchor_row
from bioetl.interfaces.http.control_plane_identity.specs import SPEC_BY_NAME
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

pytestmark = pytest.mark.unit


@pytest.fixture
def manifest() -> RunManifest:
    return RunManifest(
        manifest_id="manifest-forensic-missing",
        execution_fingerprint="fingerprint-forensic-missing",
        schema_version="1.0",
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite("forensic-missing"),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(git_commit="recorded-commit"),
    )


@pytest.mark.parametrize(
    "name", ["checkpoint_file_id", "dq_report_paths", "bronze_batch_ids"]
)
@pytest.mark.parametrize("value", [None, [], "recorded-reference"])
def test_optional_evidence_separates_absence_from_presence(manifest, name, value):
    row = build_anchor_row(
        SPEC_BY_NAME[name],
        value=value,
        manifest=manifest,
        ledger_entries=(),
        checkpoint_status="MISSING",
    )
    if value:
        assert row["status"] == "OK"
        assert row["present"] is True
        assert row["source_quality"] != "unavailable"
    else:
        assert row["status"] == row["ui_status"] == "UNKNOWN"
        assert row["value_short"] == row["value_full"] == "missing"
        assert row["present"] is False
        assert row["source_quality"] == "unavailable"
        assert row["copy"] is False
        # Optional absence does not become a new mandatory identity gap.
        assert row["identity_gap"] is False


def test_non_applicable_evidence_stays_na(manifest):
    row = build_anchor_row(
        SPEC_BY_NAME["component_run_ids"],
        value=None,
        manifest=manifest,
        ledger_entries=(),
        checkpoint_status="MISSING",
    )
    assert row["status"] == row["value_short"] == "N/A"
