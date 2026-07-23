"""Unit tests for checkpoint compatibility telemetry helpers (#6478)."""

from __future__ import annotations

from bioetl.application.services.checkpoint_compatibility_telemetry import (
    emit_checkpoint_compatibility_metric,
    log_lenient_checkpoint_compatibility_result,
    log_strict_checkpoint_compatibility_result,
)


class _Logger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, dict[str, object]]] = []
        self.warning_calls: list[tuple[str, dict[str, object]]] = []

    def info(self, message: str, **kwargs: object) -> None:
        self.info_calls.append((message, kwargs))

    def warning(self, message: str, **kwargs: object) -> None:
        self.warning_calls.append((message, kwargs))


class _Metrics:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, str]]] = []

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        self.calls.append((name, value, labels))


def test_emit_checkpoint_compatibility_metric_noop_without_metrics() -> None:
    emit_checkpoint_compatibility_metric(
        None,
        pipeline_name="chembl_activity",
        disposition="strict_compatible",
    )


def test_emit_checkpoint_compatibility_metric_uses_unknown_pipeline_fallback() -> None:
    metrics = _Metrics()
    emit_checkpoint_compatibility_metric(
        metrics,  # type: ignore[arg-type]
        pipeline_name=None,
        disposition="lenient_compatible",
    )
    assert metrics.calls == [
        (
            "bioetl_checkpoint_compatibility_events_total",
            1,
            {"pipeline": "unknown", "disposition": "lenient_compatible"},
        )
    ]


def test_log_strict_and_lenient_results() -> None:
    logger = _Logger()
    log_strict_checkpoint_compatibility_result(
        logger,  # type: ignore[arg-type]
        compatible=True,
        messages=["ok"],
    )
    log_strict_checkpoint_compatibility_result(
        logger,  # type: ignore[arg-type]
        compatible=False,
        messages=["bad"],
    )
    log_lenient_checkpoint_compatibility_result(
        logger,  # type: ignore[arg-type]
        compatible=True,
        messages=["ok-lenient"],
    )
    log_lenient_checkpoint_compatibility_result(
        logger,  # type: ignore[arg-type]
        compatible=False,
        messages=["bad-lenient"],
    )
    assert len(logger.info_calls) == 2
    assert len(logger.warning_calls) == 2
