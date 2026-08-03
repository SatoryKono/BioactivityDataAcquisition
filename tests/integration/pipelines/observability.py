# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared observability test doubles for pipeline integration tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing


@dataclass
class RecordingLogger:
    """LoggerPort-compatible test double that records structured events."""

    context: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def bind(self, **kwargs: Any) -> Self:
        return type(self)(
            context={**self.context, **kwargs},
            events=self.events,
        )

    def _record(self, level: str, event: str, **kwargs: Any) -> None:
        self.events.append(
            {
                "level": level,
                "event": event,
                "context": dict(self.context),
                "kwargs": dict(kwargs),
            }
        )

    def info(self, event: str, **kwargs: Any) -> None:
        self._record("info", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._record("warning", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._record("error", event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._record("debug", event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        self._record("exception", event, **kwargs)


def build_test_logger() -> RecordingLogger:
    """Build a fresh LoggerPort test double."""
    return RecordingLogger()


def build_test_observability_bundle(
    *,
    logger: RecordingLogger | None = None,
) -> ObservabilityBundle:
    """Build a port-backed observability bundle for integration tests."""
    return ObservabilityBundle(
        logger=logger or build_test_logger(),
        metrics=NoOpMetrics(warn_on_use=False),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )
