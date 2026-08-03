# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for checkpoint compatibility telemetry helpers (#6478)."""

from __future__ import annotations

import pytest

from bioetl.application.services.checkpoint_compatibility_telemetry import (
    emit_checkpoint_compatibility_metric,
    log_lenient_checkpoint_compatibility_result,
    log_strict_checkpoint_compatibility_result,
)

pytestmark = pytest.mark.unit


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
    # Should complete without raising when metrics port is absent.
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
