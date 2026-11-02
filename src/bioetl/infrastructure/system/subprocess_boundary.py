"""Subprocess execution boundary for SEC-001 compliance.

This module provides a unified secure boundary for external command execution
with enforced properties:
- No shell injection (shell=False)
- A finite default timeout
- Standardized error handling
- Output size validation after capture (not a memory limit)
- Explicit environment handling
"""

from __future__ import annotations

import locale
import os
import shutil
import signal
import subprocess  # nosec B404 - see suppression registry
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from typing import IO, Any, TypedDict, Unpack, cast

_MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10MB
_DEFAULT_TIMEOUT_SECONDS = 300.0
_CLEANUP_TIMEOUT_SECONDS = 0.5

_PopenResult = subprocess.Popen[bytes] | subprocess.Popen[str]


class _PopenPlatformOptions(TypedDict, total=False):
    creationflags: int
    start_new_session: bool


class _PopenReaderOptions(TypedDict, total=False):
    bufsize: int
    env: Mapping[str, str] | None
    shell: bool
    stderr: int | IO[bytes] | None
    stdout: int | IO[bytes] | None


def _copy_env(env: Mapping[str, str] | None) -> dict[str, str] | None:
    if env is None:
        return None
    return dict(env)


def _output_size(
    output: str | bytes | None, *, encoding: str, errors: str | None
) -> int:
    if output is None:
        return 0
    if isinstance(output, bytes):
        return len(output)
    return len(output.encode(encoding, errors=errors or "strict"))


def _terminate_process_tree(
    proc: subprocess.Popen[
        Any
    ],  # Any: Popen stream type follows its text-mode setting.
) -> bool:
    """Terminate the command and its descendants where the OS supports groups."""
    tree_terminated = False
    try:
        if os.name == "posix":
            kill_process_group = cast(
                Callable[[int, int], None] | None, getattr(os, "killpg", None)
            )
            kill_signal = cast(int | None, getattr(signal, "SIGKILL", None))
            if kill_process_group is None or kill_signal is None:
                proc.kill()
                return tree_terminated
            kill_process_group(proc.pid, kill_signal)
            tree_terminated = True
        elif os.name == "nt":
            taskkill = shutil.which("taskkill")
            if taskkill is not None:
                try:
                    killer = subprocess.Popen(  # nosec B603 - see suppression registry
                        [taskkill, "/PID", str(proc.pid), "/T", "/F"],
                        shell=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    try:
                        tree_terminated = (
                            killer.wait(timeout=_CLEANUP_TIMEOUT_SECONDS) == 0
                        )
                    except subprocess.TimeoutExpired:
                        killer.kill()
                except OSError:
                    pass
            proc.kill()
        else:
            proc.kill()
    except (OSError, ProcessLookupError):
        pass
    return tree_terminated


def _cleanup_process(
    proc: subprocess.Popen[
        Any
    ],  # Any: Popen stream type follows its text-mode setting.
) -> None:
    """Stop a failed command and close pipes without waiting for inherited EOF."""
    tree_terminated = _terminate_process_tree(proc)
    # A descendant may have inherited stdout/stderr even after the direct
    # child exits. Never wait for those handles to reach EOF during cleanup.
    pipes = (proc.stdin, proc.stdout, proc.stderr) if tree_terminated else (proc.stdin,)
    for pipe in pipes:
        if pipe is not None:
            with suppress(OSError, ValueError):
                pipe.close()
    try:
        proc.wait(timeout=_CLEANUP_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        _terminate_process_tree(proc)


def run_protected_command(
    command: Sequence[str],
    *,
    timeout: float | None = _DEFAULT_TIMEOUT_SECONDS,
    cwd: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    stdin: IO[bytes] | None = None,
    check: bool = False,
    text: bool = False,
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess[Any]:  # Any: stdout and stderr depend on text mode.
    """Run a subprocess with strict security boundaries (SEC-001)."""
    copied_env = _copy_env(env)

    # Run the process
    popen_options: _PopenPlatformOptions = {}
    if os.name == "posix":
        popen_options["start_new_session"] = True
    elif os.name == "nt":
        popen_options["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    proc = subprocess.Popen(  # nosec B603 - see suppression registry
        list(command),
        cwd=cwd,
        env=copied_env,
        shell=False,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
        stdin=stdin,
        text=text,
        encoding=encoding,
        errors=errors,
        **popen_options,
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except BaseException:
        _cleanup_process(proc)
        raise

    output_encoding = encoding or locale.getpreferredencoding(False)
    if capture_output and (
        _output_size(stdout, encoding=output_encoding, errors=errors)
        > _MAX_OUTPUT_BYTES
        or _output_size(stderr, encoding=output_encoding, errors=errors)
        > _MAX_OUTPUT_BYTES
    ):
        raise subprocess.SubprocessError(
            f"Command output exceeds {_MAX_OUTPUT_BYTES} bytes"
        )

    retcode = proc.poll()
    if check and retcode:
        raise subprocess.CalledProcessError(
            retcode, proc.args, output=stdout, stderr=stderr
        )
    return subprocess.CompletedProcess(proc.args, retcode or 0, stdout, stderr)


def run_protected_subprocess_popen(
    command: Sequence[str],
    **kwargs: Unpack[_PopenReaderOptions],
) -> subprocess.Popen[bytes]:
    """Start a subprocess with strict security boundaries (SEC-001)."""
    kwargs["shell"] = False

    if "env" in kwargs:
        kwargs["env"] = _copy_env(kwargs["env"])

    return subprocess.Popen(  # nosec B603 - see suppression registry
        list(command),
        **kwargs,
    )
