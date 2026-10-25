"""Isolated supervisor for pytest abort diagnostics.

Approach B keeps this process outside pytest. It records a sidecar manifest
and does not synthesize JUnit, change completeness gates, or infer host OOM
from a silent abort, SIGKILL, or a missing report.

Exit 0 is returned only when the child exits 0 and this run produced a new
well-formed JUnit file. Signal abort, watchdog timeout, spawn failure, stale
or unusable evidence, and a manifest that cannot be saved are nonzero.

``-X faulthandler`` is a Python interpreter flag. Callers may pass it in the
supervised argv; it is not a pytest addopt. ``PYTHONFAULTHANDLER=1`` is set
only in the child environment and is not copied into the manifest.

POSIX delivers ``SIGABRT`` to leaf descendants first so launchers can reap
them. With no descendants it signals the isolated process group.
Native Windows does not support ``Popen.send_signal(SIGABRT)``; the timeout
path terminates the recorded descendant tree and stays nonzero, without
claiming a faulthandler dump. A result observed on one platform is not
evidence for the other.

The manifest is not guaranteed if this supervisor itself is killed with
SIGKILL. Core dumps are not diagnostic artifacts and are not published.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import signal
import stat
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import IO

from scripts.engineering.common.repo_paths import (
    confined_io_path,
    ensure_safe_cli_argv,
    open_confined,
    write_text_confined,
)

PYTEST_PER_TEST_TIMEOUT_SECONDS = 60
DIAGNOSTIC_DUMP_MARGIN_SECONDS = 15
SERIAL_COVERAGE_JOB_TIMEOUT_SECONDS = 15 * 60
SERIAL_COVERAGE_SETUP_RESERVE_SECONDS = 180
SERIAL_COVERAGE_UPLOAD_RESERVE_SECONDS = 60
_LAUNCHER_REAP_SECONDS = 1.0
_MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
_SECRET_PREFIXES = (
    "--token",
    "--password",
    "--secret",
    "--api-key",
    "--apikey",
)
_SECRET_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "credential",
)
_JUNIT_TAGS = frozenset({"testsuite", "testsuites"})


def serial_coverage_pass_budget_seconds() -> int:
    """Pass budget that finishes before the serial-coverage job timeout.

    Checkout and interpreter setup run before the watchdog starts, and the
    artifact upload runs after it. Both are reserved so a timeout can still
    deliver the diagnostic signal and persist the manifest inside the job.
    """
    return (
        SERIAL_COVERAGE_JOB_TIMEOUT_SECONDS
        - SERIAL_COVERAGE_SETUP_RESERVE_SECONDS
        - SERIAL_COVERAGE_UPLOAD_RESERVE_SECONDS
    )


def child_watchdog_seconds(
    total_budget: float,
    *,
    dump_margin: float = DIAGNOSTIC_DUMP_MARGIN_SECONDS,
) -> float:
    """Return the pre-signal wait inside a caller budget.

    The remaining margin is reserved for the diagnostic signal and cleanup.
    The result stays above pytest's per-test timeout when the caller budget
    is the serial-coverage pass budget.
    """
    if not _positive_finite(total_budget) or not _positive_finite(dump_margin):
        raise ValueError("timeout budget and dump margin must be finite and > 0")
    if total_budget <= dump_margin:
        raise ValueError(
            "pass budget must exceed the dump margin so cleanup can finish"
        )
    return total_budget - dump_margin


def _positive_finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


@dataclass
class DiagnosticManifest:
    """One supervised run. Paths are relative to the explicit base."""

    status: str
    exit_code: int | None
    signal: int | None
    stdout_file: str
    stderr_file: str
    missing_evidence: bool
    evidence_valid: bool
    evidence_reason: str
    wrapper_exit_code: int
    run_id: str
    manifest_file: str
    diagnostic_signal_sent: int | None = None
    diagnostic_signal_delivery: str = "not_needed"
    diagnostics_persisted: bool = False
    oom_inferred: bool = False
    supervisor_sigkill_preserves_diagnostics: bool = False
    core_dumps_are_not_diagnostic_artifacts: bool = True
    platform: str = ""
    cleanup_error: str | None = None
    command: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        payload = asdict(self)
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def wrapper_exit_code(manifest: DiagnosticManifest) -> int:
    """Map a manifest to a process status. Zero is success only."""
    if manifest.status == "INVALID_INVOCATION":
        return 2
    if not manifest.diagnostics_persisted:
        return 3
    if manifest.status == "SPAWN_FAILURE":
        return 127
    if manifest.status == "WATCHDOG_TIMEOUT":
        return 124
    if manifest.status == "INTERRUPTED":
        return 130
    if manifest.status == "SIGNAL_ABORT":
        return _signal_wrapper_status(manifest)
    if manifest.exit_code is not None and manifest.exit_code > 0:
        return manifest.exit_code
    if not manifest.evidence_valid:
        return 4
    if (
        manifest.status == "NORMAL_EXIT"
        and manifest.exit_code == 0
        and manifest.evidence_valid
    ):
        return 0
    return 1


def _signal_wrapper_status(manifest: DiagnosticManifest) -> int:
    if manifest.signal is not None and manifest.signal > 0:
        return 128 + manifest.signal
    if manifest.exit_code is not None and manifest.exit_code > 0:
        return manifest.exit_code
    return 1


def junit_file_is_complete(path: Path) -> bool:
    """Return whether ``path`` is a fresh-looking JUnit document.

    A diagnostic manifest never satisfies this check.
    """
    if path.name == "diagnostic_manifest.json":
        return False
    return _junit_well_formed(path)


class PytestAbortDiagnosticAdapter:
    """Supervise one command in an isolated tree and write a sidecar."""

    def __init__(
        self,
        timeout: float | None = 60,
        dump_margin: float = DIAGNOSTIC_DUMP_MARGIN_SECONDS,
        *,
        base: Path | None = None,
        child_env: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.dump_margin = dump_margin
        self.base = base
        self.child_env = None if child_env is None else child_env.copy()

    def run(
        self,
        cmd: list[str],
        expected_evidence: Path | None,
        output_dir: Path,
        *,
        base: Path | None = None,
    ) -> DiagnosticManifest:
        """Run ``cmd``. Relative paths resolve against ``base``."""
        root = (base or self.base or Path.cwd()).expanduser().resolve(strict=False)
        run_id = uuid.uuid4().hex
        manifest = _empty_manifest(run_id=run_id, command=_redact_argv(cmd))
        if not _invocation_is_valid(cmd, self.timeout, self.dump_margin):
            manifest.status = "INVALID_INVOCATION"
            manifest.evidence_reason = "invalid_invocation"
            manifest.wrapper_exit_code = 2
            return manifest
        try:
            run_dir = _run_directory(output_dir, run_id, root)
            evidence = _optional_evidence_path(expected_evidence, root)
        except (OSError, ValueError) as exc:
            manifest.status = "INVALID_INVOCATION"
            manifest.evidence_reason = "path_rejected"
            manifest.cleanup_error = str(exc)
            manifest.wrapper_exit_code = 2
            return manifest
        manifest.stdout_file = _relative(run_dir / "stdout.log", root)
        manifest.stderr_file = _relative(run_dir / "stderr.log", root)
        manifest.manifest_file = _relative(run_dir / "diagnostic_manifest.json", root)
        before = _snapshot_evidence(evidence)
        if before is not None and before.get("kind") == "unreadable":
            manifest.status = "EVIDENCE_UNAVAILABLE"
            manifest.evidence_reason = "unreadable"
            manifest.evidence_valid = False
            _finalize(manifest, root)
            return manifest
        try:
            return self._execute(cmd, evidence, before, root, run_dir, manifest)
        except KeyboardInterrupt:
            launcher = getattr(self, "_launcher_pid", None)
            recorded = (
                _descendant_pids(launcher) if isinstance(launcher, int) else set()
            )
            _terminate_recorded(
                launcher if isinstance(launcher, int) else None, recorded
            )
            manifest.status = "INTERRUPTED"
            _finalize(manifest, root)
            raise

    def _execute(
        self,
        cmd: list[str],
        evidence: Path | None,
        before: dict[str, object] | None,
        root: Path,
        run_dir: Path,
        manifest: DiagnosticManifest,
    ) -> DiagnosticManifest:
        try:
            argv = ensure_safe_cli_argv([str(token) for token in cmd])
        except ValueError as exc:
            manifest.status = "INVALID_INVOCATION"
            manifest.evidence_reason = "unsafe_argv"
            manifest.cleanup_error = str(exc)
            manifest.wrapper_exit_code = 2
            return manifest
        env = os.environ.copy() if self.child_env is None else self.child_env.copy()
        env["PYTHONFAULTHANDLER"] = "1"
        try:
            stdout = open_confined(
                run_dir / "stdout.log",
                "xb",
                root=root,
                allow_external_absolute=False,
            )
            stderr = open_confined(
                run_dir / "stderr.log",
                "xb",
                root=root,
                allow_external_absolute=False,
            )
        except (OSError, ValueError) as exc:
            manifest.status = "INVALID_INVOCATION"
            manifest.evidence_reason = "diagnostic_path_rejected"
            manifest.cleanup_error = str(exc)
            manifest.wrapper_exit_code = 2
            return manifest
        with stdout, stderr:
            return self._supervise(
                argv, env, stdout, stderr, evidence, before, root, manifest
            )

    def _supervise(
        self,
        argv: list[str],
        env: dict[str, str],
        stdout: IO[str] | IO[bytes],
        stderr: IO[str] | IO[bytes],
        evidence: Path | None,
        before: dict[str, object] | None,
        root: Path,
        manifest: DiagnosticManifest,
    ) -> DiagnosticManifest:
        try:
            proc = _spawn(argv, env, stdout, stderr)
        except OSError as exc:
            manifest.status = "SPAWN_FAILURE"
            manifest.evidence_reason = "spawn_failure"
            manifest.cleanup_error = str(exc)
            _assess_into(manifest, evidence, before)
            _finalize(manifest, root)
            return manifest
        self._launcher_pid = proc.pid
        timed_out = False
        delivery = "not_needed"
        sent: int | None = None
        try:
            if self.timeout is None:
                proc.wait()
            elif not _wait_bounded(proc, float(self.timeout)):
                timed_out = True
                recorded = _descendant_pids(proc.pid)
                delivery, sent = _deliver_diagnostic_signal(proc, recorded)
                if delivery == "leaf_descendants":
                    # Give waiting parents time to reap native/Python leaves,
                    # then dump a still-running Python launcher as well.
                    deadline = time.monotonic() + self.dump_margin
                    if not _wait_bounded(proc, self.dump_margin / 2):
                        fallback, sent = _deliver_diagnostic_signal(proc)
                        delivery = f"leaf_descendants_then_{fallback}"
                        _wait_bounded(proc, max(0, deadline - time.monotonic()))
                elif delivery == "process_group":
                    _wait_bounded(proc, self.dump_margin)
                recorded |= _descendant_pids(proc.pid)
                cleanup_error = _terminate_recorded(proc.pid, recorded)
                manifest.cleanup_error = cleanup_error or None
        finally:
            if proc.poll() is None:
                _terminate_recorded(proc.pid, _descendant_pids(proc.pid))
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                manifest.cleanup_error = "launcher_reap_timeout"
        manifest.exit_code = proc.returncode
        manifest.status, manifest.signal = _classify(
            proc.returncode, timed_out=timed_out
        )
        manifest.diagnostic_signal_delivery = delivery
        manifest.diagnostic_signal_sent = sent
        _assess_into(manifest, evidence, before)
        _finalize(manifest, root)
        return manifest


def _empty_manifest(*, run_id: str, command: list[str]) -> DiagnosticManifest:
    return DiagnosticManifest(
        status="UNKNOWN",
        exit_code=None,
        signal=None,
        stdout_file="",
        stderr_file="",
        missing_evidence=True,
        evidence_valid=False,
        evidence_reason="not_configured",
        wrapper_exit_code=1,
        run_id=run_id,
        manifest_file="",
        platform=sys.platform,
        command=command,
    )


def _invocation_is_valid(
    cmd: list[str], timeout: float | None, dump_margin: float
) -> bool:
    if not cmd or any(not str(token).strip() for token in cmd):
        return False
    if not _positive_finite(dump_margin):
        return False
    return timeout is None or _positive_finite(timeout)


def _run_directory(output_dir: Path, run_id: str, root: Path) -> Path:
    if not run_id.isalnum():
        raise ValueError("run id must be alphanumeric")
    _refuse_symlink_components(output_dir, root)
    confined = confined_io_path(output_dir, root=root, allow_external_absolute=False)
    confined.mkdir(parents=True, exist_ok=True)
    run_dir = confined_io_path(
        confined / run_id, root=root, allow_external_absolute=False
    )
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


def _optional_evidence_path(path: Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    _refuse_symlink_components(path, root)
    return confined_io_path(path, root=root, allow_external_absolute=False)


def _refuse_symlink_components(path: Path, root: Path) -> None:
    """Reject a path before ``resolve`` follows a symlink to another file."""
    raw = path.expanduser()
    base = root.expanduser()
    candidate = raw if raw.is_absolute() else base / raw
    try:
        parts = candidate.relative_to(base).parts
    except ValueError:
        return
    current = base
    for part in parts:
        if part in {"", "."}:
            continue
        current = current / part
        try:
            linked = current.is_symlink() or (
                hasattr(current, "is_junction") and current.is_junction()
            )
        except OSError as exc:
            raise ValueError(f"refusing unreadable path: {current.as_posix()}") from exc
        if linked:
            raise ValueError(f"refusing symlink component: {current.as_posix()}")
        if not current.exists():
            return


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve(strict=False)
    return resolved.relative_to(root.resolve(strict=False)).as_posix()


def _classify(exit_code: int | None, *, timed_out: bool) -> tuple[str, int | None]:
    if timed_out:
        signal_number = -exit_code if exit_code is not None and exit_code < 0 else None
        return "WATCHDOG_TIMEOUT", signal_number
    if exit_code is None:
        return "SPAWN_FAILURE", None
    if exit_code == 0:
        return "NORMAL_EXIT", None
    if exit_code > 0:
        return "NONZERO_EXIT", None
    return "SIGNAL_ABORT", -exit_code


def _assess_into(
    manifest: DiagnosticManifest,
    evidence: Path | None,
    before: dict[str, object] | None,
) -> None:
    valid, reason = _assess_evidence(evidence, before)
    manifest.evidence_valid = valid
    manifest.evidence_reason = reason
    manifest.missing_evidence = reason in {"missing", "not_configured"}


def _finalize(manifest: DiagnosticManifest, root: Path) -> None:
    manifest.diagnostics_persisted = bool(manifest.manifest_file)
    manifest.wrapper_exit_code = wrapper_exit_code(manifest)
    if not manifest.manifest_file:
        return
    target = root / manifest.manifest_file
    try:
        _atomic_json(target, manifest.to_json(), root)
    except (OSError, ValueError) as exc:
        manifest.diagnostics_persisted = False
        manifest.cleanup_error = str(exc)
        manifest.wrapper_exit_code = wrapper_exit_code(manifest)


def _atomic_json(path: Path, text: str, root: Path) -> None:
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    write_text_confined(temporary, text, root=root, allow_external_absolute=False)
    confined_target = confined_io_path(path, root=root, allow_external_absolute=False)
    confined_temporary = confined_io_path(
        temporary, root=root, allow_external_absolute=False
    )
    os.replace(confined_temporary, confined_target)


def _snapshot_evidence(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    try:
        if not path.exists():
            return None
        stat_result = path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        return {"kind": "unreadable"}
    if not stat.S_ISREG(stat_result.st_mode):
        return {"kind": "non_regular"}
    if path.is_symlink() or stat_result.st_size > _MAX_EVIDENCE_BYTES:
        return {"kind": "file", "sha256": None, "size": stat_result.st_size}
    try:
        digest = _sha256(path)
    except OSError:
        return {"kind": "unreadable"}
    return {
        "kind": "file",
        "size": stat_result.st_size,
        "sha256": digest,
    }


def _assess_evidence(
    path: Path | None, before: dict[str, object] | None
) -> tuple[bool, str]:
    if path is None:
        return False, "not_configured"
    if not path.exists():
        return False, "missing"
    if path.is_symlink():
        return False, "symlink"
    if path.is_dir():
        return False, "directory"
    if not path.is_file():
        return False, "not_regular_file"
    size = path.stat().st_size
    if size == 0:
        return False, "empty"
    if size > _MAX_EVIDENCE_BYTES:
        return False, "too_large"
    digest = _sha256(path)
    if before and before.get("kind") == "file" and before.get("sha256") == digest:
        return False, "stale"
    if not _junit_well_formed(path):
        return False, "malformed"
    return True, "fresh_junit"


def _junit_well_formed(path: Path) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        return False
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return False
    tag = root.tag.rsplit("}", 1)[-1]
    return tag in _JUNIT_TAGS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redact_argv(argv: list[str]) -> list[str]:
    redacted: list[str] = []
    hide_next = False
    for token in argv:
        if hide_next:
            redacted.append("[REDACTED]")
            hide_next = False
            continue
        flag, separator, _value = token.partition("=")
        if _secret_flag(flag) and separator:
            redacted.append(f"{flag}=[REDACTED]")
            continue
        if _secret_flag(token):
            redacted.append(token)
            hide_next = True
            continue
        redacted.append(token[:200])
    return redacted


def _secret_flag(token: str) -> bool:
    lowered = token.lower()
    if lowered in _SECRET_PREFIXES:
        return True
    compact = lowered.lstrip("-").replace("-", "_")
    if compact in _SECRET_KEY_PARTS:
        return True
    parts = [part for part in compact.split("_") if part]
    if any(part in _SECRET_KEY_PARTS for part in parts):
        return True
    return any(
        f"{left}_{right}" in _SECRET_KEY_PARTS
        for left, right in itertools.pairwise(parts)
    )


def _spawn(
    argv: list[str],
    env: dict[str, str],
    stdout: IO[str] | IO[bytes],
    stderr: IO[str] | IO[bytes],
) -> subprocess.Popen[bytes]:
    if os.name == "posix":
        return subprocess.Popen(
            argv,
            stdout=stdout,
            stderr=stderr,
            env=env,
            start_new_session=True,
        )
    return subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=env)


def _wait_bounded(proc: subprocess.Popen[bytes], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while proc.poll() is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            return False
    return True


def _abort_leaves(leaves: set[int]) -> bool:
    """Signal live leaves, allowing vanished processes to fall back to the group."""
    delivered = False
    for pid in sorted(leaves):
        try:
            os.kill(pid, signal.SIGABRT)
            delivered = True
        except ProcessLookupError:
            continue
    return delivered


def _deliver_diagnostic_signal(
    proc: subprocess.Popen[bytes],
    descendants: set[int] | None = None,
) -> tuple[str, int | None]:
    """Abort leaves before launchers so waiting parents can reap their children."""
    if os.name != "posix":
        return "unsupported", None
    leaves = {
        pid
        for pid in (descendants or set())
        if _pid_alive(pid) and not _descendant_pids(pid)
    }
    try:
        if _abort_leaves(leaves):
            return "leaf_descendants", signal.SIGABRT
    except OSError:
        return "error", signal.SIGABRT
    # All leaves disappeared between discovery and delivery: actually signal
    # the launcher group rather than claiming a delivery that never happened.
    try:
        os.killpg(proc.pid, signal.SIGABRT)
    except ProcessLookupError:
        return "already_exited", signal.SIGABRT
    except OSError:
        return "error", signal.SIGABRT
    return "process_group", signal.SIGABRT


def _terminate_recorded(launcher_pid: int | None, descendants: set[int]) -> str:
    if launcher_pid is None:
        return ""
    errors: list[str] = []
    victims = [
        pid
        for pid in descendants
        if pid > 0 and pid != os.getpid() and pid != launcher_pid
    ]
    for pid in victims:
        error = _terminate_pid(pid)
        if error:
            errors.append(error)
    if _pid_alive(launcher_pid):
        _wait_pids_dead({launcher_pid}, timeout=_LAUNCHER_REAP_SECONDS)
    if _pid_alive(launcher_pid):
        error = _terminate_pid(launcher_pid)
        if error:
            errors.append(error)
    if os.name == "posix":
        try:
            os.killpg(launcher_pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError) as exc:
            errors.append(f"killpg:{exc.__class__.__name__}")
    survivors = _wait_pids_dead(set(victims) | {launcher_pid})
    if survivors:
        errors.append("cleanup_incomplete:" + ",".join(str(pid) for pid in survivors))
    return "; ".join(errors)


def _wait_pids_dead(pids: set[int], *, timeout: float = 2.0) -> list[int]:
    deadline = time.monotonic() + timeout
    alive = {pid for pid in pids if pid > 0}
    while alive and time.monotonic() < deadline:
        alive = {pid for pid in alive if _pid_alive(pid)}
        if alive:
            time.sleep(0.05)
    return sorted(alive)


def _terminate_pid(pid: int) -> str:
    if os.name == "nt":
        return _windows_terminate(pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return ""
    except OSError as exc:
        return f"{pid}:{exc.__class__.__name__}"
    return ""


def _posix_pid_exited(pid: int) -> bool:
    """Linux zombies retain a PID but cannot execute or survive cleanup."""
    try:
        stat = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return False
    marker = stat.rfind(")")
    fields = stat[marker + 2 :].split() if marker >= 0 else []
    return bool(fields and fields[0] in {"Z", "X"})


def _pid_alive(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    if os.name == "nt":
        return _windows_pid_alive(pid)
    if _posix_pid_exited(pid):
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    if sys.platform.startswith("linux"):
        try:
            stat_file = Path(f"/proc/{pid}/stat")
            if stat_file.exists():
                stat_content = stat_file.read_text(encoding="utf-8")
                rparen_idx = stat_content.rfind(")")
                if rparen_idx != -1 and len(stat_content) > rparen_idx + 2:
                    state = stat_content[rparen_idx + 2]
                    if state == "Z":
                        return False
        except OSError:
            pass

    return True


def _descendant_pids(root_pid: int) -> set[int]:
    if root_pid <= 0 or root_pid == os.getpid():
        return set()
    if os.name == "nt":
        return _windows_descendants(root_pid)
    return _posix_descendants(root_pid)


def _posix_descendants(root_pid: int) -> set[int]:
    children: dict[int, list[int]] = {}
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return set()
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        parent = _posix_ppid(entry)
        if parent is None:
            continue
        children.setdefault(parent, []).append(int(entry.name))
    return _walk_children(root_pid, children)


def _posix_ppid(entry: Path) -> int | None:
    try:
        stat_text = (entry / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    marker = stat_text.rfind(")")
    if marker < 0:
        return None
    fields = stat_text[marker + 2 :].split()
    if len(fields) < 2:
        return None
    try:
        return int(fields[1])
    except ValueError:
        return None


def _walk_children(root_pid: int, children: dict[int, list[int]]) -> set[int]:
    found: set[int] = set()
    stack = list(children.get(root_pid, []))
    while stack:
        pid = stack.pop()
        if pid in found or pid == os.getpid() or pid <= 0 or pid == root_pid:
            continue
        found.add(pid)
        stack.extend(children.get(pid, []))
    return found


def _windows_descendants(root_pid: int) -> set[int]:
    snapshot = _windows_parent_map()
    children: dict[int, list[int]] = {}
    for pid, parent in snapshot.items():
        children.setdefault(parent, []).append(pid)
    return _walk_children(root_pid, children)


def _windows_parent_map() -> dict[int, int]:
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if not snapshot:
        return {}
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(ProcessEntry)
    parents: dict[int, int] = {}
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return {}
        while True:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return parents


def _windows_terminate(pid: int) -> str:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(0x0001, False, wintypes.DWORD(pid))
    if not handle:
        return ""
    try:
        if not kernel32.TerminateProcess(handle, 1):
            return f"{pid}:TerminateProcess"
    finally:
        kernel32.CloseHandle(handle)
    return ""


def _windows_pid_alive(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(0x1000, False, wintypes.DWORD(pid))
    if not handle:
        return False
    code = wintypes.DWORD()
    try:
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
    finally:
        kernel32.CloseHandle(handle)
    return code.value == 259


class _CliUsageError(Exception):
    """Argparse rejected the invocation without stopping the interpreter."""

    def __init__(self, code: int) -> None:
        super().__init__(str(code))
        self.code = code


class _CliParser(argparse.ArgumentParser):
    """Report usage failures as ``_CliUsageError`` instead of ``SystemExit``."""

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._print_message(message, sys.stderr)
        raise _CliUsageError(int(status))


def _parse_cli(argv: list[str]) -> tuple[argparse.Namespace, list[str]] | int:
    if "--" not in argv:
        sys.stderr.write("missing -- separator before the command\n")
        return 2
    split = argv.index("--")
    command = argv[split + 1 :]
    if not command or any(not token.strip() for token in command):
        sys.stderr.write("empty command\n")
        return 2
    parser = _CliParser(prog="pytest_abort_diagnostic_adapter")
    parser.add_argument("--timeout", required=True)
    parser.add_argument("--dump-margin", required=True)
    parser.add_argument("--expected-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--base", default="")
    try:
        args = parser.parse_args(argv[:split])
    except _CliUsageError as exc:
        return exc.code
    return args, command


def _cli_timeouts(args: argparse.Namespace) -> tuple[float, float] | int:
    try:
        timeout = float(args.timeout)
        margin = float(args.dump_margin)
    except (TypeError, ValueError):
        sys.stderr.write("timeout and dump-margin must be numbers\n")
        return 2
    if not _positive_finite(timeout) or not _positive_finite(margin):
        sys.stderr.write("timeout and dump-margin must be finite and > 0\n")
        return 2
    return timeout, margin


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Relative outputs resolve against ``--base`` or the cwd."""
    raw = list(sys.argv[1:] if argv is None else argv)
    parsed = _parse_cli(raw)
    if isinstance(parsed, int):
        return parsed
    args, command = parsed
    timeouts = _cli_timeouts(args)
    if isinstance(timeouts, int):
        return timeouts
    timeout, margin = timeouts
    base = Path(args.base) if str(args.base).strip() else Path.cwd()
    if not base.is_absolute():
        base = Path.cwd() / base
    adapter = PytestAbortDiagnosticAdapter(
        timeout=timeout, dump_margin=margin, base=base
    )
    try:
        manifest = adapter.run(
            command,
            Path(args.expected_evidence),
            Path(args.output_dir),
            base=base,
        )
    except KeyboardInterrupt:
        return 130
    sys.stdout.write(
        "status="
        f"{manifest.status} exit_code={manifest.exit_code} "
        f"signal={manifest.signal} wrapper={manifest.wrapper_exit_code} "
        f"evidence={manifest.evidence_reason}\n"
    )
    return manifest.wrapper_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
