"""Coverage tranche tests for application-core span helpers (#6480)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from types import SimpleNamespace

from bioetl.application.core.pipeline_span_lifecycle import (
    build_pipeline_span_attributes,
    close_span,
    close_span_with_shutdown,
    start_current_span,
)


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}
        self.exceptions: list[BaseException] = []
        self.exited = False

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, error: BaseException) -> None:
        self.exceptions.append(error)

    def __enter__(self) -> _FakeSpan:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.exited = True


class _FakeTracer:
    def __init__(self, span: _FakeSpan) -> None:
        self._span = span

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object],
    ) -> _FakeSpan:
        self._span.attributes.update(attributes)
        self._span.attributes["span_name"] = name
        return self._span


class _FakeTracing:
    def __init__(self, span: _FakeSpan) -> None:
        self._tracer = _FakeTracer(span)

    def get_tracer(self, name: str) -> _FakeTracer:
        self._tracer_name = name
        return self._tracer


def test_build_pipeline_span_attributes_with_and_without_context() -> None:
    config = SimpleNamespace(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
    )
    runtime = SimpleNamespace(run_type=SimpleNamespace(value="full"))
    without_context = build_pipeline_span_attributes(config=config, runtime=runtime)
    assert without_context["bioetl.pipeline"] == "chembl_activity"
    assert "bioetl.run_id" not in without_context

    context = SimpleNamespace(run_id="run-1")
    with_context = build_pipeline_span_attributes(
        config=config,
        runtime=runtime,
        context=context,  # type: ignore[arg-type]
    )
    assert with_context["bioetl.run_id"] == "run-1"


def test_build_pipeline_span_attributes_uses_unknown_pipeline_fallback() -> None:
    config = SimpleNamespace(pipeline_name=None, provider="x", entity_type="y")
    runtime = SimpleNamespace(run_type=SimpleNamespace(value="smoke"))
    attributes = build_pipeline_span_attributes(config=config, runtime=runtime)
    assert attributes["bioetl.pipeline"] == "unknown"


def test_start_current_span_yields_span_with_attributes() -> None:
    span = _FakeSpan()
    tracing = _FakeTracing(span)
    with start_current_span(
        tracing=tracing,  # type: ignore[arg-type]
        tracer_name="bioetl.test",
        span_name="unit",
        attributes={"k": "v"},
    ) as active:
        assert active is span
        assert span.attributes["k"] == "v"
        assert span.attributes["span_name"] == "unit"


def test_close_span_paths() -> None:
    close_span(None)
    close_span(None, RuntimeError("x"))

    span = _FakeSpan()
    close_span(span)
    assert span.exited is True

    span_err = _FakeSpan()
    error = RuntimeError("boom")
    close_span(span_err, error)
    assert span_err.attributes["error"] is True
    assert span_err.exceptions == [error]
    assert span_err.exited is True


def test_close_span_with_shutdown_paths() -> None:
    close_span_with_shutdown(None)
    span = _FakeSpan()
    close_span_with_shutdown(span)
    assert span.attributes["bioetl.shutdown"] is True
    assert span.exited is True
