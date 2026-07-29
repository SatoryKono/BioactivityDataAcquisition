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
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import bioetl.infrastructure.adapters.health_check_contract as contract_module
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters._health_check_observability import (
    handle_health_check_failure,
    handle_health_check_result,
    start_health_check,
)


pytestmark = pytest.mark.unit


def test_start_health_check_builds_context_with_elapsed_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter([10.0, 12.5])
    monkeypatch.setattr(contract_module.time, "monotonic", lambda: next(ticks))

    ctx = start_health_check(provider_name="crossref", endpoint="/works")

    assert ctx.provider == "crossref"
    assert ctx.endpoint == "/works"
    assert ctx.elapsed_seconds == pytest.approx(2.5)


@pytest.mark.parametrize(
    ("status", "expected_log", "expected_metric"),
    [
        (
            HealthStatus.HEALTHY,
            "health_check_passed",
            "bioetl_health_check_success_total",
        ),
        (
            HealthStatus.DEGRADED,
            "health_check_degraded",
            "bioetl_health_check_degraded_total",
        ),
        (
            HealthStatus.UNHEALTHY,
            "health_check_unhealthy",
            "bioetl_health_check_failures_total",
        ),
    ],
)
def test_handle_health_check_result_emits_status_specific_logs_and_metrics(
    status: HealthStatus,
    expected_log: str,
    expected_metric: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contract_module.time, "monotonic", lambda: 15.0)
    ctx = start_health_check(provider_name="openalex", endpoint="/health")
    ctx.start_time = 10.0
    logger = MagicMock()
    metrics = MagicMock()

    handle_health_check_result(
        logger=logger,
        metrics=metrics,
        ctx=ctx,
        status=status,
    )

    log_mock = logger.debug if status is HealthStatus.HEALTHY else logger.warning
    log_mock.assert_called_once()
    assert log_mock.call_args.args[0] == expected_log
    metrics.increment_counter.assert_called_once_with(
        expected_metric,
        1,
        {"provider": "openalex"},
    )
    metrics.observe_histogram.assert_called_once_with(
        "bioetl_health_check_latency_seconds",
        pytest.approx(5.0),
        {"provider": "openalex"},
    )


def test_handle_health_check_result_without_metrics_only_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contract_module.time, "monotonic", lambda: 11.0)
    ctx = start_health_check(provider_name="pubmed", endpoint="/health")
    ctx.start_time = 10.0
    logger = MagicMock()

    handle_health_check_result(
        logger=logger,
        metrics=None,
        ctx=ctx,
        status=HealthStatus.HEALTHY,
    )

    logger.debug.assert_called_once()


def test_handle_health_check_failure_logs_and_returns_unhealthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contract_module.time, "monotonic", lambda: 13.0)
    ctx = start_health_check(provider_name="semanticscholar", endpoint="/health")
    ctx.start_time = 10.0
    logger = MagicMock()
    metrics = MagicMock()

    result = handle_health_check_failure(
        logger=logger,
        metrics=metrics,
        ctx=ctx,
        error=RuntimeError("boom"),
    )

    assert result is HealthStatus.UNHEALTHY
    logger.warning.assert_called_once()
    metrics.increment_counter.assert_called_once_with(
        "bioetl_health_check_failures_total",
        1,
        {"provider": "semanticscholar"},
    )
    metrics.observe_histogram.assert_called_once_with(
        "bioetl_health_check_latency_seconds",
        pytest.approx(3.0),
        {"provider": "semanticscholar"},
    )
