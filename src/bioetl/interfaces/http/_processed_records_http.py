"""Typed standard-library HTTP seam for Processed Records metrics."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, cast
from urllib.request import build_opener


class _UrlResponse(Protocol):
    """Minimal context-managed response contract used by Prometheus reads."""

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    def read(self) -> bytes: ...


def open_url(url: str, *, timeout: float) -> _UrlResponse:
    """Open one URL through a short-lived standard-library opener."""
    return cast(_UrlResponse, build_opener().open(url, timeout=timeout))
