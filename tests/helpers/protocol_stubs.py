"""Protocol-oriented test doubles for basedpyright (PD5-1 / #6996).

MagicMock without a Protocol annotation is not assignable to product Ports.
These lightweight stubs satisfy structural typing without I/O.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from bioetl.domain.types import BronzeRecord, HealthStatus, JsonDict

__all__ = [
    "AsyncEmptyDataSource",
    "RecordingLogger",
    "StubMetrics",
    "as_async_mock",
    "as_magic_mock",
    "protocol_mock",
]


def protocol_mock[T](protocol: type[T], **attrs: Any) -> T:
    """Return a MagicMock typed as ``protocol`` for assignability."""
    mock = MagicMock(spec=protocol)
    for key, value in attrs.items():
        setattr(mock, key, value)
    return mock  # type: ignore[return-value]


def as_magic_mock(value: Any = None, *, spec: type[Any] | None = None) -> Any:
    """MagicMock with optional spec, typed as Any for flexible test wiring."""
    if value is not None and spec is None:
        return MagicMock(wraps=value)
    return MagicMock(spec=spec) if spec is not None else MagicMock()


def as_async_mock(**kwargs: Any) -> Any:
    """AsyncMock typed as Any for coroutine Port methods."""
    return AsyncMock(**kwargs)


@dataclass
class RecordingLogger:
    """Minimal LoggerPort-shaped recorder for unit tests."""

    events: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)

    def bind(self, **kwargs: Any) -> RecordingLogger:
        del kwargs  # LoggerPort.bind contract; binder is intentionally identity
        return self

    def info(self, event: str, **kwargs: Any) -> None:
        self.events.append(("info", event, dict(kwargs)))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.events.append(("warning", event, dict(kwargs)))

    def error(self, event: str, **kwargs: Any) -> None:
        self.events.append(("error", event, dict(kwargs)))

    def debug(self, event: str, **kwargs: Any) -> None:
        self.events.append(("debug", event, dict(kwargs)))

    def exception(self, event: str, **kwargs: Any) -> None:
        self.events.append(("exception", event, dict(kwargs)))


@dataclass
class StubMetrics:
    """Minimal MetricsPort-shaped counter/histogram sink."""

    counters: dict[str, float] = field(default_factory=dict)
    histograms: dict[str, list[float]] = field(default_factory=dict)

    def increment_counter(
        self,
        name: str,
        amount: float = 1,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        del labels
        self.counters[name] = self.counters.get(name, 0.0) + amount

    def observe_histogram(
        self,
        name: str,
        amount: float,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        del labels
        self.histograms.setdefault(name, []).append(amount)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        del labels
        self.counters[name] = value


@dataclass
class AsyncEmptyDataSource:
    """Async empty DataSourcePort-shaped double."""

    entity_type: str = "test"
    provider_name: str = "test"

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        del entity_type, limit, query, filter_ids, filter_field, offset
        if False:  # pragma: no cover - typing aid for async generator
            yield {}
        return
        yield  # pragma: no cover

    async def health_check(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    def iter_empty(self) -> Iterator[JsonDict]:
        return iter(())
