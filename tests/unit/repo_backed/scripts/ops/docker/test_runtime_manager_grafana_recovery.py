# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportAssignmentType=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Grafana cutover and late-recovery tests split out of the runtime manager module."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.unit.repo_backed.scripts.ops.docker.test_runtime_manager import (
    _cat_status_runner,
    _claim_script_results,
    _grafana_cutover_runner,
    _monitoring_spec,
    _prepare_claim_shell,
    _prometheus_only_deferred,
    _spec,
    runtime_manager,
)

pytestmark = pytest.mark.repo_backed


def test_post_start_grafana_cutover_restarts_when_deferred(
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
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred, ready],
        expected_source_id=source_id,
    )

    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )
    assert result is not None
    assert result["restart_returncode"] == 0
    assert result["previous_reason"] == "identity_timeout_or_unreachable"
    assert ["docker", "restart", runtime_manager._GRAFANA_CONTAINER] in commands


@pytest.mark.parametrize("ownership", ["active", "claimed", "unavailable", "full"])
def test_post_start_grafana_cutover_does_not_compete_for_restart(
    monkeypatch: pytest.MonkeyPatch, ownership: str
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    deferred = {
        "ops_http": "deferred",
        "reason": "identity_timeout_or_unreachable",
        "dashboard_profile": "prometheus_only",
    }
    ready = {"ops_http": "ready", "dashboard_profile": "full"}
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred, ready], expected_source_id="a" * 64, ownership=ownership
    )
    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(), runner=runner, timeout=5, sleep=lambda _: None, clock=lambda: 0
    )
    assert result is not None
    assert result["recovery_ownership"] == ownership
    assert result["status"] == (
        "full" if ownership in {"active", "full"} else "deferred"
    )
    assert not any(cmd[:2] == ["docker", "restart"] for cmd in commands)


def test_monitoring_gate_cannot_pass_while_watcher_remains_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    now = [0.0]
    deferred = {
        "ops_http": "deferred",
        "reason": "identity_timeout_or_unreachable",
        "dashboard_profile": "prometheus_only",
    }
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred], expected_source_id="a" * 64, ownership="active"
    )
    result = runtime_manager._post_start_grafana_bootstrap_gate(
        spec=_monitoring_spec(),
        runner=runner,
        timeout=3,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )
    assert result is False
    assert not any(cmd[:2] == ["docker", "restart"] for cmd in commands)


def test_full_profile_status_is_not_ready_until_grafana_health_responds() -> None:
    health_calls = {"n": 0}
    now = [0.0]

    def runner(
        command: Sequence[str], cwd: Path, timeout: float
    ) -> runtime_manager.CommandResult:
        del cwd, timeout
        current = list(command)
        if current[:4] == [
            "docker",
            "exec",
            runtime_manager._GRAFANA_CONTAINER,
            "cat",
        ]:
            return runtime_manager.CommandResult(
                current,
                0,
                stdout=json.dumps(
                    {
                        "ops_http": "ready",
                        "reason": "identity_matched",
                        "dashboard_profile": "full",
                    }
                ),
            )
        if any("api/health" in part for part in current):
            health_calls["n"] += 1
            if health_calls["n"] == 1:
                return runtime_manager.CommandResult(current, 1, stderr="down")
            return runtime_manager.CommandResult(current, 0, stdout='{"database":"ok"}')
        raise AssertionError(current)

    ready = runtime_manager._wait_for_grafana_full_profile(
        runner,
        deadline=10.0,
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
        clock=lambda: now[0],
    )

    assert ready is True
    assert health_calls["n"] == 2


def test_manager_waits_for_live_lease_before_probing_late_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    deferred = {
        "ops_http": "deferred",
        "reason": "identity_timeout_or_unreachable",
        "dashboard_profile": "prometheus_only",
        "late_recovery_state": "waiting",
    }
    ready = {"ops_http": "ready", "dashboard_profile": "full"}
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred, ready],
        expected_source_id="a" * 64,
        actual_source_id="",
        ownership="active",
    )
    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(), runner=runner, timeout=5, sleep=lambda _: None, clock=lambda: 0
    )
    assert result is not None
    assert result["status"] == "full"
    assert not any(cmd[:2] == ["docker", "restart"] for cmd in commands)
    assert not any(
        len(cmd) > 3
        and cmd[3] == "wget"
        and any("ops/control-plane/ready" in part for part in cmd)
        for cmd in commands
    )
    assert any(
        len(cmd) > 3 and cmd[3] == "wget" and any("api/health" in part for part in cmd)
        for cmd in commands
    )
    assert any(cmd[-1] == "check" for cmd in commands)


@pytest.mark.parametrize(
    ("lease", "expected"),
    [
        (None, "acquired"),
        ("42 200 boot 150", "active"),
        ("42 201 boot 150", "acquired"),
        ("42 200 previous-boot 150", "acquired"),
        ("42 200 boot 99", "acquired"),
    ],
)
def test_late_cutover_claim_checks_current_process_and_deadline(
    tmp_path: Path, lease: str | None, expected: str
) -> None:
    shell, env, recovery_root, source_id = _prepare_claim_shell(tmp_path)
    if lease is not None:
        (recovery_root / f"{source_id}.lease").write_text(
            lease + "\n", encoding="utf-8", newline="\n"
        )
    command = (
        'PATH="$(cd "$TEST_BIN" && pwd):$PATH"\n'
        + runtime_manager._GRAFANA_LATE_CUTOVER_CLAIM
    )
    result = subprocess.run(
        [shell, "-c", command],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
    claim = recovery_root / f"{source_id}.claim"
    assert claim.is_dir() == (expected == "acquired")
    if expected == "acquired":
        repeated = subprocess.run(
            [shell, "-c", command],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=10,
        )
        assert repeated.returncode == 0, repeated.stderr
        assert repeated.stdout.strip() == "claimed"


def test_check_mode_sees_active_lease_while_claim_remains(
    tmp_path: Path,
) -> None:
    shell, env, recovery_root, source_id = _prepare_claim_shell(tmp_path)
    (recovery_root / f"{source_id}.lease").write_text(
        "42 200 boot 150\n", encoding="utf-8", newline="\n"
    )
    (recovery_root / f"{source_id}.claim").mkdir()
    script = (
        'PATH="$(cd "$TEST_BIN" && pwd):$PATH"\n'
        + runtime_manager._GRAFANA_LATE_CUTOVER_CLAIM
    )

    def run(mode: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [shell, "-c", script, "bioetl-late-cutover", mode],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=10,
        )

    checked = run("check")
    claimed = run("claim")
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout.strip() == "active"
    assert claimed.returncode == 0, claimed.stderr
    assert claimed.stdout.strip() == "claimed"


def test_late_cutover_claim_has_one_owner_across_concurrent_processes(
    tmp_path: Path,
) -> None:
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX sh is required for the atomic recovery claim test")
    env = {
        **os.environ,
        "BIOETL_EXPECTED_RUNTIME_SOURCE_ID": "a" * 64,
        "BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE": str(tmp_path / "bootstrap-status.json"),
    }
    results = _claim_script_results(shell, env)
    assert all(code == 0 for _stdout, _stderr, code in results), results
    assert sorted(stdout.strip() for stdout, _stderr, _code in results) == [
        "acquired",
        "claimed",
    ]


@pytest.mark.parametrize("other_actor", ["manager", "watcher"])
def test_late_cutover_claim_elects_one_owner_when_mkdir_is_not_exclusive(
    tmp_path: Path,
    other_actor: str,
) -> None:
    """Ubuntu 26.04 uutils mkdir can return success to every concurrent creator."""
    shell = shutil.which("sh")
    real_mkdir = shutil.which("mkdir")
    if shell is None or real_mkdir is None:
        pytest.skip("POSIX sh and mkdir are required for the recovery claim test")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    shim = fake_bin / "mkdir"
    real_mkdir = Path(real_mkdir).as_posix()
    shim.write_text(
        f"""#!/bin/sh
real="{real_mkdir}"
if [ "$1" = "-p" ]; then
  exec "$real" "$@"
fi
target="$1"
arrived="$(dirname "$target")/mkdir-arrived"
printf '%s\\n' "$$" >> "$arrived"
i=0
while [ "$i" -lt 50 ]; do
  count="$(wc -l < "$arrived" 2>/dev/null || printf '0')"
  [ "$count" -ge 2 ] && break
  i=$((i + 1))
  sleep 0.05
done
"$real" "$target" 2>/dev/null
exit 0
""",
        encoding="utf-8",
        newline="\n",
    )
    shim.chmod(0o755)
    recovery_root = tmp_path / "bioetl-late-cutover"
    recovery_root.mkdir()
    env = {
        **os.environ,
        "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
        "BIOETL_EXPECTED_RUNTIME_SOURCE_ID": "a" * 64,
        "BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE": str(tmp_path / "bootstrap-status.json"),
        "TEST_BIN": str(fake_bin),
    }
    manager_script = runtime_manager._GRAFANA_LATE_CUTOVER_CLAIM
    source = (
        runtime_manager.ROOT / "grafana/scripts/bootstrap-datasources.sh"
    ).read_text(encoding="utf-8")
    watcher_script = (
        source.split("# --- Always provision Prometheus first", 1)[0]
        + r"""
now=100
LATE_RECOVERY_FOREGROUND=424242
LATE_RECOVERY_STATE=waiting
LATE_RECOVERY_LEASE_VALUE=test
LATE_RECOVERY_DEADLINE=580
late_recovery_now() { printf '%s\n' "$now"; }
late_recovery_alive() { return 0; }
late_recovery_identity() { return 0; }
late_recovery_health() { return 0; }
sleep() { now=$((now + $1)); }
write_bootstrap_status() {
  [ "$LATE_RECOVERY_STATE" != blocked ] || printf 'claimed\n'
}
kill() { printf 'acquired\n'; }
late_recovery_watch
"""
    )
    scripts = [
        manager_script,
        manager_script if other_actor == "manager" else watcher_script,
    ]
    script_paths = []
    for index, script in enumerate(scripts):
        path = tmp_path / f"claim-{index}.sh"
        path.write_text(
            'PATH="$(cd "$TEST_BIN" && pwd):$PATH"\n' + script,
            encoding="utf-8",
            newline="\n",
        )
        script_paths.append(path)
    processes = [
        subprocess.Popen(
            [shell, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        for path in script_paths
    ]
    results = [process.communicate(timeout=10) for process in processes]
    assert all(process.returncode == 0 for process in processes), results
    assert len((recovery_root / "mkdir-arrived").read_text().splitlines()) == 2
    assert sorted(stdout.strip() for stdout, _stderr in results) == [
        "acquired",
        "claimed",
    ], results


@pytest.mark.parametrize("current_source", [True, False])
def test_late_cutover_claim_rechecks_full_profile_after_acquisition(
    tmp_path: Path, current_source: bool
) -> None:
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX sh is required for the recovery claim race test")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    source_id = "a" * 64
    payload = json.dumps(
        {
            "ops_http": "ready",
            "dashboard_profile": "full",
            "late_recovery_source_id": source_id if current_source else "b" * 64,
        }
    )
    scripts = {
        "cat": (
            '#!/bin/sh\nif [ ! -f "$STATUS_READ_ONCE" ]; then\n'
            "  : > \"$STATUS_READ_ONCE\"\n  printf '{}\\n'\nelse\n"
            f"  printf '%s\\n' '{payload}'\nfi\n"
        ),
        "wget": f"#!/bin/sh\nprintf '%s\\n' '{{\"runtime_source_id\":\"{source_id}\"}}'\n",
    }
    for name, content in scripts.items():
        executable = fake_bin / name
        executable.write_text(content, encoding="utf-8", newline="\n")
        executable.chmod(0o755)
    env = {
        **os.environ,
        "TEST_BIN": str(fake_bin),
        "STATUS_READ_ONCE": str(tmp_path / "read-once"),
        "BIOETL_EXPECTED_RUNTIME_SOURCE_ID": source_id,
        "BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE": str(tmp_path / "bootstrap-status.json"),
    }
    command = (
        'PATH="$(cd "$TEST_BIN" && pwd):$PATH"\n'
        + runtime_manager._GRAFANA_LATE_CUTOVER_CLAIM
    )
    result = subprocess.run(
        [shell, "-c", command],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ("full" if current_source else "acquired")
    claim = tmp_path / "bioetl-late-cutover" / f"{source_id}.claim"
    assert claim.is_dir() is not current_source


def test_post_start_grafana_cutover_skips_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    commands: list[list[str]] = []
    runner = _cat_status_runner(
        commands, _prometheus_only_deferred("identity_mismatch")
    )

    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )
    assert result is None
    assert not any(cmd[:2] == ["docker", "restart"] for cmd in commands)


def test_post_start_grafana_cutover_skips_when_identity_does_not_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    deferred = {
        "ops_http": "deferred",
        "reason": "identity_timeout_or_unreachable",
        "dashboard_profile": "prometheus_only",
    }
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred],
        expected_source_id="a" * 64,
        actual_source_id="b" * 64,
    )

    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )
    assert result is None
    assert not any(cmd[:2] == ["docker", "restart"] for cmd in commands)


def test_post_start_grafana_cutover_records_failed_restart(
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
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred],
        expected_source_id=source_id,
        restart_code=1,
    )

    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )
    assert result is not None
    assert result["restart_returncode"] == 1
    assert ["docker", "restart", runtime_manager._GRAFANA_CONTAINER] in commands
    assert sum(1 for cmd in commands if cmd[:2] == ["docker", "restart"]) == 1
    assert sum(1 for cmd in commands if len(cmd) > 3 and cmd[3] == "cat") == 1


def test_post_start_grafana_cutover_uses_container_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(runtime_manager, "_GRAFANA_CONTAINER", "grafana-test")
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
    commands, runner = _grafana_cutover_runner(
        statuses=[deferred, ready],
        expected_source_id=source_id,
    )

    result = runtime_manager._post_start_grafana_ops_cutover(
        spec=_spec(),
        runner=runner,
        timeout=5.0,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )
    assert result is not None
    assert ["docker", "restart", "grafana-test"] in commands


def test_post_start_grafana_cutover_skips_when_ops_http_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        runtime_manager,
        "_load_grafana_bootstrap_status",
        lambda *_args, **_kwargs: (
            {
                "ops_http": "ready",
                "reason": "identity_matched",
                "dashboard_profile": "full",
            },
            True,
        ),
    )

    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        raise AssertionError(f"unexpected {cmd}")

    assert (
        runtime_manager._post_start_grafana_ops_cutover(
            spec=_spec(),
            runner=runner,
            timeout=5.0,
            sleep=lambda _seconds: None,
            clock=lambda: 0.0,
        )
        is None
    )


def test_post_start_grafana_cutover_skips_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_post_start_grafana_cutover")

    def runner(cmd: Sequence[str], _cwd: Path, _timeout: float):
        raise AssertionError(f"unexpected {cmd}")

    assert (
        runtime_manager._post_start_grafana_ops_cutover(
            spec=_spec(),
            runner=runner,
            timeout=5.0,
        )
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


@pytest.mark.parametrize(
    ("ops_url", "expected_ready_url"),
    [
        (
            "http://[fd00::10]:8000/bioetl",
            "http://[fd00::10]:8000/bioetl/ops/control-plane/ready",
        ),
        (
            "http://user:secret@host",
            "http://bioetl:8000/ops/control-plane/ready",
        ),
    ],
)
def test_late_cutover_claim_uses_bootstrap_ops_url_rules(
    tmp_path: Path, ops_url: str, expected_ready_url: str
) -> None:
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX sh is required for the recovery claim test")
    source_id = "a" * 64
    status = tmp_path / "bootstrap-status.json"
    status.write_text(
        json.dumps(
            {
                "ops_http": "ready",
                "dashboard_profile": "full",
                "late_recovery_source_id": source_id,
            }
        ),
        encoding="utf-8",
    )
    seen = tmp_path / "wget-urls"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    shim = fake_bin / "wget"
    shim.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{seen}'\n"
        'case "$*" in\n'
        "  *api/health*) printf '%s\\n' '{\"database\":\"ok\"}' ;;\n"
        "  *control-plane/ready*) printf '%s\\n' "
        f'\'{{"runtime_source_id":"{source_id}"}}\' ;;\n'
        "  *) exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
        newline="\n",
    )
    shim.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
        "BIOETL_EXPECTED_RUNTIME_SOURCE_ID": source_id,
        "BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE": str(status),
        "BIOETL_OPS_HTTP_URL": ops_url,
    }
    result = subprocess.run(
        [shell, "-c", runtime_manager._GRAFANA_LATE_CUTOVER_CLAIM],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "full"
    assert expected_ready_url in seen.read_text(encoding="utf-8")
