"""Failure-detail helpers for detached observability backend startup."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import build_opener

from bioetl.domain.exceptions._redaction import _redact_string
from bioetl.interfaces.cli.commands.domains.health.observability_backend_probes import (
    _HttpProbeResponse,
    _UrlOpenFn,
)


class _SupportsPoll(Protocol):
    """Minimal detached-process interface used for startup diagnostics."""

    def poll(self) -> int | None: ...


class _ResponseOpener(Protocol):
    """Standard-library opener surface with a typed probe response."""

    def open(
        self,
        fullurl: str,
        data: bytes | None = None,
        timeout: float = ...,
    ) -> _HttpProbeResponse: ...


def _open_probe_response(
    opener: _ResponseOpener,
    url: str,
    *,
    timeout: float,
) -> _HttpProbeResponse:
    return opener.open(url, timeout=timeout)


def _open_url(url: str, *, timeout: float) -> _HttpProbeResponse:
    """Open one HTTP probe URL through a short-lived standard-library opener."""
    return _open_probe_response(build_opener(), url, timeout=timeout)


def _read_backend_startup_log_excerpt(
    log_path: Path,
    *,
    max_lines: int = 8,
    max_chars: int = 1200,
) -> str | None:
    max_read_bytes = min(max(max_chars * 4, 4096), 64 * 1024)
    try:
        with log_path.open("rb") as stream:
            stream.seek(0, 2)
            file_size = stream.tell()
            stream.seek(max(0, file_size - max_read_bytes))
            content = stream.read(max_read_bytes).decode("utf-8", errors="replace")
    except OSError:
        return None
    nonempty_lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not nonempty_lines:
        return None
    excerpt = _redact_string(" || ".join(nonempty_lines[-max_lines:]))
    if len(excerpt) > max_chars:
        excerpt = f"...{excerpt[-max_chars:]}"
    return excerpt


def _build_startup_failure_detail(
    log_path: Path,
    *,
    process: _SupportsPoll | None = None,
) -> str:
    details: list[str] = [f"Startup log: {log_path}."]
    if process is not None and hasattr(process, "poll"):
        exit_code = process.poll()
        if isinstance(exit_code, int):
            details.append(f"Exit code: {exit_code}.")
    excerpt = _read_backend_startup_log_excerpt(log_path)
    if excerpt:
        details.append(f"Tail: {excerpt}")
    return " ".join(details)


def _build_backend_base_url(health_url: str) -> str:
    if health_url.endswith("/health"):
        return health_url[: -len("/health")]
    return health_url.rstrip("/")


def _append_backend_startup_diagnostic(
    log_path: Path,
    *,
    parent_pid: int,
    child_pid: int | None,
    command: Sequence[str],
    diagnostic_lines: Sequence[str],
) -> None:
    """Append parent/child/process diagnostics to one backend startup log."""
    rendered_command = " ".join(command) if command else "<unknown>"
    sections = [
        "",
        "=== BioETL detached backend diagnostics ===",
        f"parent_pid={parent_pid}",
        f"child_pid={child_pid if child_pid is not None else '<unknown>'}",
        f"command={rendered_command}",
    ]
    sections.extend(line for line in diagnostic_lines if line.strip())
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(sections))
            handle.write("\n")
    except OSError:
        return


def _describe_required_probe_failure(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = 1.0,
    urlopen_fn: _UrlOpenFn = _open_url,
) -> str | None:
    if not required_probe_paths:
        return None
    base_url = _build_backend_base_url(health_url)
    for raw_path in required_probe_paths:
        path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        failure = _probe_required_path(
            f"{base_url}{path}",
            timeout_seconds=timeout_seconds,
            urlopen_fn=urlopen_fn,
        )
        if failure is not None:
            return failure
    return None


def _probe_required_path(
    probe_url: str,
    *,
    timeout_seconds: float,
    urlopen_fn: _UrlOpenFn,
) -> str | None:
    """Return one capability-probe failure, or None for a healthy path."""
    try:
        with urlopen_fn(probe_url, timeout=timeout_seconds) as response:
            status = response.status
            if status < 400:
                return None
            return f"Capability probe {probe_url} returned HTTP {status}."
    except HTTPError as exc:
        body_excerpt = ""
        try:
            raw_body = exc.read().decode("utf-8", errors="replace").strip()
        except OSError:
            raw_body = ""
        if raw_body:
            body_excerpt = f" body={raw_body[:400]!r}"
        return (
            f"Capability probe {probe_url} returned HTTP {exc.code} {exc.reason}."
            f"{body_excerpt}"
        )
    except URLError as exc:
        return f"Capability probe {probe_url} failed: {exc.reason}."
    except OSError as exc:
        return f"Capability probe {probe_url} failed: {exc}."
    except ValueError as exc:
        return f"Capability probe {probe_url} failed: {exc}."


__all__ = [
    "_append_backend_startup_diagnostic",
    "_build_startup_failure_detail",
    "_describe_required_probe_failure",
    "_open_url",
    "_read_backend_startup_log_excerpt",
]
