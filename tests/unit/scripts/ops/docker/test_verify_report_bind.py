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
from bioetl.composition.observability_runtime import create_run_report_store


def _attest_reports(tmp_path: Path, *, source_id: str | None = None) -> str:
    expected = (
        source_id
        or mod._expected_runtime_environment(tmp_path)["BIOETL_RUNTIME_SOURCE_ID"]
    )
    write_report_root_source_identity(
        report_root=tmp_path / "reports" / "run-reports",
        source_id=expected,
        store=create_run_report_store(),
    )
    return expected


def test_security_guards_reject_remote_urls_and_shell_like_container_names() -> None:
    with pytest.raises(ValueError, match="non-local URL host"):
        mod._json_get("https://example.com/health/ready")
    with pytest.raises(ValueError, match="invalid Docker container name"):
        mod._docker_inspect_mounts("bioetl;touch-pwned")


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


def test_host_report_root_follows_dashboard_report_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active_reports = tmp_path / "active-checkout" / "reports"
    monkeypatch.setenv("BIOETL_REPORT_ROOT", "/app/reports/run-reports")
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(active_reports))

    assert mod._host_report_root(tmp_path) == (active_reports / "run-reports").resolve()


def test_ready_timeout_with_live_up_is_warning_when_bind_aligned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, *, timeout: float = 5.0):
        if url.endswith("/health/live"):
            return {"status": "healthy"}
        return None

    monkeypatch.setattr(mod, "_json_get", fake_get)
    state = mod._VerificationState()
    mod._verify_ready_endpoint(
        state,
        ops_url="http://127.0.0.1:8000",
        expected_source_id="a" * 64,
        require_ops=True,
        bind_aligned=True,
    )
    assert state.ok is True
    assert any("timed out" in line for line in state.findings)

    state2 = mod._VerificationState()
    mod._verify_pipeline_endpoint(
        state2,
        ops_url="http://127.0.0.1:8000",
        pipeline="chembl_assay",
        expected_source_id="a" * 64,
        host_count=3,
        host_latest_run_id="run-a",
        require_ops=True,
        bind_aligned=True,
    )
    assert state2.ok is True
    assert any("timed out" in line for line in state2.findings)


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


def _seed_aligned_host_with_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Host marker + one chembl_assay report + matching docker mount/identity."""
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
    return expected_source_id


def _aligned_list_ops_payload(
    expected_source_id: str,
    *,
    selected_run: dict[str, object] | None = None,
):
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
        if selected_run is not None and "selected-run-status" in url:
            return selected_run
        return {
            "status": "ok",
            "count": 1,
            "marker_status": "healthy",
            "source_identity_status": "healthy",
            "source_identity_actual": expected_source_id,
            "items": [{"run_id": "run-a"}],
        }

    return ops_payload


def test_verify_accepts_exact_mount_identity_and_newest_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_source_id = _seed_aligned_host_with_run(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "_json_get", _aligned_list_ops_payload(expected_source_id))

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


def test_host_pipeline_summary_reads_composed_store(tmp_path: Path) -> None:
    report = (
        tmp_path / "pipeline" / "chembl_activity" / "run-a" / "pipeline-run-report.json"
    )
    report.parent.mkdir(parents=True)
    report.write_text('{"identity": {"status": "success"}}', encoding="utf-8")
    state = mod._VerificationState()
    assert mod._host_pipeline_summary(
        state, pipeline="chembl_activity", host_root=tmp_path
    ) == (1, "run-a")
    assert state.ok


def _ready_selected_run_payload() -> dict[str, object]:
    """Use the producer's replay projection and HTTP presentation shape."""
    from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
        project_selected_run_replay_readiness,
    )
    from bioetl.interfaces.http._selected_run_presentation import _readiness_fields

    hashes = (
        "effective_config_hash",
        "dependency_lock_hash",
        "input_snapshot_fingerprint",
    )
    projection = project_selected_run_replay_readiness(
        identity={"run_id": "run-a", "pipeline": "chembl_assay", "status": "success"},
        manifest={
            **dict.fromkeys(hashes, "recorded"),
            "objects": dict.fromkeys(hashes, True),
            "replay_capability": "exact_replay_supported",
        },
        artifact_probes=[
            {"code": "pipeline_run_report_json", "result": "pass", "reason": "present"},
        ],
        inventory_present=True,
    )
    return {
        "verdict": "OK",
        "evidence_completeness": "COMPLETE",
        **_readiness_fields(projection),
    }


def test_verify_run_id_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_source_id = _seed_aligned_host_with_run(tmp_path, monkeypatch)
    monkeypatch.setattr(
        mod,
        "_json_get",
        _aligned_list_ops_payload(
            expected_source_id,
            selected_run=_ready_selected_run_payload(),
        ),
    )

    assert (
        mod.verify(
            repo=tmp_path,
            ops_url="http://127.0.0.1:8000",
            container="bioetl",
            pipeline="chembl_assay",
            require_ops=True,
            run_id="run-a",
        )
        == 0
    )


def _mutate_readiness_verdict(payload: dict[str, object]) -> None:
    readiness = payload["replay_readiness"]
    assert isinstance(readiness, list)
    row = readiness[0]
    assert isinstance(row, dict)
    row["verdict"] = "INSUFFICIENT"


def _mutate_evidence_completeness(payload: dict[str, object]) -> None:
    payload["evidence_completeness"] = "INCOMPLETE"


def _mutate_empty_replay_readiness(payload: dict[str, object]) -> None:
    payload["replay_readiness"] = []


def _mutate_non_ready_domain(payload: dict[str, object]) -> None:
    readiness = payload["replay_readiness"]
    assert isinstance(readiness, list)
    row = readiness[0]
    assert isinstance(row, dict)
    row["domain_verdict"] = "blocked"


def _mutate_manifest_not_recorded(payload: dict[str, object]) -> None:
    # Tip contract: missing manifest is a replay_checks unknown, not top-level
    # manifest_present (Jules/CodeRabbit invented field — not on selected-run-status).
    payload["replay_checks"] = [
        {
            "code": "manifest_not_recorded",
            "result": "unknown",
            "reason": "manifest_not_recorded",
        }
    ]


def _mutate_missing_manifest_checks(payload: dict[str, object]) -> None:
    payload["replay_checks"] = []


def _mutate_corrupt_object_check(payload: dict[str, object]) -> None:
    # Recorded object verification reports failed hashes through replay_checks.
    checks = payload["replay_checks"]
    assert isinstance(checks, list)
    check = next(item for item in checks if item["code"] == "effective_config_hash")
    check.update(result="fail", reason="hash_without_object")


def _mutate_location_missing_check(payload: dict[str, object]) -> None:
    # Resolver refusal is represented by the top-level reason.
    payload["reason"] = "location_missing"


@pytest.mark.parametrize(
    ("mutate", "fail_needle"),
    [
        (_mutate_readiness_verdict, "replay_readiness is not READY"),
        (_mutate_evidence_completeness, "evidence_completeness is not COMPLETE"),
        (_mutate_empty_replay_readiness, "no replay_readiness found"),
        (_mutate_non_ready_domain, "domain_verdict is not exact_replay_ready"),
        (_mutate_manifest_not_recorded, "replay_checks unknown"),
        (_mutate_missing_manifest_checks, "manifest checks not passed"),
        (_mutate_corrupt_object_check, "corrupt real objects"),
        (_mutate_location_missing_check, "missing location"),
    ],
    ids=[
        "verdict",
        "evidence_completeness",
        "empty_replay_readiness",
        "domain_verdict",
        "manifest_via_replay_checks",
        "missing_manifest_checks",
        "corrupt_via_replay_checks",
        "location_reason",
    ],
)
def test_verify_run_id_negative_selected_run_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate,
    fail_needle: str,
) -> None:
    """One-field regressions against the real selected-run-status contract."""
    expected_source_id = _seed_aligned_host_with_run(tmp_path, monkeypatch)
    payload = _ready_selected_run_payload()
    mutate(payload)
    monkeypatch.setattr(
        mod,
        "_json_get",
        _aligned_list_ops_payload(expected_source_id, selected_run=payload),
    )

    assert (
        mod.verify(
            repo=tmp_path,
            ops_url="http://127.0.0.1:8000",
            container="bioetl",
            pipeline="chembl_assay",
            require_ops=False,
            run_id="run-a",
        )
        == 1
    )

    state = mod._VerificationState()
    mod._verify_run_id_endpoint(
        state,
        ops_url="http://127.0.0.1:8000",
        pipeline="chembl_assay",
        run_id="run-a",
        require_ops=False,
        bind_aligned=True,
    )
    assert state.ok is False
    assert any(fail_needle in line for line in state.findings), state.findings


@pytest.mark.parametrize("require_ops", [False, True])
def test_verify_run_id_fails_when_endpoint_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    require_ops: bool,
) -> None:
    """Explicit --run-id fails closed when selected-run-status is unreachable."""
    expected_source_id = _seed_aligned_host_with_run(tmp_path, monkeypatch)

    def ops_payload(url: str, **_kwargs: object) -> dict[str, object] | None:
        if "selected-run-status" in url:
            return None
        return _aligned_list_ops_payload(expected_source_id)(url)

    monkeypatch.setattr(mod, "_json_get", ops_payload)
    assert (
        mod.verify(
            repo=tmp_path,
            ops_url="http://127.0.0.1:8000",
            container="bioetl",
            pipeline="chembl_assay",
            require_ops=require_ops,
            run_id="run-a",
        )
        == 1
    )

    state = mod._VerificationState()
    mod._verify_run_id_endpoint(
        state,
        ops_url="http://127.0.0.1:8000",
        pipeline="chembl_assay",
        run_id="run-a",
        require_ops=require_ops,
        bind_aligned=True,
    )
    assert state.ok is False
    assert any(
        "selected-run-status endpoint unreachable" in line for line in state.findings
    ), state.findings


def test_verify_run_id_requires_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_aligned_host_with_run(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "_json_get", lambda _url, **_kw: None)
    state = mod._VerificationState()
    mod._verify_run_id_endpoint(
        state,
        ops_url="http://127.0.0.1:8000",
        pipeline=None,
        run_id="run-a",
        require_ops=False,
        bind_aligned=True,
    )
    assert state.ok is False
    assert any("--run-id requires --pipeline" in line for line in state.findings)
