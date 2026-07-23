"""Probe and readiness helpers for the observability backend."""

from __future__ import annotations

import time
from types import TracebackType
from typing import TYPE_CHECKING, Protocol, Self
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

_HEALTH_PATH_SUFFIX = "/health"


if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS = 20.0
DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS = 60.0
DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS = 5.0
DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS = 0.25


class _HttpProbeResponse(Protocol):
    """HTTP response surface consumed by observability probes."""

    @property
    def status(self) -> int: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


class _UrlOpenFn(Protocol):
    """Callable contract for opening one observability probe URL."""

    def __call__(self, url: str, *, timeout: float) -> _HttpProbeResponse: ...


def _build_observability_backend_probe_urls(health_url: str) -> tuple[str, ...]:
    """Return canonical readiness probe URLs for one backend base health URL."""
    return (
        (f"{health_url}/live", health_url)
        if health_url.endswith(_HEALTH_PATH_SUFFIX)
        else (health_url,)
    )


def probe_observability_backend(
    health_url: str,
    *,
    timeout_seconds: float = 1.0,
    urlopen_fn: _UrlOpenFn = urlopen,
) -> bool:
    """Return True when the observability backend responds successfully."""
    for probe_url in _build_observability_backend_probe_urls(health_url):
        try:
            with urlopen_fn(probe_url, timeout=timeout_seconds) as response:
                if response.status < 400:
                    return True
        except (HTTPError, URLError, OSError, ValueError):
            continue
    return False


def probe_observability_backend_required_paths(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = 1.0,
    urlopen_fn: _UrlOpenFn = urlopen,
) -> bool:
    """Return True when the backend exposes all required HTTP capability paths."""
    if not required_probe_paths:
        return True
    base_url = (
        health_url[: -len(_HEALTH_PATH_SUFFIX)]
        if health_url.endswith(_HEALTH_PATH_SUFFIX)
        else health_url.rstrip("/")
    )
    for raw_path in required_probe_paths:
        path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        try:
            with urlopen_fn(f"{base_url}{path}", timeout=timeout_seconds) as response:
                if response.status >= 400:
                    return False
        except (HTTPError, URLError, OSError, ValueError):
            return False
    return True


def wait_for_observability_backend_ready(
    health_url: str,
    *,
    timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    probe_fn: Callable[..., bool] = probe_observability_backend,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Poll the backend health URL until it responds or timeout expires."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if probe_fn(health_url):
            return True
        sleep_fn(poll_seconds)
    return probe_fn(health_url)


def wait_for_observability_backend_required_paths_ready(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    probe_timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    required_probe_fn: Callable[..., bool] = probe_observability_backend_required_paths,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Poll backend capability routes until they respond or timeout expires."""
    if not required_probe_paths:
        return True
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if required_probe_fn(
            health_url,
            required_probe_paths=required_probe_paths,
            timeout_seconds=probe_timeout_seconds,
        ):
            return True
        sleep_fn(poll_seconds)
    return required_probe_fn(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=probe_timeout_seconds,
    )


__all__ = [
    "DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS",
    "_build_observability_backend_probe_urls",
    "probe_observability_backend",
    "probe_observability_backend_required_paths",
    "wait_for_observability_backend_ready",
    "wait_for_observability_backend_required_paths_ready",
]
