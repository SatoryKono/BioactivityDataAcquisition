"""Typed dependency contracts for observability backend startup."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, TypedDict


class _StartedBackendProcess(Protocol):
    @property
    def args(self) -> object: ...

    @property
    def pid(self) -> int | None: ...

    def poll(self) -> int | None: ...


class _ProbeFn(Protocol):
    def __call__(self, health_url: str) -> bool: ...


class _RequiredProbeFn(Protocol):
    def __call__(
        self,
        health_url: str,
        *,
        required_probe_paths: tuple[str, ...],
        timeout_seconds: float,
    ) -> bool: ...


class _StartFn(Protocol):
    def __call__(
        self,
        *,
        bind_host: str,
        port: int,
    ) -> _StartedBackendProcess: ...


class _WaitFn(Protocol):
    def __call__(
        self,
        health_url: str,
        *,
        timeout_seconds: float,
        poll_seconds: float,
        probe_fn: _ProbeFn,
    ) -> bool: ...


class _WaitRequiredPathsFn(Protocol):
    def __call__(
        self,
        health_url: str,
        *,
        required_probe_paths: tuple[str, ...],
        timeout_seconds: float,
        probe_timeout_seconds: float,
        poll_seconds: float,
        required_probe_fn: _RequiredProbeFn,
    ) -> bool: ...


class _DropStaleBackendFn(Protocol):
    def __call__(self, port: int) -> bool: ...


class _ListenerPidFn(Protocol):
    def __call__(self, port: int) -> int | None: ...


class _MessagePrinter(Protocol):
    def __call__(self, message: str) -> None: ...


class _BuildStartupFailureDetailFn(Protocol):
    def __call__(
        self,
        log_path: Path,
        *,
        process: _StartedBackendProcess | None = ...,
    ) -> str: ...


class _DescribeRequiredProbeFailureFn(Protocol):
    def __call__(
        self,
        health_url: str,
        *,
        required_probe_paths: tuple[str, ...],
        timeout_seconds: float,
    ) -> str | None: ...


class _AppendBackendStartupDiagnosticFn(Protocol):
    def __call__(
        self,
        log_path: Path,
        *,
        parent_pid: int,
        child_pid: int | None,
        command: Sequence[str],
        diagnostic_lines: Sequence[str],
    ) -> None: ...


class _PythonExecutableToTupleFn(Protocol):
    def __call__(self, args: object) -> tuple[str, ...]: ...


class _BackendResultConstructor[ResultT](Protocol):
    def __call__(
        self,
        *,
        status: str,
        health_url: str,
        pid: int | None = ...,
        command: tuple[str, ...] = ...,
        message: str | None = ...,
    ) -> ResultT: ...


class _ObservabilityBackendStartupKwargs(TypedDict):
    enabled: bool
    health_url: str
    startup_log_path: Path
    port: int
    bind_host: str
    ready_timeout_seconds: float
    required_probe_timeout_seconds: float
    poll_seconds: float
    required_probe_paths: tuple[str, ...]


class _ObservabilityBackendRuntimeHooks(TypedDict):
    probe_fn: _ProbeFn
    required_probe_fn: _RequiredProbeFn
    start_fn: _StartFn
    wait_fn: _WaitFn
    wait_required_paths_fn: _WaitRequiredPathsFn
    drop_stale_backend_fn: _DropStaleBackendFn
    listener_pid_fn: _ListenerPidFn
    info_printer: _MessagePrinter
    warning_printer: _MessagePrinter


class _ObservabilityBackendFailureHandlers(TypedDict):
    build_startup_failure_detail_fn: _BuildStartupFailureDetailFn
    describe_required_probe_failure_fn: _DescribeRequiredProbeFailureFn
    append_backend_startup_diagnostic_fn: _AppendBackendStartupDiagnosticFn
    python_executable_to_tuple_fn: _PythonExecutableToTupleFn
