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
"""Unit tests for file-backed control-plane durability policy."""

from __future__ import annotations

import pytest

import bioetl.infrastructure.control_plane._durability as durability

pytestmark = pytest.mark.unit


def test_durability_policy_should_fsync_control_plane_writes_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("BIOETL_TEST_MODE", raising=False)
    durability.get_settings.cache_clear()
    try:
        assert durability.should_fsync_control_plane_writes(os_name="nt") is True
    finally:
        durability.get_settings.cache_clear()


def test_should_skip_fsync_for_windows_test_mode__control_plane_durability(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    durability.get_settings.cache_clear()
    try:
        assert durability.should_fsync_control_plane_writes(os_name="nt") is False
    finally:
        durability.get_settings.cache_clear()


def test_non_windows_keeps_fsync_even_in_test_mode(monkeypatch) -> None:
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    durability.get_settings.cache_clear()
    try:
        assert durability.should_fsync_control_plane_writes(os_name="posix") is True
    finally:
        durability.get_settings.cache_clear()


def test_flush_file_descriptor_skips_fsync_when_policy_is_relaxed(
    monkeypatch,
) -> None:
    fsync_calls: list[int] = []

    monkeypatch.setattr(
        durability,
        "should_fsync_control_plane_writes",
        lambda: False,
    )
    monkeypatch.setattr(durability.os, "fsync", fsync_calls.append)

    durability.flush_control_plane_file_descriptor(42)

    assert fsync_calls == []
