# pyright: reportArgumentType=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Unit tests for verify_report_bind operator script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.services.run_reports.paths import (
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_TOKEN,
)


def _load_module() -> ModuleType:
    # Path(__file__) = tests/unit/repo_backed/scripts/ops/docker/test_*.py
    # parents[6] = repository root
    path = (
        Path(__file__).resolve().parents[6]
        / "scripts"
        / "ops"
        / "runtime"
        / "docker"
        / "verify_report_bind.py"
    )
    spec = importlib.util.spec_from_file_location("verify_report_bind", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_host_report_root_ignores_container_bioetl_report_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_module()
    monkeypatch.setenv("BIOETL_REPORT_ROOT", "/app/reports/run-reports")
    monkeypatch.delenv("BIOETL_DASHBOARD_REPORT_ROOT", raising=False)
    root = mod._host_report_root(tmp_path)
    assert root == (tmp_path / "reports" / "run-reports").resolve()
    assert mod._looks_like_container_path("/app/reports/run-reports") is True
    assert (
        mod._looks_like_container_path(
            r"C:\Program Files\Git\app\reports\run-reports"
        )
        is True
    )
    assert mod._looks_like_container_path(str(tmp_path / "reports")) is False


def test_compose_host_bind_path_uses_drive_letter_forward_slashes(
    tmp_path: Path,
) -> None:
    from scripts.ops.runtime.docker.docker_runtime_preflight import (
        compose_host_bind_path,
        dashboard_source_environment,
    )

    reports = tmp_path / "reports"
    reports.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    path = compose_host_bind_path("reports", root=tmp_path)
    assert path.replace("\\", "/").endswith("/reports")
    assert "\\" not in path
    env = dashboard_source_environment(
        tmp_path,
        {
            "dashboard_data_plane": {
                "required_bind_mounts": {
                    "/app/data": {
                        "relative_source": "data",
                        "environment_name": "BIOETL_DASHBOARD_DATA_ROOT",
                    },
                    "/app/reports": {
                        "relative_source": "reports",
                        "environment_name": "BIOETL_DASHBOARD_REPORT_ROOT",
                    },
                },
                "source_identity": {
                    "schema_version": "bioetl-dashboard-source-v1",
                    "environment_name": "BIOETL_RUNTIME_SOURCE_ID",
                },
            }
        },
    )
    assert "\\" not in env["BIOETL_DASHBOARD_REPORT_ROOT"]
    assert env["BIOETL_DASHBOARD_REPORT_ROOT"].replace("\\", "/").endswith("/reports")


def test_verify_host_marker_ok_without_ops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_module()
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    (reports / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_TOKEN + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    monkeypatch.setattr(mod, "_docker_inspect_mounts", lambda _name: None)
    monkeypatch.setattr(mod, "_json_get", lambda _url, **_kw: None)
    rc = mod.verify(
        repo=tmp_path,
        ops_url="http://127.0.0.1:9",
        container="bioetl",
        pipeline=None,
        require_ops=False,
    )
    assert rc == 0


def test_verify_fails_when_marker_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_module()
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    monkeypatch.setattr(mod, "_docker_inspect_mounts", lambda _name: None)
    monkeypatch.setattr(mod, "_json_get", lambda _url, **_kw: None)
    rc = mod.verify(
        repo=tmp_path,
        ops_url="http://127.0.0.1:9",
        container="bioetl",
        pipeline=None,
        require_ops=False,
    )
    assert rc == 1


def test_verify_detects_bind_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_module()
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    (reports / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_TOKEN + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    monkeypatch.setattr(
        mod,
        "_docker_inspect_mounts",
        lambda _name: [
            {
                "Destination": "/app/reports",
                "Source": str(tmp_path / "stale-empty-reports"),
            }
        ],
    )
    monkeypatch.setattr(
        mod,
        "_json_get",
        lambda url, **_kw: (
            {
                "status": "unhealthy",
                "checks": {
                    "report_root": {
                        "status": "unhealthy",
                        "marker": "missing",
                        "message": "missing",
                    }
                },
            }
            if url.endswith("/health/ready")
            else {"status": "ok", "count": 0, "marker_status": "unhealthy", "items": []}
        ),
    )
    # Create one host report so empty ops count is a hard fail when pipeline set.
    pipeline_dir = run_reports / "pipeline" / "chembl_assay" / "run-a"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "pipeline-run-report.json").write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v1",
                "identity": {
                    "run_id": "run-a",
                    "pipeline_name": "chembl_assay",
                    "status": "success",
                },
            }
        ),
        encoding="utf-8",
    )
    rc = mod.verify(
        repo=tmp_path,
        ops_url="http://127.0.0.1:8000",
        container="bioetl",
        pipeline="chembl_assay",
        require_ops=True,
    )
    assert rc == 1
