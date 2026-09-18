"""Stream B IF: remaining CLI renderers, policy, and evidence helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.checkpoint import (
    _extract_persistence_profile_details,
    _render_audit_entry_lines,
    _render_checkpoint_workflow_payload,
    _resolve_replay_view,
)
from bioetl.interfaces.cli.commands.domains.diagnostics.rendering import (
    echo_health_results,
)
from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
    _append_error_code_lines,
    _append_group_lines,
    _append_status_lines,
    _coerce_total_count,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    _format_failure_detail,
    _handle_boundary_failure,
    run_sync_with_cli_failure_policy,
)
from bioetl.interfaces.cli.commands.health import (
    _provider_subject,
    get_health_server_dependencies,
    get_health_server_quarantine_service,
    get_quarantine_service,
)
from bioetl.interfaces.cli.main import _load_cli_command
from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
    ForensicEndpointUnavailable,
    _latest_complete_payload,
)

pytestmark = pytest.mark.unit


def test_checkpoint_and_quarantine_renderers() -> None:
    assert _render_audit_entry_lines([]) == ["  - none"]
    assert "records=" in _render_audit_entry_lines(
        [
            {
                "timestamp": "t",
                "layer": "silver",
                "table_name": "t",
                "operation": "write",
                "records_count": 1,
            }
        ]
    )[0]
    assert _render_audit_entry_lines(["raw"])[0] == "  - raw"
    manifest, view = _resolve_replay_view(
        {
            "manifest": {"manifest_id": "m"},
            "diagnostics": {"operator_replay_mode": "live"},
            "identity_graph": {},
        }
    )
    assert manifest is not None
    assert view is not None
    assert _extract_persistence_profile_details({"persistence_profile": "nope"}) == (
        None,
        None,
        None,
        None,
    )
    text = _render_checkpoint_workflow_payload(
        {
            "pipeline_name": "chembl_activity",
            "checkpoint": {"run_id": "r", "metadata": {"a": 1}},
            "run_manifest": {
                "manifest": {"manifest_id": "m"},
                "diagnostics": {"operator_replay_mode": "live"},
            },
            "audit": {"entries": []},
        }
    )
    assert "Checkpoint Workflow" in text
    empty = _render_checkpoint_workflow_payload({"pipeline_name": "p", "checkpoint": "x"})
    assert "checkpoint: none" in empty
    assert _coerce_total_count(True) == 1
    assert _coerce_total_count(1.5) == 1
    assert _coerce_total_count("x") == 0
    lines: list[str] = []
    _append_group_lines(lines, values={}, total=0, title="T", top=3)
    _append_group_lines(lines, values={"a": 2, "b": 1}, total=3, title="T", top=3)
    _append_error_code_lines(lines, by_error={"E": 2}, total=2)
    _append_status_lines(lines, by_status={"ok": 1}, total=1)
    assert any("By Error Code" in item for item in lines)


def test_diagnostics_health_and_cli_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    echo_health_results({"chembl": {"status": "healthy"}}, output_json=True)
    echo_health_results({"chembl": {"status": "unhealthy"}}, output_json=False)
    policy = CliBoundaryExecutionPolicy(
        reason_prefix="CLI_TEST",
        subject_key="pipeline",
        subject_value="chembl_activity",
        domain_error_title="domain",
        unexpected_error_title="unexpected",
        interrupted_message="interrupted",
    )
    detail = _format_failure_detail(
        BioETLError("boom"),
        reason_code="CLI_TEST_DOMAIN_ERROR",
        subject_key="pipeline",
        subject_value="chembl_activity",
    )
    assert detail
    monkeypatch.setattr(
        "bioetl.interfaces.cli.commands.domains.shared.execution_policy.handle_cli_failure",
        lambda *_a, **_k: None,
    )
    _handle_boundary_failure(BioETLError("x"), policy=policy, reason_suffix="DOMAIN_ERROR")
    assert (
        run_sync_with_cli_failure_policy(
            lambda: (_ for _ in ()).throw(BioETLError("x")),
            policy=policy,
        )
        is None
    )
    assert (
        run_sync_with_cli_failure_policy(
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            policy=policy,
        )
        is None
    )
    assert (
        run_sync_with_cli_failure_policy(
            lambda: (_ for _ in ()).throw(ValueError("typed")),
            policy=policy,
        )
        is None
    )


def test_health_getters_and_main_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _provider_subject(()) == "all"
    assert _provider_subject(("chembl", "pubchem")) == "chembl,pubchem"
    monkeypatch.setattr(
        "bioetl.composition.health_service_access.get_quarantine_service",
        lambda: "q",
    )
    monkeypatch.setattr(
        "bioetl.composition.health_service_access.get_health_server_dependencies",
        lambda: "deps",
    )
    monkeypatch.setattr(
        "bioetl.interfaces.cli.commands.domains.health.server_integration.get_health_server_quarantine_service",
        lambda: "hq",
    )
    assert get_quarantine_service() == "q"
    assert get_health_server_dependencies() == "deps"
    assert get_health_server_quarantine_service() == "hq"
    cmd = _load_cli_command("dq")
    assert cmd is not None
    assert _load_cli_command("definitely-missing") is None
    import importlib

    cli_main = importlib.import_module("bioetl.interfaces.cli.main")
    monkeypatch.setattr(cli_main, "_register_all_pipelines", lambda **_k: None)
    cli_main.register_all_pipelines(registry=object())


@pytest.mark.asyncio
async def test_latest_complete_scope_errors() -> None:
    host = SimpleNamespace(
        _read_required_param=lambda query, key: "ALL",
        _read_scope_csv_param=lambda query, key: ("incremental",),
        _is_all_scope_token=lambda value: value == "ALL",
        _run_manifest_port=object(),
        _workflow_manifest_port=None,
    )
    with pytest.raises(ValueError, match="latest-complete-run"):
        await _latest_complete_payload(host, {})  # type: ignore[arg-type]

    host._read_required_param = lambda query, key: "chembl_activity"
    host._run_manifest_port = None
    with pytest.raises(ForensicEndpointUnavailable):
        await _latest_complete_payload(host, {})  # type: ignore[arg-type]


def test_composite_metrics_and_run_support_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.cli.commands.domains.composite import support as composite_support
    from bioetl.interfaces.cli.commands.domains.run import support as run_support
    from bioetl.interfaces.cli.commands.run_manifest_output_support import (
        append_section,
        render_ledger_section,
    )

    monkeypatch.setattr(
        "bioetl.composition.observability_runtime.push_metrics_to_gateway",
        lambda **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    assert composite_support.push_metrics_to_gateway(pipeline_name="chembl_activity") is False
    assert run_support._resolve_populated_default_registry() is None
    assert run_support.resolve_context_registry(None) is None

    lines: list[str] = []
    append_section(lines, "Title", (("a", None), ("b", [])), json_renderer=lambda _v: ["x"])
    assert lines == []
    append_section(lines, "Title", (("a", "v"),), json_renderer=lambda _v: ["x"])
    assert "Title" in lines
    ledger = render_ledger_section(["raw", {"occurred_at": "t", "event_type": "e", "stage": "s", "status": "ok"}])
    assert any("stage=s" in item for item in ledger)


@pytest.mark.asyncio
async def test_health_mixin_invalid_status_phrases() -> None:
    from bioetl.interfaces.http.health_server_http_mixin import HealthServerHTTPMixin

    class _Writer:
        def __init__(self) -> None:
            self.payload = b""

        def write(self, data: bytes) -> None:
            self.payload += data

        async def drain(self) -> None:
            return None

    mixin = HealthServerHTTPMixin()
    writer = _Writer()
    await mixin._send_text_response(writer, 999, "hello")  # type: ignore[arg-type]
    assert b"999" in writer.payload
    writer.payload = b""
    await mixin._send_response(writer, 999, "err")  # type: ignore[arg-type]
    assert b"999" in writer.payload
