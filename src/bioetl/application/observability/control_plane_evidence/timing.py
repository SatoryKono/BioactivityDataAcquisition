"""Request-local evidence stage observations, propagated through to_thread."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter

StageObserver = Callable[[str, float], None]
_observer: ContextVar[StageObserver | None] = ContextVar("evidence_stage_observer", default=None)


@contextmanager
def observe_evidence_stages(observer: StageObserver) -> Iterator[None]:
    """Bind an observer to this request without affecting concurrent requests."""
    token = _observer.set(observer)
    try:
        yield
    finally:
        _observer.reset(token)


@contextmanager
def evidence_stage(name: str) -> Iterator[None]:
    """Measure a stage when the caller requested diagnostics, including failures."""
    observer = _observer.get()
    started = perf_counter()
    try:
        yield
    finally:
        if observer is not None:
            observer(name, perf_counter() - started)
