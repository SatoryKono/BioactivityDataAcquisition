"""Failure-detail helpers for detached observability backend startup."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.request import build_opener


class _SupportsPoll(Protocol):
    """Minimal detached-process interface used for startup diagnostics."""

    def poll(self) -> int | None: ...


def _open_url(url: str, *, timeout: float) -> object:
    """Open one HTTP probe URL through a short-lived standard-library opener."""
    return build_opener().open(url, timeout=timeout)


def _read_backend_startup_log_excerpt(
    log_path: Path,
    *,
    max_lines: int = 8,
    max_chars: int = 1200,
) -> str | None:
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    nonempty_lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not nonempty_lines:
        return None
    excerpt = " || ".join(nonempty_lines[-max_lines:])
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
    urlopen_fn: Callable[..., object] = _open_url,
) -> str | None:
    if not required_probe_paths:
        return None
    base_url = _build_backend_base_url(health_url)
    raw_path = required_probe_paths[0]
    path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
    probe_url = f"{base_url}{path}"
    try:
        with urlopen_fn(probe_url, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
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
