"""Stream B IF: CLI command error paths, formatters, identity routing helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionCorruptionError,
)
from bioetl.application.services.export_lineage.export_models import (
    ColumnInfo,
    ExportResult,
    TablePreview,
)
from bioetl.interfaces.cli.commands._run_manifest_output import (
    _render_cross_surface_replay_diff,
    render_diff_payload,
    render_text_payload,
)
from bioetl.interfaces.cli.commands.lineage import (
    _render_text_payload,
    _resolve_explain_identifier,
)
from bioetl.interfaces.cli.formatters import (
    echo_export_preview,
    echo_export_result,
    echo_quarantine_record,
)
from bioetl.interfaces.cli.main import cli
from bioetl.interfaces.http._health_server_identity_routing_support import (
    _require_run_manifest_port,
    _timeout_identity_payload,
)

pytestmark = pytest.mark.unit


def test_run_manifest_command_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import bioetl.interfaces.cli.commands.run_manifest as run_manifest_cmd

    class _Svc:
        def show(self, identifier: str) -> object:
            raise RunManifestInspectionCorruptionError(identifier, "corrupt")

        def diff(self, left: str, right: str) -> object:
            raise ValueError("diff missing")

        def verify(self, left: str, right: str) -> object:
            raise RunManifestInspectionCorruptionError(left, "corrupt")

    monkeypatch.setattr(run_manifest_cmd, "get_run_manifest_service", lambda: _Svc())
    runner = CliRunner()
    score = runner.invoke(cli, ["run-manifest", "score", "m1"])
    assert score.exit_code == 0

    class _ValueShow:
        def show(self, identifier: str) -> object:
            raise ValueError("not found")

    monkeypatch.setattr(
        run_manifest_cmd, "get_run_manifest_service", lambda: _ValueShow()
    )
    runner.invoke(cli, ["run-manifest", "score", "m1"])
    runner.invoke(cli, ["run-manifest", "diff", "a", "b"])

    class _CorruptDiff:
        def diff(self, left: str, right: str) -> object:
            raise RunManifestInspectionCorruptionError(left, "corrupt")

        def verify(self, left: str, right: str) -> object:
            raise ValueError("verify missing")

        def show(self, identifier: str) -> object:
            raise ValueError("not found")

    monkeypatch.setattr(
        run_manifest_cmd, "get_run_manifest_service", lambda: _CorruptDiff()
    )
    runner.invoke(cli, ["run-manifest", "diff", "a", "b"])
    runner.invoke(cli, ["run-manifest", "verify", "a", "b"])
    runner.invoke(cli, ["run-manifest", "replay-bundle", "m1"])

    class _Forensic:
        def compare(self, left: str, right: str) -> object:
            raise RunManifestInspectionCorruptionError(left, "corrupt")

    monkeypatch.setattr(
        run_manifest_cmd, "get_forensic_run_diff_service", lambda: _Forensic()
    )
    runner.invoke(cli, ["run-manifest", "forensic-diff", "a", "b"])

    class _ForensicValue:
        def compare(self, left: str, right: str) -> object:
            raise ValueError("forensic missing")

    monkeypatch.setattr(
        run_manifest_cmd, "get_forensic_run_diff_service", lambda: _ForensicValue()
    )
    runner.invoke(cli, ["run-manifest", "forensic-diff", "a", "b"])


def test_run_manifest_output_and_lineage_text_helpers() -> None:
    assert _render_cross_surface_replay_diff({}) == []
    rendered = _render_cross_surface_replay_diff(
        {
            "cross_surface_replay_diff": {
                "verdict": "ok",
                "effective_config": "nope",
                "checkpoint_anchors": {
                    "compatible": False,
                    "mismatched_fields": ["a"],
                },
                "lineage": "nope",
            }
        }
    )
    assert any("mismatched_fields" in line for line in rendered)
    diff_text = render_diff_payload(
        {
            "left_manifest_id": "a",
            "right_manifest_id": "b",
            "differences": [
                "raw",
                {"field": "x", "left": 1, "right": {"nested": True}},
            ],
        }
    )
    assert "differences" in diff_text
    fallback = render_text_payload({"no": "match"})
    assert "{" in fallback
    score_text = render_text_payload({"reproducibility_audit_score": {}})
    assert "score" in score_text.lower() or "Reproducibility" in score_text
    assert _render_text_payload({"identifier": "r"}).startswith("Lineage Run")
    assert _resolve_explain_identifier(run_id="r1", manifest_id=None) == "r1"
    assert _resolve_explain_identifier(run_id=None, manifest_id="m1") == "m1"
    assert _resolve_explain_identifier(run_id="r1", manifest_id="m1") is None
    assert _resolve_explain_identifier(run_id=None, manifest_id=None) is None


def test_formatters_optional_export_and_quarantine() -> None:
    echo_quarantine_record(
        {
            "error_code": "E",
            "payload_hash": "abc123def4567890ffff",
            "dq_status": "FAIL",
            "ingestion_ts": "2026-01-01T00:00:00Z",
            "payload": {"k": 1},
            "error_details": {"message": "boom", "field": "x"},
        }
    )
    columns = tuple(
        ColumnInfo(name=f"c{i}", type="str", nullable=True) for i in range(7)
    )
    preview = TablePreview(
        table_name="t",
        layer="silver",
        row_count=3,
        columns=columns,
        sample_rows=({"c0": "x" * 40, "c1": "y"},),
    )
    echo_export_preview(preview)
    echo_export_result(
        ExportResult(
            table_name="t",
            layer="silver",
            format="csv",
            output_path=Path("out.csv"),
            row_count=1,
            manifest_paths=(Path("m1"), Path("m2")),
            audit_ref="audit",
            checksum_manifest_path=Path("sum.json"),
            expires_at="soon",
            redaction_profile="default",
            redacted_columns=("secret",),
        )
    )


def test_identity_routing_timeout_and_port_guard() -> None:
    payload = _timeout_identity_payload(
        {"pipeline": "chembl_activity", "run_type": "incremental"}
    )
    assert payload.get("rows") is not None or payload.get("display_rows") is not None
    host = SimpleNamespace(_run_manifest_port=None)
    with pytest.raises(RuntimeError, match="run_manifest_port"):
        _require_run_manifest_port(host)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_identity_handlers_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.http import (
        _health_server_identity_routing_support as routing,
    )

    host = SimpleNamespace(
        _run_manifest_port=object(),
        _send_payload_response=AsyncMock(),
        _read_optional_param=lambda query, key: None,
        _run_ledger_port=None,
        _checkpoint_port=None,
    )
    writer = object()

    async def _timeout(*_a: object, **_k: object) -> object:
        raise TimeoutError

    monkeypatch.setattr(routing.asyncio, "wait_for", _timeout)
    await routing.handle_control_plane_identity_table(
        host,
        writer,
        {"pipeline": "p"},  # type: ignore[arg-type]
    )
    host._send_payload_response.assert_called()
    host._send_payload_response.reset_mock()
    await routing.handle_control_plane_identity_evidence(
        host,
        writer,
        {"pipeline": "p"},  # type: ignore[arg-type]
    )
    host._send_payload_response.assert_called()

    none_host = SimpleNamespace(_checkpoint_port=None, _run_ledger_port=None)
    assert (
        await routing._load_identity_checkpoint_metadata(
            none_host,  # type: ignore[arg-type]
            SimpleNamespace(resolved_manifest=None, requested_pipeline="p"),
        )
        is None
    )
