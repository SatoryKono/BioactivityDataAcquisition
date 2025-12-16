"""Security tests for the UnifiedQuarantine component."""

from unittest.mock import MagicMock, patch

import pytest
from bioetl.domain.types import DQStatus
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine


@pytest.fixture
def mock_delta_table():
    """Fixture for a mocked DeltaTable."""
    with patch(
        "bioetl.infrastructure.quarantine.unified_quarantine.DeltaTable"
    ) as mock_dt:
        yield mock_dt


@pytest.mark.security
def test_purge_handles_malicious_pipeline_name(mock_delta_table):
    """Test that purge method safely handles pipeline names with quotes."""
    mock_instance = mock_delta_table.return_value
    mock_arrow_table = MagicMock()
    mock_arrow_table.__len__ = MagicMock(return_value=1)
    mock_instance.to_pyarrow_table.return_value = mock_arrow_table

    quarantine = UnifiedQuarantine(base_path="/fake/path")
    malicious_name = "test-pipeline'; DROP TABLE common.quarantine; --"

    quarantine.purge(pipeline=malicious_name, older_than_days=30)

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
    # Simulate that a record with the hash exists
    mock_arrow_table = MagicMock()
    mock_arrow_table.__len__.return_value = 1
    mock_instance.to_pyarrow_table.return_value = mock_arrow_table

    quarantine = UnifiedQuarantine(base_path="/fake/path")
    malicious_hash = "abc'; --"

    quarantine.update_status(payload_hash=malicious_hash, new_status=DQStatus.IGNORED)

    # Verify that the predicate is properly escaped
    _args, kwargs = mock_instance.update.call_args
    predicate = kwargs["predicate"]
    assert f"payload_hash = '{malicious_hash.replace("'", "''")}'" in predicate

    # Verify that the update value is also escaped
    updates = kwargs["updates"]
    assert f"'{DQStatus.IGNORED.value}'" in updates["dq_status"]
