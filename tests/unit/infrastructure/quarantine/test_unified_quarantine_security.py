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
"""Security tests for the UnifiedQuarantineAdapter component."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.types import QuarantineRecordStatus
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter


@pytest.fixture
def mock_delta_table():
    """Fixture for a mocked DeltaTable."""
    mock = MagicMock()
    with (
        patch("bioetl.infrastructure.quarantine.unified.DeltaTable", mock),
        patch("bioetl.infrastructure.quarantine._lifecycle.DeltaTable", mock),
    ):
        yield mock


@pytest.mark.security
def test_purge_handles_malicious_pipeline_name(mock_delta_table):
    """Test that purge method safely handles pipeline names with quotes."""
    mock_instance = mock_delta_table.return_value
    mock_arrow_table = MagicMock()
    mock_arrow_table.__len__ = MagicMock(return_value=1)
    mock_instance.to_pyarrow_table.return_value = mock_arrow_table

    quarantine = UnifiedQuarantineAdapter(base_path="/fake/path")
    malicious_name = "test-pipeline'; DROP TABLE common.quarantine; --"

    quarantine.purge(
        pipeline=malicious_name,
        older_than_days=30,
        now=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    # Verify that the predicate sent to Delta Lake is properly escaped
    args, _kwargs = mock_instance.delete.call_args
    predicate = args[0]  # predicate is passed as positional argument

    # Check that single quotes are properly escaped (single quote -> two single quotes)
    # This ensures the SQL injection attempt becomes a literal string value
    # Original: test-pipeline'; DROP TABLE...
    # Escaped:  test-pipeline''; DROP TABLE... (inside single quotes)
    assert "test-pipeline''" in predicate.lower()
    # The entire malicious payload should be enclosed in quotes as a literal value
    # not executed as a separate SQL statement
    assert predicate.lower().startswith("pipeline = '")


@pytest.mark.security
def test_update_status_handles_malicious_hash(mock_delta_table):
    """Test that update_status safely handles payload_hash with quotes."""
    mock_instance = mock_delta_table.return_value
    quarantine = UnifiedQuarantineAdapter(base_path="/fake/path")
    malicious_hash = "abc'; --"

    with (
        patch(
            "bioetl.infrastructure.quarantine.unified.read_delta_records",
            return_value=[{"payload_hash": malicious_hash}],
        ),
        patch(
            "bioetl.infrastructure.quarantine.unified.append_status_event"
        ) as append_mock,
    ):
        quarantine.update_status(
            payload_hash=malicious_hash, new_status=QuarantineRecordStatus.IGNORED
        )

    append_mock.assert_called_once_with(
        quarantine.status_events_path,
        None,
        payload_hash=malicious_hash,
        new_status=QuarantineRecordStatus.IGNORED,
    )
    mock_instance.update.assert_not_called()
