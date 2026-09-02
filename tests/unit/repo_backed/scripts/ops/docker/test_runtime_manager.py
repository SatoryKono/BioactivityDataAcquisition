# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.ops.runtime.docker import runtime_manager

pytestmark = pytest.mark.repo_backed


def _spec(
    *, expected_images: dict[str, str] | None = None
) -> runtime_manager.StackSpec:
    return runtime_manager.StackSpec(
        name="main",
        project="bioetl-main",
        compose_file=Path("docker-compose.yml"),
        required_services=("bioetl",),
        expected_images=(
            expected_images
            if expected_images is not None
            else {"bioetl": "bioetl:test@sha256:expected"}
        ),
    )


def _monitoring_spec() -> runtime_manager.StackSpec:
    return runtime_manager.StackSpec(
        name="monitoring",
        project="bioetl-monitoring",
        compose_file=Path("docker-compose.monitoring.yml"),
        required_services=("prometheus", "pushgateway", "grafana"),
        expected_images={"grafana": "grafana/grafana:test@sha256:expected"},
    )


def test_direct_script_help_bootstraps_repository_imports(tmp_path: Path) -> None:
    script = Path(runtime_manager.__file__).resolve()

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "ensure-networks" in result.stdout


def test_windows_entrypoint_uses_shared_process_local_env_loader() -> None:
    wrapper = (runtime_manager.ROOT / "scripts/ops/docker-setup.ps1").read_text(
        encoding="utf-8"
    )

    assert "scripts/ai/mcp/support/load_repo_env.ps1" in wrapper
    assert '$env:BIOETL_SKIP_ENV_LOCAL = "1"' in wrapper
    assert "Import-BioetlRepoEnv -RepoRoot $ProjectRoot" in wrapper
    assert ".venv-win/Scripts/python.exe" in wrapper
    assert '"ensure-networks"' in wrapper
    assert '"grafana-preflight"' in wrapper
    assert "SetEnvironmentVariable" not in wrapper
    assert "Set-Content" not in wrapper
    assert "Add-Content" not in wrapper


@pytest.mark.parametrize("action", ["start", "recover"])
def test_failed_start_or_recover_prints_redacted_bounded_json_summary(
    action: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "docker-incident-main.json"
    runtime_manager.write_report(
        report,
        {
            "primary_cause": "preflight_failed",
            "token": "ghp_abcdefghijklmnop",
        },
    )
    monkeypatch.setattr(
        runtime_manager,
        "_materialize_report_source_identity",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        runtime_manager,
        "start_or_recover",
        lambda *_args, **_kwargs: 1,
    )
    args = SimpleNamespace(
        action=action,
        timeout=180.0,
        max_attempts=3,
        poll_interval=2.0,
        stabilization_seconds=5.0,
        allow_transient_origin=True,
    )

    result = runtime_manager._dispatch_action(
        args,
        spec=_spec(),
        contract_path=Path("contract.yml"),
        report_dir=tmp_path,
        runner=lambda command, cwd, timeout: runtime_manager.CommandResult(
            list(command), 0
        ),
    )

    assert result == 1
    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload == {
        "action": action,
        "ok": False,
        "primary_cause": "preflight_failed",
        "report": str(report),
        "stack": "main",
    }
    assert "ghp_" not in output
    assert len(output) < 1000


def test_dashboard_runtime_environment_is_scoped_and_managed(tmp_path: Path) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
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
            }
        ),
        encoding="utf-8",
    )
    previous = os.environ.get("BIOETL_RUNTIME_SOURCE_ID")
    stale_process_identity = "f" * 64
    os.environ["BIOETL_RUNTIME_SOURCE_ID"] = stale_process_identity
    try:
        with runtime_manager._dashboard_runtime_environment(contract) as environment:
            assert len(environment["BIOETL_RUNTIME_SOURCE_ID"]) == 64
            assert environment["BIOETL_RUNTIME_SOURCE_ID"] != stale_process_identity
            assert (
                os.environ["BIOETL_RUNTIME_SOURCE_ID"]
                == environment["BIOETL_RUNTIME_SOURCE_ID"]
            )
        assert os.environ["BIOETL_RUNTIME_SOURCE_ID"] == stale_process_identity
    finally:
        if previous is None:
            os.environ.pop("BIOETL_RUNTIME_SOURCE_ID", None)
        else:
            os.environ["BIOETL_RUNTIME_SOURCE_ID"] = previous


def test_main_start_materializes_source_bound_report_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
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
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "reports" / "run-reports").mkdir(parents=True)
    monkeypatch.setattr(runtime_manager, "ROOT", tmp_path)
    monkeypatch.delenv("BIOETL_DASHBOARD_DATA_ROOT", raising=False)
    monkeypatch.delenv("BIOETL_DASHBOARD_REPORT_ROOT", raising=False)

    target = runtime_manager._materialize_report_source_identity(
        spec=_spec(),
        contract_path=contract,
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    expected = runtime_manager.runtime_preflight.dashboard_source_environment(
        tmp_path,
        yaml.safe_load(contract.read_text(encoding="utf-8")),
    )["BIOETL_RUNTIME_SOURCE_ID"]

    assert target == tmp_path / "reports" / ".bioetl-report-source.json"
    assert payload == {
        "schema_version": "bioetl-report-source-v1",
        "runtime_source_id": expected,
    }
    mode = target.stat().st_mode
    assert mode & stat.S_IRUSR
    if os.name != "nt":
        assert mode & 0o777 == 0o644


def test_reject_transient_origin_blocks_issue_worktree(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "contract.yaml"
    contract.write_text(
        yaml.safe_dump(
            {
                "path_policy": {
                    "discouraged_compose_working_dir_prefixes": ["/tmp/bioetl-issues"]
                }
            }
        ),
        encoding="utf-8",
    )
    blocked = runtime_manager._reject_transient_origin(
        contract_path=contract,
        root=Path("/tmp/bioetl-issues-8860-8861"),
        allow=False,
    )
    allowed = runtime_manager._reject_transient_origin(
        contract_path=contract,
        root=Path("/tmp/bioetl-issues-8860-8861"),
        allow=True,
    )
    canonical = runtime_manager._reject_transient_origin(
        contract_path=contract,
        root=tmp_path,
        allow=False,
    )

    assert blocked is not None
    assert blocked["code"] == "TRANSIENT_ORIGIN"
    assert allowed is None
    assert canonical is None


def test_live_transient_origin_is_recoverable_from_canonical_start(
    tmp_path: Path,
) -> None:
    """Live leftover compose must not block start from the canonical checkout."""
    report = tmp_path / "preflight.json"
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "TRANSIENT_ORIGIN",
                        "severity": "error",
                        "evidence": {"stack": "main"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert (
        runtime_manager._preflight_errors_are_recoverable(report, stack="main") is True
    )
    spec = _spec()
    assert runtime_manager._preflight_requires_force_recreate(report, spec) is True


def test_post_start_source_gate_failure_cannot_report_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.ops.runtime.docker import verify_report_bind

    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(verify_report_bind, "verify", lambda **_kwargs: 1)

    result = runtime_manager._post_start_report_bind_gate(
        spec=_spec(),
        report_dir=tmp_path,
    )

    assert result == 1
    incident = json.loads(
        (tmp_path / "docker-incident-main.json").read_text(encoding="utf-8")
    )
    assert incident["primary_cause"] == "report_bind_mismatch"


def test_grafana_bootstrap_timeout_retry_restarts_when_identity_now_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    source_id = "a" * 64
    deferred = {
        "ops_http": "deferred",
        "reason": "identity_timeout_or_unreachable",
        "dashboard_profile": "prometheus_only",
    }
    ready = {
        "ops_http": "ready",
        "reason": "identity_matched",
        "dashboard_profile": "full",
    }
    commands: list[list[str]] = []
    status_reads = {"n": 0}

    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        commands.append(list(cmd))
        if cmd[:3] == ["docker", "exec", "bioetl-grafana"] and cmd[3] == "cat":
            status_reads["n"] += 1
            payload = deferred if status_reads["n"] == 1 else ready
            return runtime_manager.CommandResult(
                list(cmd), 0, stdout=json.dumps(payload)
            )
        if cmd[:4] == ["docker", "exec", "bioetl-grafana", "printenv"]:
            return runtime_manager.CommandResult(list(cmd), 0, stdout=source_id + "\n")
        if cmd[:4] == ["docker", "exec", "bioetl-grafana", "wget"]:
            return runtime_manager.CommandResult(
                list(cmd),
                0,
                stdout=json.dumps({"runtime_source_id": source_id}),
            )
        if cmd[:2] == ["docker", "restart"]:
            return runtime_manager.CommandResult(list(cmd), 0)
        raise AssertionError(f"unexpected {cmd}")

    result = runtime_manager._post_start_grafana_bootstrap_gate(
        spec=_monitoring_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )

    assert result == 0
    assert ["docker", "restart", "bioetl-grafana"] in commands


def test_grafana_bootstrap_timeout_retry_skips_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    commands: list[list[str]] = []

    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        commands.append(list(cmd))
        if cmd[:3] == ["docker", "exec", "bioetl-grafana"] and cmd[3] == "cat":
            return runtime_manager.CommandResult(
                list(cmd),
                0,
                stdout=json.dumps(
                    {
                        "ops_http": "deferred",
                        "reason": "identity_mismatch",
                        "dashboard_profile": "prometheus_only",
                    }
                ),
            )
        raise AssertionError(f"unexpected {cmd}")

    result = runtime_manager._post_start_grafana_bootstrap_gate(
        spec=_monitoring_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )

    assert result == 0
    assert not any(cmd[:2] == ["docker", "restart"] for cmd in commands)


def test_grafana_bootstrap_timeout_retry_skips_non_monitoring_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        raise AssertionError(f"unexpected {cmd}")

    result = runtime_manager._post_start_grafana_bootstrap_gate(
        spec=_spec(),
        runner=runner,
        timeout=5.0,
    )
    assert result == 0


def test_grafana_bootstrap_timeout_retry_caps_status_poll_timeout_to_remaining_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    source_id = "b" * 64
    deferred = {
        "ops_http": "deferred",
        "reason": "identity_timeout_or_unreachable",
        "dashboard_profile": "prometheus_only",
    }
    now = [0.0]
    restarted = {"done": False}
    post_restart_status_timeouts: list[float] = []

    def runner(cmd: Sequence[str], _cwd: Path, timeout: float):
        if cmd[:3] == ["docker", "exec", "bioetl-grafana"] and cmd[3] == "cat":
            if restarted["done"]:
                post_restart_status_timeouts.append(timeout)
            return runtime_manager.CommandResult(
                list(cmd), 0, stdout=json.dumps(deferred)
            )
        if cmd[:4] == ["docker", "exec", "bioetl-grafana", "printenv"]:
            return runtime_manager.CommandResult(list(cmd), 0, stdout=source_id + "\n")
        if cmd[:4] == ["docker", "exec", "bioetl-grafana", "wget"]:
            return runtime_manager.CommandResult(
                list(cmd),
                0,
                stdout=json.dumps({"runtime_source_id": source_id}),
            )
        if cmd[:2] == ["docker", "restart"]:
            restarted["done"] = True
            return runtime_manager.CommandResult(list(cmd), 0)
        raise AssertionError(f"unexpected {cmd}")

    result = runtime_manager._post_start_grafana_bootstrap_gate(
        spec=_monitoring_spec(),
        runner=runner,
        timeout=1.0,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )

    assert result == 0
    assert post_restart_status_timeouts
    assert all(timeout <= 1.0 for timeout in post_restart_status_timeouts)


def test_preflight_errors_are_recoverable_for_dashboard_and_cross_stack(
    tmp_path: Path,
) -> None:
    report = tmp_path / "preflight.json"
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "DASHBOARD_SOURCE_MOUNT",
                        "severity": "error",
                        "evidence": {"stack": "main", "target": "/app/reports"},
                    },
                    {
                        "code": "PROJECT_ORIGIN",
                        "severity": "error",
                        "evidence": {"stack": "monitoring"},
                    },
                    {
                        "code": "F003",
                        "severity": "error",
                        "evidence": {"actual_owner": "neo4j/neo4j", "port": 7474},
                    },
                    {
                        "code": "MOUNT_ORIGIN",
                        "severity": "error",
                        "evidence": {"stack": "main"},
                    },
                    {
                        "code": "CAPACITY_DOCKER_ROOT",
                        "severity": "error",
                        "evidence": {},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    assert (
        runtime_manager._preflight_errors_are_recoverable(report, stack="main") is True
    )


def test_compose_up_force_recreates_main_stack_on_first_attempt() -> None:
    start = runtime_manager._compose_up_start_args(
        _spec(), attempts=1, force_recreate=True
    )
    assert "--force-recreate" in start
    wait = runtime_manager._compose_up_wait_args(
        _spec(), attempts=1, remaining=30.0, force_recreate=True
    )
    assert "--force-recreate" in wait


def test_monitoring_project_origin_drift_requires_force_recreate(
    tmp_path: Path,
) -> None:
    report = tmp_path / "preflight.json"
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "PROJECT_ORIGIN",
                        "severity": "error",
                        "evidence": {"project": "bioetl-main"},
                    },
                    {
                        "code": "PROJECT_ORIGIN",
                        "severity": "error",
                        "evidence": {"project": "bioetl-monitoring"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monitoring = runtime_manager.StackSpec(
        name="monitoring",
        project="bioetl-monitoring",
        compose_file=Path("docker-compose.monitoring.yml"),
        required_services=("grafana",),
        expected_images={},
    )

    assert runtime_manager._preflight_requires_force_recreate(report, monitoring)


def test_status_origin_findings_exposes_dashboard_source_drift(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "preflight.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "DASHBOARD_SOURCE_MOUNT",
                        "severity": "error",
                        "message": "wrong root",
                        "evidence": {"target": "/app/data"},
                    },
                    {
                        "code": "CAPACITY_DISK",
                        "severity": "error",
                        "message": "unrelated",
                        "evidence": {},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    findings = runtime_manager._status_origin_findings(
        report_path,
        runtime_manager.CommandResult(["preflight"], 2),
        _spec(),
    )

    assert findings == [
        {
            "cause": "dashboard_source_drift",
            "code": "DASHBOARD_SOURCE_MOUNT",
            "message": "wrong root",
            "evidence": {"target": "/app/data"},
        }
    ]


def test_status_origin_findings_ignore_foreign_stack_projects(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "preflight.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "PROJECT_ORIGIN",
                        "severity": "error",
                        "message": "main is foreign",
                        "evidence": {"project": "bioetl-main"},
                    },
                    {
                        "code": "PROJECT_ORIGIN",
                        "severity": "error",
                        "message": "monitoring is foreign",
                        "evidence": {"project": "bioetl-monitoring"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monitoring = runtime_manager.StackSpec(
        name="monitoring",
        project="bioetl-monitoring",
        compose_file=Path("docker-compose.monitoring.yml"),
        required_services=("grafana",),
        expected_images={},
    )

    findings = runtime_manager._status_origin_findings(
        report_path,
        runtime_manager.CommandResult(["preflight"], 2),
        monitoring,
    )

    assert [finding["message"] for finding in findings] == ["monitoring is foreign"]


def test_status_origin_findings_fail_closed_for_foreign_clone_on_selected_stack(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "preflight.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "PROJECT_ORIGIN",
                        "severity": "error",
                        "message": "Live Compose project originates from an unexpected config path",
                        "evidence": {
                            "project": "bioetl-main",
                            "expected": (
                                "/mnt/e/github/bioactivitydataacquisition/"
                                "docker-compose.yml"
                            ),
                            "actual": [
                                "/mnt/e/g-drive/05_ai/github/"
                                "bioactivitydataacquisition2/docker-compose.yml"
                            ],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    findings = runtime_manager._status_origin_findings(
        report_path,
        runtime_manager.CommandResult(["preflight"], 2),
        _spec(),
    )
    assert findings
    assert findings[0]["code"] == "PROJECT_ORIGIN"
    assert "unexpected config path" in str(findings[0]["message"])


def _neo4j_spec() -> runtime_manager.StackSpec:
    return runtime_manager.StackSpec(
        name="neo4j",
        project="bioetl-neo4j",
        compose_file=Path("docker-compose.neo4j.yml"),
        required_services=("neo4j",),
        expected_images={"neo4j": "neo4j:5.15-community@sha256:0123456789abcdef"},
    )


def test_reseed_neo4j_auth_skips_missing_volume() -> None:
    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        if cmd[:3] == ["docker", "volume", "inspect"]:
            return runtime_manager.CommandResult(list(cmd), 1, stderr="missing")
        return runtime_manager.CommandResult(list(cmd), 0)

    assert (
        runtime_manager._reseed_neo4j_auth_volume(
            _neo4j_spec(), runner=runner, timeout=30.0
        )
        is None
    )


def test_reseed_neo4j_auth_clears_files_on_existing_volume() -> None:
    seen: list[list[str]] = []

    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        seen.append(list(cmd))
        return runtime_manager.CommandResult(list(cmd), 0, stdout="cleared")

    result = runtime_manager._reseed_neo4j_auth_volume(
        _neo4j_spec(), runner=runner, timeout=30.0
    )
    assert result is not None
    assert result.returncode == 0
    run_cmds = [cmd for cmd in seen if cmd[:2] == ["docker", "run"]]
    assert run_cmds
    assert "bioetl-neo4j_neo4j_data:/data" in run_cmds[0]
    assert (
        "rm -f /data/dbms/auth /data/dbms/auth.ini /data/databases/store_lock"
        in (run_cmds[0])
    )


def test_reseed_neo4j_auth_is_noop_for_other_stacks() -> None:
    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        raise AssertionError(f"unexpected {cmd}")

    assert (
        runtime_manager._reseed_neo4j_auth_volume(_spec(), runner=runner, timeout=5.0)
        is None
    )


def test_status_grafana_bootstrap_deferred_is_finding() -> None:
    findings = runtime_manager._status_grafana_bootstrap_findings(
        {
            "ops_http": "deferred",
            "reason": "identity_mismatch",
            "dashboard_profile": "prometheus_only",
        },
        readable=True,
        grafana_running=True,
    )
    assert findings
    assert findings[0]["ops_http"] == "deferred"
    assert findings[0]["reason"] == "identity_mismatch"
    assert findings[0]["code"] == "GRAFANA_OPS_HTTP_BOOTSTRAP"
    assert findings[0]["dashboard_profile"] == "prometheus_only"
    assert (
        "static Prometheus-only dashboard notices are active" in findings[0]["message"]
    )


def test_status_grafana_bootstrap_ready_has_no_finding() -> None:
    findings = runtime_manager._status_grafana_bootstrap_findings(
        {
            "ops_http": "ready",
            "reason": "identity_matched",
            "dashboard_profile": "full",
        },
        readable=True,
        grafana_running=True,
    )
    assert findings == []


def test_status_grafana_bootstrap_ready_reports_non_full_profile() -> None:
    findings = runtime_manager._status_grafana_bootstrap_findings(
        {
            "ops_http": "ready",
            "reason": "identity_matched",
            "dashboard_profile": "failed",
        },
        readable=True,
        grafana_running=True,
    )

    assert findings[0]["code"] == "GRAFANA_DASHBOARD_PROFILE"
    assert findings[0]["dashboard_profile"] == "failed"


def test_status_grafana_bootstrap_ignored_when_grafana_stopped() -> None:
    findings = runtime_manager._status_grafana_bootstrap_findings(
        {"ops_http": "deferred", "reason": "identity_mismatch"},
        readable=True,
        grafana_running=False,
    )
    assert findings == []


def test_readiness_fails_on_restart_oom_and_image_drift() -> None:
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=1,
        oom_killed=True,
        image="bioetl:test@sha256:actual",
    )

    findings = runtime_manager.readiness_findings(_spec(), [snapshot], baseline={})

    assert {finding["cause"] for finding in findings} == {
        "oom_killed",
        "unexpected_restart",
        "image_identity_drift",
    }


def test_readiness_accepts_matching_repo_digest_when_config_reference_differs() -> None:
    spec = _spec(expected_images={"bioetl": "bioetl:test@sha256:" + "a" * 64})
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=0,
        oom_killed=False,
        image="sha256:container-image-id",
        image_digests=("bioetl:test@sha256:" + "a" * 64,),
    )

    assert runtime_manager.readiness_findings(spec, [snapshot], baseline={}) == []


def test_readiness_accepts_build_only_service_without_expected_image() -> None:
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=0,
        oom_killed=False,
        image="bioetl-main-bioetl:local",
    )

    assert (
        runtime_manager.readiness_findings(
            _spec(expected_images={}), [snapshot], baseline={}
        )
        == []
    )


def test_collect_snapshots_resolves_repo_digests_from_real_container_shape() -> None:
    spec = _spec(expected_images={"bioetl": "bioetl:test@sha256:" + "a" * 64})
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        if "compose" in current and "ps" in current:
            assert runtime_manager._COMPOSE_PS_LEAN_FORMAT in current
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps([{"ID": "abcdef123456", "Service": "bioetl"}]),
            )
        if current[:2] == ["docker", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "State": {
                            "Status": "running",
                            "OOMKilled": False,
                            "Health": {"Status": "healthy"},
                        },
                        "RestartCount": 0,
                        "Image": "bioetl:test",
                        "ImageID": "sha256:exact-image-id",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": ["bioetl:test@sha256:" + "a" * 64]}),
            )
        raise AssertionError(current)

    snapshots, observations = runtime_manager.collect_snapshots(spec, runner=runner)

    assert len(snapshots) == 1
    assert snapshots[0].image == "bioetl:test"
    assert snapshots[0].image_digests == ("bioetl:test@sha256:" + "a" * 64,)
    assert runtime_manager.readiness_findings(spec, snapshots, baseline={}) == []
    assert len(observations) == 3
    container_template = calls[1][calls[1].index("--format") + 1]
    assert ".RepoDigests" not in container_template
    assert calls[2][:3] == ["docker", "image", "inspect"]


def test_collect_snapshots_parses_ndjson_even_when_full_json_would_truncate() -> None:
    """Regression: full compose ps JSON with Labels exceeds _bounded(4000)."""
    fat_label_row = {
        "ID": "aaaaaaaaaaaa",
        "Service": "grafana",
        "Name": "bioetl-grafana",
        "State": "running",
        "Health": "healthy",
        "Image": "grafana/grafana:12.0.0",
        "Labels": "x" * 5000,
    }
    lean_rows = [
        {
            "ID": "bbbbbbbbbbbb",
            "Service": "prometheus",
            "Name": "bioetl-prometheus",
            "State": "running",
            "Health": "healthy",
            "Image": "prom/prometheus:v3",
        },
        {
            "ID": "cccccccccccc",
            "Service": "pushgateway",
            "Name": "bioetl-pushgateway",
            "State": "running",
            "Health": "healthy",
            "Image": "prom/pushgateway:v1",
        },
        {
            "ID": "dddddddddddd",
            "Service": "renderer",
            "Name": "bioetl-renderer",
            "State": "running",
            "Health": "healthy",
            "Image": "grafana/grafana-image-renderer",
        },
        {
            "ID": "aaaaaaaaaaaa",
            "Service": "grafana",
            "Name": "bioetl-grafana",
            "State": "running",
            "Health": "healthy",
            "Image": "grafana/grafana:12.0.0",
        },
    ]
    # Prove the historical failure mode: full JSON truncates later services.
    full_stdout = "\n".join(json.dumps(row) for row in [fat_label_row, *lean_rows[1:]])
    assert len(full_stdout) > 4000
    truncated = runtime_manager._bounded(full_stdout)
    truncated_services: set[str] = set()
    for line in truncated.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # Partial final line after truncation is expected.
            continue
        if isinstance(row, dict) and row.get("Service"):
            truncated_services.add(str(row["Service"]))
    # Later lean services are dropped once the fat Labels row fills the bound.
    assert "prometheus" not in truncated_services
    assert "renderer" not in truncated_services

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        if "compose" in current and "ps" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="\n".join(json.dumps(row) for row in lean_rows),
            )
        if current[:2] == ["docker", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "State": {
                            "Status": "running",
                            "OOMKilled": False,
                            "Health": {"Status": "healthy"},
                        },
                        "RestartCount": 0,
                        "Image": "img:test",
                        "ImageID": "sha256:img",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": []}),
            )
        raise AssertionError(current)

    mon = runtime_manager.StackSpec(
        name="monitoring",
        project="bioetl-monitoring",
        compose_file=Path("docker-compose.monitoring.yml"),
        required_services=("prometheus", "pushgateway", "grafana"),
        expected_images={},
        optional_services=("renderer",),
    )
    snapshots, _ = runtime_manager.collect_snapshots(mon, runner=runner)
    names = {snap.service for snap in snapshots}
    assert names == {"prometheus", "pushgateway", "grafana", "renderer"}
    # Readiness ignores optional renderer even if present/unhealthy in ps output.
    assert runtime_manager.readiness_findings(mon, snapshots, baseline={}) == []


def test_compose_up_start_includes_optional_but_wait_is_required_only() -> None:
    mon = runtime_manager.StackSpec(
        name="monitoring",
        project="bioetl-monitoring",
        compose_file=Path("docker-compose.monitoring.yml"),
        required_services=("prometheus", "pushgateway", "grafana"),
        expected_images={},
        optional_services=("renderer",),
    )
    start = runtime_manager._compose_up_start_args(
        mon, attempts=1, force_recreate=False
    )
    assert "renderer" in start
    assert "prometheus" in start
    assert "--wait" not in start

    wait = runtime_manager._compose_up_wait_args(
        mon, attempts=1, remaining=30.0, force_recreate=False
    )
    assert "--wait" in wait
    assert "prometheus" in wait
    assert "grafana" in wait
    assert "renderer" not in wait


def test_running_without_health_is_not_ready() -> None:
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="none",
        restart_count=0,
        oom_killed=False,
        image="bioetl:test@sha256:expected",
    )

    assert runtime_manager.readiness_findings(_spec(), [snapshot]) == [
        {
            "cause": "service_unready",
            "service": "bioetl",
            "state": "running",
            "health": "none",
        }
    ]


def test_preflight_failure_writes_one_redacted_incident_without_mutation(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        calls.append(list(command))
        return runtime_manager.CommandResult(
            list(command), 2, stderr="token=ghp_abcdefghijklmnop"
        )

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=False,
        runner=runner,
        sleep=lambda _seconds: None,
    )

    assert result == 1
    assert len(calls) == 1
    assert "compose" not in calls[0]
    incidents = list(tmp_path.glob("docker-incident-*.json"))
    assert len(incidents) == 1
    payload = json.loads(incidents[0].read_text(encoding="utf-8"))
    assert payload["primary_cause"] == "preflight_failed"
    assert "ghp_" not in incidents[0].read_text(encoding="utf-8")


def test_recover_reports_daemon_probe_mismatch_without_desktop_restart(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "docker-runtime-main-preflight.json"
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        del cwd, timeout
        current = list(command)
        calls.append(current)
        if "docker_runtime_preflight.py" in " ".join(current):
            report_path.write_text(
                json.dumps(
                    {
                        "findings": [
                            {
                                "code": "DOCKER_DAEMON",
                                "severity": "warning",
                                "message": "Docker daemon is unavailable",
                                "evidence": {"error": "permission denied"},
                            },
                            {
                                "code": "MONITORING_PROMQL_SYNTAX",
                                "severity": "error",
                                "message": "promtool failed",
                                "evidence": {"stderr": "permission denied"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return runtime_manager.CommandResult(current, 2)
        if current[:2] == ["docker", "info"]:
            return runtime_manager.CommandResult(current, 0, stdout="29.7.2\n")
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        sleep=lambda _seconds: None,
    )

    assert result == 1
    assert not any("restart-docker.ps1" in " ".join(call) for call in calls)
    incident = json.loads(
        (tmp_path / "docker-incident-main.json").read_text(encoding="utf-8")
    )
    assert incident["primary_cause"] == "preflight_probe_mismatch"
    mismatch = next(
        finding
        for finding in incident["findings"]
        if finding["cause"] == "preflight_probe_mismatch"
    )
    assert mismatch["probe"]["stdout"].strip() == "29.7.2"


def test_unmeasurable_docker_root_does_not_mean_daemon_unavailable(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "docker-runtime-main-preflight.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "CAPACITY_DOCKER_ROOT",
                        "severity": "error",
                        "message": (
                            "Docker data root capacity cannot be measured from this host"
                        ),
                        "evidence": {
                            "docker_root_dir": "/var/lib/docker",
                            "error": "No such file or directory",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert not runtime_manager._preflight_indicates_daemon_unavailable(report_path)


def test_recover_continues_when_preflight_only_reports_container_health(
    tmp_path: Path,
) -> None:
    """Recover must not fail closed solely because the target service is unhealthy."""
    preflight_path = tmp_path / "docker-runtime-main-preflight.json"
    preflight_path.write_text(
        json.dumps(
            {
                "summary": {"errors": 1, "warnings": 0, "ok": False},
                "findings": [
                    {
                        "code": "CONTAINER_HEALTH",
                        "severity": "error",
                        "message": "Container is unhealthy",
                        "evidence": {"name": "/bioetl"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined:
            return runtime_manager.CommandResult(current, 2)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "compose" in current and "ps" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "ID": "abcdef123456",
                        "Service": "bioetl",
                        "State": "running",
                        "Health": "healthy",
                        "Image": "bioetl:test@sha256:" + "a" * 64,
                    }
                ),
            )
        if current[:2] == ["docker", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "State": {
                            "Status": "running",
                            "OOMKilled": False,
                            "Health": {"Status": "healthy"},
                        },
                        "RestartCount": 0,
                        "Image": "bioetl:test",
                        "ImageID": "sha256:img",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": ["bioetl:test@sha256:" + "a" * 64]}),
            )
        if "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "up" in current:
            return runtime_manager.CommandResult(current, 0)
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(expected_images={"bioetl": "bioetl:test@sha256:" + "a" * 64}),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        sleep=lambda _seconds: None,
    )

    assert result == 0
    up_calls = [call for call in calls if "up" in call]
    assert up_calls
    # Main stack force-recreates on attempt 1 so stale Desktop report binds cannot stick.
    assert "--force-recreate" in up_calls[0]
    assert not list(tmp_path.glob("docker-incident-*.json"))


def test_recovery_force_recreates_only_after_first_failed_attempt(
    tmp_path: Path,
) -> None:
    up_calls: list[list[str]] = []
    attempts = {"up": 0}

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        del cwd, timeout
        current = list(command)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined or "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "compose" in current and "ps" in current:
            if attempts["up"] < 2:
                return runtime_manager.CommandResult(current, 0, stdout="")
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps([{"ID": "abcdef123456", "Service": "bioetl"}]),
            )
        if current[:2] == ["docker", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "State": {
                            "Status": "running",
                            "OOMKilled": False,
                            "Health": {"Status": "healthy"},
                        },
                        "RestartCount": 0,
                        "Image": "bioetl:test",
                        "ImageID": "sha256:img",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": ["bioetl:test@sha256:expected"]}),
            )
        if "up" in current:
            attempts["up"] += 1
            up_calls.append(current)
            if attempts["up"] == 1:
                return runtime_manager.CommandResult(current, 1, stderr="still unready")
            return runtime_manager.CommandResult(current, 0)
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        max_attempts=3,
        sleep=lambda _seconds: None,
        stabilization_seconds=0.0,
    )

    assert result == 0
    assert len(up_calls) >= 2
    # Main stack always force-recreates; later attempts remain force-recreate too.
    assert "--force-recreate" in up_calls[0]
    assert "--force-recreate" in up_calls[1]


def test_recovery_is_bounded_to_three_attempts_and_writes_one_incident(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined:
            return runtime_manager.CommandResult(current, 0)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "compose" in current and "ps" in current:
            return runtime_manager.CommandResult(current, 0, stdout="")
        if current[-2:] == ["--format", "json"]:
            return runtime_manager.CommandResult(current, 0, stdout="[]")
        if "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "up" in current:
            return runtime_manager.CommandResult(current, 1, stderr="unready")
        if "logs" in current:
            return runtime_manager.CommandResult(current, 0, stdout="bounded logs")
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        max_attempts=3,
        sleep=lambda _seconds: None,
    )

    assert result == 1
    # Each attempt: start phase + wait phase when start succeeds; here start
    # fails so only one "up" per attempt (3 attempts).
    assert sum("up" in call for call in calls) == 3
    assert len(list(tmp_path.glob("docker-incident-*.json"))) == 1
    incident = json.loads(
        next(tmp_path.glob("docker-incident-*.json")).read_text(encoding="utf-8")
    )
    assert incident["config_origin"] == "docker-compose.yml"
    assert incident["recent_logs"]["captured"] is True
    # recovery_history records start (and wait when reached) rows
    assert len(incident["recovery_history"]) >= 3


def test_clean_requires_confirmation_and_never_deletes_data(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        calls.append(list(command))
        return runtime_manager.CommandResult(list(command), 0)

    assert (
        runtime_manager.main(["clean", "--report-dir", str(tmp_path)], runner=runner)
        == 2
    )
    assert calls == []
    assert (
        runtime_manager.main(
            [
                "clean",
                "--report-dir",
                str(tmp_path),
                "--confirm-destructive",
                "CLEAN",
            ],
            runner=runner,
        )
        == 0
    )
    rendered = " ".join(calls[-1])
    assert "--volumes" not in rendered
    assert "-v" not in calls[-1]
    assert "prune" not in rendered


def test_recovery_waits_for_daemon_after_transient_socket_failure(
    tmp_path: Path,
) -> None:
    """Compose can fail mid-up when Desktop flaps; recover must wait and retry."""
    up_attempts = 0
    info_probes = 0

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        del cwd, timeout
        nonlocal up_attempts, info_probes
        current = list(command)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined or "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "info" in current and "--format" in current:
            info_probes += 1
            return runtime_manager.CommandResult(current, 0, stdout="29.6.2\n")
        if "compose" in current and "ps" in current:
            if up_attempts < 1:
                return runtime_manager.CommandResult(current, 0, stdout="")
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps([{"ID": "abcdef123456", "Service": "bioetl"}]),
            )
        if current[:2] == ["docker", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "State": {
                            "Status": "running",
                            "OOMKilled": False,
                            "Health": {"Status": "healthy"},
                        },
                        "RestartCount": 0,
                        "Image": "bioetl:test",
                        "ImageID": "sha256:img",
                    }
                ),
            )
        if current[:3] == ["docker", "image", "inspect"]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps({"RepoDigests": ["bioetl:test@sha256:expected"]}),
            )
        if "up" in current:
            up_attempts += 1
            if up_attempts == 1:
                return runtime_manager.CommandResult(
                    current,
                    1,
                    stderr=(
                        "unable to get image 'bioetl-main-bioetl': "
                        "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. "
                        "Is the docker daemon running?"
                    ),
                )
            return runtime_manager.CommandResult(current, 0)
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        max_attempts=3,
        sleep=lambda _seconds: None,
        stabilization_seconds=0.0,
    )

    assert result == 0
    # Attempt 1: start fails (daemon). Attempt 2: start ok + wait ok → 3 ups.
    assert up_attempts == 3
    assert info_probes >= 1
    assert not list(tmp_path.glob("docker-incident-*.json"))


def test_recovery_attempts_share_one_overall_deadline(tmp_path: Path) -> None:
    now = [0.0]
    up_calls = 0

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        nonlocal up_calls
        current = list(command)
        joined = " ".join(current)
        if "docker_runtime_preflight.py" in joined or "config" in current:
            return runtime_manager.CommandResult(current, 0)
        if "network" in current and "inspect" in current:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout="scripts/ops/runtime/docker/runtime_manager.py\n",
            )
        if "compose" in current and "ps" in current:
            return runtime_manager.CommandResult(current, 0, stdout="")
        if current[-2:] == ["--format", "json"]:
            return runtime_manager.CommandResult(current, 0, stdout="[]")
        if "up" in current:
            up_calls += 1
            now[0] += timeout
            return runtime_manager.CommandResult(current, 1, stderr="timeout")
        if "logs" in current:
            return runtime_manager.CommandResult(current, 0)
        raise AssertionError(current)

    result = runtime_manager.start_or_recover(
        _spec(),
        Path("contract.yml"),
        tmp_path,
        recover=True,
        runner=runner,
        timeout=10,
        max_attempts=3,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )

    assert result == 1
    assert up_calls == 1
    incident = json.loads(
        next(tmp_path.glob("docker-incident-*.json")).read_text(encoding="utf-8")
    )
    assert incident["elapsed_seconds"] <= 10


def test_readiness_stabilization_never_runs_past_global_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    observed_timeouts: list[float] = []
    snapshot = runtime_manager.ServiceSnapshot(
        service="bioetl",
        container_id="abc",
        state="running",
        health="healthy",
        restart_count=0,
        oom_killed=False,
        image="bioetl:test@sha256:expected",
    )

    def collect(
        spec: runtime_manager.StackSpec,
        *,
        runner: runtime_manager.Runner,
        timeout: float,
    ) -> tuple[
        list[runtime_manager.ServiceSnapshot], list[runtime_manager.CommandResult]
    ]:
        del spec, runner
        observed_timeouts.append(timeout)
        now[0] += timeout
        return [snapshot], []

    monkeypatch.setattr(runtime_manager, "collect_snapshots", collect)

    snapshots, findings = runtime_manager._wait_ready(
        _spec(),
        {},
        runner=lambda command, cwd, timeout: runtime_manager.CommandResult(
            list(command), 0
        ),
        timeout=10.0,
        poll_interval=2.0,
        stabilization_seconds=5.0,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )

    assert snapshots == [snapshot]
    assert findings == [{"cause": "readiness_timeout"}]
    assert observed_timeouts == [10.0]
    assert now[0] == 10.0


def test_shared_network_bootstrap_creates_only_missing_contracted_networks(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main", "monitoring"],
                    },
                    "unrelated": {
                        "name": "bioetl-unrelated",
                        "owner": "other",
                        "consumers": ["neo4j"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        calls.append(current)
        if "inspect" in current:
            return runtime_manager.CommandResult(current, 1, stderr="not found")
        if "create" in current:
            return runtime_manager.CommandResult(current, 0, stdout="network-id")
        raise AssertionError(current)

    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(), contract, tmp_path / "networks.json", runner=runner
    )

    assert ok is True
    assert findings == []
    assert sum("create" in call for call in calls) == 1
    assert all("bioetl-unrelated" not in call for call in calls)
    assert "com.bioetl.owner=runtime-manager" in calls[-1]


def test_shared_network_bootstrap_rejects_conflicting_owner(tmp_path: Path) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        return runtime_manager.CommandResult(list(command), 0, stdout="another-owner\n")

    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(), contract, tmp_path / "networks.json", runner=runner
    )

    assert ok is False
    assert findings == [
        {
            "cause": "network_owner_drift",
            "network": "bioetl-monitoring",
            "expected_owner": "runtime-manager",
            "observed_owner": "another-owner",
        }
    ]


def test_shared_network_bootstrap_rejects_unlabeled_existing_network(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        return runtime_manager.CommandResult(list(command), 0, stdout="\n")

    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(), contract, tmp_path / "networks.json", runner=runner
    )

    assert ok is False
    assert findings == [
        {
            "cause": "network_owner_drift",
            "network": "bioetl-monitoring",
            "expected_owner": "runtime-manager",
            "observed_owner": "",
        }
    ]


def test_ensure_shared_networks_all_networks_ignores_consumer_filter(
    tmp_path: Path,
) -> None:
    """Full reinstall path must create every contracted shared net, not stack-only."""
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["monitoring"],
                    },
                    "runtime": {
                        "name": "bioetl-runtime",
                        "owner": "runtime-manager",
                        "consumers": ["neo4j"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    created: list[str] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        if "inspect" in current:
            return runtime_manager.CommandResult(current, 1, stderr="not found")
        if "create" in current:
            created.append(current[-1])
            return runtime_manager.CommandResult(current, 0, stdout="id")
        raise AssertionError(current)

    # Stack is main, but neither net lists main as consumer — all_networks still ensures both.
    ok, findings = runtime_manager.ensure_shared_networks(
        _spec(),
        contract,
        tmp_path / "networks.json",
        runner=runner,
        all_networks=True,
    )

    assert ok is True
    assert findings == []
    assert set(created) == {"bioetl-monitoring", "bioetl-runtime"}
    report = json.loads((tmp_path / "networks.json").read_text(encoding="utf-8"))
    assert report["stack"] == "all"
    assert report["all_networks"] is True


def test_ensure_networks_action_creates_all_shared_nets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = tmp_path / "contract.yml"
    contract.write_text(
        yaml.safe_dump(
            {
                "stacks": {
                    "main": {
                        "project_name": "bioetl-main",
                        "compose_file": "docker-compose.yml",
                        "required_services": ["bioetl"],
                        "expected_images": {"bioetl": "bioetl:local"},
                    }
                },
                "shared_networks": {
                    "monitoring": {
                        "name": "bioetl-monitoring",
                        "owner": "runtime-manager",
                        "consumers": ["main", "monitoring"],
                    },
                    "runtime": {
                        "name": "bioetl-runtime",
                        "owner": "runtime-manager",
                        "consumers": ["main", "neo4j"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    created: list[str] = []

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        current = list(command)
        if "inspect" in current:
            return runtime_manager.CommandResult(current, 1, stderr="missing")
        if "create" in current:
            created.append(current[-1])
            return runtime_manager.CommandResult(current, 0, stdout="id")
        return runtime_manager.CommandResult(current, 0)

    monkeypatch.setattr(
        runtime_manager,
        "_dashboard_runtime_environment",
        lambda _path: __import__("contextlib").nullcontext({}),
    )
    # resolve_stack needs compose file present only as path string — no read here.
    code = runtime_manager.main(
        [
            "ensure-networks",
            "--stack",
            "main",
            "--contract",
            str(contract),
            "--report-dir",
            str(report_dir),
            "--timeout",
            "10",
        ],
        runner=runner,
    )
    assert code == 0
    assert set(created) == {"bioetl-monitoring", "bioetl-runtime"}
    assert (report_dir / "docker-runtime-all-networks.json").is_file()
