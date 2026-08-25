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
"""Tests for stable lineage fragment ID helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.lineage import (
    metadata_lineage_fragment_ids as fragment_ids,
)

pytestmark = pytest.mark.unit


def test_fragment_timestamp_uses_first_supplied_timestamp() -> None:
    first = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    second = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    assert fragment_ids.fragment_timestamp(None, first, second) == first


def test_fragment_id_timestamp_all_none_raises() -> None:
    with pytest.raises(RuntimeError, match="wall-clock fallback is not allowed"):
        fragment_ids.fragment_timestamp(None, None)


def test_build_fragment_id_preserves_none_slots() -> None:
    left = fragment_ids.build_fragment_id("src", "a", None)
    right = fragment_ids.build_fragment_id("src", None, "a")
    empty = fragment_ids.build_fragment_id("src", "a", "")

    assert left != right
    assert left != empty
