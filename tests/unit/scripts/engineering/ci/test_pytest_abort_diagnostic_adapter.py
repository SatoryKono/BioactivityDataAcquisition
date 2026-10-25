"""Subprocess contracts for the isolated pytest abort supervisor."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import affected_pytest_targets
from scripts.engineering.ci.pytest_abort_diagnostic_adapter import (
    DIAGNOSTIC_DUMP_MARGIN_SECONDS,
    PYTEST_PER_TEST_TIMEOUT_SECONDS,
    SERIAL_COVERAGE_JOB_TIMEOUT_SECONDS,
    SERIAL_COVERAGE_SETUP_RESERVE_SECONDS,
    SERIAL_COVERAGE_UPLOAD_RESERVE_SECONDS,
    PytestAbortDiagnosticAdapter,
    _pid_alive,
    _terminate_pid,
    junit_file_is_complete,
    serial_coverage_pass_budget_seconds,
)
from scripts.engineering.ci.run_pytest_resilient import (
    _create_parser,
    main as resilient_main,
)

pytestmark = [pytest.mark.unit, pytest.mark.subprocess_backed]

JUNIT = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<testsuite name="synthetic" tests="1"></testsuite>\n'
)
_ADAPTER = "scripts.engineering.ci.pytest_abort_diagnostic_adapter"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _write_junit(path: Path, payload: str = JUNIT) -> None:
    path.write_text(payload, encoding="utf-8")


def _python_script(base: Path, name: str, source: str, *args: str) -> list[str]:
    path = base / name
    path.write_text(source, encoding="utf-8")
    return [sys.executable, str(path), *args]


def _junit_writer(base: Path, evidence: Path, payload: str = JUNIT) -> list[str]:
    return _python_script(
        base,
        f"write-{evidence.name}.py",
        "import pathlib, sys\n"
        f"pathlib.Path(sys.argv[1]).write_text({payload!r}, encoding='utf-8')\n",
        str(evidence),
    )


def _adapter(
    base: Path, *, timeout: float = 5, margin: float = 0.4
) -> PytestAbortDiagnosticAdapter:
    return PytestAbortDiagnosticAdapter(timeout=timeout, dump_margin=margin, base=base)


def _run(
    base: Path,
    command: list[str],
    evidence: Path | None,
    *,
    timeout: float = 5,
    margin: float = 0.4,
) -> tuple[PytestAbortDiagnosticAdapter, object]:
    adapter = _adapter(base, timeout=timeout, margin=margin)
    manifest = adapter.run(command, evidence, base / "out", base=base)
    return adapter, manifest


def _disk_manifest(base: Path) -> dict[str, object]:
    matches = sorted((base / "out").rglob("diagnostic_manifest.json"))
    assert len(matches) == 1
    payload = json.loads(matches[0].read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _cli(base: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the module from a non-repo cwd, as CI does not export PYTHONPATH."""
    env = os.environ.copy()
    root = str(_repo_root())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = root if not existing else os.pathsep.join((root, existing))
    return subprocess.run(
        [sys.executable, "-m", _ADAPTER, *args],
        cwd=base,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _stop_recorded(pid_dir: Path) -> None:
    for name in ("launcher.txt", "child.txt"):
        path = pid_dir / name
        if not path.is_file():
            continue
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except ValueError:
            continue
        if _pid_alive(pid):
            _terminate_pid(pid)


def test_normal_success_requires_fresh_valid_junit(tmp_path: Path) -> None:
    evidence = tmp_path / "junit.xml"
    command = _junit_writer(tmp_path, evidence)
    _adapter_unused, manifest = _run(tmp_path, command, evidence)
    del _adapter_unused
    assert manifest.status == "NORMAL_EXIT"
    assert manifest.exit_code == 0
    assert manifest.signal is None
    assert manifest.evidence_valid is True
    assert manifest.evidence_reason == "fresh_junit"
    assert manifest.wrapper_exit_code == 0
    assert manifest.oom_inferred is False
    payload = _disk_manifest(tmp_path)
    assert payload["status"] == manifest.status
    assert payload["exit_code"] == 0
    assert payload["signal"] is None
    assert payload["wrapper_exit_code"] == 0
    stdout = tmp_path / str(payload["stdout_file"])
    stderr = tmp_path / str(payload["stderr_file"])
    assert stdout.is_file()
    assert stderr.is_file()
    assert junit_file_is_complete(evidence)
    assert not junit_file_is_complete(tmp_path / str(payload["manifest_file"]))


def test_positive_nonzero_exit_is_preserved(tmp_path: Path) -> None:
    evidence = tmp_path / "junit.xml"
    _write_junit(evidence)
    _, manifest = _run(
        tmp_path,
        _python_script(tmp_path, "exit42.py", "import sys\nsys.exit(42)\n"),
        evidence,
    )
    assert manifest.status == "NONZERO_EXIT"
    assert manifest.exit_code == 42
    assert manifest.wrapper_exit_code == 42
    assert _disk_manifest(tmp_path)["exit_code"] == 42


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX signal abort is verified only on POSIX"
)
def test_posix_signal_abort_wrapper_is_nonzero(tmp_path: Path) -> None:
    _, manifest = _run(
        tmp_path,
        _python_script(
            tmp_path,
            "abort.py",
            "import os, signal\nos.kill(os.getpid(), signal.SIGABRT)\n",
        ),
        tmp_path / "missing.xml",
    )
    assert manifest.status == "SIGNAL_ABORT"
    assert manifest.exit_code is not None and manifest.exit_code < 0
    assert manifest.signal == -manifest.exit_code
    assert manifest.wrapper_exit_code == 128 + manifest.signal
    assert manifest.wrapper_exit_code != 0
    assert manifest.oom_inferred is False


def test_timeout_is_nonzero_and_does_not_invent_junit(tmp_path: Path) -> None:
    evidence = tmp_path / "missing.xml"
    _, manifest = _run(
        tmp_path,
        _python_script(tmp_path, "sleep.py", "import time\ntime.sleep(30)\n"),
        evidence,
        timeout=0.6,
        margin=0.3,
    )
    assert manifest.status == "WATCHDOG_TIMEOUT"
    assert manifest.wrapper_exit_code == 124
    assert manifest.evidence_valid is False
    assert not evidence.exists()
    assert manifest.oom_inferred is False


@pytest.mark.skipif(os.name == "nt", reason="SIGABRT handler is verified only on POSIX")
def test_posix_timeout_handler_exit_zero_is_still_failure(tmp_path: Path) -> None:
    _, manifest = _run(
        tmp_path,
        _python_script(
            tmp_path,
            "handle_abort.py",
            "import signal, sys, time\n"
            "signal.signal(signal.SIGABRT, lambda *_: sys.exit(0))\n"
            "time.sleep(30)\n",
        ),
        tmp_path / "missing.xml",
        timeout=0.6,
        margin=0.8,
    )
    assert manifest.status == "WATCHDOG_TIMEOUT"
    assert manifest.diagnostic_signal_delivery == "process_group"
    assert manifest.exit_code == 0
    assert manifest.wrapper_exit_code == 124


@pytest.mark.skipif(
    os.name != "nt", reason="Windows SIGABRT fallback is verified only on Windows"
)
def test_windows_timeout_does_not_claim_sigabrt_dump(tmp_path: Path) -> None:
    _, manifest = _run(
        tmp_path,
        _python_script(tmp_path, "sleep-win.py", "import time\ntime.sleep(30)\n"),
        tmp_path / "missing.xml",
        timeout=0.6,
        margin=0.3,
    )
    assert manifest.status == "WATCHDOG_TIMEOUT"
    assert manifest.diagnostic_signal_delivery == "unsupported"
    assert manifest.diagnostic_signal_sent is None
    assert manifest.wrapper_exit_code == 124
    text = json.dumps(_disk_manifest(tmp_path))
    assert "faulthandler dump captured" not in text


@pytest.mark.parametrize("launcher_depth", [1, 2])
def test_launcher_descendant_is_gone_after_cleanup(
    tmp_path: Path, launcher_depth: int
) -> None:
    pid_dir = tmp_path / "pids"
    pid_dir.mkdir()
    child_script = pid_dir / "child_sleep.py"
    child_script.write_text(
        "import os, pathlib, sys, time\n"
        "if os.name == 'posix':\n"
        "    import resource\n"
        "    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    if launcher_depth == 2:
        intermediate = pid_dir / "intermediate.py"
        intermediate.write_text(
            "import subprocess, sys\n"
            f"subprocess.run([sys.executable, {str(child_script)!r}, sys.argv[1]], check=False)\n",
            encoding="utf-8",
        )
        child_script = intermediate
    try:
        _, manifest = _run(
            tmp_path,
            _python_script(
                tmp_path,
                "launcher.py",
                "import pathlib, subprocess, sys\n"
                "root = pathlib.Path(sys.argv[1])\n"
                "child_script = pathlib.Path(sys.argv[2])\n"
                "child = subprocess.Popen([sys.executable, str(child_script), str(root / 'child.txt')])\n"
                "(root / 'launcher.txt').write_text(str(__import__('os').getpid()))\n"
                "child.wait()\n",
                str(pid_dir),
                str(child_script),
            ),
            tmp_path / "missing.xml",
            timeout=1.5,
            margin=0.4,
        )
        assert manifest.status == "WATCHDOG_TIMEOUT"
        assert manifest.wrapper_exit_code != 0
        launcher = int((pid_dir / "launcher.txt").read_text(encoding="utf-8"))
        child = int((pid_dir / "child.txt").read_text(encoding="utf-8"))
        assert not _pid_alive(launcher)
        assert not _pid_alive(child)
        assert "cleanup_incomplete" not in (manifest.cleanup_error or "")
        if os.name == "posix":
            # Loaded runners may not reap both waiting parents within half
            # the dump margin; the documented group fallback is valid too.
            assert manifest.diagnostic_signal_delivery in {
                "leaf_descendants",
                "leaf_descendants_then_process_group",
            }
            diagnostic = (tmp_path / manifest.stderr_file).read_text(encoding="utf-8")
            assert "Fatal Python error: Aborted" in diagnostic
            assert "child_sleep.py" in diagnostic
    finally:
        _stop_recorded(pid_dir)


@pytest.mark.parametrize(
    ("prepare", "reason"),
    [
        ("missing", "missing"),
        ("stale", "stale"),
        ("empty", "empty"),
        ("malformed", "malformed"),
        ("directory", "directory"),
    ],
)
def test_unusable_evidence_is_not_success(
    tmp_path: Path, prepare: str, reason: str
) -> None:
    evidence = tmp_path / "junit.xml"
    command = _python_script(tmp_path, f"{prepare}.py", "import sys\nsys.exit(0)\n")
    if prepare == "stale":
        _write_junit(evidence)
    elif prepare == "empty":
        command = _python_script(
            tmp_path,
            "empty.py",
            "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('', encoding='utf-8')\n",
            str(evidence),
        )
    elif prepare == "malformed":
        command = _python_script(
            tmp_path,
            "malformed.py",
            "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('not-xml', encoding='utf-8')\n",
            str(evidence),
        )
    elif prepare == "directory":
        evidence.mkdir()
    _, manifest = _run(tmp_path, command, evidence)
    assert manifest.evidence_valid is False
    assert manifest.evidence_reason == reason
    assert manifest.wrapper_exit_code != 0
    if prepare == "directory":
        assert evidence.is_dir()
    if prepare == "stale":
        assert evidence.read_text(encoding="utf-8") == JUNIT


def test_spawn_failure_and_cli_rejections(tmp_path: Path) -> None:
    _, manifest = _run(
        tmp_path, ["command-does-not-exist-12069"], tmp_path / "junit.xml"
    )
    assert manifest.status == "SPAWN_FAILURE"
    assert manifest.wrapper_exit_code == 127
    assert _disk_manifest(tmp_path)["status"] == "SPAWN_FAILURE"

    base = tmp_path / "cli"
    base.mkdir()
    empty = _cli(
        base,
        [
            "--timeout",
            "1",
            "--dump-margin",
            "0.2",
            "--expected-evidence",
            "junit.xml",
            "--output-dir",
            "out",
            "--base",
            str(base),
            "--",
        ],
    )
    assert empty.returncode == 2
    missing_separator = _cli(
        base,
        [
            "--timeout",
            "1",
            "--dump-margin",
            "0.2",
            "--expected-evidence",
            "junit.xml",
            "--output-dir",
            "out",
        ],
    )
    assert missing_separator.returncode == 2
    bad_timeout = _cli(
        base,
        [
            "--timeout",
            "0",
            "--dump-margin",
            "0.2",
            "--expected-evidence",
            "junit.xml",
            "--output-dir",
            "out",
            "--base",
            str(base),
            "--",
            sys.executable,
            "-c",
            "import sys; sys.exit(0)",
        ],
    )
    assert bad_timeout.returncode == 2
    bad_margin = _cli(
        base,
        [
            "--timeout",
            "1",
            "--dump-margin",
            "-1",
            "--expected-evidence",
            "junit.xml",
            "--output-dir",
            "out",
            "--base",
            str(base),
            "--",
            sys.executable,
            "-c",
            "import sys; sys.exit(0)",
        ],
    )
    assert bad_margin.returncode == 2


def test_memory_error_keeps_traceback_without_claiming_oom(tmp_path: Path) -> None:
    evidence = tmp_path / "junit.xml"
    _, manifest = _run(
        tmp_path,
        [sys.executable, "-c", "raise MemoryError('synthetic-memory-error')"],
        evidence,
    )
    assert manifest.status == "NONZERO_EXIT"
    assert manifest.exit_code == 1
    assert manifest.wrapper_exit_code == 1
    assert manifest.oom_inferred is False
    stderr = (tmp_path / str(_disk_manifest(tmp_path)["stderr_file"])).read_text(
        encoding="utf-8",
        errors="replace",
    )
    assert "Traceback" in stderr
    assert "MemoryError" in stderr
    assert "synthetic-memory-error" in stderr


def test_relative_base_and_rejected_escape(tmp_path: Path) -> None:
    base = tmp_path / "base"
    elsewhere = tmp_path / "elsewhere"
    base.mkdir()
    elsewhere.mkdir()
    evidence = base / "junit.xml"
    completed = _cli(
        elsewhere,
        [
            "--timeout",
            "5",
            "--dump-margin",
            "0.2",
            "--expected-evidence",
            "junit.xml",
            "--output-dir",
            "diag",
            "--base",
            str(base),
            "--",
            *_junit_writer(base, evidence),
        ],
    )
    assert completed.returncode == 0
    assert not (elsewhere / "diag").exists()
    assert list((base / "diag").rglob("diagnostic_manifest.json"))

    outside = tmp_path / "outside"
    escaped = _cli(
        base,
        [
            "--timeout",
            "5",
            "--dump-margin",
            "0.2",
            "--expected-evidence",
            "junit.xml",
            "--output-dir",
            "../outside",
            "--base",
            str(base),
            "--",
            *_python_script(base, "ok.py", "import sys\nsys.exit(0)\n"),
        ],
    )
    assert escaped.returncode == 2
    assert not outside.exists()


def test_parallel_runs_do_not_overwrite_logs(tmp_path: Path) -> None:
    output = tmp_path / "shared"
    errors: list[BaseException] = []

    def _once(token: str) -> None:
        try:
            evidence = tmp_path / f"{token}.xml"
            command = _python_script(
                tmp_path,
                f"{token}.py",
                "import pathlib, sys\n"
                f"pathlib.Path(sys.argv[1]).write_text({JUNIT!r}, encoding='utf-8')\n"
                "print(sys.argv[2])\n",
                str(evidence),
                token,
            )
            manifest = _adapter(tmp_path).run(command, evidence, output, base=tmp_path)
            if manifest.wrapper_exit_code != 0:
                raise AssertionError(manifest.evidence_reason)
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=_once, args=(token,))
        for token in ("alpha-token", "beta-token")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert errors == []
    manifests = list(output.rglob("diagnostic_manifest.json"))
    assert len(manifests) == 2
    stdout_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in output.rglob("stdout.log")
    )
    assert "alpha-token" in stdout_text
    assert "beta-token" in stdout_text


def test_secret_arguments_are_not_published(tmp_path: Path) -> None:
    evidence = tmp_path / "junit.xml"
    secret = "super-secret-value-12069"
    command = [
        *_junit_writer(tmp_path, evidence),
        "--token",
        secret,
        "--access-token",
        secret,
        "--github-token",
        secret,
        f"--client-secret={secret}",
    ]
    _, manifest = _run(tmp_path, command, evidence)
    assert manifest.wrapper_exit_code == 0
    published = (tmp_path / str(_disk_manifest(tmp_path)["manifest_file"])).read_text(
        encoding="utf-8"
    )
    assert secret not in published
    assert "environ" not in json.loads(published)


_LIGHT_ADDOPTS = "-q --tb=line --noconftest -p no:cacheprovider -p no:xdist"


def _resilient_args(target: Path, reports: Path) -> list[str]:
    return [
        "--target",
        str(target),
        "--reports-dir",
        str(reports),
        "--skip-serial-pass",
        "--parallel-timeout-seconds",
        "180",
        "--fallback-timeout-seconds",
        "180",
        "--parallel-marker",
        "not memory",
        "--parallel-addopts",
        _LIGHT_ADDOPTS,
        "--fallback-addopts",
        _LIGHT_ADDOPTS,
    ]


def test_target_accepts_every_affected_path() -> None:
    """Affected pytest passes every selected path after one --target flag."""
    args = _create_parser().parse_args(
        [
            "--target",
            "tests/a.py",
            "tests/b.py",
            "--reports-dir",
            "reports/quality",
        ]
    )
    assert args.target == ["tests/a.py", "tests/b.py"]


def test_resilient_runner_propagates_failure_and_success(tmp_path: Path) -> None:
    failing = tmp_path / "test_fail.py"
    failing.write_text("def test_fail():\n    assert False\n", encoding="utf-8")
    reports = tmp_path / "reports-fail"
    failure = resilient_main(_resilient_args(failing, reports))
    assert failure != 0
    manifest_path = next(reports.rglob("diagnostic_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["status"] == "NONZERO_EXIT"
    assert payload["wrapper_exit_code"] == failure
    assert payload["oom_inferred"] is False
    junit = reports / "junit_parallel.xml"
    assert junit.is_file() and junit.stat().st_size > 0
    assert not junit_file_is_complete(manifest_path)
    assert not (reports / "junit_fallback.xml").exists()

    passing = tmp_path / "test_ok.py"
    passing.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    ok_reports = tmp_path / "reports-ok"
    success = resilient_main(_resilient_args(passing, ok_reports))
    assert success == 0
    ok_payload = json.loads(
        next(ok_reports.rglob("diagnostic_manifest.json")).read_text(encoding="utf-8")
    )
    assert ok_payload["status"] == "NORMAL_EXIT"
    assert ok_payload["evidence_reason"] == "fresh_junit"
    assert (ok_reports / "junit_parallel.xml").is_file()


def test_runner_rejects_budget_that_cannot_cover_dump_margin(tmp_path: Path) -> None:
    code = resilient_main(
        [
            "--target",
            "tests-not-used",
            "--reports-dir",
            str(tmp_path / "reports"),
            "--skip-serial-pass",
            "--parallel-timeout-seconds",
            "1",
            "--parallel-addopts=-q",
        ]
    )
    assert code == 2


def test_serial_coverage_budget_fits_job_and_pytest_timeout() -> None:
    budget = serial_coverage_pass_budget_seconds()
    assert budget == (
        SERIAL_COVERAGE_JOB_TIMEOUT_SECONDS
        - SERIAL_COVERAGE_SETUP_RESERVE_SECONDS
        - SERIAL_COVERAGE_UPLOAD_RESERVE_SECONDS
    )
    assert budget == 660
    watchdog = budget - DIAGNOSTIC_DUMP_MARGIN_SECONDS
    assert (
        SERIAL_COVERAGE_SETUP_RESERVE_SECONDS
        + watchdog
        + DIAGNOSTIC_DUMP_MARGIN_SECONDS
        + SERIAL_COVERAGE_UPLOAD_RESERVE_SECONDS
        == SERIAL_COVERAGE_JOB_TIMEOUT_SECONDS
    )
    assert budget > PYTEST_PER_TEST_TIMEOUT_SECONDS + DIAGNOSTIC_DUMP_MARGIN_SECONDS
    workflow = (_repo_root() / ".github/workflows/tests.yml").read_text(
        encoding="utf-8"
    )
    serial = workflow.split("  serial-coverage:\n", 1)[1].split(
        "\n  coverage-verify:", 1
    )[0]
    assert "timeout-minutes: 15" in serial
    assert "--parallel-timeout-seconds 660" in serial
    assert "--no-fallback" in serial
    assert "junit_parallel.xml" in serial
    assert "serial-coverage-abort-diagnostics" in serial
    assert "diagnostic_manifest.json" not in serial.split("junit_parallel.xml", 1)[0]


def test_source_only_adapter_change_selects_this_test() -> None:
    targets = affected_pytest_targets(
        ["scripts/engineering/ci/pytest_abort_diagnostic_adapter.py"],
        repo_root=_repo_root(),
    )
    assert any(
        target.endswith("test_pytest_abort_diagnostic_adapter.py") for target in targets
    )


def test_evidence_symlink_is_rejected_before_spawn(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    target = base / "unrelated.txt"
    target.write_text("keep-me", encoding="utf-8")
    link = base / "junit.xml"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("this environment cannot create a file symlink")
    marker = base / "spawned.txt"
    manifest = _adapter(base).run(
        _python_script(
            base,
            "would-spawn.py",
            "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('spawned', encoding='utf-8')\n",
            str(marker),
        ),
        link,
        base / "out",
        base=base,
    )
    assert manifest.status == "INVALID_INVOCATION"
    assert manifest.wrapper_exit_code == 2
    assert target.read_text(encoding="utf-8") == "keep-me"
    assert not marker.exists()


def test_unreadable_evidence_does_not_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = tmp_path / "junit.xml"
    _write_junit(evidence)
    real_open = Path.open

    def locked(self: Path, *args: object, **kwargs: object) -> object:
        if self.name == "junit.xml":
            raise OSError("locked")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", locked)
    marker = tmp_path / "spawned.txt"
    _, manifest = _run(
        tmp_path,
        _python_script(
            tmp_path,
            "would-spawn.py",
            "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('spawned', encoding='utf-8')\n",
            str(marker),
        ),
        evidence,
    )
    assert manifest.evidence_reason == "unreadable"
    assert manifest.evidence_valid is False
    assert manifest.wrapper_exit_code != 0
    assert _disk_manifest(tmp_path)["evidence_reason"] == "unreadable"
    assert not marker.exists()


def test_no_fallback_skips_second_pass_after_timeout(tmp_path: Path) -> None:
    sleeping = tmp_path / "test_sleep.py"
    sleeping.write_text(
        "import time\n\ndef test_sleep() -> None:\n    time.sleep(30)\n",
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    code = resilient_main(
        [
            *_resilient_args(sleeping, reports),
            "--no-fallback",
            "--parallel-timeout-seconds",
            "20",
        ]
    )
    assert code == 124
    assert not (reports / "junit_fallback.xml").exists()
    summary = (reports / "summary.txt").read_text(encoding="utf-8")
    assert "fallback_skipped=true" in summary


def test_symlink_output_escape_is_rejected(tmp_path: Path) -> None:
    base = tmp_path / "base"
    outside = tmp_path / "outside"
    base.mkdir()
    outside.mkdir()
    link = base / "linked-out"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("this environment cannot create a directory symlink")
    escaped = _adapter(base).run(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
        base / "junit.xml",
        link,
        base=base,
    )
    assert escaped.status == "INVALID_INVOCATION"
    assert escaped.wrapper_exit_code == 2
    assert list(outside.rglob("diagnostic_manifest.json")) == []


def test_journal_child_identity_survives_supervision(tmp_path: Path) -> None:
    evidence = tmp_path / "junit.xml"
    child_env = os.environ.copy()
    child_env["BIOETL_JOURNAL_INVOCATION_ID"] = "synthetic-invocation"
    child_env["BIOETL_JOURNAL_PASS"] = "parallel"
    command = _python_script(
        tmp_path,
        "journal-identity.py",
        "import os, pathlib, sys\n"
        "assert os.environ['BIOETL_JOURNAL_INVOCATION_ID'] == 'synthetic-invocation'\n"
        "assert os.environ['BIOETL_JOURNAL_PASS'] == 'parallel'\n"
        "assert os.environ['PYTHONFAULTHANDLER'] == '1'\n"
        f"pathlib.Path(sys.argv[1]).write_text({JUNIT!r}, encoding='utf-8')\n",
        str(evidence),
    )
    adapter = PytestAbortDiagnosticAdapter(
        timeout=5, dump_margin=0.4, base=tmp_path, child_env=child_env
    )
    child_env["BIOETL_JOURNAL_PASS"] = "mutated-after-construction"
    manifest = adapter.run(command, evidence, tmp_path / "out")
    assert manifest.wrapper_exit_code == 0
    assert child_env["BIOETL_JOURNAL_PASS"] == "mutated-after-construction"


@pytest.mark.skipif(
    os.name != "posix" or not Path("/proc").is_dir(),
    reason="POSIX signal integration requires /proc descendant discovery",
)
def test_native_child_timeout_dumps_python_runner_and_reaps_child(
    tmp_path: Path,
) -> None:
    import shutil
    import time

    sleep = shutil.which("sleep")
    if sleep is None:
        pytest.skip("native sleep executable unavailable")
    pid_file = tmp_path / "native.pid"
    started = time.monotonic()
    try:
        _, manifest = _run(
            tmp_path,
            _python_script(
                tmp_path,
                "native_runner.py",
                "import pathlib, subprocess, time\n"
                f"child = subprocess.Popen([{sleep!r}, '60'])\n"
                f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))\n"
                "child.wait()\n"
                "time.sleep(60)\n",
            ),
            tmp_path / "missing.xml",
            timeout=1.5,
            margin=1.0,
        )
        assert manifest.status == "WATCHDOG_TIMEOUT"
        assert manifest.wrapper_exit_code == 124
        assert (
            manifest.diagnostic_signal_delivery == "leaf_descendants_then_process_group"
        )
        diagnostic = (tmp_path / manifest.stderr_file).read_text()
        assert "Fatal Python error: Aborted" in diagnostic
        assert "native_runner.py" in diagnostic
        assert not _pid_alive(int(pid_file.read_text()))
        assert "cleanup_incomplete" not in (manifest.cleanup_error or "")
        assert time.monotonic() - started < 10
    finally:
        if pid_file.exists() and _pid_alive(int(pid_file.read_text())):
            _terminate_pid(int(pid_file.read_text()))


def test_disappearing_leaves_really_fall_back_to_launcher(monkeypatch) -> None:
    import signal
    from types import SimpleNamespace
    from scripts.engineering.ci import pytest_abort_diagnostic_adapter as owner

    if os.name != "posix":
        pytest.skip("POSIX signal delivery")
    delivered = []
    monkeypatch.setattr(owner, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(owner, "_descendant_pids", lambda pid: set())

    def disappeared(pid, sig):
        raise ProcessLookupError(pid)

    monkeypatch.setattr(owner.os, "kill", disappeared)
    monkeypatch.setattr(
        owner.os, "killpg", lambda pid, sig: delivered.append((pid, sig))
    )
    result = owner._deliver_diagnostic_signal(SimpleNamespace(pid=101), {202, 203})
    assert result == ("process_group", signal.SIGABRT)
    assert delivered == [(101, signal.SIGABRT)]


def test_runner_accepts_multiple_pytest_targets() -> None:
    from scripts.engineering.ci.run_pytest_resilient import _create_parser

    parsed = _create_parser().parse_args(
        ["--target", "tests/a.py", "tests/b.py", "--no-fallback"]
    )
    assert parsed.target == ["tests/a.py", "tests/b.py"]
