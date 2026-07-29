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
"""Unit tests for immutable quarantine admin record views."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services._quarantine_models import QuarantineRecord

pytestmark = pytest.mark.unit


def test_quarantine_record_freezes_nested_payload_and_metadata() -> None:
    record = QuarantineRecord(
        error_code="DQ_INVALID",
        payload={"id": 1, "nested": {"tags": ["a", "b"]}},
        batch_id="batch-1",
        pipeline="chembl_activity",
        ingestion_ts=datetime(2026, 6, 19, 12, 0, tzinfo=UTC),
        metadata={"details": {"field": "title"}},
    )

    assert record.payload["id"] == 1
    assert record.payload["nested"]["tags"] == ("a", "b")
    assert record.metadata["details"]["field"] == "title"

    with pytest.raises(TypeError):
        record.payload["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        record.payload["nested"]["tags"] += ("c",)  # type: ignore[index]
    with pytest.raises(TypeError):
        record.metadata["details"]["field"] = "other"  # type: ignore[index]
