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
"""Unit tests for SystemClock infrastructure adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.ports import ClockPort
from bioetl.infrastructure.time import SystemClock


@pytest.mark.unit
def test_system_clock_implements_clock_port() -> None:
    """SystemClock satisfies ClockPort contract."""
    clock = SystemClock()
    assert isinstance(clock, ClockPort)


@pytest.mark.unit
def test_system_clock_returns_utc_aware_datetime() -> None:
    """SystemClock.now returns timezone-aware UTC datetime."""
    clock = SystemClock()
    value = clock.now()

    assert isinstance(value, datetime)
    assert value.tzinfo is UTC


@pytest.mark.unit
def test_system_clock_now_uses_system_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SystemClock.now converts the current POSIX timestamp to UTC."""
    clock = SystemClock()
    expected = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    fixed_timestamp = expected.timestamp()
    monkeypatch.setattr(
        "bioetl.infrastructure.time.system_clock.time.time", lambda: fixed_timestamp
    )

    assert clock.now() == expected


@pytest.mark.unit
def test_current_utc_time_uses_system_clock_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ restore #9793: current_utc_time must go through SystemClock."""
    from bioetl.infrastructure.time.system_clock import current_utc_time

    expected = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "bioetl.infrastructure.time.system_clock.time.time",
        lambda: expected.timestamp(),
    )
    assert current_utc_time() == expected
