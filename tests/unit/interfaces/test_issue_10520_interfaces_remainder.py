"""Stream B IF: leftover unavailable, CLI, and rehydrate branches."""

from __future__ import annotations

import asyncio
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.error import HTTPError

import click
import pytest
from click.testing import CliRunner

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands import _run_manifest_output as manifest_output
from bioetl.interfaces.cli.commands import checkpoint as checkpoint_mod
from bioetl.interfaces.cli.commands import config_dq as config_dq_mod
from bioetl.interfaces.cli.commands import export_support as export_support_mod
from bioetl.interfaces.cli.commands import lineage as lineage_mod
from bioetl.interfaces.cli.commands import run_manifest as run_manifest_mod
from bioetl.interfaces.cli.commands.checkpoint import _render_audit_run_manifest_lines
from bioetl.interfaces.cli.commands.domains.composite import (
    support as composite_support,
)
from bioetl.interfaces.cli.commands.domains.diagnostics import operations as diag_ops
from bioetl.interfaces.cli.commands.domains.diagnostics import (
    rendering as diag_rendering,
)
from bioetl.interfaces.cli.commands.domains.diagnostics.contract_checks import (
    _load_yaml,
)
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_observability as obs_mod,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _describe_required_probe_failure,
    _probe_required_path,
)
from bioetl.interfaces.cli.commands.domains.quarantine import (
    support as quarantine_support,
)
from bioetl.interfaces.cli.commands.domains.quarantine._run_scope_stats import (
    enrich_run_scoped_stats,
)
from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
    _append_all_silver_filter_groupings,
    build_quarantine_stats_lines,
)
from bioetl.interfaces.cli.commands.domains.run import support as run_support
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    run_async_with_cli_failure_policy,
    run_sync_with_cli_failure_policy,
)
from bioetl.interfaces.http import (
    _health_server_control_plane_evidence_routing as evidence,
)
from bioetl.interfaces.http import _health_server_identity_routing_support as routing
from bioetl.interfaces.http.health_server_http_mixin import HealthServerHTTPMixin

pytestmark = pytest.mark.unit


def test_observability_ready_and_rehydrate_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        observability=SimpleNamespace(
            metrics_enabled=True,
            metrics_server_enabled=True,
            metrics_fail_fast=False,
            metrics_retry_count=0,
            metrics_retry_delay=0.0,
        ),
        metrics_port=9100,
        metrics_addr="127.0.0.1",
    )
    logger = MagicMock()
    monkeypatch.setattr(obs_mod, "get_runtime_settings", lambda: settings)
    monkeypatch.setattr(
        obs_mod, "get_metrics_server_starter", lambda: lambda **_k: True
    )
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
    orig_import = obs_mod.import_module

    def _import_ok(name: str, *args: object, **kwargs: object) -> object:
        if name.endswith("current_metrics_rehydrate"):
            return SimpleNamespace(
                rehydrate_current_pipeline_run_metrics=lambda *_a, **_k: result
            )
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(obs_mod, "import_module", _import_ok)
    monkeypatch.setattr(obs_mod, "create_run_report_store", lambda: object())
    monkeypatch.setattr(
        obs_mod, "_rehydrate_provider_health_gauges", lambda _deps: None
    )
    monkeypatch.setattr(
        "bioetl.composition.health_service_access.get_health_server_dependencies",
        lambda: (_ for _ in ()).throw(RuntimeError("deps boom")),
    )
    obs_mod._rehydrate_current_metrics(logger=logger)
    obs_mod._rehydrate_current_metrics(logger=None)
    monkeypatch.setattr(
        "bioetl.composition.health_service_access.get_health_server_dependencies",
        lambda: SimpleNamespace(metrics=object()),
    )
    obs_mod._start_health_observability(logger)
    logger.info.assert_called()
    obs_mod._start_health_observability(None)
    obs_mod._rehydrate_current_metrics(logger=logger)
    result.error = ""
    obs_mod._rehydrate_current_metrics(logger=logger)
    obs_mod._rehydrate_current_metrics(logger=None)


def test_rendering_unavailable_and_empty_next_steps() -> None:
    assert "unavailable" in diag_rendering._render_run_manifest_lines("x")[0]
    assert "unavailable" in diag_rendering._render_checkpoint_lines(None)[0]
    assert "unavailable" in diag_rendering._render_quarantine_lines([])[0]
    assert "unavailable" in diag_rendering._render_lineage_lines(1)[0]
    assert "unavailable" in diag_rendering._render_traceability_lines("nope")[0]
    assert diag_rendering._render_next_step_lines(None) == ["  - none"]


def test_manifest_output_non_dict_diff_and_differences() -> None:
    assert manifest_output._render_cross_surface_replay_diff(
        {
            "cross_surface_replay_diff": {
                "verdict": "ok",
                "effective_config": "x",
                "checkpoint_anchors": 1,
                "lineage": None,
            }
        }
    )
    text = manifest_output.render_diff_payload(
        {
            "left_manifest_id": "a",
            "right_manifest_id": "b",
            "occurrence_difference_fields": ["f"],
            "differences": "not-a-list",
        }
    )
    assert "differences: 0" in text
    text = manifest_output.render_diff_payload(
        {
            "left_manifest_id": "a",
            "right_manifest_id": "b",
            "differences": ["raw", {"field": "x"}],
        }
    )
    assert "differences: 2" in text


def test_checkpoint_replay_none_workflow_and_json_fallback() -> None:
    lines = _render_audit_run_manifest_lines(
        {"manifest": {"manifest_id": "m"}, "diagnostics": "nope", "identity_graph": 1}
    )
    assert any("manifest_id" in line for line in lines)
    workflow = checkpoint_mod._render_checkpoint_workflow_payload(
        {
            "pipeline_name": "p",
            "audit": {"entries": "nope"},
            "checkpoint": None,
            "run_manifest": None,
        }
    )
    assert "Audit" in workflow
    assert "only" in checkpoint_mod._render_checkpoint_payload({"only": "json"})


def test_composite_policy_error_and_failed_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(composite_support, "push_metrics_to_gateway", lambda **_k: None)

    async def _boom(
        _composite: str,
        _runtime: object,
        _health_server: bool,
        _health_port: int,
    ) -> tuple[bool, str | None]:
        raise BioETLError("domain")

    composite_support.run_composite_with_cli_policy(
        composite="chembl",
        runtime=object(),  # type: ignore[arg-type]
        health_server=False,
        run_async=_boom,
        exception_handler=lambda *_a, **_k: None,
    )

    async def _pending(
        _composite: str,
        _runtime: object,
        _health_server: bool,
        _health_port: int,
    ) -> tuple[bool, str | None]:
        return True, None

    monkeypatch.setattr(
        composite_support.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(RuntimeError("typed")),
    )
    composite_support.run_composite_with_cli_policy(
        composite="chembl",
        runtime=object(),  # type: ignore[arg-type]
        health_server=False,
        run_async=_pending,
        exception_handler=lambda *_a, **_k: None,
    )
    with pytest.raises(SystemExit):
        composite_support.exit_with_composite_result(False, "boom")
    monkeypatch.setattr(
        composite_support, "handle_run_composite_exception", lambda *_a, **_k: None
    )
    composite_support._default_exception_handler(
        BioETLError("domain"), "chembl", "CLI_COMPOSITE_DOMAIN_ERROR"
    )


def test_diagnostics_operations_and_contract_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(click.UsageError, match="exactly one"):
        diag_ops.emit_run_dossier(
            SimpleNamespace(),  # type: ignore[arg-type]
            run_id=None,
            manifest_id=None,
            limit=1,
            output_format="text",
        )
    monkeypatch.setattr(
        diag_ops, "run_async_inspection_command", lambda *_a, **_k: None
    )
    diag_ops.emit_checkpoint_diagnostics(
        SimpleNamespace(
            workflow_service=SimpleNamespace(
                inspect_checkpoint_workflow=lambda **_k: {}
            )
        ),  # type: ignore[arg-type]
        pipeline="p",
        run_id=None,
        audit_limit=1,
        output_format="text",
    )
    monkeypatch.setattr(diag_ops, "_show_quarantine_stats", lambda *_a, **_k: None)
    diag_ops.emit_quarantine_stats(
        SimpleNamespace(run_manifest_service=object()),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        pipeline="p",
        output_json=False,
        error_code=None,
        top=1,
        group_by=None,
        run_id="r1",
    )
    bad = tmp_path / "bad.yaml"
    bad.write_text(": : :", encoding="utf-8")
    with pytest.raises(ValueError, match="Unable to load YAML"):
        _load_yaml(bad)
    empty = tmp_path / "empty.yaml"
    empty.write_text("[]\n", encoding="utf-8")
    assert _load_yaml(empty) == {}


def test_backend_probe_success_and_httperror_body() -> None:
    class _Ok:
        status = 200

        def __enter__(self) -> _Ok:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    assert (
        _describe_required_probe_failure(
            "http://127.0.0.1:8000/health",
            required_probe_paths=("/ready",),
            timeout_seconds=0.1,
            urlopen_fn=lambda *_a, **_k: _Ok(),
        )
        is None
    )

    class _Err(HTTPError):
        def read(self) -> bytes:
            raise OSError("closed")

    def _raise(*_a: object, **_k: object) -> object:
        raise _Err("http://x", 500, "fail", hdrs=None, fp=None)  # type: ignore[arg-type]

    message = _probe_required_path("http://x", timeout_seconds=0.1, urlopen_fn=_raise)
    assert message is not None and "HTTP 500" in message


def test_export_scrub_filenotfound_and_none_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    real_pkg = sys.modules["bioetl.interfaces.cli.commands"]
    module = sys.modules["bioetl.interfaces.cli.commands.export_support"]
    fake_pkg = SimpleNamespace(export_support=module)
    sys.modules["bioetl.interfaces.cli.commands"] = fake_pkg  # type: ignore[assignment]
    try:
        export_support_mod._scrub_parent_package_binding()
        assert not hasattr(fake_pkg, "export_support")
    finally:
        sys.modules["bioetl.interfaces.cli.commands"] = real_pkg

    async def _missing() -> object:
        raise FileNotFoundError("gone")

    with pytest.raises(SystemExit):
        export_support_mod._run_export_async(
            _missing(),
            table="t",
            reason_prefix="CLI_EXPORT_RUN",
            domain_error_title="x",
            unexpected_error_title="y",
            handle_file_not_found=True,
        )

    def _raise_fnf(coro: object, **_k: object) -> object:
        close = getattr(coro, "close", None)
        if callable(close):
            close()
        raise FileNotFoundError("gone")

    monkeypatch.setattr(
        export_support_mod, "run_async_with_cli_failure_policy", _raise_fnf
    )

    async def _ok() -> object:
        return object()

    with pytest.raises(FileNotFoundError):
        export_support_mod._run_export_async(
            _ok(),
            table="t",
            reason_prefix="CLI_EXPORT_RUN",
            domain_error_title="x",
            unexpected_error_title="y",
            handle_file_not_found=False,
        )
    monkeypatch.setattr(export_support_mod, "_run_export_async", lambda *_a, **_k: None)
    export_support_mod._run_export(
        SimpleNamespace(export=lambda *_a, **_k: None),
        "t",
        "silver",
        SimpleNamespace(),
    )


def test_config_dq_yaml_and_validate_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(get_dq_config=lambda _p: {"k": 1})
    monkeypatch.setattr(config_dq_mod, "get_config_service", lambda: service)
    runner = CliRunner()
    result = runner.invoke(config_dq_mod.dq, ["show", "chembl_activity"])
    assert result.exit_code == 0
    service.get_dq_config = lambda _p: (_ for _ in ()).throw(FileNotFoundError("nope"))
    result = runner.invoke(config_dq_mod.dq, ["validate", "chembl_activity"])
    assert result.exit_code != 0


def test_quarantine_rendering_groups_and_stats_helper() -> None:
    lines: list[str] = []
    _append_all_silver_filter_groupings(
        lines,
        silver_filter_stats={"by_reason_code": {"r": 1}, "by_field": 1},
        silver_total=1,
        top=3,
    )
    assert lines
    assert build_quarantine_stats_lines({"total_count": 0}, pipeline="p")


def test_run_scope_resolve_and_replay_mark_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Service:
        def show(self, run_id: str) -> object:
            return SimpleNamespace(
                ledger_entries=(
                    SimpleNamespace(metrics_snapshot={"records_bronze": 8}),
                )
            )

    enriched = enrich_run_scoped_stats(
        {"silver_filter_rejects": {"total_count": 2}},
        run_id="ok",
        run_manifest_service=_Service(),
    )
    assert enriched["silver_filter_rejects"]["bronze_records"] == 8
    calls = {"n": 0}

    def _run_sync(*_a: object, **_k: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            return ["rec"]
        return None

    monkeypatch.setattr(
        quarantine_support._QuarantineCommandContext, "run_sync", _run_sync
    )
    quarantine_support._replay_quarantine(
        SimpleNamespace(),
        pipeline="chembl",
        error_code=None,
        max_age_days=1,
        dry_run=False,
    )
    enrich_run_scoped_stats({}, run_id=None, run_manifest_service=None)
    enrich_run_scoped_stats(
        {"silver_filter_rejects": {"total_count": 1}},
        run_id="r1",
        run_manifest_service=None,
    )


def test_run_support_preview_and_policy_async(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _impl(_pipeline: str) -> object:
        return SimpleNamespace()

    monkeypatch.setattr(run_support, "preview_maintenance_cleanup", _impl)
    assert asyncio.run(run_support.preview_cleanup("chembl_activity")) is not None
    policy = CliBoundaryExecutionPolicy(
        reason_prefix="CLI_X",
        subject_key="target",
        subject_value="t",
        domain_error_title="d",
        unexpected_error_title="u",
        interrupted_message="i",
    )
    from bioetl.interfaces.cli.commands.domains.shared import (
        execution_policy as policy_mod,
    )

    monkeypatch.setattr(policy_mod, "_handle_boundary_failure", lambda *_a, **_k: None)
    with pytest.raises(IndexError):
        run_sync_with_cli_failure_policy(
            lambda: (_ for _ in ()).throw(IndexError("untyped")),
            policy=policy,
        )

    async def _pending() -> str:
        return "ok"

    monkeypatch.setattr(
        policy_mod.asyncio,
        "run",
        lambda _coro: (_ for _ in ()).throw(RuntimeError("typed")),
    )
    assert run_async_with_cli_failure_policy(_pending(), policy=policy) is None


def test_lineage_json_fallback_and_identity_rewrite() -> None:
    assert "unexpected" in lineage_mod._render_text_payload({"unexpected": True})
    lineage_mod._render_text_payload({"fragment": {"id": "f"}})
    lineage_mod._render_text_payload({"dataset_ref": "d"})
    rewritten = {"rows": [{"parameter": "x", "value": "not available"}, "keep"]}
    routing._rewrite_timeout_identity_rows(rewritten, pipeline="p")
    routing._rewrite_timeout_identity_rows({"rows": "nope"}, pipeline="p")
    assert rewritten["rows"][1] == "keep"


def test_evidence_error_payload_and_mixin_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _resolve(*_a: object, **_k: object) -> tuple[None, dict[str, bool]]:
        return None, {"error": True}

    monkeypatch.setattr(evidence, "resolve_evidence_scope", _resolve)

    async def _run() -> dict[str, object]:
        return await evidence._service_payload(
            SimpleNamespace(_control_plane_evidence_service=object()),  # type: ignore[arg-type]
            {},
            endpoint="trust-summary",
        )

    assert asyncio.run(_run()) == {"error": True}

    class _Writer:
        def write(self, _data: bytes) -> None:
            return None

        async def drain(self) -> None:
            return None

    class _Mixin(HealthServerHTTPMixin):
        async def _process_request(self, *_a: object, **_k: object) -> None:
            raise OSError("connection")

        async def _handle_request_error(self, *_a: object, **_k: object) -> None:
            return None

        async def _close_writer(self, _writer: object) -> None:
            return None

    asyncio.run(_Mixin()._handle_connection(object(), _Writer()))  # type: ignore[arg-type]


def test_universe_report_durable_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    report = SimpleNamespace(
        to_dict=lambda: {"ok": True},
        durable_evidence_coverage_claim={"claimed": False},
    )
    monkeypatch.setattr(
        run_manifest_mod,
        "get_historical_replay_universe_service",
        lambda: SimpleNamespace(
            build_universe_closure_report=lambda **_k: report,
        ),
    )
    monkeypatch.setattr(
        run_manifest_mod, "_load_universe_external_records", lambda _p: ()
    )
    monkeypatch.setattr(
        run_manifest_mod, "_has_required_universal_exact_replay_claim", lambda _r: True
    )
    assert run_manifest_mod.universe_report_command.callback is not None
    with pytest.raises(click.ClickException, match="Durable evidence"):
        run_manifest_mod.universe_report_command.callback(
            external_pack_paths=(),
            write_artifact=False,
            require_universal_claim=False,
            require_durable_evidence_coverage=True,
            output_format="json",
        )


def test_debug_breakpoints_and_log_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.cli.commands import debug as debug_mod

    class _BP:
        def __init__(self, value: str) -> None:
            self.value = value

        def __hash__(self) -> int:
            return hash(self.value)

        def __eq__(self, other: object) -> bool:
            return isinstance(other, _BP) and other.value == self.value

    monkeypatch.setattr(debug_mod, "_load_stage_breakpoint", lambda: _BP)
    monkeypatch.setattr(
        debug_mod, "_load_run_options_type", lambda: lambda **_k: SimpleNamespace()
    )
    monkeypatch.setattr(debug_mod, "_resolve_context_registry", lambda *_a, **_k: None)
    monkeypatch.setattr(debug_mod, "_load_debug_abort_error_type", lambda: RuntimeError)

    async def _session(*_a: object, **_k: object) -> SimpleNamespace:
        return SimpleNamespace(
            status=SimpleNamespace(value="ok"),
            records_fetched=0,
            records_silver=0,
            records_quarantined=0,
        )

    monkeypatch.setattr(debug_mod, "_run_debug_session", _session)
    assert debug_mod.debug.callback is not None
    with click.Context(debug_mod.debug):
        debug_mod.debug.callback(
            pipeline="chembl_activity",
            breakpoints="extract",
            limit=1,
            mode="log",
            run_type="incremental",
        )

    class _Svc:
        async def run(self, *_a: object, **_k: object) -> str:
            return "ok"

    monkeypatch.undo()
    monkeypatch.setattr(debug_mod, "get_pipeline_runner_service", lambda **_k: _Svc())
    assert (
        asyncio.run(
            debug_mod._run_debug_session(
                "chembl_activity",
                object(),  # type: ignore[arg-type]
                "log",
                None,
                registry=None,
            )
        )
        == "ok"
    )


def test_lifecycle_metrics_rehydrate_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.interfaces.cli.commands.domains.health import (
        server_integration_lifecycle as life,
    )

    class _Server:
        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    async def _close(**_k: object) -> None:
        return None

    monkeypatch.setattr(life.sys, "pycache_prefix", "already")
    monkeypatch.setattr(
        life._deps, "get_health_server_dependencies", lambda **_k: object()
    )
    monkeypatch.setattr(
        life._deps, "_get_optional_health_server_quarantine_service", lambda **_k: None
    )
    monkeypatch.setattr(life._deps, "build_health_server", lambda **_k: _Server())
    monkeypatch.setattr(life._deps, "close_health_server_resources", _close)
    monkeypatch.setattr(
        life._observability, "_start_health_observability", lambda: None
    )
    monkeypatch.setattr(life._observability, "_rehydrate_current_metrics", lambda: None)
    ticks = {"n": 0}

    async def _sleep(_seconds: float) -> None:
        ticks["n"] += 1
        if ticks["n"] > 30:
            raise KeyboardInterrupt()

    monkeypatch.setattr(life.asyncio, "sleep", _sleep)
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(life._run_health_server("127.0.0.1", 8000, start_metrics=True))


def test_cli_main_dunder_main(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    main_mod = importlib.import_module("bioetl.interfaces.cli.main")
    monkeypatch.setattr("click.core.Group.__call__", lambda *_a, **_k: None)
    runpy.run_path(str(Path(main_mod.__file__)), run_name="__main__")
