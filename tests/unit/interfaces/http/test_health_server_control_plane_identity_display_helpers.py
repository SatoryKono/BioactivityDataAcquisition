# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit coverage for control-plane identity display and severity helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.control_plane.run_ledger import RUN_FAILED_EVENT
from bioetl.domain.control_plane.run_ledger import RunLedgerEntry
from bioetl.domain.types import RunType
from bioetl.interfaces.http import _health_server_identity_support
from bioetl.interfaces.http.control_plane_identity.severity import domain_severity
from bioetl.interfaces.http.control_plane_identity.specs import SPEC_BY_NAME
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite


pytestmark = pytest.mark.unit


def _identity_severity_manifest(*, exact_replay: bool = False) -> RunManifest:
    return RunManifest(
        manifest_id="manifest-severity",
        execution_fingerprint="fingerprint-severity",
        schema_version="1.0",
        created_at=datetime(2026, 5, 12, 8, 21, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_identity"
        ),
        run_type=RunType.REBUILD,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"exact_replay": exact_replay},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )


def test_control_plane_identity_support_formats_contract_replay_and_health_edges() -> (
    None
):
    """Identity table support helpers should render fallback and unknown states."""
    assert (
        _health_server_identity_support._contract_schema({"contract_version": "1.2.3"})
        == "version=1.2.3"
    )
    assert (
        _health_server_identity_support._contract_schema(
            {"contract_schema_hash": "abc123"}
        )
        == "schema=abc123"
    )
    assert (
        _health_server_identity_support._contract_schema(
            {
                "contract_ref": "gold.pubchem",
                "contract_version": "1.0.0",
                "contract_schema_hash": "hash",
            }
        )
        == "gold.pubchem.1.0.0 [hash]"
    )

    assert _health_server_identity_support._replay_summary({}) is None
    assert (
        _health_server_identity_support._replay_summary(
            {
                "exact_replay_eligible": None,
                "replay_capability": "custom-capability",
                "replay_mode": "custom-mode",
            }
        )
        == "Unknown [Custom Capability.Custom Mode]"
    )
    assert (
        _health_server_identity_support._replay_summary(
            {
                "exact_replay_eligible": "yes",
                "replay_capability": "resume_only",
                "replay_mode": "exact_replay",
            }
        )
        == "Yes [Resume only.Exact Replay]"
    )

    assert (
        _health_server_identity_support._checkpoint_anchor_status(
            {"checkpoint_anchor_status": "PARTIAL"},
            {"checkpoint_anchor_status": ""},
        )
        == "PARTIAL"
    )
    assert (
        _health_server_identity_support._identity_health(
            {},
            {"identity_graph_complete": None, "identity_gap_count": "bad"},
        )
        == "Unknown [0 gaps]"
    )
    assert (
        _health_server_identity_support._identity_health(
            {},
            {"identity_graph_complete": True, "identity_gap_count": -1},
        )
        == "Complete [0 gaps]"
    )
    assert (
        _health_server_identity_support._identity_health(
            {
                "identity_graph_complete": "partial",
                "correlation_anchor_gaps": {
                    "missing_bool": True,
                    "missing_list": ["a", "b"],
                    "missing_dict": {"x": 1},
                    "missing_text": "yes",
                },
            },
            None,
        )
        == "Incomplete [5 gaps]"
    )


def test_control_plane_identity_support_payload_and_display_edges() -> None:
    """Small display helpers should preserve deterministic yes/no/unavailable text."""
    manifest = RunManifest(
        manifest_id="manifest-display",
        execution_fingerprint="fingerprint-display",
        schema_version="1.0",
        created_at=datetime(2026, 5, 12, 8, 21, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_identity"
        ),
        run_type=RunType.BACKFILL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"dry_run": "1"},
        runtime_config={"resume": False, "execution_context": ""},
        resolved_config={"use_cached_bronze": "yes", "execution_context": "manual"},
        code_provenance=RunCodeProvenance(),
    )

    assert (
        _health_server_identity_support._execution_summary(
            manifest,
            {"git_commit": " abc123 "},
        )
        == "backfill | manual | git=abc123"
    )
    assert _health_server_identity_support._execution_flags(manifest) == (
        "No | Yes | Yes"
    )
    assert (
        _health_server_identity_support._payload_value(
            manifest,
            "missing",
            "use_cached_bronze",
        )
        == "yes"
    )
    assert _health_server_identity_support._yes_no(True) == "Yes"
    assert _health_server_identity_support._yes_no("false") == "No"
    assert _health_server_identity_support._display_eligible(False) == "No"
    assert _health_server_identity_support._display_eligible("false") == "No"
    assert _health_server_identity_support._display_capability(None) == "Unknown"
    assert _health_server_identity_support._display_replay_mode("backfill") == (
        "Backfill"
    )
    assert _health_server_identity_support._gap_count(["a", "b"]) == 2
    assert (
        _health_server_identity_support._display(
            "",
            unavailable="not available",
        )
        == "not available"
    )
    assert _health_server_identity_support._text(None) is None


@pytest.mark.parametrize(
    ("checkpoint_status", "expected"),
    [
        ("OK", "OK"),
        ("MISMATCH", "FAILING"),
        ("PARTIAL", "DEGRADED"),
        ("UNKNOWN", "DEGRADED"),
    ],
)
def test_control_plane_identity_domain_severity_maps_checkpoint_status(
    checkpoint_status: str, expected: str
) -> None:
    assert (
        domain_severity(
            SPEC_BY_NAME["checkpoint_anchor_status"],
            value=checkpoint_status,
            present=True,
            manifest=None,
            ledger_entries=(),
            checkpoint_status=checkpoint_status,
            applicable=True,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, "OK"),
        ("complete (0 gaps)", "OK"),
        ("missing run_id", "FAILING"),
        ("partial graph", "DEGRADED"),
    ],
)
def test_control_plane_identity_domain_severity_maps_identity_graph_value(
    value: object, expected: str
) -> None:
    assert (
        domain_severity(
            SPEC_BY_NAME["identity_graph_complete"],
            value=value,
            present=True,
            manifest=None,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == expected
    )


def test_control_plane_identity_domain_severity_fails_exact_replay_missing_anchor() -> (
    None
):
    assert (
        domain_severity(
            SPEC_BY_NAME["effective_config_hash"],
            value=None,
            present=False,
            manifest=_identity_severity_manifest(exact_replay=True),
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )


def test_control_plane_identity_domain_severity_fails_terminal_missing_manifest() -> (
    None
):
    run_id = deterministic_run_uuid_from_callsite(
        "test_health_server_control_plane_identity"
    )
    terminal_entry = RunLedgerEntry(
        entry_id="ledger-terminal",
        manifest_id="manifest-severity",
        run_id=run_id,
        event_type=RUN_FAILED_EVENT,
        occurred_at=datetime(2026, 5, 12, 8, 22, tzinfo=UTC),
        status="failed",
    )

    assert (
        domain_severity(
            SPEC_BY_NAME["manifest_id"],
            value=None,
            present=False,
            manifest=_identity_severity_manifest(),
            ledger_entries=(terminal_entry,),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )
