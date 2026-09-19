"""Behavior tests closing #10518 application-layer residuals (svc1 batch, part A).

Covers: observability_backend_startup, run_reports.query,
run_reports.workflow_observations, run_reports.source_identity,
workflow.workflow_runner_reports, effective_config.runtime_overrides,
control_plane.forensic_diff_service.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.services.control_plane.effective_config.runtime_overrides import (  # noqa: E402
    apply_deep_update,
    apply_runtime_overrides,
    build_effective_execution_config,
    build_execution_environment_snapshot,
    build_runtime_override_snapshot,
    coerce_runtime_override_layer,
    normalize_runtime_overrides_for_semantic_identity,
    validate_runtime_environment_provenance,
)
from bioetl.application.services.control_plane.forensic import (  # noqa: E402
    ForensicRunDiffResult,
    ForensicRunDiffService,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (  # noqa: E402
    RunManifestDiffResult,
)
from bioetl.application.services.control_plane.manifest.inspection_result_model import (  # noqa: E402
    RunManifestInspectionResult,
)
from bioetl.application.services.ops.observability_backend_startup import (  # noqa: E402
    _reuse_observability_backend_if_ready,
    _start_observability_backend_detached,
    ensure_observability_backend_started_impl,
)
from bioetl.application.services.run_reports import query as _query  # noqa: E402
from bioetl.application.services.run_reports import source_identity as _sid  # noqa: E402
from bioetl.application.services.run_reports.snapshots import (  # noqa: E402
    publish_snapshot,
)
from bioetl.application.services.run_reports.workflow_observations import (  # noqa: E402
    _child_path,
    _verified_child,
    finalize_workflow_children,
)
from bioetl.application.services.workflow.workflow_runner_reports import (  # noqa: E402
    _execution_rows_from_result,
    _load_child_report_slice,
    _pipeline_name_for_step,
    _plan_steps_from_config,
    _require_workflow_result,
    attach_workflow_run_report,
)
from bioetl.domain.control_plane import RunManifest  # noqa: E402
from bioetl.domain.run_reports.models import (  # noqa: E402
    WorkflowExecutionRow,
    WorkflowRunReport,
)


# ---------------------------------------------------------------------------
# observability_backend_startup
# ---------------------------------------------------------------------------


def _result_factory(**kwargs):
    return dict(kwargs)


def _reuse_kwargs(**overrides):
    kwargs = {
        "health_url": "http://127.0.0.1:9/health",
        "port": 9,
        "required_probe_paths": ("/a",),
        "probe_fn": lambda url: True,
        "required_probe_fn": lambda url, **kw: True,
        "required_probe_timeout_seconds": 1.0,
        "drop_stale_backend_fn": lambda port: True,
        "listener_pid_fn": lambda port: None,
        "info_printer": MagicMock(),
        "warning_printer": MagicMock(),
        "result_factory": _result_factory,
    }
    kwargs.update(overrides)
    return kwargs


class TestReuseBackendIfReady:
    def test_no_listener_returns_none(self):
        assert (
            _reuse_observability_backend_if_ready(
                **_reuse_kwargs(probe_fn=lambda url: False)
            )
            is None
        )

    def test_stale_listener_dropped_returns_none(self):
        warning = MagicMock()
        result = _reuse_observability_backend_if_ready(
            **_reuse_kwargs(
                probe_fn=lambda url: False,
                listener_pid_fn=lambda port: 4242,
                drop_stale_backend_fn=lambda port: True,
                warning_printer=warning,
            )
        )
        assert result is None
        warning.assert_called_once()

    def test_stale_listener_not_droppable_reports_failed(self):
        result = _reuse_observability_backend_if_ready(
            **_reuse_kwargs(
                probe_fn=lambda url: False,
                listener_pid_fn=lambda port: 4242,
                drop_stale_backend_fn=lambda port: False,
            )
        )
        assert result["status"] == "failed"
        assert "4242" in result["message"]

    def test_ready_backend_is_reused(self):
        info = MagicMock()
        result = _reuse_observability_backend_if_ready(
            **_reuse_kwargs(info_printer=info)
        )
        assert result["status"] == "reused"
        info.assert_called_once()

    def test_missing_capabilities_restarts(self):
        warning = MagicMock()
        result = _reuse_observability_backend_if_ready(
            **_reuse_kwargs(
                required_probe_fn=lambda url, **kw: False,
                warning_printer=warning,
            )
        )
        assert result is None
        warning.assert_called_once()

    def test_missing_capabilities_unrestartable_reports_failed(self):
        result = _reuse_observability_backend_if_ready(
            **_reuse_kwargs(
                required_probe_fn=lambda url, **kw: False,
                drop_stale_backend_fn=lambda port: False,
            )
        )
        assert result["status"] == "failed"
        assert "9" in result["message"]


def _detached_hooks(**overrides):
    hooks = {
        "probe_fn": lambda url: True,
        "required_probe_fn": lambda url, **kw: True,
        "start_fn": MagicMock(return_value=SimpleNamespace(pid=11, args=("py", "app"))),
        "wait_fn": lambda url, **kw: True,
        "wait_required_paths_fn": lambda url, **kw: True,
        "info_printer": MagicMock(),
        "warning_printer": MagicMock(),
        "build_startup_failure_detail_fn": lambda *a, **k: "detail",
        "describe_required_probe_failure_fn": lambda *a, **k: "capability-detail",
        "append_backend_startup_diagnostic_fn": MagicMock(),
        "python_executable_to_tuple_fn": lambda args: tuple(args),
    }
    hooks.update(overrides)
    return hooks


def _detached_kwargs(**overrides):
    kwargs = {
        "health_url": "http://127.0.0.1:9/health",
        "startup_log_path": Path("/tmp/startup.log"),
        "port": 9,
        "bind_host": "0.0.0.0",
        "timing": (5.0, 1.0, 0.1),
        "required_probe_paths": ("/a",),
        "hooks": _detached_hooks(),
        "result_factory": _result_factory,
    }
    kwargs.update(overrides)
    return kwargs


class TestStartBackendDetached:
    def test_start_os_error_reports_failed(self):
        warning = MagicMock()
        hooks = _detached_hooks(
            start_fn=MagicMock(side_effect=OSError("bind denied")),
            warning_printer=warning,
        )
        result = _start_observability_backend_detached(**_detached_kwargs(hooks=hooks))
        assert result["status"] == "failed"
        assert "bind denied" in result["message"]
        warning.assert_called_once()

    def test_ready_backend_reports_started(self):
        info = MagicMock()
        hooks = _detached_hooks(info_printer=info)
        result = _start_observability_backend_detached(**_detached_kwargs(hooks=hooks))
        assert result["status"] == "started"
        assert result["pid"] == 11
        assert result["command"] == ("py", "app")
        info.assert_called_once()

    def test_process_without_args_uses_empty_command(self):
        hooks = _detached_hooks(
            start_fn=MagicMock(return_value=SimpleNamespace(pid=7)),
        )
        result = _start_observability_backend_detached(**_detached_kwargs(hooks=hooks))
        assert result["status"] == "started"
        assert result["command"] == ()

    def test_capability_failure_reports_failed(self):
        warning = MagicMock()
        appended = MagicMock()
        hooks = _detached_hooks(
            wait_required_paths_fn=lambda url, **kw: False,
            warning_printer=warning,
            append_backend_startup_diagnostic_fn=appended,
        )
        result = _start_observability_backend_detached(**_detached_kwargs(hooks=hooks))
        assert result["status"] == "failed"
        assert "capability-detail" in result["message"]
        warning.assert_called_once()
        appended.assert_called_once()

    def test_not_ready_reports_failed(self):
        hooks = _detached_hooks(wait_fn=lambda url, **kw: False)
        result = _start_observability_backend_detached(**_detached_kwargs(hooks=hooks))
        assert result["status"] == "failed"


def _startup_kwargs(**overrides):
    kwargs = {
        "enabled": True,
        "health_url": "http://127.0.0.1:9/health",
        "port": 9,
        "required_probe_paths": ("/a",),
        "required_probe_timeout_seconds": 1.0,
        "startup_log_path": Path("/tmp/startup.log"),
        "bind_host": "0.0.0.0",
        "ready_timeout_seconds": 5.0,
        "poll_seconds": 0.1,
    }
    kwargs.update(overrides)
    return kwargs


def _runtime_hooks(**overrides):
    hooks = {
        "probe_fn": lambda url: True,
        "required_probe_fn": lambda url, **kw: True,
        "drop_stale_backend_fn": lambda port: True,
        "listener_pid_fn": lambda port: None,
        "info_printer": MagicMock(),
        "warning_printer": MagicMock(),
        "start_fn": MagicMock(side_effect=OSError("nope")),
        "wait_fn": lambda url, **kw: True,
        "wait_required_paths_fn": lambda url, **kw: True,
        "build_startup_failure_detail_fn": lambda *a, **k: "detail",
        "describe_required_probe_failure_fn": lambda *a, **k: "",
        "append_backend_startup_diagnostic_fn": MagicMock(),
        "python_executable_to_tuple_fn": lambda args: (),
    }
    hooks.update(overrides)
    return hooks


class TestEnsureBackendStarted:
    def test_disabled_reports_disabled(self):
        result = ensure_observability_backend_started_impl(
            startup_kwargs=_startup_kwargs(enabled=False),
            runtime_hooks=_runtime_hooks(),
            failure_handlers={},
            result_factory=_result_factory,
        )
        assert result["status"] == "disabled"

    def test_reuses_ready_backend(self):
        result = ensure_observability_backend_started_impl(
            startup_kwargs=_startup_kwargs(),
            runtime_hooks=_runtime_hooks(),
            failure_handlers={},
            result_factory=_result_factory,
        )
        assert result["status"] == "reused"

    def test_falls_back_to_detached_start(self):
        result = ensure_observability_backend_started_impl(
            startup_kwargs=_startup_kwargs(),
            runtime_hooks=_runtime_hooks(probe_fn=lambda url: False),
            failure_handlers={},
            result_factory=_result_factory,
        )
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# run_reports.query (filesystem-backed fake store)
# ---------------------------------------------------------------------------


class _FsStore:
    """Minimal RunReportStorePort over a tmp directory."""

    def mkdir(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    def write_text(self, path: str, content: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def is_file(self, path: str) -> bool:
        return Path(path).is_file()

    def is_dir(self, path: str) -> bool:
        return Path(path).is_dir()

    def iterdir(self, path: str) -> list[str]:
        return [str(item) for item in Path(path).iterdir()]

    def mtime(self, path: str) -> float:
        return Path(path).stat().st_mtime

    def remove_tree(self, path: str, *, root: str) -> None:
        shutil.rmtree(path)


def _write_pipeline_report(
    root: Path,
    store: _FsStore,
    owner: str,
    run_id: str,
    *,
    mtime: float,
    identity: dict | None = None,
) -> Path:
    report = {
        "identity": identity
        if identity is not None
        else {"status": "success", "run_id": run_id},
        "funnel": [],
    }
    path = root / "pipeline" / owner / run_id / "pipeline-run-report.json"
    store.write_text(str(path), json.dumps(report))
    os.utime(str(path), (mtime, mtime))
    return path


class TestLoadLatestPointer:
    def test_missing_pointer_returns_none(self, tmp_path):
        store = _FsStore()
        assert (
            _query.load_latest_pointer(
                kind="pipeline", owner="pipe1", root=tmp_path, store=store
            )
            is None
        )

    def test_corrupt_pointer_returns_none(self, tmp_path):
        store = _FsStore()
        pointer = tmp_path / "pipeline" / "pipe1" / "_latest.json"
        store.write_text(str(pointer), "{not json")
        assert (
            _query.load_latest_pointer(
                kind="pipeline", owner="pipe1", root=tmp_path, store=store
            )
            is None
        )

    def test_non_dict_pointer_returns_none(self, tmp_path):
        store = _FsStore()
        pointer = tmp_path / "pipeline" / "pipe1" / "_latest.json"
        store.write_text(str(pointer), "[1, 2]")
        assert (
            _query.load_latest_pointer(
                kind="pipeline", owner="pipe1", root=tmp_path, store=store
            )
            is None
        )

    def test_valid_pointer_returns_payload(self, tmp_path):
        store = _FsStore()
        report_path = _write_pipeline_report(
            tmp_path, store, "pipe1", "run1", mtime=1_700_000_000.0
        )
        pointer = tmp_path / "pipeline" / "pipe1" / "_latest.json"
        store.write_text(str(pointer), json.dumps({"json_path": str(report_path)}))
        payload = _query.load_latest_pointer(
            kind="pipeline", owner="pipe1", root=tmp_path, store=store
        )
        assert payload == {"json_path": str(report_path)}


class TestLoadReports:
    def test_pipeline_latest_without_pointer_returns_none(self, tmp_path):
        store = _FsStore()
        assert (
            _query.load_pipeline_report(
                pipeline_name="pipe1", latest=True, root=tmp_path, store=store
            )
            is None
        )

    def test_pipeline_latest_resolves_pointer(self, tmp_path):
        store = _FsStore()
        report_path = _write_pipeline_report(
            tmp_path, store, "pipe1", "run1", mtime=1_700_000_000.0
        )
        pointer = tmp_path / "pipeline" / "pipe1" / "_latest.json"
        store.write_text(str(pointer), json.dumps({"json_path": str(report_path)}))
        payload = _query.load_pipeline_report(
            pipeline_name="pipe1", latest=True, root=tmp_path, store=store
        )
        assert payload["identity"]["run_id"] == "run1"

    def test_pointer_with_empty_json_path_returns_none(self, tmp_path):
        store = _FsStore()
        pointer = tmp_path / "pipeline" / "pipe1" / "_latest.json"
        store.write_text(str(pointer), json.dumps({"json_path": ""}))
        assert (
            _query.load_pipeline_report(
                pipeline_name="pipe1", latest=True, root=tmp_path, store=store
            )
            is None
        )

    def test_pipeline_direct_hit_and_miss(self, tmp_path):
        store = _FsStore()
        _write_pipeline_report(tmp_path, store, "pipe1", "run1", mtime=1_700_000_000.0)
        payload = _query.load_pipeline_report(
            pipeline_name="pipe1", run_id="run1", root=tmp_path, store=store
        )
        assert payload["identity"]["status"] == "success"
        assert (
            _query.load_pipeline_report(
                pipeline_name="pipe1", run_id="nope", root=tmp_path, store=store
            )
            is None
        )

    def test_direct_corrupt_and_non_dict_return_none(self, tmp_path):
        store = _FsStore()
        bad = tmp_path / "pipeline" / "pipe1" / "badrun" / "pipeline-run-report.json"
        store.write_text(str(bad), "{oops")
        assert (
            _query.load_pipeline_report(
                pipeline_name="pipe1", run_id="badrun", root=tmp_path, store=store
            )
            is None
        )
        store.write_text(str(bad), "[1]")
        assert (
            _query.load_pipeline_report(
                pipeline_name="pipe1", run_id="badrun", root=tmp_path, store=store
            )
            is None
        )

    def test_workflow_direct_and_latest(self, tmp_path):
        store = _FsStore()
        payload_path = (
            tmp_path / "workflow" / "wf1" / "run9" / "workflow-run-report.json"
        )
        store.write_text(
            str(payload_path), json.dumps({"identity": {"run_id": "run9"}})
        )
        payload = _query.load_workflow_report(
            workflow_name="wf1", workflow_run_id="run9", root=tmp_path, store=store
        )
        assert payload["identity"]["run_id"] == "run9"
        assert (
            _query.load_workflow_report(
                workflow_name="wf1", latest=True, root=tmp_path, store=store
            )
            is None
        )


class TestListReports:
    def test_missing_kind_dir_returns_empty(self, tmp_path):
        assert (
            _query.list_pipeline_reports(
                pipeline_name=None, root=tmp_path, store=_FsStore()
            )
            == []
        )

    def test_newest_first_with_limit(self, tmp_path):
        store = _FsStore()
        _write_pipeline_report(tmp_path, store, "pipe1", "run1", mtime=1_700_000_100.0)
        _write_pipeline_report(tmp_path, store, "pipe1", "run2", mtime=1_700_000_200.0)
        _write_pipeline_report(tmp_path, store, "pipe2", "run3", mtime=1_700_000_300.0)
        entries = _query.list_pipeline_reports(
            pipeline_name=None, root=tmp_path, store=store
        )
        assert [entry.run_id for entry in entries] == ["run3", "run2", "run1"]
        limited = _query.list_pipeline_reports(
            pipeline_name=None, limit=2, root=tmp_path, store=store
        )
        assert [entry.run_id for entry in limited] == ["run3", "run2"]
        assert (
            _query.list_pipeline_reports(
                pipeline_name=None, limit=0, root=tmp_path, store=store
            )
            == []
        )
        everything = _query.list_pipeline_reports(
            pipeline_name=None, limit=None, root=tmp_path, store=store
        )
        assert len(everything) == 3

    def test_explicit_missing_owner_returns_empty(self, tmp_path):
        store = _FsStore()
        (tmp_path / "pipeline").mkdir(parents=True)
        assert (
            _query.list_pipeline_reports(
                pipeline_name="ghost", root=tmp_path, store=store
            )
            == []
        )

    def test_owner_filter_and_workflow_kind(self, tmp_path):
        store = _FsStore()
        _write_pipeline_report(tmp_path, store, "pipe1", "run1", mtime=1_700_000_100.0)
        entries = _query.list_pipeline_reports(
            pipeline_name="pipe1", root=tmp_path, store=store
        )
        assert [entry.run_id for entry in entries] == ["run1"]
        assert (
            _query.list_workflow_reports(workflow_name=None, root=tmp_path, store=store)
            == []
        )

    def test_skips_hidden_and_incomplete_candidates(self, tmp_path):
        store = _FsStore()
        _write_pipeline_report(tmp_path, store, "pipe1", "run1", mtime=1_700_000_100.0)
        hidden = (
            tmp_path / "pipeline" / "pipe1" / ".hidden" / "pipeline-run-report.json"
        )
        store.write_text(str(hidden), "{}")
        empty_dir = tmp_path / "pipeline" / "pipe1" / "emptyrun"
        empty_dir.mkdir(parents=True)
        stray = tmp_path / "pipeline" / "stray-file"
        stray.write_text("x", encoding="utf-8")
        entries = _query.list_pipeline_reports(
            pipeline_name="pipe1", root=tmp_path, store=store
        )
        assert [entry.run_id for entry in entries] == ["run1"]

    def test_mtime_error_candidates_are_skipped(self, tmp_path):
        class _FlakyMtime(_FsStore):
            def mtime(self, path: str) -> float:
                if path.endswith("run-bad" + os.sep + "pipeline-run-report.json"):
                    raise OSError("stat failed")
                return super().mtime(path)

        store = _FlakyMtime()
        _write_pipeline_report(tmp_path, store, "pipe1", "run1", mtime=1_700_000_100.0)
        _write_pipeline_report(
            tmp_path, store, "pipe1", "run-bad", mtime=1_700_000_200.0
        )
        entries = _query.list_pipeline_reports(
            pipeline_name="pipe1", root=tmp_path, store=store
        )
        assert [entry.run_id for entry in entries] == ["run1"]

    def test_entry_hydrates_markdown_and_pipeline_ids(self, tmp_path):
        store = _FsStore()
        report_path = _write_pipeline_report(
            tmp_path,
            store,
            "pipe1",
            "run1",
            mtime=1_700_000_100.0,
            identity={
                "status": "success",
                "run_id": "run1",
                "started_at": "2026-01-01",
                "completed_at": "2026-01-02",
                "workflow_id": "wf1",
                "workflow_run_id": "wrun1",
                "run_type": "incremental",
            },
        )
        (report_path.parent / "pipeline-run-report.md").write_text(
            "# report", encoding="utf-8"
        )
        (
            entries := _query.list_pipeline_reports(
                pipeline_name="pipe1", root=tmp_path, store=store
            )
        )
        assert len(entries) == 1
        entry = entries[0]
        assert entry.markdown_path is not None
        assert entry.status == "success"
        assert entry.workflow_id == "wf1"
        assert entry.workflow_run_id == "wrun1"
        assert entry.run_type == "incremental"

    def test_entry_without_markdown(self, tmp_path):
        store = _FsStore()
        _write_pipeline_report(tmp_path, store, "pipe1", "run1", mtime=1_700_000_100.0)
        (
            entries := _query.list_pipeline_reports(
                pipeline_name="pipe1", root=tmp_path, store=store
            )
        )
        assert entries[0].markdown_path is None
        assert entries[0].workflow_id is None


class TestDiffReports:
    def test_funnel_and_reason_deltas(self):
        left = {
            "identity": {"run_id": "a"},
            "funnel": [
                {
                    "stage_id": "s1",
                    "records_in": 10,
                    "records_out": 8,
                    "removed_total": 2,
                },
                {
                    "stage_id": "s2",
                    "records_in": 8,
                    "records_out": 8,
                    "removed_total": 0,
                },
            ],
            "reasons_top_n": [{"reason_code": "r1", "count": 2}],
        }
        right = {
            "identity": {"run_id": "b"},
            "funnel": [
                {
                    "stage_id": "s1",
                    "records_in": 12,
                    "records_out": 8,
                    "removed_total": 4,
                },
            ],
            "reasons_top_n": [
                {"reason_code": "r1", "count": 3},
                {"reason_code": "r2", "count": 1},
            ],
        }
        result = _query.diff_pipeline_reports(left, right)
        assert result["left_run_id"] == "a"
        assert result["right_run_id"] == "b"
        s1 = next(row for row in result["funnel_delta"] if row["stage_id"] == "s1")
        assert s1["records_in_delta"] == 2
        assert s1["removed_total_delta"] == 2
        deltas = {
            row["reason_code"]: row["count_delta"] for row in result["reasons_delta"]
        }
        assert deltas == {"r1": 1, "r2": 1}

    def test_empty_payloads_diff_to_empty(self):
        result = _query.diff_pipeline_reports({}, {})
        assert result["funnel_delta"] == []
        assert result["reasons_delta"] == []
        assert result["left_run_id"] is None

    def test_non_mapping_raises_type_error(self):
        with pytest.raises(TypeError):
            _query.diff_pipeline_reports(["not", "mapping"], {})

    def test_int_coercion_branches(self):
        assert _query._int(None) == 0
        assert _query._int("7") == 0 + 7
        assert _query._int(3.9) == 3
        assert _query._int(b"4") == 4
        assert _query._int("nope") == 0
        assert _query._int(object()) == 0
        assert _query._int(float("inf")) == 0


class TestPruneReports:
    def test_invalid_kind_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="kind must be"):
            _query.prune_reports(
                kind="bogus", max_count=1, root=tmp_path, store=_FsStore()
            )

    def test_missing_options_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="provide max_count"):
            _query.prune_reports(kind="pipeline", root=tmp_path, store=_FsStore())

    def test_max_age_requires_now(self, tmp_path):
        with pytest.raises(ValueError, match="now is required"):
            _query.prune_reports(
                kind="pipeline", max_age_days=7, root=tmp_path, store=_FsStore()
            )

    def test_dry_run_returns_candidates_without_deleting(self, tmp_path):
        from datetime import UTC, datetime

        store = _FsStore()
        old = _write_pipeline_report(
            tmp_path, store, "pipe1", "run-old", mtime=1_700_000_000.0
        )
        _write_pipeline_report(
            tmp_path, store, "pipe1", "run-new", mtime=1_800_000_000.0
        )
        now = datetime.fromtimestamp(1_800_000_000.0, tz=UTC)
        victims = _query.prune_reports(
            kind="pipeline",
            max_age_days=30,
            now=now,
            root=tmp_path,
            dry_run=True,
            store=store,
        )
        assert victims == [str(old.parent.as_posix())]
        assert old.is_file()

    def test_max_count_prunes_oldest_and_removes(self, tmp_path):
        store = _FsStore()
        oldest = _write_pipeline_report(
            tmp_path, store, "pipe1", "run1", mtime=1_700_000_100.0
        )
        _write_pipeline_report(tmp_path, store, "pipe1", "run2", mtime=1_700_000_200.0)
        _write_pipeline_report(tmp_path, store, "pipe1", "run3", mtime=1_700_000_300.0)
        removed = _query.prune_reports(
            kind="pipeline", max_count=2, root=tmp_path, dry_run=False, store=store
        )
        assert removed == [str(oldest.parent.as_posix())]
        assert not oldest.parent.exists()

    def test_duplicate_directories_removed_once(self):
        store = _FsStore()
        entry = _query.ReportIndexEntry(
            kind="pipeline",
            owner="pipe1",
            run_id="run1",
            json_path=Path("/tmp/x/run1/pipeline-run-report.json"),
            markdown_path=None,
            status=None,
            started_at=None,
            completed_at=None,
            mtime=1.0,
        )
        removed = _query._remove_report_directories(
            [entry, entry], dry_run=True, store=store
        )
        assert removed == ["/tmp/x/run1"]


# ---------------------------------------------------------------------------
# run_reports.workflow_observations
# ---------------------------------------------------------------------------


def _obs_row(**overrides):
    kwargs = {
        "step_id": "s1",
        "status": "success",
        "records_extracted": 5,
        "pipeline_name": "pipe1",
        "pipeline_run_id": "run1",
    }
    kwargs.update(overrides)
    return WorkflowExecutionRow(**kwargs)


def _obs_report(rows, **identity):
    base = {"status": "success", "workflow_run_id": "wrun1"}
    base.update(identity)
    return WorkflowRunReport(
        identity=base, plan_steps=(), execution=tuple(rows), totals={}
    )


def _publish_verified_child(store, root, row, workflow_run_id="wrun1", **extra_child):
    child = {
        "identity": {
            "run_id": row.pipeline_run_id,
            "pipeline_name": row.pipeline_name,
            "workflow_run_id": workflow_run_id,
        },
        "evidence_field": "kept",
    }
    child.update(extra_child)
    path = (
        root
        / "pipeline"
        / row.pipeline_name
        / row.pipeline_run_id
        / "pipeline-run-report.json"
    )
    payload = publish_snapshot(child, path, store=store)
    store.write_text(str(path), json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


class TestChildPath:
    def test_rejects_parent_segments(self, tmp_path):
        row = _obs_row(pipeline_name="..")
        with pytest.raises(ValueError, match="workflow_child_identity_invalid"):
            _child_path(tmp_path, row)

    def test_rejects_slash_segments(self, tmp_path):
        row = _obs_row(pipeline_run_id="a/b")
        with pytest.raises(ValueError, match="workflow_child_identity_invalid"):
            _child_path(tmp_path, row)

    def test_resolves_valid_path(self, tmp_path):
        assert _child_path(tmp_path, _obs_row()) == (
            tmp_path / "pipeline" / "pipe1" / "run1" / "pipeline-run-report.json"
        )


class TestVerifiedChild:
    def test_missing_file_returns_none(self, tmp_path):
        assert (
            _verified_child(
                tmp_path / "absent.json", _obs_row(), "wrun1", store=_FsStore()
            )
            is None
        )

    def test_non_dict_report_raises(self, tmp_path):
        store = _FsStore()
        path = tmp_path / "child.json"
        store.write_text(str(path), "[1, 2]")
        with pytest.raises(ValueError, match="workflow_child_report_corrupt"):
            _verified_child(path, _obs_row(), "wrun1", store=store)

    def test_missing_snapshot_returns_none(self, tmp_path):
        store = _FsStore()
        path = tmp_path / "child.json"
        store.write_text(str(path), json.dumps({"identity": {}}))
        assert _verified_child(path, _obs_row(), "wrun1", store=store) is None

    def test_tampered_snapshot_raises(self, tmp_path):
        store = _FsStore()
        row = _obs_row()
        path = _publish_verified_child(store, tmp_path, row)
        payload = json.loads(store.read_text(str(path)))
        payload["evidence_field"] = "tampered"
        store.write_text(str(path), json.dumps(payload))
        with pytest.raises(ValueError, match="workflow_child_snapshot_corrupt"):
            _verified_child(path, row, "wrun1", store=store)

    def test_identity_mismatch_raises(self, tmp_path):
        store = _FsStore()
        row = _obs_row()
        path = _publish_verified_child(store, tmp_path, row, workflow_run_id="other-wf")
        with pytest.raises(ValueError, match="workflow_child_identity_mismatch"):
            _verified_child(path, row, "wrun1", store=store)

    def test_manifest_id_mismatch_raises(self, tmp_path):
        store = _FsStore()
        row = _obs_row(pipeline_manifest_id="manifest-1")
        path = _publish_verified_child(store, tmp_path, row)
        with pytest.raises(ValueError, match="workflow_child_identity_mismatch"):
            _verified_child(path, row, "wrun1", store=store)

    def test_verified_child_returned(self, tmp_path):
        store = _FsStore()
        row = _obs_row(pipeline_manifest_id="manifest-1")
        child_extra = {
            "identity": {
                "run_id": row.pipeline_run_id,
                "pipeline_name": row.pipeline_name,
                "workflow_run_id": "wrun1",
                "manifest_id": "manifest-1",
            }
        }
        path = _publish_verified_child(store, tmp_path, row, **child_extra)
        assert _verified_child(path, row, "wrun1", store=store) is not None


class TestFinalizeWorkflowChildren:
    def test_skips_rows_without_identity(self, tmp_path):
        store = _FsStore()
        report = _obs_report([_obs_row(pipeline_name=None, pipeline_run_id=None)])
        finalize_workflow_children(report, root=tmp_path, store=store)

    def test_skips_children_without_snapshot(self, tmp_path):
        store = _FsStore()
        row = _obs_row()
        path = tmp_path / "pipeline" / "pipe1" / "run1" / "pipeline-run-report.json"
        store.write_text(str(path), json.dumps({"identity": {}}))
        finalize_workflow_children(_obs_report([row]), root=tmp_path, store=store)
        assert "selected_run_snapshot" not in store.read_text(str(path))

    def test_rejects_non_dict_observations(self, tmp_path):
        store = _FsStore()
        row = _obs_row()
        _publish_verified_child(store, tmp_path, row, observations=["not", "dict"])
        with pytest.raises(ValueError, match="workflow_child_observations_corrupt"):
            finalize_workflow_children(_obs_report([row]), root=tmp_path, store=store)

    @pytest.mark.parametrize(
        ("status", "verdict"),
        [
            ("success", "OK"),
            ("failed", "ERROR"),
            ("partial", "WARN"),
            ("cancelled", "WARN"),
            ("shutdown", "WARN"),
            ("mystery", "UNKNOWN"),
        ],
    )
    def test_verdict_mapping(self, tmp_path, status, verdict):
        store = _FsStore()
        row = _obs_row()
        path = _publish_verified_child(store, tmp_path, row)
        finalize_workflow_children(
            _obs_report([row], status=status), root=tmp_path, store=store
        )
        child = json.loads(store.read_text(str(path)))
        observation = child["observations"]["Workflow"]
        assert observation["verdict"] == verdict
        assert observation["reason"] == f"workflow_{status}"
        assert observation["facts"]["step_id"] == "s1"
        republished_snapshot = child["selected_run_snapshot"]
        assert (
            republished_snapshot["evidence"]["observations"]["Workflow"]["verdict"]
            == verdict
        )


# ---------------------------------------------------------------------------
# run_reports.source_identity
# ---------------------------------------------------------------------------


class TestNormalizeSourceId:
    def test_valid_digest(self):
        assert _sid.normalize_source_id("a" * 64) == "a" * 64

    def test_normalizes_case_and_whitespace(self):
        assert _sid.normalize_source_id("  " + "B" * 64 + "  ") == "b" * 64

    def test_rejects_invalid(self):
        assert _sid.normalize_source_id("xyz") is None
        assert _sid.normalize_source_id(None) is None
        assert _sid.normalize_source_id("") is None


class TestRuntimePaths:
    def test_empty_path_normalizes_empty(self):
        assert _sid.normalize_runtime_path("", root="/repo") == ""

    def test_windows_drive_matches_docker_desktop(self):
        windows = _sid.normalize_runtime_path("E:/repo/file", root="E:/repo")
        desktop = _sid.normalize_runtime_path("/mnt/e/repo/file", root="/mnt/e/repo")
        assert windows == desktop

    def test_relative_path_joins_root(self):
        assert (
            _sid.normalize_runtime_path("sub/file", root="/mnt/e/repo")
            == "/mnt/e/repo/sub/file"
        )

    def test_wsl_unc_spelling(self):
        assert (
            _sid.normalize_runtime_path("//wsl$/Ubuntu/mnt/e/repo", root="/x")
            == "/mnt/e/repo"
        )

    def test_docker_desktop_drive_spelling(self):
        assert (
            _sid.normalize_runtime_path("/host_mnt/e/repo/file", root="/x")
            == "/mnt/e/repo/file"
        )

    def test_docker_desktop_wsl_spelling(self):
        assert (
            _sid.normalize_runtime_path("/host_mnt/wsl/distro", root="/x")
            == "/mnt/wsl/distro"
        )

    def test_drive_without_suffix(self):
        assert _sid.normalize_runtime_path("E:", root="/x") == "/mnt/e"

    def test_interior_double_slashes_collapsed(self):
        assert _sid.normalize_runtime_path("a//b//c", root="/r") == "/r/a/b/c"

    def test_canonical_comparison_with_mapped_spelling(self):
        assert _sid._canonical_comparison_path("E:/Repo/File") == "/mnt/e/repo/file"

    def test_relative_root_is_resolved(self):
        result = _sid.normalize_runtime_path("sub", root="relroot")
        assert result.endswith("/relroot/sub")

    def test_local_posix_path_on_windows_returns_none(self, monkeypatch):
        import os as _os

        monkeypatch.setattr(_os, "name", "nt")
        assert _sid._local_posix_runtime_path("E:/repo") is None

    def test_unmapped_value_returns_none(self):
        assert _sid._mapped_runtime_path("/plain/posix") is None

    def test_local_path_empty_returns_root(self, tmp_path):
        assert _sid.runtime_path_to_local_path("", root=tmp_path) == Path(tmp_path)

    def test_local_path_maps_windows_spelling(self, tmp_path):
        assert _sid.runtime_path_to_local_path("E:/repo/file", root=tmp_path) == Path(
            "/mnt/e/repo/file"
        )

    def test_local_path_relative_resolves_under_root(self, tmp_path):
        assert (
            _sid.runtime_path_to_local_path("sub/file", root=tmp_path)
            == (tmp_path / "sub" / "file").resolve()
        )


class TestComputeRuntimeSourceId:
    def test_deterministic_for_same_inputs(self):
        first = _sid.compute_runtime_source_id(
            runtime_root="/mnt/e/repo", mounts={"/data": "/mnt/e/data"}
        )
        second = _sid.compute_runtime_source_id(
            runtime_root="/mnt/e/repo", mounts={"/data": "/mnt/e/data"}
        )
        assert first is not None
        assert first == second

    def test_blank_entries_are_skipped(self):
        assert (
            _sid.compute_runtime_source_id(
                runtime_root="/mnt/e/repo",
                mounts={"": "/mnt/e/data", "/data": "  "},
            )
            is None
        )

    def test_empty_schema_returns_none(self):
        assert (
            _sid.compute_runtime_source_id(
                runtime_root="/mnt/e/repo",
                mounts={"/data": "/mnt/e/data"},
                schema_version="  ",
            )
            is None
        )

    def test_empty_mounts_returns_none(self):
        assert (
            _sid.compute_runtime_source_id(runtime_root="/mnt/e/repo", mounts={})
            is None
        )


def _digest(seed: str) -> str:
    import hashlib

    return hashlib.sha256(seed.encode()).hexdigest()


class TestResolveRuntimeSourceIdentity:
    def test_all_missing(self):
        result = _sid.resolve_runtime_source_identity()
        assert result.status == _sid.IDENTITY_RESOLUTION_MISSING
        assert result.source == _sid.IDENTITY_SOURCE_NONE
        assert result.state == _sid.IDENTITY_STATE_MISSING
        assert not result.is_resolved
        assert not result.is_consistent

    def test_computed_identity_selected(self):
        value = _digest("root")
        result = _sid.resolve_runtime_source_identity(computed_identity=value)
        assert result.value == value
        assert result.source == _sid.IDENTITY_SOURCE_RUNTIME_ROOT
        assert result.is_consistent
        assert result.state == _sid.IDENTITY_STATE_ALIGNED

    def test_invalid_top_value_is_fail_closed(self):
        result = _sid.resolve_runtime_source_identity(
            computed_identity="bogus",
            process_environment={_sid.RUNTIME_SOURCE_ID_ENV: _digest("env")},
        )
        assert result.status == _sid.IDENTITY_RESOLUTION_INVALID
        assert result.state == _sid.IDENTITY_STATE_INVALID
        assert result.invalid_sources == (_sid.IDENTITY_SOURCE_RUNTIME_ROOT,)

    def test_lower_disagreement_recorded_as_conflict(self):
        value = _digest("same")
        result = _sid.resolve_runtime_source_identity(
            computed_identity=value,
            process_environment={_sid.RUNTIME_SOURCE_ID_ENV: value},
            container_environment={_sid.RUNTIME_SOURCE_ID_ENV: _digest("other")},
        )
        assert result.is_resolved
        assert result.state == _sid.IDENTITY_STATE_FOREIGN
        assert _sid.IDENTITY_SOURCE_CONTAINER_ENVIRONMENT in result.conflicts
        assert not result.is_consistent

    def test_lower_invalid_recorded(self):
        value = _digest("same")
        result = _sid.resolve_runtime_source_identity(
            computed_identity=value,
            container_labels={_sid.RUNTIME_SOURCE_ID_LABEL: "bogus"},
        )
        assert result.is_resolved
        assert result.state == _sid.IDENTITY_STATE_INVALID
        assert _sid.IDENTITY_SOURCE_CONTAINER_LABEL in result.invalid_sources

    def test_blank_values_skipped(self):
        value = _digest("same")
        result = _sid.resolve_runtime_source_identity(
            computed_identity="   ",
            repository_environment={_sid.RUNTIME_SOURCE_ID_ENV: value},
        )
        assert result.value == value
        assert result.source == _sid.IDENTITY_SOURCE_REPOSITORY_ENVIRONMENT

    def test_as_dict_reports_state(self):
        result = _sid.resolve_runtime_source_identity()
        payload = result.as_dict()
        assert payload["status"] == _sid.IDENTITY_RESOLUTION_MISSING
        assert payload["state"] == _sid.IDENTITY_STATE_MISSING


class TestCompareRuntimeSourceIdentity:
    def test_missing_when_either_blank(self):
        result = _sid.compare_runtime_source_identity(expected="", actual=_digest("a"))
        assert result.state == _sid.IDENTITY_STATE_MISSING
        assert not result.is_aligned

    def test_invalid_when_malformed(self):
        result = _sid.compare_runtime_source_identity(
            expected="bogus", actual=_digest("a")
        )
        assert result.state == _sid.IDENTITY_STATE_INVALID

    def test_foreign_on_mismatch(self):
        result = _sid.compare_runtime_source_identity(
            expected=_digest("a"), actual=_digest("b")
        )
        assert result.state == _sid.IDENTITY_STATE_FOREIGN
        assert not result.is_aligned

    def test_aligned_normalizes_case(self):
        value = _digest("a")
        result = _sid.compare_runtime_source_identity(
            expected=value.upper(), actual="  " + value + "  "
        )
        assert result.state == _sid.IDENTITY_STATE_ALIGNED
        assert result.is_aligned


class TestLoadRepositorySourceEnvironment:
    def test_reads_env_with_local_override(self, tmp_path):
        (tmp_path / ".env").write_text(
            "BIOETL_RUNTIME_SOURCE_ID=aaa\nOTHER=1\n", encoding="utf-8"
        )
        (tmp_path / ".env.local").write_text(
            "BIOETL_RUNTIME_SOURCE_ID=bbb\n", encoding="utf-8"
        )
        values = _sid.load_repository_source_environment(
            tmp_path, names=["BIOETL_RUNTIME_SOURCE_ID"]
        )
        assert values == {"BIOETL_RUNTIME_SOURCE_ID": "bbb"}

    def test_missing_files_return_empty(self, tmp_path):
        assert _sid.load_repository_source_environment(tmp_path, names=["ANY"]) == {}

    def test_skip_env_local(self, tmp_path):
        (tmp_path / ".env").write_text("MY_KEY=base\n", encoding="utf-8")
        (tmp_path / ".env.local").write_text("MY_KEY=override\n", encoding="utf-8")
        values = _sid.load_repository_source_environment(
            tmp_path,
            names=["MY_KEY"],
            process_environment={"BIOETL_SKIP_ENV_LOCAL": "1"},
        )
        assert values == {"MY_KEY": "base"}

    def test_custom_env_file(self, tmp_path):
        custom = tmp_path / "custom.env"
        custom.write_text("MY_KEY=custom\n", encoding="utf-8")
        values = _sid.load_repository_source_environment(
            tmp_path,
            names=["MY_KEY"],
            process_environment={"BIOETL_ENV_FILE": "custom.env"},
        )
        assert values == {"MY_KEY": "custom"}

    def test_parsing_branches(self, tmp_path):
        (tmp_path / ".env").write_text(
            "# comment\n"
            "NOEQUALS\n"
            "MY_KEY='single quoted'\n"
            'MY_OTHER="double quoted"\n'
            "MY_THIRD=plain # trailing comment\n"
            "MY_HASH=keep#hash\n",
            encoding="utf-8",
        )
        values = _sid.load_repository_source_environment(
            tmp_path, names=["MY_KEY", "MY_OTHER", "MY_THIRD", "MY_HASH"]
        )
        assert values == {
            "MY_KEY": "single quoted",
            "MY_OTHER": "double quoted",
            "MY_THIRD": "plain",
            "MY_HASH": "keep#hash",
        }


# ---------------------------------------------------------------------------
# workflow.workflow_runner_reports
# ---------------------------------------------------------------------------


def _pipeline_step_mock(step_id="step-pipe", pipeline_name="pipe1"):
    from bioetl.domain.workflow import WorkflowStepConfig

    step = MagicMock(spec=WorkflowStepConfig)
    step.step_id = step_id
    step.depends_on = []
    step.pipeline_name = pipeline_name
    return step


def _plan_config():
    pipe_step = _pipeline_step_mock()
    transform_step = SimpleNamespace(
        step_id="step-t", depends_on=["step-pipe"], transform_name="norm"
    )
    steps = {"step-pipe": pipe_step, "step-t": transform_step}
    return SimpleNamespace(
        topological_step_ids=("step-pipe", "step-t", "step-gone"),
        get_step=lambda step_id: steps.get(step_id),
    )


class TestPlanStepsFromConfig:
    def test_pipeline_transform_and_missing_steps(self):
        plan = _plan_steps_from_config(_plan_config())
        assert [step["step_id"] for step in plan] == ["step-pipe", "step-t"]
        pipe, transform = plan
        assert pipe["kind"] == "pipeline"
        assert pipe["pipeline_name"] == "pipe1"
        assert pipe["transform_name"] is None
        assert transform["kind"] == "transform"
        assert transform["pipeline_name"] is None
        assert transform["transform_name"] == "norm"
        assert transform["depends_on"] == ["step-pipe"]


class TestPipelineNameForStep:
    def test_prefers_payload_pipeline_name(self):
        from bioetl.application.services.workflow.workflow_runner_models import (
            WorkflowStepExecutionResult,
        )

        step = WorkflowStepExecutionResult(
            step_id="s1", step_kind="pipeline", status="success"
        )
        payload = SimpleNamespace(pipeline_name="from-payload")
        assert (
            _pipeline_name_for_step(step, plan_steps=[], payload=payload)
            == "from-payload"
        )

    def test_falls_back_to_plan(self):
        from bioetl.application.services.workflow.workflow_runner_models import (
            WorkflowStepExecutionResult,
        )

        step = WorkflowStepExecutionResult(
            step_id="step-pipe", step_kind="pipeline", status="success"
        )
        plan = [{"step_id": "step-pipe", "pipeline_name": "planned-pipe"}]
        assert (
            _pipeline_name_for_step(step, plan_steps=plan, payload=None)
            == "planned-pipe"
        )

    def test_returns_none_without_match(self):
        from bioetl.application.services.workflow.workflow_runner_models import (
            WorkflowStepExecutionResult,
        )

        step = WorkflowStepExecutionResult(
            step_id="unknown", step_kind="pipeline", status="success"
        )
        assert _pipeline_name_for_step(step, plan_steps=[], payload=None) is None


class TestLoadChildReportSlice:
    def test_empty_ref_returns_empty(self):
        assert _load_child_report_slice("", store=MagicMock()) == ((), None)

    def test_missing_file_returns_empty(self, tmp_path):
        assert _load_child_report_slice(
            str(tmp_path / "absent.json"), store=_FsStore()
        ) == ((), None)

    def test_corrupt_file_returns_empty(self, tmp_path):
        store = _FsStore()
        path = tmp_path / "child.json"
        store.write_text(str(path), "{bad")
        assert _load_child_report_slice(str(path), store=store) == ((), None)

    def test_non_mapping_returns_empty(self, tmp_path):
        store = _FsStore()
        path = tmp_path / "child.json"
        store.write_text(str(path), "[1]")
        assert _load_child_report_slice(str(path), store=store) == ((), None)

    def test_reasons_and_gold_excluded(self, tmp_path):
        store = _FsStore()
        path = tmp_path / "child.json"
        store.write_text(
            str(path),
            json.dumps(
                {
                    "reasons_top_n": [{"reason_code": "r1"}],
                    "layers": {"gold_excluded_by_contract": 3},
                }
            ),
        )
        reasons, excluded = _load_child_report_slice(str(path), store=store)
        assert reasons == [{"reason_code": "r1"}]
        assert excluded == 3

    def test_non_int_excluded_and_missing_layers(self, tmp_path):
        store = _FsStore()
        path = tmp_path / "child.json"
        store.write_text(
            str(path),
            json.dumps(
                {"layers": {"gold_excluded_by_contract": "many"}, "reasons_top_n": None}
            ),
        )
        assert _load_child_report_slice(str(path), store=store) == ((), None)
        store.write_text(str(path), json.dumps({"layers": ["not", "mapping"]}))
        assert _load_child_report_slice(str(path), store=store) == ((), None)


class TestExecutionRowsFromResult:
    def _result(self):
        from bioetl.application.services.workflow.workflow_runner_models import (
            WorkflowRunExecutionResult,
            WorkflowStepExecutionResult,
        )

        transform_payload = SimpleNamespace(
            output=SimpleNamespace(
                pipeline_name=None, run_report_json_path="/tmp/absent.json"
            )
        )
        return WorkflowRunExecutionResult(
            workflow_name="wf",
            status="success",
            steps=(
                WorkflowStepExecutionResult(
                    step_id="step-pipe",
                    step_kind="pipeline",
                    status="success",
                    payload=None,
                    child_run_id="c1",
                    child_manifest_id="m1",
                ),
                WorkflowStepExecutionResult(
                    step_id="step-t",
                    step_kind="transform",
                    status="success",
                    payload=transform_payload,
                    error_type="E",
                    error_message="boom",
                ),
            ),
        )

    def test_rows_resolve_names_and_reports(self):
        plan = [{"step_id": "step-pipe", "pipeline_name": "planned-pipe"}]
        rows = _execution_rows_from_result(
            self._result(), plan_steps=plan, store=_FsStore()
        )
        assert len(rows) == 2
        assert rows[0]["pipeline_name"] == "planned-pipe"
        assert rows[0]["child_run_id"] == "c1"
        assert rows[0]["top_reasons"] == ()
        assert rows[0]["gold_excluded_by_contract"] is None
        assert rows[1]["error_type"] == "E"


class TestAttachWorkflowRunReport:
    def _result(self):
        from bioetl.application.services.workflow.workflow_runner_models import (
            WorkflowRunExecutionResult,
        )

        return WorkflowRunExecutionResult(
            workflow_name="wf", status="success", steps=()
        )

    def test_happy_path_attaches_paths(self, monkeypatch):
        import bioetl.application.services.run_reports.writer as _writer
        import bioetl.domain.run_reports.workflow_builder as _builder

        monkeypatch.setattr(
            _builder,
            "build_workflow_run_report",
            lambda *, identity, plan_steps, execution_steps: {"identity": identity},
        )
        monkeypatch.setattr(
            _writer,
            "write_workflow_run_report",
            lambda report, root=None, store=None: SimpleNamespace(
                json_path=Path("report.json"), markdown_path=Path("report.md")
            ),
        )
        result = attach_workflow_run_report(
            config=_plan_config(),
            result=self._result(),
            store=MagicMock(),
            report_root=None,
        )
        assert result.run_report_json_path == "report.json"
        assert result.run_report_markdown_path == "report.md"

    def test_failure_logs_warning_and_records_error(self):
        logger = MagicMock()
        result = attach_workflow_run_report(
            config=None,
            result=self._result(),
            logger=logger,
            store=MagicMock(),
        )
        assert result.run_report_error.startswith("AttributeError")
        logger.warning.assert_called_once()

    def test_failure_without_logger(self):
        result = attach_workflow_run_report(
            config=None, result=self._result(), store=MagicMock()
        )
        assert "AttributeError" in result.run_report_error

    def test_require_result_rejects_other_types(self):
        with pytest.raises(TypeError):
            _require_workflow_result(object())


# ---------------------------------------------------------------------------
# effective_config.runtime_overrides
# ---------------------------------------------------------------------------


class TestApplyOverrides:
    def test_deep_update_merges_nested(self):
        target = {"a": {"x": 1, "y": 2}, "b": 1}
        apply_deep_update(target, {"a": {"y": 3, "z": 4}, "c": 5})
        assert target == {"a": {"x": 1, "y": 3, "z": 4}, "b": 1, "c": 5}

    def test_deep_update_replaces_non_dict(self):
        target = {"a": 1}
        apply_deep_update(target, {"a": {"nested": True}})
        assert target == {"a": {"nested": True}}

    def test_runtime_layer_wins_and_non_dict_ignored(self):
        base = {"k": "base", "n": {"v": 0}}
        overrides = {
            "cli": {"k": "cli"},
            "env": "not-a-mapping",
            "runtime": {"k": "runtime"},
        }
        assert apply_runtime_overrides(base, overrides) == {
            "k": "runtime",
            "n": {"v": 0},
        }
        assert base == {"k": "base", "n": {"v": 0}}


class TestCoerceRuntimeOverrideLayer:
    def test_missing_and_none_return_empty(self):
        assert coerce_runtime_override_layer({}, "cli") == {}
        assert coerce_runtime_override_layer({"cli": None}, "cli") == {}

    def test_non_mapping_raises__svc1a_1(self):
        with pytest.raises(TypeError, match="runtime_overrides.cli must be a mapping"):
            coerce_runtime_override_layer({"cli": ["x"]}, "cli")


class TestValidateRuntimeEnvironmentProvenance:
    def test_non_strict_profile_skips_validation(self):
        validate_runtime_environment_provenance(
            runtime_overrides={"env": {"anything": 1}},
            required_persistence_profile="standard",
        )

    def test_unsupported_env_keys_rejected(self):
        with pytest.raises(ValueError, match="non-allowlisted"):
            validate_runtime_environment_provenance(
                runtime_overrides={"env": {"PATH": "/bin"}},
                required_persistence_profile="replay_ready",
            )

    def test_missing_execution_environment_rejected(self):
        with pytest.raises(ValueError, match="must be materialized"):
            validate_runtime_environment_provenance(
                runtime_overrides={"env": {}},
                required_persistence_profile="forensic_grade",
            )

    def test_non_mapping_execution_environment_rejected(self):
        with pytest.raises(TypeError, match="must be a mapping"):
            validate_runtime_environment_provenance(
                runtime_overrides={"env": {"execution_environment": "x"}},
                required_persistence_profile="replay_ready",
            )

    def test_empty_execution_environment_rejected(self):
        with pytest.raises(ValueError, match="must be non-empty"):
            validate_runtime_environment_provenance(
                runtime_overrides={"env": {"execution_environment": {}}},
                required_persistence_profile="replay_ready",
            )

    def test_valid_materialized_environment_passes(self):
        validate_runtime_environment_provenance(
            runtime_overrides={"env": {"execution_environment": {"k": "v"}}},
            required_persistence_profile="replay_ready",
        )


class TestNormalizeSemanticIdentityBranches:
    def test_non_explicit_settings_kept(self):
        overrides = {
            "runtime": {
                "settings_snapshot": {
                    "settings": {"data_root_mode": "standard", "data_dir": "/keep/me"},
                }
            }
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        snapshot = normalized["runtime"]["settings_snapshot"]
        assert snapshot["settings"]["data_dir"] == "/keep/me"
        assert snapshot["snapshot_hash"].startswith("sha256:")

    def test_non_dict_cached_bronze_ignored(self):
        overrides = {"cli": {"cached_bronze": "not-a-mapping"}}
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        assert normalized["cli"]["cached_bronze"] == "not-a-mapping"

    def test_explicit_mode_without_data_dir_skips_sentinel(self):
        overrides = {
            "runtime": {
                "settings_snapshot": {
                    "settings": {"data_root_mode": "explicit", "data_dir": ""},
                }
            }
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        snapshot = normalized["runtime"]["settings_snapshot"]
        assert snapshot["settings"]["data_dir"] == ""
        assert snapshot["snapshot_hash"].startswith("sha256:")

    def test_cached_bronze_without_path_kept(self):
        overrides = {"runtime": {"cached_bronze": {"other": 1}}}
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        assert normalized["runtime"]["cached_bronze"] == {"other": 1}

    def test_non_dict_settings_snapshot_skipped(self):
        overrides = {
            "runtime": {"settings_snapshot": "not-a-mapping"},
            "env": {"execution_environment": {}},
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        assert normalized["runtime"]["settings_snapshot"] == "not-a-mapping"
        assert (
            "settings_snapshot_hash" not in normalized["env"]["execution_environment"]
        )

    def test_non_dict_execution_environment_skipped(self):
        overrides = {"env": {"execution_environment": ["not", "a", "mapping"]}}
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        assert normalized["env"]["execution_environment"] == ["not", "a", "mapping"]


class TestRuntimeOverrideSnapshots:
    def test_build_snapshot_splits_layers(self):
        snapshot = build_runtime_override_snapshot(
            {"cli": {"a": 1}, "env": {"b": 2}, "runtime": {"c": 3}}
        )
        assert snapshot.cli_overrides == {"a": 1}
        assert snapshot.env_overrides == {"b": 2}
        assert snapshot.runtime_adjustments == {"c": 3}
        assert snapshot.override_hash

    def test_normalize_masks_explicit_data_dir(self):
        overrides = {
            "runtime": {
                "settings_snapshot": {
                    "settings": {"data_root_mode": "explicit", "data_dir": "/secret/x"},
                }
            }
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        snapshot = normalized["runtime"]["settings_snapshot"]
        assert snapshot["settings"]["data_dir"] == "<explicit-data-dir>"
        assert snapshot["snapshot_hash"].startswith("sha256:")
        assert overrides["runtime"]["settings_snapshot"]["settings"]["data_dir"] == (
            "/secret/x"
        )

    def test_normalize_masks_cached_bronze_paths(self):
        overrides = {
            "cli": {"cached_bronze": {"bronze_path": "/secret/bronze"}},
            "runtime": {"cached_bronze": {"bronze_path": "/secret/other"}},
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        assert (
            normalized["cli"]["cached_bronze"]["bronze_path"] == "<cached-bronze-path>"
        )
        assert (
            normalized["runtime"]["cached_bronze"]["bronze_path"]
            == "<cached-bronze-path>"
        )

    def test_normalize_propagates_settings_hash_to_environment(self):
        overrides = {
            "runtime": {"settings_snapshot": {"settings": {}}},
            "env": {"execution_environment": {}},
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        env = normalized["env"]["execution_environment"]
        assert (
            env["settings_snapshot_hash"]
            == normalized["runtime"]["settings_snapshot"]["snapshot_hash"]
        )

    def test_normalize_drops_stale_environment_hash(self):
        overrides = {
            "runtime": {},
            "env": {"execution_environment": {"settings_snapshot_hash": "old"}},
        }
        normalized = normalize_runtime_overrides_for_semantic_identity(overrides)
        assert (
            "settings_snapshot_hash" not in normalized["env"]["execution_environment"]
        )

    def test_execution_environment_materialized(self):
        from bioetl.application.services.control_plane.effective_config import (  # noqa
            runtime_overrides as _ro,
        )
        from bioetl.domain.control_plane.effective_config_environment import (
            MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY,
        )
        from bioetl.domain.control_plane.effective_config_environment import (
            semantic_runtime_env_dependencies as _deps,
        )

        snapshot = build_execution_environment_snapshot(
            {"env": {"execution_environment": {"k": "v"}}},
            required_persistence_profile="replay_ready",
        )
        assert snapshot.materialized_env_keys == ("execution_environment",)
        assert snapshot.ambient_environment_policy == (
            MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY
        )
        assert snapshot.non_materialized_semantic_env_dependencies == ()

    def test_execution_environment_ambient(self):
        from bioetl.domain.control_plane.effective_config_environment import (
            AMBIENT_ENVIRONMENT_POLICY,
            semantic_runtime_env_dependencies,
        )

        snapshot = build_execution_environment_snapshot(
            {}, required_persistence_profile="standard"
        )
        assert snapshot.ambient_environment_policy == AMBIENT_ENVIRONMENT_POLICY
        assert snapshot.non_materialized_semantic_env_dependencies == (
            semantic_runtime_env_dependencies()
        )

    def test_effective_execution_config_applies_overrides(self):
        config = build_effective_execution_config(
            resolved_config={"k": "base"},
            runtime_overrides={"runtime": {"k": "override"}},
        )
        assert config.config_data == {"k": "override"}
        assert config.effective_hash


# ---------------------------------------------------------------------------
# control_plane.forensic_diff_service
# ---------------------------------------------------------------------------


def _inspection_result(manifest_id, diagnostics=None, ledger=()):
    return RunManifestInspectionResult(
        manifest=RunManifest(
            manifest_id=manifest_id, execution_fingerprint=f"fp-{manifest_id}"
        ),
        ledger_entries=ledger,
        diagnostics=dict(diagnostics or {}),
    )


def _manifest_diff(**overrides):
    kwargs = {
        "left_manifest_id": "m-left",
        "right_manifest_id": "m-right",
        "differences": (),
        "classification": "identical",
        "semantic_equivalent": True,
        "occurrence_only": False,
        "occurrence_difference_fields": (),
        "semantic_difference_fields": ("cfg.a",),
        "noncanonical_difference_fields": ("meta.x",),
        "replay_relationship": "none",
        "cross_surface_replay_diff": {},
    }
    kwargs.update(overrides)
    return RunManifestDiffResult(**kwargs)


class TestForensicRunDiffResultDict:
    def test_to_dict_materializes_field_lists(self):
        result = ForensicRunDiffResult(
            left_manifest_id="m-left",
            right_manifest_id="m-right",
            manifest_diff=_manifest_diff(),
            forensic_diff={"verdict": "semantic_equivalent_replay"},
            missing_evidence={"left": ("gap-a",)},
        )
        payload = result.to_dict()
        assert payload["semantic_difference_fields"] == ["cfg.a"]
        assert payload["occurrence_difference_fields"] == []
        assert payload["noncanonical_difference_fields"] == ["meta.x"]
        assert payload["missing_evidence"] == {"left": ["gap-a"]}
        assert payload["manifest_diff"]["classification"] == "identical"


class TestForensicRunDiffService:
    def _service(self, inspection, port=None):
        return ForensicRunDiffService(
            manifest_port=MagicMock(),
            ledger_port=None,
            inspection_service_factory=lambda: inspection,
            artifact_byte_comparison_port=port,
        )

    def test_compare_without_byte_port(self):
        inspection = MagicMock()
        inspection.show.side_effect = [
            _inspection_result("m-left"),
            _inspection_result("m-right"),
        ]
        inspection.diff.return_value = _manifest_diff()
        result = self._service(inspection).compare("m-left", "m-right")
        assert result.left_manifest_id == "m-left"
        assert result.right_manifest_id == "m-right"
        assert result.forensic_diff["verdict"] == "semantic_equivalent_replay"
        assert result.artifact_byte_equivalence["comparison_scope"] == (
            "unavailable_no_port"
        )
        assert result.artifact_completeness["left"]["manifest_id"] == "m-left"
        assert result.lineage_closure["right"]["manifest_id"] == "m-right"
        assert "run_ledger_entries_missing" in result.missing_evidence["left"]

    def test_compare_with_missing_refs(self):
        inspection = MagicMock()
        inspection.show.side_effect = [
            _inspection_result("m-left"),
            _inspection_result("m-right"),
        ]
        inspection.diff.return_value = _manifest_diff()
        result = self._service(inspection, port=MagicMock()).compare("l", "r")
        assert result.artifact_byte_equivalence["comparison_scope"] == (
            "unavailable_missing_refs"
        )

    def test_compare_delegates_to_byte_port(self):
        diagnostics = {
            "artifact_refs": [
                {"artifact_id": "a1", "metadata_path": "m1"},
            ]
        }
        inspection = MagicMock()
        inspection.show.side_effect = [
            _inspection_result("m-left", diagnostics),
            _inspection_result("m-right", diagnostics),
        ]
        inspection.diff.return_value = _manifest_diff()
        port = MagicMock()
        port.compare_artifacts.return_value = {
            "available": True,
            "equivalent": True,
        }
        result = self._service(inspection, port=port).compare("l", "r")
        assert result.artifact_byte_equivalence["equivalent"] is True
        left_refs, right_refs = port.compare_artifacts.call_args[0]
        assert left_refs == [{"artifact_id": "a1", "metadata_path": "m1"}]
        assert right_refs == [{"artifact_id": "a1", "metadata_path": "m1"}]
