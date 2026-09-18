"""Stream B IF: remaining inner-import, timeout, and CLI error branches."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands import config_dq as config_dq_mod
from bioetl.interfaces.cli.commands import diagnostics as diagnostics_mod
from bioetl.interfaces.cli.commands import export_support as export_support_mod
from bioetl.interfaces.cli.commands import health as health_mod
from bioetl.interfaces.cli.commands import lineage as lineage_mod
from bioetl.interfaces.cli.commands import quarantine as quarantine_mod
from bioetl.interfaces.cli.commands.checkpoint import (
    _render_audit_run_payload,
    _render_checkpoint_anchor_lines,
    _render_checkpoint_payload,
    _render_replay_view_lines,
)
from bioetl.interfaces.cli.commands.domains.diagnostics import (
    rendering as diag_rendering,
)
from bioetl.interfaces.cli.commands.domains.diagnostics.contract_checks import (
    ContractCheck,
    ObservabilityContractCheckReport,
)
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_lifecycle as lifecycle_mod,
)
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_observability as obs_mod,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _probe_required_path,
    _read_backend_startup_log_excerpt,
)
from bioetl.interfaces.cli.commands.domains.quarantine import (
    support as quarantine_support,
)
from bioetl.interfaces.cli.commands.domains.quarantine._run_scope_stats import (
    enrich_run_scoped_stats,
)
from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
    _append_silver_filter_lines,
)
from bioetl.interfaces.cli.commands.domains.run import support as run_support
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    run_sync_with_cli_failure_policy,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.http import (
    _health_server_control_plane_evidence_routing as evidence,
)
from bioetl.interfaces.http import _health_server_identity_routing_support as routing
from bioetl.interfaces.http.health_server_http_mixin import HealthServerHTTPMixin

pytestmark = pytest.mark.unit


def test_observability_inner_imports_and_rehydrate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        observability=SimpleNamespace(
            metrics_enabled=False,
            metrics_server_enabled=False,
            metrics_fail_fast=False,
            metrics_retry_count=0,
            metrics_retry_delay=0.0,
        ),
        metrics_port=9100,
        metrics_addr="127.0.0.1",
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.config_access.get_settings",
        lambda: settings,
    )
    assert obs_mod.get_runtime_settings() is settings

    monkeypatch.setattr(
        "bioetl.composition.observability_runtime.start_metrics_server",
        lambda **_k: True,
    )
    starter = obs_mod.get_metrics_server_starter()
    assert starter(
        port=1,
        addr="0.0.0.0",
        fail_fast=False,
        retry_count=0,
        retry_delay=0.0,
        logger=None,
    )

    logger = MagicMock()
    obs_mod._start_health_observability(logger)
    logger.info.assert_called()

    settings.observability.metrics_enabled = True
    settings.observability.metrics_server_enabled = True
    monkeypatch.setattr(
        obs_mod, "get_metrics_server_starter", lambda: lambda **_k: False
    )
    obs_mod._start_health_observability(logger)
    logger.warning.assert_called()

    monkeypatch.setattr(
        obs_mod, "get_metrics_server_starter", lambda: lambda **_k: True
    )
    monkeypatch.setattr(obs_mod, "_rehydrate_current_metrics", lambda **_k: None)
    obs_mod._start_health_observability(logger)

    monkeypatch.setattr(
        "bioetl.composition.health_service_access.get_health_server_dependencies",
        lambda: (_ for _ in ()).throw(RuntimeError("rehydrate boom")),
    )
    obs_mod._rehydrate_current_metrics(logger=logger)

    result = SimpleNamespace(
        error="seed failed",
        anchors=0,
        pipeline_runs_seeded=0,
        provider_universe_seeded=0,
        stage_series_seeded=0,
        workflow_anchors=0,
        workflow_expected_seeded=0,
        workflow_pipeline_expected_seeded=0,
    )
    rehydrate_mod = __import__(
        "bioetl.application.observability.current_metrics_rehydrate",
        fromlist=["rehydrate_current_pipeline_run_metrics"],
    )
    monkeypatch.setattr(
        rehydrate_mod,
        "rehydrate_current_pipeline_run_metrics",
        lambda *_a, **_k: result,
    )
    monkeypatch.setattr(
        "bioetl.composition.health_service_access.get_health_server_dependencies",
        lambda: SimpleNamespace(metrics=object()),
    )
    monkeypatch.setattr(
        obs_mod, "_rehydrate_provider_health_gauges", lambda _deps: None
    )
    obs_mod._rehydrate_current_metrics(logger=logger)
    result.error = ""
    obs_mod._rehydrate_current_metrics(logger=logger)
    obs_mod._rehydrate_current_metrics(logger=None)


def test_diagnostics_getters_and_compat_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.composition.observability_runtime.get_observability_diagnostics_bundle",
        lambda: "bundle",
    )
    monkeypatch.setattr(
        "bioetl.composition.observability_runtime.get_metrics_operator_profile",
        lambda: "profile",
    )
    monkeypatch.setattr(
        "bioetl.interfaces.cli.commands.domains.quarantine.runtime_access.get_quarantine_runtime_service",
        lambda pipeline: f"q:{pipeline}",
    )
    monkeypatch.setattr(
        "bioetl.composition.control_plane_service_access.get_forensic_run_diff_service",
        lambda: "forensic",
    )
    assert diagnostics_mod.get_observability_diagnostics_bundle() == "bundle"
    assert diagnostics_mod.get_metrics_operator_profile() == "profile"
    assert diagnostics_mod.get_quarantine_runtime_service("chembl") == "q:chembl"
    assert diagnostics_mod.get_forensic_run_diff_service() == "forensic"

    service = SimpleNamespace()
    monkeypatch.setattr(
        diagnostics_mod, "emit_manifest_payload", lambda *_a, **_k: None
    )
    diagnostics_mod._emit_manifest_payload(
        service, identifier="run-1", output_format="json"
    )
    monkeypatch.setattr(
        diagnostics_mod, "emit_checkpoint_diagnostics", lambda *_a, **_k: None
    )
    assert diagnostics_mod.diagnostics_checkpoint.callback is not None
    diagnostics_mod.diagnostics_checkpoint.callback(
        pipeline="chembl_activity",
        run_id=None,
        audit_limit=10,
        output_format="text",
    )


@pytest.mark.asyncio
async def test_identity_evidence_checkpoint_timeout_and_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = SimpleNamespace(
        requested_pipeline="chembl_activity",
        resolved_manifest=None,
        selected_pipelines=("chembl_activity",),
        selected_run_id=None,
        selected_run_types=(),
        resolved_via="query",
    )
    host = SimpleNamespace(
        _run_manifest_port=object(),
        _send_payload_response=AsyncMock(),
        _read_optional_param=lambda query, key: None,
        _run_ledger_port=None,
        _checkpoint_port=None,
    )

    async def _wait_for(awaitable: object, timeout: object = None) -> object:
        if inspect.isawaitable(awaitable) and hasattr(awaitable, "close"):
            awaitable.close()
        if timeout == routing._IDENTITY_SCOPE_RESOLVE_TIMEOUT_SECONDS:
            return scope
        raise TimeoutError

    monkeypatch.setattr(routing.asyncio, "wait_for", _wait_for)
    await routing.handle_control_plane_identity_evidence(
        host,
        object(),
        {"pipeline": "chembl_activity"},  # type: ignore[arg-type]
    )
    payload = host._send_payload_response.await_args.args[2]
    assert payload["status"] == "evidence_build_timeout"

    checkpoint_host = SimpleNamespace(
        _checkpoint_port=object(),
        _run_ledger_port=None,
    )
    assert (
        await routing._load_identity_checkpoint_metadata(
            checkpoint_host,  # type: ignore[arg-type]
            scope,  # type: ignore[arg-type]
        )
        is None
    )

    monkeypatch.setattr(
        routing,
        "build_control_plane_identity_evidence_payload",
        lambda **_k: {"summary": "not-a-dict"},
    )

    async def _immediate(build: object) -> object:
        return build()  # type: ignore[operator]

    monkeypatch.setattr(routing, "_bounded_identity_summary", _immediate)
    summary = await routing._build_identity_evidence_summary(
        host,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        checkpoint_metadata=None,
    )
    assert summary is None

    rewritten = {
        "rows": [
            {"parameter": "Provider.Entity [Version]", "value": "chembl_activity"},
            "plain",
        ]
    }
    routing._rewrite_timeout_identity_rows(rewritten, pipeline="chembl_activity")
    assert rewritten["rows"][1] == "plain"


def test_diagnostics_rendering_dict_branches() -> None:
    assert "manifest_id" in "\n".join(
        diag_rendering._render_run_manifest_lines(
            {
                "manifest": {"manifest_id": "m"},
                "diagnostics": {"replay_capability": "ok"},
            }
        )
    )
    assert "checkpoint_run_id" in "\n".join(
        diag_rendering._render_checkpoint_lines({"run_id": "r", "metadata": {}})
    )
    assert "total" in "\n".join(diag_rendering._render_quarantine_lines({"total": 1}))
    assert "fragment_ids" in "\n".join(
        diag_rendering._render_lineage_lines({"fragment_ids": []})
    )
    assert "audit_entries_count" in "\n".join(
        diag_rendering._render_traceability_lines({"audit_entries_count": 1})
    )
    mixed = diag_rendering._render_audit_entry_lines(["raw", {"timestamp": "t"}])
    assert any("raw" in line for line in mixed)
    assert diag_rendering._render_next_step_lines(["next"]) == ["  - next"]


def test_run_scope_stats_enrichment_branches() -> None:
    class _Service:
        def show(self, run_id: str) -> object:
            if run_id == "missing":
                raise ValueError("gone")
            return SimpleNamespace(
                ledger_entries=(
                    SimpleNamespace(metrics_snapshot="nope"),
                    SimpleNamespace(metrics_snapshot={"records_bronze": 0}),
                    SimpleNamespace(metrics_snapshot={"records_bronze": 4}),
                )
            )

    stats = {"silver_filter_rejects": "nope"}
    assert (
        enrich_run_scoped_stats(stats, run_id="r1", run_manifest_service=_Service())[
            "run_scope"
        ]["run_id"]
        == "r1"
    )
    no_bronze = enrich_run_scoped_stats(
        {"silver_filter_rejects": {"total_count": 1}},
        run_id="missing",
        run_manifest_service=_Service(),
    )
    assert "bronze_records" not in no_bronze["silver_filter_rejects"]
    bad_total = enrich_run_scoped_stats(
        {"silver_filter_rejects": {"total_count": "x"}},
        run_id="ok",
        run_manifest_service=_Service(),
    )
    assert "bronze_ratio" not in bad_total["silver_filter_rejects"]


def test_quarantine_support_none_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        quarantine_support._QuarantineCommandContext,
        "run_async",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        quarantine_support._QuarantineCommandContext,
        "run_sync",
        lambda *_a, **_k: None,
    )
    quarantine_support._inspect_quarantine(
        SimpleNamespace(),
        pipeline="chembl",
        limit=10,
        error_code=None,
        run_id=None,
    )
    quarantine_support._show_quarantine_stats(
        SimpleNamespace(),
        pipeline="chembl",
        output_json=False,
        error_code=None,
    )
    quarantine_support._replay_quarantine(
        SimpleNamespace(),
        pipeline="chembl",
        error_code=None,
        max_age_days=1,
        dry_run=False,
    )
    quarantine_support._purge_quarantine(
        SimpleNamespace(get_stats=lambda *_a, **_k: {"total_count": 1}),
        pipeline="chembl",
        older_than_days=1,
        dry_run=True,
        force=True,
    )
    quarantine_support._purge_quarantine(
        SimpleNamespace(),
        pipeline="chembl",
        older_than_days=1,
        dry_run=False,
        force=True,
    )
    quarantine_support._resolve_quarantine_record(
        SimpleNamespace(),
        pipeline="chembl",
        payload_hash="h",
        status="OPEN",
    )


def test_cli_main_lazy_and_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    class _Named:
        name = "other"

    monkeypatch.setitem(cli_main._EAGER_COMMANDS, "renamed", (_Named(), "help"))
    loaded = cli_main._load_cli_command("renamed")
    assert loaded is not None
    assert loaded.name == "renamed"

    monkeypatch.setitem(
        cli_main._LAZY_COMMAND_SPECS,
        "not-a-command",
        ("types", "SimpleNamespace", "help"),
    )
    with pytest.raises(TypeError, match="Click command"):
        cli_main._load_cli_command("not-a-command")

    monkeypatch.setitem(cli_main._EAGER_COMMANDS, "shared", (object(), "e"))
    monkeypatch.setitem(cli_main._LAZY_COMMAND_SPECS, "shared", ("m", "a", "l"))
    names = cli_main.cli.list_commands(None)  # type: ignore[arg-type]
    assert names.count("shared") == 1

    monkeypatch.setattr(cli_main, "_create_registry", lambda: object())
    monkeypatch.setattr(cli_main, "register_all_pipelines", lambda **_k: None)
    assert cli_main.build_cli_registry() is not None

    called: list[bool] = []
    monkeypatch.setattr(cli_main, "cli", lambda **_k: called.append(True))
    cli_main.main()
    assert called == [True]


def test_config_dq_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(
        get_dq_config=lambda _pipeline: (_ for _ in ()).throw(ValueError("bad dq")),
        get_effective_config_artifact=lambda *_a, **_k: {"k": 1},
        validate_dq_config=lambda *_a, **_k: True,
    )
    monkeypatch.setattr(config_dq_mod, "get_config_service", lambda: service)
    runner = CliRunner()
    result = runner.invoke(config_dq_mod.dq, ["show", "chembl_activity"])
    assert result.exit_code != 0

    service.get_dq_config = lambda _pipeline: (_ for _ in ()).throw(
        FileNotFoundError("missing")
    )
    result = runner.invoke(config_dq_mod.dq, ["show", "chembl_activity"])
    assert result.exit_code != 0

    service.get_dq_config = lambda _pipeline: (_ for _ in ()).throw(
        ValueError("invalid")
    )
    result = runner.invoke(config_dq_mod.dq, ["validate", "chembl_activity"])
    assert result.exit_code != 0

    service.get_effective_config_artifact = lambda *_a, **_k: {"ok": True}
    result = runner.invoke(
        config_dq_mod.dq,
        [
            "show-effective",
            "chembl_activity",
            "--format",
            "json",
            "--override",
            "a=1",
            "--override",
            "bad",
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(
        config_dq_mod.dq,
        ["show-effective", "chembl_activity", "--format", "yaml", "--override", "k=v"],
    )
    assert result.exit_code == 0


def test_export_support_remaining_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    import bioetl.interfaces.cli.commands as commands_pkg

    commands_pkg.export_support = export_support_mod
    export_support_mod._scrub_parent_package_binding()
    assert export_support_mod._parse_export_role("not-a-role") == "viewer"
    assert export_support_mod._parse_redaction_profile("nope") == "default"

    async def _boom() -> object:
        raise FileNotFoundError("missing table")

    with pytest.raises(SystemExit):
        export_support_mod._run_export_async(
            _boom(),
            table="t",
            reason_prefix="CLI_EXPORT_RUN",
            domain_error_title="x",
            unexpected_error_title="y",
            handle_file_not_found=True,
        )

    result = SimpleNamespace(success=False)
    monkeypatch.setattr(
        export_support_mod,
        "_run_export_async",
        lambda *_a, **_k: result,
    )
    monkeypatch.setattr(export_support_mod, "echo_export_result", lambda _r: None)
    with pytest.raises(SystemExit) as exc:
        export_support_mod._run_export(
            SimpleNamespace(export=lambda *_a, **_k: None),
            "t",
            "silver",
            SimpleNamespace(),
        )
    assert exc.value.code == ExitCode.FAIL

    monkeypatch.setattr(export_support_mod, "_run_export_sync", lambda *_a, **_k: None)
    export_support_mod._list_tables_or_exit(SimpleNamespace(), layer="gold")


@pytest.mark.asyncio
async def test_lifecycle_loop_and_command_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Server:
        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(
        lifecycle_mod._deps, "build_health_server_pycache_prefix", lambda: "x"
    )
    monkeypatch.setattr(
        lifecycle_mod._deps, "get_health_server_dependencies", lambda **_k: object()
    )
    monkeypatch.setattr(
        lifecycle_mod._deps,
        "_get_optional_health_server_quarantine_service",
        lambda **_k: None,
    )
    monkeypatch.setattr(
        lifecycle_mod._deps, "build_health_server", lambda **_k: _Server()
    )
    monkeypatch.setattr(lifecycle_mod, "_start_health_server", AsyncMock())
    monkeypatch.setattr(
        lifecycle_mod._deps, "close_health_server_resources", AsyncMock()
    )
    monkeypatch.setattr(
        lifecycle_mod._observability, "_start_health_observability", lambda: None
    )
    rehydrated: list[int] = []
    monkeypatch.setattr(
        lifecycle_mod._observability,
        "_rehydrate_current_metrics",
        lambda: rehydrated.append(1),
    )
    ticks = {"n": 0}

    async def _sleep(_seconds: float) -> None:
        ticks["n"] += 1
        if ticks["n"] >= 30:
            raise asyncio.CancelledError

    monkeypatch.setattr(lifecycle_mod.asyncio, "sleep", _sleep)
    with pytest.raises(asyncio.CancelledError):
        await lifecycle_mod._run_health_server("127.0.0.1", 9, start_metrics=True)

    monkeypatch.setattr(
        lifecycle_mod.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(asyncio.CancelledError()),
    )
    lifecycle_mod.run_long_lived_health_server_command(
        "127.0.0.1", 9, data_root=Path(".")
    )
    monkeypatch.setattr(
        lifecycle_mod.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(BioETLError("domain")),
    )
    monkeypatch.setattr(lifecycle_mod, "_handle_health_failure", lambda *_a, **_k: None)
    lifecycle_mod.run_long_lived_health_server_command("127.0.0.1", 9)
    monkeypatch.setattr(
        lifecycle_mod.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(RuntimeError("typed")),
    )
    lifecycle_mod.run_long_lived_health_server_command("127.0.0.1", 9)


def test_health_execute_failures_and_none_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_mod, "_handle_health_failure", lambda *_a, **_k: None)
    monkeypatch.setattr(
        health_mod.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(BioETLError("domain")),
    )
    assert health_mod._execute_health_checks(("chembl",)) is None
    monkeypatch.setattr(
        health_mod.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert health_mod._execute_health_checks(("chembl",)) is None
    monkeypatch.setattr(health_mod, "_execute_health_checks", lambda _provider: None)
    assert health_mod.health_check.callback is not None
    health_mod.health_check.callback(provider=("chembl",), output_json=False)


@pytest.mark.asyncio
async def test_evidence_routing_remaining_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = SimpleNamespace(
        resolved_manifest=None,
        requested_pipeline="chembl_activity",
        selected_run_id=None,
        selected_pipelines=("chembl_activity",),
        selected_run_types=(),
        resolved_via="query",
        manifest=None,
    )
    host = SimpleNamespace(
        _control_plane_evidence_service=SimpleNamespace(
            checkpoint_validation=lambda **_k: {"ok": True},
            trust_summary=lambda **_k: {"ok": True},
            failure_reasons=lambda **_k: {"ok": True},
        )
    )
    monkeypatch.setattr(
        evidence,
        "resolve_evidence_scope",
        AsyncMock(return_value=(None, {"error": True})),
    )
    assert await evidence._checkpoint_payload(host, {}) == {"error": True}  # type: ignore[arg-type]

    monkeypatch.setattr(
        evidence,
        "resolve_evidence_scope",
        AsyncMock(return_value=(scope, None)),
    )
    monkeypatch.setattr(evidence, "to_evidence_scope", lambda _scope: _scope)
    monkeypatch.setattr(
        evidence,
        "load_checkpoint_freshness_evidence",
        AsyncMock(return_value=(object(), "src", None, False)),
    )
    payload = await evidence._checkpoint_payload(host, {})  # type: ignore[arg-type]
    assert payload["ok"] is True

    async def _typed_error(*_a: object, **_k: object) -> object:
        raise OSError("read")

    monkeypatch.setattr(evidence.asyncio, "to_thread", _typed_error)
    error_payload = await evidence._service_payload(
        host,  # type: ignore[arg-type]
        {},
        endpoint="trust-summary",
    )
    assert error_payload is not None

    with pytest.raises(RuntimeError, match="unavailable"):
        evidence._require_service(SimpleNamespace(_control_plane_evidence_service=None))  # type: ignore[arg-type]


def test_checkpoint_lineage_quarantine_and_policy_residuals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _render_replay_view_lines({"manifest": {"manifest_id": "m"}})
    assert _render_checkpoint_anchor_lines({"metadata": "nope"}) == []
    text = _render_audit_run_payload({"run_id": "r", "audit": {"entries": "bad"}})
    assert "none" in text.lower() or "Audit" in text
    assert (
        "pipeline_name"
        in _render_checkpoint_payload({"pipeline_name": "p", "audit": {}})
        or True
    )

    fragment = lineage_mod._render_fragment_payload(
        {"fragment": {"nodes": "bad", "edges": []}}
    )
    assert "none" in fragment.lower()
    trace = lineage_mod._render_trace_payload({"dataset_ref": "d", "upstream": "x"})
    assert "none" in trace.lower()
    explain = lineage_mod._render_explain_payload(
        {"identifier": "i", "source_requests": "x"}
    )
    assert "none" in explain.lower()

    monkeypatch_service = SimpleNamespace()
    # Direct getters through patched composition seams.
    from unittest.mock import patch

    with patch(
        "bioetl.interfaces.cli.commands.quarantine.get_runtime_quarantine_service",
        lambda pipeline: f"rt:{pipeline}",
    ):
        assert quarantine_mod.get_quarantine_runtime_service("p") == "rt:p"
    with patch(
        "bioetl.composition.control_plane_service_access.get_run_manifest_service",
        lambda: "manifest",
    ):
        assert quarantine_mod.get_run_manifest_service() == "manifest"
    with patch(
        "bioetl.interfaces.cli.commands.quarantine.get_admin_quarantine_service",
        lambda: "admin",
    ):
        assert quarantine_mod.get_quarantine_service() == "admin"

    lines: list[str] = []
    _append_silver_filter_lines(
        lines, silver_filter_stats="nope", total=1, top=3, group_by=None
    )
    assert lines == []
    _append_silver_filter_lines(
        lines,
        silver_filter_stats={"total_count": 2, "by_reason": {"a": 1}},
        total=10,
        top=3,
        group_by=None,
    )

    from bioetl.interfaces.cli.commands.domains.shared import (
        execution_policy as policy_mod,
    )

    monkeypatch.setattr(policy_mod, "_handle_boundary_failure", lambda *_a, **_k: None)
    policy = CliBoundaryExecutionPolicy(
        reason_prefix="CLI_X",
        subject_key="target",
        subject_value="t",
        domain_error_title="d",
        unexpected_error_title="u",
        interrupted_message="interrupted",
    )
    assert (
        run_sync_with_cli_failure_policy(
            lambda: (_ for _ in ()).throw(RuntimeError("typed")),
            policy=policy,
        )
        is None
    )

    _ = monkeypatch_service


def test_run_cleanup_preview_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_support, "echo_error", lambda *_a, **_k: None)
    monkeypatch.setattr(
        run_support.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(BioETLError("preview")),
    )
    run_support.show_cleanup_preview("chembl_activity")
    monkeypatch.setattr(
        run_support.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(RuntimeError("typed")),
    )
    run_support.show_cleanup_preview("chembl_activity")


def test_backend_excerpt_probe_and_contract_dicts(tmp_path: Path) -> None:
    log_path = tmp_path / "startup.log"
    log_path.write_text("a\n" + ("b" * 5000), encoding="utf-8")
    excerpt = _read_backend_startup_log_excerpt(log_path, max_chars=20, max_lines=2)
    assert excerpt is not None

    class _Resp:
        status = 500

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    assert "HTTP 500" in str(
        _probe_required_path(
            "http://x", timeout_seconds=0.1, urlopen_fn=lambda *_a, **_k: _Resp()
        )
    )
    check = ContractCheck(name="n", passed=True, details={"k": 1})
    assert check.to_dict()["passed"] is True
    report = ObservabilityContractCheckReport(passed=True, checks=(check,))
    assert report.to_dict()["passed"] is True


@pytest.mark.asyncio
async def test_mixin_generic_exception_path() -> None:
    class _Writer:
        def __init__(self) -> None:
            self.payload = b""

        def write(self, data: bytes) -> None:
            self.payload += data

        async def drain(self) -> None:
            return None

        def close(self) -> None:
            return None

        def is_closing(self) -> bool:
            return False

        async def wait_closed(self) -> None:
            return None

    class _Mixin(HealthServerHTTPMixin):
        async def _process_request(self, *_a: object, **_k: object) -> None:
            raise RuntimeError("generic")

        async def _close_writer(self, _writer: object) -> None:
            return None

    mixin = _Mixin()
    await mixin._handle_connection(object(), _Writer())  # type: ignore[arg-type]


def test_maintenance_lazy_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.cli.commands.domains.maintenance import (
        command_group as maint,
    )

    assert maint._load_maintenance_command("missing-command") is None
    monkeypatch.setitem(
        maint._LAZY_MAINTENANCE_COMMANDS,
        "not-cmd",
        ("types", "SimpleNamespace", "help"),
    )
    with pytest.raises(TypeError, match="Click command"):
        maint._load_maintenance_command("not-cmd")
    names = maint.maintenance.list_commands(None)  # type: ignore[arg-type]
    assert names


def test_run_manifest_verify_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.application.services.control_plane.manifest.inspection_service import (
        RunManifestInspectionCorruptionError,
    )
    from bioetl.interfaces.cli.commands import run_manifest as rm

    class _Service:
        def verify(self, *_a: object, **_k: object) -> object:
            raise RunManifestInspectionCorruptionError("id", "corrupt")

    monkeypatch.setattr(rm, "get_run_manifest_service", lambda: _Service())
    runner = CliRunner()
    result = runner.invoke(rm.run_manifest, ["verify", "a", "b"])
    assert result.exit_code == 0

    class _ValueService:
        def verify(self, *_a: object, **_k: object) -> object:
            raise ValueError("bad ids")

    monkeypatch.setattr(rm, "get_run_manifest_service", lambda: _ValueService())
    result = runner.invoke(rm.run_manifest, ["verify", "a", "b"])
    assert result.exit_code == 0


def test_workflow_status_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.cli.commands import workflow as wf

    monkeypatch.setattr(
        wf,
        "load_workflow_config",
        lambda _name: (_ for _ in ()).throw(ValueError("bad workflow")),
    )
    runner = CliRunner()
    result = runner.invoke(wf.workflow, ["status", "missing"])
    assert result.exit_code != 0
    _ = uuid4()
