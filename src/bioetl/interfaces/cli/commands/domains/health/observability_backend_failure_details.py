"""Failure-detail helpers for detached observability backend startup."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Callable


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
    process: subprocess.Popen[bytes] | None = None,
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


def _describe_required_probe_failure(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = 1.0,
    urlopen_fn: Callable[..., object] = urlopen,
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
    "_build_startup_failure_detail",
    "_describe_required_probe_failure",
    "_read_backend_startup_log_excerpt",
]
