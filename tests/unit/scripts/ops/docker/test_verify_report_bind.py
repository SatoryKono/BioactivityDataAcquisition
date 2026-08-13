# pyright: reportArgumentType=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Unit tests for verify_report_bind operator script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.runtime.docker import verify_report_bind as mod

pytestmark = pytest.mark.unit

from bioetl.application.services.run_reports.paths import (
    REPORT_ROOT_MARKER_NAME,
    REPORT_ROOT_MARKER_VALUE,
    write_report_root_source_identity,
)


def _attest_reports(tmp_path: Path, *, source_id: str | None = None) -> str:
    expected = (
        source_id
        or mod._expected_runtime_environment(tmp_path)["BIOETL_RUNTIME_SOURCE_ID"]
    )
    write_report_root_source_identity(
        report_root=tmp_path / "reports" / "run-reports",
        source_id=expected,
    )
    return expected


def test_host_report_root_ignores_container_bioetl_report_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIOETL_REPORT_ROOT", "/app/reports/run-reports")
    monkeypatch.delenv("BIOETL_DASHBOARD_REPORT_ROOT", raising=False)
    root = mod._host_report_root(tmp_path)
    assert root == (tmp_path / "reports" / "run-reports").resolve()
    assert mod._looks_like_container_path("/app/reports/run-reports") is True
    assert (
        mod._looks_like_container_path(r"C:\Program Files\Git\app\reports\run-reports")
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


def test_docker_identity_inspect_prefers_env_and_records_label_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment_identity = "a" * 64
    label_identity = "b" * 64
    payload = json.dumps(
        {
            "environment": [
                "IGNORED=value",
                f"BIOETL_RUNTIME_SOURCE_ID={environment_identity}",
            ],
            "label": label_identity,
        }
    )
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *_args, **_kwargs: mod.subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=payload,
            stderr="",
        ),
    )

    resolution = mod._docker_inspect_source_identity("bioetl")

    assert resolution is not None
    assert resolution.value == environment_identity
    assert resolution.source == "container_environment"
    assert resolution.conflicts == ("container_label",)


def test_verify_host_marker_ok_without_ops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    (reports / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_VALUE + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    _attest_reports(tmp_path)
    monkeypatch.setattr(mod, "_docker_inspect_mounts", lambda _name: None)
    monkeypatch.setattr(mod, "_docker_inspect_source_identity", lambda _name: None)
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
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    monkeypatch.setattr(mod, "_docker_inspect_mounts", lambda _name: None)
    monkeypatch.setattr(mod, "_docker_inspect_source_identity", lambda _name: None)
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
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    (reports / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_VALUE + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    expected_source_id = _attest_reports(tmp_path)
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
        "_docker_inspect_source_identity",
        lambda _name: expected_source_id,
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
                        "source_identity_status": "unhealthy",
                    }
                },
            }
            if url.endswith("/health/ready")
            else {
                "status": "ok",
                "count": 0,
                "marker_status": "unhealthy",
                "source_identity_status": "unhealthy",
                "items": [],
            }
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


def test_verify_accepts_exact_mount_identity_and_newest_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    target = (
        run_reports / "pipeline" / "chembl_assay" / "run-a" / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
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
    (reports / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_VALUE + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    expected_source_id = _attest_reports(tmp_path)
    monkeypatch.setattr(
        mod,
        "_docker_inspect_mounts",
        lambda _name: [{"Destination": "/app/reports", "Source": str(reports)}],
    )
    monkeypatch.setattr(
        mod,
        "_docker_inspect_source_identity",
        lambda _name: expected_source_id,
    )

    def ops_payload(url: str, **_kwargs: object) -> dict[str, object]:
        if url.endswith("/health/ready"):
            return {
                "status": "healthy",
                "checks": {
                    "report_root": {
                        "status": "healthy",
                        "layout_status": "healthy",
                        "source_identity_status": "healthy",
                        "source_identity_actual": expected_source_id,
                    }
                },
            }
        return {
            "status": "ok",
            "count": 1,
            "marker_status": "healthy",
            "source_identity_status": "healthy",
            "source_identity_actual": expected_source_id,
            "items": [{"run_id": "run-a"}],
        }

    monkeypatch.setattr(mod, "_json_get", ops_payload)

    assert (
        mod.verify(
            repo=tmp_path,
            ops_url="http://127.0.0.1:8000",
            container="bioetl",
            pipeline="chembl_assay",
            require_ops=True,
        )
        == 0
    )


@pytest.mark.parametrize(
    "container_path",
    [
        "E:/github/BioactivityDataAcquisition/reports",
        r"E:\github\BioactivityDataAcquisition\reports",
        "/run/desktop/mnt/host/e/github/BioactivityDataAcquisition/reports",
        "/host_mnt/e/github/BioactivityDataAcquisition/reports",
    ],
)
def test_paths_equivalent_normalizes_windows_wsl_and_desktop(
    container_path: str,
) -> None:
    assert mod._paths_equivalent(
        container_path,
        Path("/mnt/e/github/BioactivityDataAcquisition/reports"),
    )


@pytest.mark.parametrize("with_report", [False, True])
def test_verify_fails_foreign_source_even_when_report_counts_do_not_reveal_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    with_report: bool,
) -> None:
    reports = tmp_path / "reports"
    run_reports = reports / "run-reports"
    run_reports.mkdir(parents=True)
    (reports / REPORT_ROOT_MARKER_NAME).write_text(
        REPORT_ROOT_MARKER_VALUE + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(reports))
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(run_reports))
    expected_source_id = mod._expected_runtime_environment(tmp_path)[
        "BIOETL_RUNTIME_SOURCE_ID"
    ]
    foreign_source_id = "f" * 64
    _attest_reports(tmp_path, source_id=foreign_source_id)
    if with_report:
        target = (
            run_reports
            / "pipeline"
            / "chembl_assay"
            / "run-a"
            / "pipeline-run-report.json"
        )
        target.parent.mkdir(parents=True)
        target.write_text(
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
    monkeypatch.setattr(
        mod,
        "_docker_inspect_mounts",
        lambda _name: [{"Destination": "/app/reports", "Source": str(reports)}],
    )
    monkeypatch.setattr(
        mod,
        "_docker_inspect_source_identity",
        lambda _name: foreign_source_id,
    )

    def ops_payload(url: str, **_kwargs: object) -> dict[str, object]:
        if url.endswith("/health/ready"):
            return {
                "status": "unhealthy",
                "checks": {
                    "report_root": {
                        "status": "unhealthy",
                        "layout_status": "healthy",
                        "source_identity_status": "unhealthy",
                        "source_identity_actual": foreign_source_id,
                    }
                },
            }
        return {
            "status": "ok",
            "count": int(with_report),
            "marker_status": "healthy",
            "source_identity_status": "unhealthy",
            "source_identity_actual": foreign_source_id,
            "items": [{"run_id": "run-a"}] if with_report else [],
        }

    monkeypatch.setattr(mod, "_json_get", ops_payload)

    rc = mod.verify(
        repo=tmp_path,
        ops_url="http://127.0.0.1:8000",
        container="bioetl",
        pipeline="chembl_assay",
        require_ops=True,
    )

    assert expected_source_id != foreign_source_id
    assert rc == 1
