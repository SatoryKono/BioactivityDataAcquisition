# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
"""Focused coverage for context field binding (#8614)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.composition.runtime_builders._context_field_binding import (
    bind_context_fields,
)


@dataclass(frozen=True, slots=True)
class _Ctx:
    pipeline: str
    limit: int = 1


class _KwargHost:
    def __init__(self, *, pipeline: str, limit: int = 1) -> None:
        self.pipeline = pipeline
        self.limit = limit


class _NoKwargHost:
    def __init__(self) -> None:
        self.pipeline = "seed"
        self.limit = 0


def test_bind_context_fields_empty_updates_returns_same_instance() -> None:
    ctx = _Ctx(pipeline="activity")
    assert bind_context_fields(ctx, updates={}, unsupported_message="bad") is ctx


def test_bind_context_fields_dataclass_replace() -> None:
    ctx = _Ctx(pipeline="activity", limit=1)
    out = bind_context_fields(
        ctx,
        updates={"limit": 9},
        unsupported_message="bad",
    )
    assert out is not ctx
    assert out == _Ctx(pipeline="activity", limit=9)


def test_bind_context_fields_dataclass_unknown_field_raises() -> None:
    ctx = _Ctx(pipeline="activity")
    with pytest.raises(TypeError, match="unknown context fields"):
        bind_context_fields(
            ctx,
            updates={"missing": 1},
            unsupported_message="unsupported context host",
        )


def test_bind_context_fields_kwargs_host_copy() -> None:
    host = _KwargHost(pipeline="activity", limit=2)
    out = bind_context_fields(
        host,
        updates={"limit": 5},
        unsupported_message="unsupported context host",
    )
    assert out is not host
    assert out.pipeline == "activity"
    assert out.limit == 5
    assert host.limit == 2


def test_bind_context_fields_no_kwargs_host_uses_setattr_clone() -> None:
    host = _NoKwargHost()
    out = bind_context_fields(
        host,
        updates={"pipeline": "assay"},
        unsupported_message="unsupported context host",
    )
    assert out is not host
    assert out.pipeline == "assay"
    assert host.pipeline == "seed"


def test_bind_context_fields_unsupported_host_raises() -> None:
    with pytest.raises(TypeError, match="unsupported context host"):
        bind_context_fields(
            42,  # type: ignore[arg-type]
            updates={"x": 1},
            unsupported_message="unsupported context host",
        )


class _InitRejectsKwargs:
    """Constructor rejects kwargs so bind falls back to object.__new__ + setattr."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        if args or kwargs:
            raise TypeError("no kwargs")
        self.pipeline = "seed"
        self.limit = 0


def test_bind_context_fields_init_reject_kwargs_uses_object_new_clone() -> None:
    host = _InitRejectsKwargs()
    out = bind_context_fields(
        host,
        updates={"pipeline": "target"},
        unsupported_message="unsupported context host",
    )
    assert out is not host
    assert out.pipeline == "target"
    assert host.pipeline == "seed"


def test_bind_context_fields_setattr_failure_raises_unsupported() -> None:
    class _SlotsOnly:
        __slots__ = ("pipeline",)

        def __init__(self, pipeline: str = "seed") -> None:
            self.pipeline = pipeline

    host = _SlotsOnly()
    # Constructor rejects unknown kwarg "limit"; fallback setattr also cannot set it.
    with pytest.raises(TypeError, match="unsupported context host"):
        bind_context_fields(
            host,
            updates={"limit": 9},
            unsupported_message="unsupported context host",
        )
